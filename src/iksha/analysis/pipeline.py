"""
Core analysis pipeline for IKSHA.

Coordinates project sources, parsers, dependency resolvers, and the
dependency graph without putting language-specific logic into the
orchestration layer.
"""

from dataclasses import dataclass, field

from iksha.config.loader import load_config
from iksha.config.model import Config
from iksha.dependency.php_resolver import (
    PHPDependencyResolver,
    ResolutionResult,
)
from iksha.domain.project import Project
from iksha.graph.dependency import DependencyGraph
from iksha.parsing.registry import ParserRegistry
from iksha.parsing.result import Diagnostic
from iksha.source.loader import SourceLoader


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
    - preserve unresolved references and diagnostics

    The pipeline itself contains no language-specific parsing rules.
    """

    def __init__(
        self,
        project: Project,
        source_loader: SourceLoader,
        parser_registry: ParserRegistry,
        dependency_resolver: PHPDependencyResolver,
        config: Config | None = None,
        config_diagnostics: list[Diagnostic] | None = None,
    ) -> None:
        self.project = project
        self.source_loader = source_loader
        self.parser_registry = parser_registry
        self.dependency_resolver = dependency_resolver
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

        # Ensure the resolver uses the authoritative File objects
        # belonging to this Project.
        self.dependency_resolver.index_files(
            list(self.project.files.values())
        )

        for file in self._project_files():
            parser = self.parser_registry.get(
                file.file_type
            )

            if parser is None:
                continue

            document = self.source_loader.load(file.path)

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

            parse_result = parser.parse(
                file,
                document,
            )

            result.diagnostics.extend(
                parse_result.diagnostics
            )

            resolutions = (
                self.dependency_resolver.resolve_all(
                    parse_result.observations
                )
            )

            for resolution in resolutions:
                if resolution.resolved:
                    result.graph.add(
                        source=file,
                        target=resolution.target,
                        observation=resolution.observation,
                    )
                else:
                    result.unresolved.append(
                        resolution
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

