"""
CSS dependency resolution.

Resolves static local CSS @import observations into authoritative
project files.
"""

from pathlib import Path

from iksha.dependency.result import ResolutionResult
from iksha.domain.file import File
from iksha.domain.identity import (
    is_external_reference,
    normalize_reference_path,
)
from iksha.domain.project import Project
from iksha.domain.reference import ReferenceKind
from iksha.parsing.result import Observation
from iksha.parsing.support import looks_dynamic


class CSSDependencyResolver:
    """
    Resolve static CSS @import references.

    Resolution is conservative:

    - only CSS @import observations are handled
    - external references remain outside this resolver
    - dynamic references remain outside this resolver
    - targets must remain inside the project
    - only CSS files are accepted as import targets
    - authoritative Project File objects are returned
    """

    def __init__(
        self,
        project: Project,
    ) -> None:
        self.project = project
        self._files: dict[Path, File] = {}

    def handles(
        self,
        observation: Observation,
    ) -> bool:
        """Return whether this resolver owns the observation."""

        source = observation.source

        if source is None:
            return False

        if source.file_type != "css":
            return False

        if observation.kind is not ReferenceKind.IMPORT:
            return False

        raw = observation.value.strip()

        if not raw:
            return False

        if is_external_reference(raw):
            return False

        if looks_dynamic(raw):
            return False

        return normalize_reference_path(raw) is not None

    def index_files(
        self,
        files: list[File],
    ) -> None:
        """
        Index authoritative project files.

        The Project remains the source of truth for File objects.
        """

        self._files.clear()

        for file in files:
            try:
                canonical = (
                    file.path
                    .expanduser()
                    .resolve()
                )
            except (
                OSError,
                RuntimeError,
                ValueError,
            ):
                continue

            self._files[canonical] = file

    def resolve(
        self,
        observation: Observation,
    ) -> ResolutionResult:
        """Resolve one CSS @import observation."""

        if not self.handles(observation):
            return ResolutionResult(
                observation=observation,
            )

        source = observation.source

        if source is None:
            return ResolutionResult(
                observation=observation,
            )

        normalized = normalize_reference_path(
            observation.value.strip()
        )

        if not normalized:
            return ResolutionResult(
                observation=observation,
            )

        target = self._resolve_source_relative(
            source,
            normalized,
        )

        if target is not None:
            return ResolutionResult(
                observation=observation,
                target=target,
            )

        target = self._resolve_project_relative(
            normalized,
        )

        if target is not None:
            return ResolutionResult(
                observation=observation,
                target=target,
            )

        return ResolutionResult(
            observation=observation,
        )

    def _resolve_source_relative(
        self,
        source: File,
        normalized: str,
    ) -> File | None:
        """Resolve an import relative to the importing CSS file."""

        try:
            path = (
                source.path.parent / normalized
            ).resolve()
        except (
            OSError,
            RuntimeError,
            ValueError,
        ):
            return None

        if not self._inside_project(path):
            return None

        return self._get_css_target(path)

    def _resolve_project_relative(
        self,
        normalized: str,
    ) -> File | None:
        """Resolve an import relative to the project root."""

        found = self.project.get_by_relative_path(
            normalized
        )

        if found is not None:
            return self._css_target(found)

        try:
            path = (
                self.project.root / normalized
            ).resolve()
        except (
            OSError,
            RuntimeError,
            ValueError,
        ):
            return None

        if not self._inside_project(path):
            return None

        return self._get_css_target(path)

    def _get_css_target(
        self,
        path: Path,
    ) -> File | None:
        """Return the authoritative CSS File for a canonical path."""

        indexed = self._files.get(path)

        if indexed is not None:
            return self._css_target(indexed)

        project_file = self.project.get_file(path)

        if project_file is not None:
            return self._css_target(project_file)

        return None

    @staticmethod
    def _css_target(
        file: File,
    ) -> File | None:
        """Accept only CSS files as stylesheet import targets."""

        if file.file_type != "css":
            return None

        return file

    def _inside_project(
        self,
        path: Path,
    ) -> bool:
        """Return whether a path is inside the project root."""

        try:
            path.relative_to(
                self.project.root
            )
        except ValueError:
            return False

        return True