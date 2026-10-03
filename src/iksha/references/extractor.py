"""
Reference extraction for IKSHA.

Turns parser observations into References with resolution status,
strategy, and (when possible) an authoritative project File target.
"""

from pathlib import Path

from iksha.dependency.php_resolver import PHPDependencyResolver
from iksha.domain.confidence import ConfidenceScore
from iksha.domain.evidence import Evidence
from iksha.domain.file import File
from iksha.domain.identity import (
    is_external_reference,
    normalize_reference_path,
)
from iksha.domain.project import Project
from iksha.domain.reference import (
    FILE_DEPENDENCY_KINDS,
    Reference,
    ReferenceKind,
    ResolutionStatus,
    ResolutionStrategy,
)
from iksha.domain.states import Confidence
from iksha.parsing.result import Observation
from iksha.parsing.support import looks_dynamic


class ReferenceExtractor:
    """
    Extract and resolve references from parser observations.

    File-to-file references are resolved against the project inventory.
    Usage evidence (class/ID/selector) is recorded without inventing
    a filesystem target.
    """

    def __init__(
        self,
        project: Project,
        php_resolver: PHPDependencyResolver,
    ) -> None:
        self.project = project
        self.php_resolver = php_resolver

    def extract(
        self,
        observation: Observation,
    ) -> Reference | None:
        """Build one Reference from a parser observation."""

        if observation.source is None:
            return None

        if self.php_resolver.handles(observation):
            return self._extract_php(observation)

        if observation.kind in FILE_DEPENDENCY_KINDS:
            return self._extract_file_reference(observation)

        return self._extract_usage(observation)

    def extract_all(
        self,
        observations: list[Observation],
    ) -> list[Reference]:
        """Extract references while preserving observation order."""

        references: list[Reference] = []

        for observation in observations:
            reference = self.extract(observation)

            if reference is not None:
                references.append(reference)

        return references

    def _extract_php(
        self,
        observation: Observation,
    ) -> Reference:
        resolution = self.php_resolver.resolve(observation)
        raw = observation.value
        normalized = normalize_reference_path(raw)
        dynamic = looks_dynamic(raw) or (
            observation.confidence is Confidence.UNKNOWN
            and resolution.target is None
            and normalized is None
        )

        if resolution.target is not None:
            return self._reference(
                observation,
                raw=raw,
                normalized=normalized or raw,
                target=resolution.target,
                strategy=ResolutionStrategy.SOURCE_RELATIVE,
                status=ResolutionStatus.RESOLVED,
            )

        if dynamic or looks_dynamic(raw):
            return self._reference(
                observation,
                raw=raw,
                normalized=normalized,
                strategy=ResolutionStrategy.DYNAMIC,
                status=ResolutionStatus.DYNAMIC,
            )

        return self._reference(
            observation,
            raw=raw,
            normalized=normalized or raw,
            strategy=ResolutionStrategy.SOURCE_RELATIVE,
            status=ResolutionStatus.UNRESOLVED,
        )

    def _extract_file_reference(
        self,
        observation: Observation,
    ) -> Reference:
        raw = observation.value.strip()
        source = observation.source

        if is_external_reference(raw):
            return self._reference(
                observation,
                raw=raw,
                normalized=None,
                strategy=ResolutionStrategy.URL,
                status=ResolutionStatus.EXTERNAL,
            )

        if not raw or looks_dynamic(raw):
            return self._reference(
                observation,
                raw=raw,
                normalized=None,
                strategy=ResolutionStrategy.DYNAMIC,
                status=ResolutionStatus.DYNAMIC,
            )

        normalized = normalize_reference_path(raw)

        if not normalized:
            return self._reference(
                observation,
                raw=raw,
                normalized=None,
                strategy=ResolutionStrategy.UNKNOWN,
                status=ResolutionStatus.UNRESOLVED,
            )

        strategy = self._strategy_for(
            raw,
            normalized,
            observation.kind,
            source,
        )

        return self._resolve_local_path(
            observation,
            raw=raw,
            normalized=normalized,
            strategy=strategy,
        )

    def _extract_usage(
        self,
        observation: Observation,
    ) -> Reference:
        raw = observation.value
        dynamic = (
            looks_dynamic(raw)
            or observation.confidence is Confidence.UNKNOWN
        )

        return self._reference(
            observation,
            raw=raw,
            normalized=raw.strip() or None,
            strategy=(
                ResolutionStrategy.DYNAMIC
                if dynamic
                else ResolutionStrategy.UNKNOWN
            ),
            status=(
                ResolutionStatus.DYNAMIC
                if dynamic
                else ResolutionStatus.UNRESOLVED
            ),
        )

    def _strategy_for(
        self,
        raw: str,
        normalized: str,
        kind: ReferenceKind,
        source: File,
    ) -> ResolutionStrategy:
        if _is_absolute_path(normalized):
            return ResolutionStrategy.ABSOLUTE

        stripped = raw.strip().replace("\\", "/")

        if stripped.startswith("/"):
            return ResolutionStrategy.PROJECT_RELATIVE

        if (
            kind is ReferenceKind.IMPORT
            and source.file_type == "css"
        ):
            return ResolutionStrategy.IMPORT_RELATIVE

        return ResolutionStrategy.SOURCE_RELATIVE

    def _resolve_local_path(
        self,
        observation: Observation,
        *,
        raw: str,
        normalized: str,
        strategy: ResolutionStrategy,
    ) -> Reference:
        source = observation.source
        used_strategy = strategy

        source_hit = self._source_relative_target(source, normalized)
        project_hit = self._project_relative_target(normalized)
        absolute_hit = self._absolute_target(normalized)

        if strategy is ResolutionStrategy.ABSOLUTE and absolute_hit:
            return self._reference(
                observation,
                raw=raw,
                normalized=normalized,
                target=absolute_hit,
                strategy=strategy,
                status=ResolutionStatus.RESOLVED,
            )

        if (
            source_hit is not None
            and project_hit is not None
            and source_hit is not project_hit
            and not normalized.startswith("/")
            and "/" not in normalized
        ):
            return self._reference(
                observation,
                raw=raw,
                normalized=normalized,
                strategy=ResolutionStrategy.UNKNOWN,
                status=ResolutionStatus.AMBIGUOUS,
                candidates=(source_hit, project_hit),
            )

        if strategy is ResolutionStrategy.PROJECT_RELATIVE:
            if project_hit is not None:
                return self._reference(
                    observation,
                    raw=raw,
                    normalized=normalized,
                    target=project_hit,
                    strategy=strategy,
                    status=ResolutionStatus.RESOLVED,
                )
        elif source_hit is not None:
            return self._reference(
                observation,
                raw=raw,
                normalized=normalized,
                target=source_hit,
                strategy=used_strategy,
                status=ResolutionStatus.RESOLVED,
            )
        elif project_hit is not None:
            return self._reference(
                observation,
                raw=raw,
                normalized=normalized,
                target=project_hit,
                strategy=ResolutionStrategy.PROJECT_RELATIVE,
                status=ResolutionStatus.RESOLVED,
            )

        if "/" not in normalized:
            named = list(self.project.files_named(Path(normalized).name))

            if len(named) > 1:
                return self._reference(
                    observation,
                    raw=raw,
                    normalized=normalized,
                    strategy=ResolutionStrategy.UNKNOWN,
                    status=ResolutionStatus.AMBIGUOUS,
                    candidates=tuple(named),
                )

            if len(named) == 1:
                return self._reference(
                    observation,
                    raw=raw,
                    normalized=normalized,
                    target=named[0],
                    strategy=ResolutionStrategy.UNKNOWN,
                    status=ResolutionStatus.RESOLVED,
                )

        return self._reference(
            observation,
            raw=raw,
            normalized=normalized,
            strategy=strategy,
            status=ResolutionStatus.UNRESOLVED,
        )

    def _source_relative_target(
        self,
        source: File,
        normalized: str,
    ) -> File | None:
        try:
            path = (source.path.parent / normalized).resolve()
        except (OSError, RuntimeError, ValueError):
            return None

        if not self._inside_project(path):
            return None

        return self.project.get_file(path)

    def _project_relative_target(self, normalized: str) -> File | None:
        found = self.project.get_by_relative_path(normalized)

        if found is not None:
            return found

        try:
            path = (self.project.root / normalized).resolve()
        except (OSError, RuntimeError, ValueError):
            return None

        if not self._inside_project(path):
            return None

        return self.project.get_file(path)

    def _absolute_target(self, normalized: str) -> File | None:
        try:
            path = Path(normalized).expanduser().resolve()
        except (OSError, RuntimeError, ValueError):
            return None

        if not self._inside_project(path):
            return None

        return self.project.get_file(path)

    def _inside_project(self, path: Path) -> bool:
        try:
            path.relative_to(self.project.root)
        except ValueError:
            return False

        return True

    @staticmethod
    def _reference(
        observation: Observation,
        *,
        raw: str,
        normalized: str | None,
        strategy: ResolutionStrategy,
        status: ResolutionStatus,
        target: File | None = None,
        candidates: tuple[File, ...] = (),
    ) -> Reference:
        source = observation.source

        if source is None:
            raise ValueError("observation.source is required")

        return Reference(
            source=source,
            kind=observation.kind,
            raw_target=raw,
            location=observation.location,
            target=target,
            confidence=observation.confidence,
            resolved=status is ResolutionStatus.RESOLVED,
            normalized=normalized,
            resolution=strategy,
            status=status,
            candidates=candidates,
            evidence=Evidence(
                source=source,
                raw=raw,
                kind=observation.kind,
                location=observation.location,
                normalized=normalized,
                resolution=strategy,
                target=target,
                confidence=ConfidenceScore.from_band(
                    observation.confidence
                ),
            ),
        )


def _is_absolute_path(value: str) -> bool:
    if len(value) >= 2 and value[1] == ":" and value[0].isalpha():
        return True

    return Path(value).is_absolute()
