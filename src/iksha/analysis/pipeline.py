"""
Core analysis pipeline for IKSHA.

Coordinates project sources, parsers, dependency resolvers, the
dependency graph, and reachability analysis without putting
language-specific logic into the orchestration layer.
"""

from dataclasses import dataclass, field

from iksha.analysis.entry_points import EntryPointResolver
from iksha.analysis.reachability import ReachabilityAnalyzer
from iksha.analysis.reachability_result import ReachabilityResult
from iksha.config.loader import load_config
from iksha.config.model import Config
from iksha.dependency.registry import ResolverRegistry
from iksha.dependency.result import ResolutionResult
from iksha.domain.file import File
from iksha.domain.project import Project
from iksha.domain.reference import (
    FILE_DEPENDENCY_KINDS,
    Reference,
    ReferenceKind,
)
from iksha.domain.resolution import ResolutionStatus
from iksha.graph.dependency import DependencyGraph
from iksha.parsing.registry import ParserRegistry
from iksha.parsing.result import Diagnostic, Observation
from iksha.parsing.html_document import HtmlDocument
from iksha.references.extractor import ReferenceExtractor
from iksha.source.loader import SourceLoader
from iksha.analysis.selector_usage_result import SelectorUsageResult
from iksha.analysis.selector_usage import (
    SelectorUsage,
    analyze_selector_usage,
)


@dataclass
class AnalysisResult:
    """Complete result produced by one pipeline execution."""

    graph: DependencyGraph = field(
        default_factory=DependencyGraph
    )

    unresolved: list[ResolutionResult] = field(
        default_factory=list
    )

    diagnostics: list[Diagnostic] = field(
        default_factory=list
    )

    observations: list[Observation] = field(
        default_factory=list
    )
    html_documents: dict[File, HtmlDocument] = field(
        default_factory=dict
    )

    references: list[Reference] = field(
        default_factory=list
    )
    selector_usage: SelectorUsageResult = field(
        default_factory=SelectorUsageResult
    )
    reachability: ReachabilityResult | None = None

    config: Config | None = None


class AnalysisPipeline:
    """
    Orchestrates the IKSHA analysis process.

    Responsibilities:

    - iterate authoritative project files
    - load source documents
    - select parsers
    - parse source
    - resolve supported references
    - construct the dependency graph
    - resolve configured entry points
    - classify file reachability
    - preserve unresolved references and diagnostics

    The pipeline itself contains no language-specific parsing rules.
    """

    def __init__(
        self,
        project: Project,
        source_loader: SourceLoader,
        parser_registry: ParserRegistry,
        resolver_registry: ResolverRegistry,
        config: Config | None = None,
        config_diagnostics: list[Diagnostic] | None = None,
    ) -> None:
        self.project = project
        self.source_loader = source_loader
        self.parser_registry = parser_registry
        self.resolver_registry = resolver_registry
        self.config = (
            config
            if config is not None
            else load_config(project.root).config
        )
        self.config_diagnostics = list(
            config_diagnostics or ()
        )

    def run(self) -> AnalysisResult:
        """Run a fresh analysis of the project."""

        result = AnalysisResult(
            config=self.config,
            diagnostics=list(self.config_diagnostics),
        )

        # Ensure every resolver uses the authoritative File objects
        # belonging to this Project.
        self.resolver_registry.index_files(
            list(self.project.files.values())
        )

        extractor = ReferenceExtractor(
            self.project,
            self.resolver_registry,
        )

        for file in self._project_files():
            parser = self.parser_registry.get(
                file.file_type
            )

            if parser is None:
                continue

            document = self.source_loader.load(file)

            if not document.success:
                result.diagnostics.append(
                    Diagnostic(
                        message=(
                            document.error
                            or "Source document could not be loaded"
                        ),
                        severity="error",
                        source=file,
                    )
                )
                continue

            if document.truncated:
                result.diagnostics.append(
                    Diagnostic(
                        message=(
                            "File exceeds maxFileSizeMB and was truncated"
                        ),
                        severity="warning",
                        source=file,
                    )
                )

            parse_result = parser.parse(
                file,
                document,
            )
            if file.file_type == "html":
                result.html_documents[file] = (
                    parser.parse_document(
                        file,
                        document,
                    )
                )
            result.diagnostics.extend(
                parse_result.diagnostics
            )
            result.observations.extend(
                parse_result.observations
            )

            for observation in parse_result.observations:
                reference = extractor.extract(observation)

                if reference is None:
                    continue

                result.references.append(reference)

                if (
                    reference.resolved
                    and reference.target is not None
                ):
                    result.graph.add(
                        source=file,
                        target=reference.target,
                        observation=observation,
                    )
                    continue

                if (
                    reference.kind in FILE_DEPENDENCY_KINDS
                    and reference.status
                    is not ResolutionStatus.EXTERNAL
                ):
                    result.unresolved.append(
                        ResolutionResult(
                            observation=observation,
                            target=reference.target,
                        )
                    )
        result.selector_usage = self._analyze_selector_usage(
            result.observations,
            result.html_documents,
        )
        entry_points = EntryPointResolver(
            self.project,
        ).resolve(
            self.config.entry_points,
        )

        result.reachability = ReachabilityAnalyzer(
            result.graph,
        ).analyze(
            entry_points=entry_points,
            files=list(self.project.files.values()),
        )

        return result

    def _project_files(self):
        """Return project files in deterministic order."""

        return sorted(
            self.project.files.values(),
            key=lambda file: (
                file.relative_path.lower(),
                file.relative_path,
            ),
        )
    def _analyze_selector_usage(
        self,
        observations: list[Observation],
        html_documents: dict[File, HtmlDocument],
    ) -> SelectorUsageResult:
        """Correlate CSS selector observations with usage evidence."""

        usage_observations = [
            observation
            for observation in observations
            if observation.kind in {
                ReferenceKind.CLASS,
                ReferenceKind.ID,
            }
        ]

        result: dict[File, tuple[SelectorUsage, ...]] = {}

        for file in self._project_files():
            if file.file_type != "css":
                continue

            selectors = [
                observation
                for observation in observations
                if (
                    observation.source is file
                    and observation.kind
                    is ReferenceKind.DOM_SELECTOR
                )
            ]

            if not selectors:
                continue

            result[file] = tuple(
                analyze_selector_usage(
                    selector.value,
                    usage_observations,
                    html_documents=html_documents,
                )
                for selector in selectors
            )

        return SelectorUsageResult(
            by_file=result,
        )