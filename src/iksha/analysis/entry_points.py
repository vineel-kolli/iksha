"""
Entry-point resolution for IKSHA.
"""

from iksha.domain.file import File
from iksha.domain.project import Project


class EntryPointResolver:
    """
    Resolve configured project entry points to authoritative File objects.

    Entry-point discovery is configuration-driven. This resolver does not
    guess additional roots from filenames or project structure.
    """

    def __init__(
        self,
        project: Project,
    ) -> None:
        self.project = project

    def resolve(
        self,
        entry_points: tuple[str, ...],
    ) -> tuple[File, ...]:
        """
        Resolve configured entry-point paths.

        Paths are interpreted relative to the project root. Only files
        already present in the authoritative Project inventory are returned.
        Invalid or missing paths are ignored.
        """

        resolved: list[File] = []
        seen: set[File] = set()

        for raw in entry_points:
            normalized = self._normalize(raw)

            if not normalized:
                continue

            file = self.project.get_by_relative_path(
                normalized,
            )

            if file is None or file in seen:
                continue

            seen.add(file)
            resolved.append(file)

        return tuple(resolved)

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:
        """Normalize a configured project-relative entry-point path."""

        return (
            value.strip()
            .replace("\\", "/")
            .lstrip("./")
        )