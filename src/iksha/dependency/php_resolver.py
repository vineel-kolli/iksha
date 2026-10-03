"""
PHP dependency path resolution.

Converts static PHP include/require observations into concrete
project files.
"""

from pathlib import Path

from iksha.dependency.result import ResolutionResult
from iksha.domain.file import File
from iksha.domain.reference import ReferenceKind
from iksha.parsing.result import Observation
from iksha.php.static_path import PHPStaticPathEvaluator



class PHPDependencyResolver:
    """
    Resolve static PHP include and require references.

    Resolution is conservative:

    - only include/require observations are considered
    - supported static PHP expressions are evaluated
    - dynamic expressions are not resolved
    - targets must remain inside the project
    - only PHP files are accepted
    - relative paths are resolved from the source file context
    """

    def __init__(
        self,
        root: str | Path,
    ) -> None:
        self.root = Path(root).expanduser().resolve()

        self._files: dict[Path, File] = {}

        self._static_path_evaluator = (
            PHPStaticPathEvaluator()
        )

    def handles(
        self,
        observation: Observation,
    ) -> bool:
        """Return whether this resolver owns the observation kind."""

        return observation.kind in {
            ReferenceKind.INCLUDE,
            ReferenceKind.REQUIRE,
        }

    def index_files(
        self,
        files: list[File],
    ) -> None:
        """
        Index authoritative project files.

        The inventory remains the source of truth for File objects.
        """

        self._files.clear()

        for file in files:
            canonical = (
                file.path
                .expanduser()
                .resolve()
            )

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

        target_path = self._resolve_expression(
            observation,
        )

        if target_path is None:
            return ResolutionResult(
                observation=observation,
            )

        if not self._is_inside_project(
            target_path
        ):
            return ResolutionResult(
                observation=observation,
            )

        target = self._get_target(
            target_path
        )

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
            if self.handles(observation)
        ]

    def _resolve_expression(
        self,
        observation: Observation,
    ) -> Path | None:
        """
        Resolve a PHP expression into a canonical filesystem path.

        First use the existing simple relative-path behavior for
        ordinary static strings. Then use the PHP static evaluator
        for expressions such as __DIR__ and __FILE__.
        """

        source = observation.source

        if source is None:
            return None

        value = observation.value.strip()

        if not value:
            return None

        # Existing simple-path behavior.
        if self._is_simple_static_path(value):
            return self._resolve_path(
                source.path,
                value,
            )

        # PHP static expression evaluation.
        result = self._static_path_evaluator.evaluate(
            value,
            source.path,
        )

        if not result.resolved:
            return None

        return result.path

    @staticmethod
    def _is_simple_static_path(
        value: str,
    ) -> bool:
        """
        Determine whether a value is a simple quoted/static path.

        The PHP parser normally provides the unquoted path value.
        """

        if "$" in value:
            return False

        if "(" in value or ")" in value:
            return False

        if "[" in value or "]" in value:
            return False

        if "__DIR__" in value:
            return False

        if "__FILE__" in value:
            return False

        if "dirname(" in value:
            return False

        return True

    def _get_target(
        self,
        target_path: Path,
    ) -> File | None:
        """
        Return the authoritative indexed File.

        If an inventory entry is unavailable, fall back to the
        physical filesystem for standalone resolver usage.
        """

        indexed = self._files.get(
            target_path
        )

        if indexed is not None:
            return indexed

        try:
            if not target_path.is_file():
                return None
        except OSError:
            return None

        if target_path.suffix.lower() != ".php":
            return None

        try:
            relative_path = (
                target_path
                .relative_to(self.root)
                .as_posix()
            )

            size = target_path.stat().st_size

        except (
            OSError,
            ValueError,
        ):
            return None

        return File(
            path=target_path,
            relative_path=relative_path,
            file_type="php",
            size=size,
        )

    def _resolve_path(
        self,
        source_path: Path,
        raw_target: str,
    ) -> Path | None:
        """Resolve a simple path relative to the source file."""

        try:
            target = (
                source_path.parent / raw_target
            ).resolve()

        except (
            OSError,
            RuntimeError,
            ValueError,
        ):
            return None

        if not self._is_inside_project(
            target
        ):
            return None

        return target

    def _is_inside_project(
        self,
        path: Path,
    ) -> bool:
        """Return whether a path is inside the project root."""

        try:
            path.relative_to(self.root)

        except ValueError:
            return False

        return True
