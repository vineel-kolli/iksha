"""
Project file inventory for IKSHA.

Responsible only for discovering and classifying project files.
It does not parse source code or analyze dependencies.
"""

from pathlib import Path
import os

from iksha.config.loader import load_config
from iksha.config.model import Config
from iksha.domain.file import File
from iksha.domain.project import Project


class ProjectInventory:
    """
    Discovers supported files inside a project and builds the
    authoritative Project file registry.
    """

    def __init__(
        self,
        root: str | Path,
        config: Config | None = None,
    ) -> None:
        self.root = Path(root).expanduser().resolve()

        if config is None:
            loaded = load_config(self.root)
            self.config = loaded.config
            self.config_diagnostics = loaded.diagnostics
        else:
            self.config = config
            self.config_diagnostics = []

        self.ignored_directories = frozenset(self.config.ignore)
        self.supported_extensions = self.config.extension_types()

    def scan(self) -> Project:
        """Discover files and return the populated project."""

        project = Project(root=self.root)

        if not self.root.is_dir():
            return project

        for path in self._discover_files():
            file_type = self._classify(path)

            if file_type is None:
                continue

            try:
                relative_path = path.relative_to(
                    self.root
                ).as_posix()
            except ValueError:
                continue

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
        visited: set[Path] = set()
        follow_symlinks = self.config.follow_symlinks

        for current_root, directories, filenames in os.walk(
            self.root,
            followlinks=follow_symlinks,
        ):
            current_path = Path(current_root)

            try:
                real_path = current_path.resolve()
            except OSError:
                directories[:] = []
                continue

            if real_path in visited:
                directories[:] = []
                continue

            visited.add(real_path)

            directories[:] = sorted(
                directory
                for directory in directories
                if directory not in self.ignored_directories
            )

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

        return self.supported_extensions.get(
            path.suffix.lower()
        )

    @staticmethod
    def _get_file_size(path: Path) -> int:
        """Return file size without allowing metadata errors to crash."""

        try:
            return path.stat().st_size
        except OSError:
            return 0
