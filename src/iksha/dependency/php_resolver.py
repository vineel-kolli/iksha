"""
PHP dependency path resolution.

Converts static PHP include/require observations into concrete
project files.

The resolver can operate directly against the project filesystem,
but can also receive the authoritative inventory through index_files().
"""

from dataclasses import dataclass
from pathlib import Path

from iksha.domain.file import File
from iksha.domain.reference import ReferenceKind
from iksha.parsing.result import Observation


@dataclass(frozen=True)
class ResolutionResult:
    """Result of resolving one dependency observation."""

    observation: Observation
    target: File | None = None

    @property
    def resolved(self) -> bool:
        """Return whether the dependency resolved."""
        return self.target is not None


class PHPDependencyResolver:
    """
    Resolve static PHP include and require references.

    Resolution is conservative:

    - only include/require observations are considered
    - dynamic expressions are not resolved
    - targets must remain inside the project
    - only PHP files are accepted
    - the source file's directory is the base for relative paths
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

        # Optional authoritative inventory index.
        self._files: dict[Path, File] = {}

    def index_files(self, files: list[File]) -> None:
        """
        Index authoritative project files.

        When an inventory is available, it is preferred over direct
        filesystem discovery.
        """

        self._files.clear()

        for file in files:
            canonical = file.path.expanduser().resolve()
            self._files[canonical] = file

    def resolve(
        self,
        observation: Observation,
    ) -> ResolutionResult:
        """Resolve one PHP dependency observation."""

        if observation.source is None:
            return ResolutionResult(
                observation=observation,
            )

        if observation.kind not in {
            ReferenceKind.INCLUDE,
            ReferenceKind.REQUIRE,
        }:
            return ResolutionResult(
                observation=observation,
            )

        if not self._is_static_path(observation.value):
            return ResolutionResult(
                observation=observation,
            )

        target_path = self._resolve_path(
            observation.source.path,
            observation.value,
        )

        if target_path is None:
            return ResolutionResult(
                observation=observation,
            )

        target = self._get_target(target_path)

        if target is None:
            return ResolutionResult(
                observation=observation,
            )

        if target.file_type != "php":
            return ResolutionResult(
                observation=observation,
            )

        return ResolutionResult(
            observation=observation,
            target=target,
        )

    def resolve_all(
        self,
        observations: list[Observation],
    ) -> list[ResolutionResult]:
        """Resolve observations while preserving their order."""

        return [
            self.resolve(observation)
            for observation in observations
        ]

    def _get_target(
        self,
        target_path: Path,
    ) -> File | None:
        """Return the authoritative File for a canonical path."""

        return self._files.get(target_path)

    def _resolve_path(
        self,
        source_path: Path,
        raw_target: str,
    ) -> Path | None:
        """Resolve a dependency relative to the source file."""

        try:
            target = (
                source_path.parent / raw_target
            ).resolve()
        except (OSError, RuntimeError, ValueError):
            return None

        if not self._is_inside_project(target):
            return None

        return target

    def _is_inside_project(
        self,
        path: Path,
    ) -> bool:
        """Return whether the path is inside the project root."""

        try:
            path.relative_to(self.root)
        except ValueError:
            return False

        return True

    @staticmethod
    def _is_static_path(
        value: str,
    ) -> bool:
        """
        Return whether a PHP dependency expression is statically
        resolvable.
        """

        value = value.strip()

        if not value:
            return False

        # PHP variable.
        if "$" in value:
            return False

        # Function call / dynamic expression.
        if "(" in value or ")" in value:
            return False

        return True
