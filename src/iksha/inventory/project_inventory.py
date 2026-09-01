"""
Project file inventory for IKSHA.

Responsible only for discovering and classifying project files.
It does not parse source code or analyze dependencies.
"""

from pathlib import Path
import os

from iksha.domain.file import File
from iksha.domain.project import Project


class ProjectInventory:
    """
    Discovers supported files inside a project and builds the
    authoritative Project file registry.
    """

    SUPPORTED_EXTENSIONS: dict[str, str] = {
        ".php": "php",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
    }

    DEFAULT_IGNORED_DIRECTORIES: frozenset[str] = frozenset(
        {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            "node_modules",
            "vendor",
            "dist",
            "build",
            "coverage",
            ".pytest_cache",
        }
    )

    def __init__(
        self,
        root: str | Path,
        ignored_directories: set[str] | frozenset[str] | None = None,
    ) -> None:
        self.root = Path(root).expanduser().resolve()

        self.ignored_directories = frozenset(
            name.strip()
            for name in (
                self.DEFAULT_IGNORED_DIRECTORIES
                if ignored_directories is None
                else ignored_directories
            )
            if name.strip()
        )

    def scan(self) -> Project:
        """Discover files and return the populated project."""

        project = Project(root=self.root)

        if not self.root.is_dir():
            return project

        for path in self._discover_files():
            file_type = self._classify(path)

            if file_type is None:
                continue

            relative_path = path.relative_to(
                self.root
            ).as_posix()

            file = File(
                path=path,
                relative_path=relative_path,
                file_type=file_type,
                size=self._get_file_size(path),
            )

            project.add_file(file)

        return project

    def _discover_files(self) -> list[Path]:
        """
        Discover files recursively.

        os.walk() returns strings, so every filesystem path is
        explicitly converted to Path before path operations.
        """

        discovered: list[Path] = []

        for current_root, directories, filenames in os.walk(
            self.root
        ):
            directories[:] = sorted(
                directory
                for directory in directories
                if directory not in self.ignored_directories
            )

            current_path = Path(current_root)

            for filename in sorted(filenames):
                path = current_path / filename

                try:
                    if path.is_file():
                        discovered.append(path.resolve())
                except OSError:
                    continue

        return sorted(
            discovered,
            key=lambda path: path.relative_to(
                self.root
            ).as_posix(),
        )

    def _classify(self, path: Path) -> str | None:
        """Return the project file type for a supported extension."""

        return self.SUPPORTED_EXTENSIONS.get(
            path.suffix.lower()
        )

    @staticmethod
    def _get_file_size(path: Path) -> int:
        """Return file size without allowing metadata errors to crash."""

        try:
            return path.stat().st_size
        except OSError:
            return 0
