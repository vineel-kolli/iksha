"""
Project file inventory for IKSHA.

Responsible only for discovering and classifying project files.
It does not parse source code or analyze dependencies.
"""

from pathlib import Path
import os

from iksha.config.loader import load_config
from iksha.config.model import CaseSensitivity, Config
from iksha.domain.file import File
from iksha.domain.identity import file_identity_key
from iksha.domain.project import Project
from iksha.inventory.classification import (
    MINIFIED_PEEK_BYTES,
    has_minified_line,
    is_generated_source,
    is_minified_filename,
)
from iksha.parsing.result import Diagnostic


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
        self.diagnostics: list[Diagnostic] = []
        self.case_sensitive = (
            self.config.effective_case_sensitivity
            is CaseSensitivity.SENSITIVE
        )

    def scan(self) -> Project:
        """Discover files and return the populated project."""

        self.diagnostics = list(self.config_diagnostics)

        project = Project(
            root=self.root,
            case_sensitive=self.case_sensitive,
        )

        if not self.root.is_dir():
            return project

        for real_path, relative_path in self._discover_files():
            file_type = self._classify(real_path)

            if file_type is None:
                continue

            if project.contains(real_path):
                continue

            size, readable, source_error = self._inspect(real_path)

            if source_error is not None:
                self.diagnostics.append(
                    Diagnostic(
                        message=source_error,
                        severity="warning",
                    )
                )

            minified = is_minified_filename(Path(relative_path).name)

            if readable and not minified:
                peek = min(
                    MINIFIED_PEEK_BYTES,
                    int(self.config.max_file_size_mb * 1024 * 1024),
                )

                minified = has_minified_line(
                    real_path,
                    size=size,
                    max_bytes=max(peek, 0),
                )

            file = File(
                path=real_path,
                relative_path=relative_path,
                file_type=file_type,
                size=size,
                readable=readable,
                parseable=readable,
                ignored=False,
                generated=is_generated_source(relative_path),
                minified=minified,
                source_error=source_error,
            )

            project.add_file(file)

        return project

    def _discover_files(self) -> list[tuple[Path, str]]:
        """
        Discover files recursively.

        Each result is (resolved real path, on-disk relative path).
        """

        discovered: list[tuple[Path, str]] = []
        visited: set[Path] = set()
        follow_symlinks = self.config.follow_symlinks

        for current_root, directories, filenames in os.walk(
            self.root,
            followlinks=follow_symlinks,
        ):
            current_path = Path(current_root)

            try:
                real_dir = current_path.resolve()
            except OSError:
                directories[:] = []
                continue

            if real_dir in visited:
                directories[:] = []
                continue

            visited.add(real_dir)

            directories[:] = sorted(
                directory
                for directory in directories
                if directory not in self.ignored_directories
            )

            for filename in sorted(filenames):
                path = current_path / filename

                try:
                    if not path.is_file():
                        continue

                    real_path = path.resolve()
                except OSError:
                    continue

                relative_path = self._relative_path(
                    path,
                    real_path,
                )

                if relative_path is None:
                    continue

                discovered.append((real_path, relative_path))

        return sorted(
            discovered,
            key=lambda item: (
                item[1].lower(),
                item[1],
                item[0].as_posix(),
            ),
        )

    def _relative_path(
        self,
        walk_path: Path,
        real_path: Path,
    ) -> str | None:
        """
        Return the project-relative path, preferring on-disk casing.

        Files whose real path is outside the project are excluded.
        """

        try:
            walk_relative = walk_path.relative_to(
                self.root
            ).as_posix()
        except ValueError:
            walk_relative = None

        try:
            real_relative = real_path.relative_to(
                self.root
            ).as_posix()
        except ValueError:
            return None

        try:
            if walk_path.is_symlink():
                return real_relative
        except OSError:
            return real_relative

        if walk_relative is None:
            return real_relative

        walk_key = file_identity_key(
            self.root / walk_relative,
            case_sensitive=self.case_sensitive,
        )
        real_key = file_identity_key(
            real_path,
            case_sensitive=self.case_sensitive,
        )

        if walk_key == real_key:
            return walk_relative

        return real_relative

    def _classify(self, path: Path) -> str | None:
        """Return the project file type for a supported extension."""

        return self.supported_extensions.get(
            path.suffix.lower()
        )

    @staticmethod
    def _inspect(
        path: Path,
    ) -> tuple[int, bool, str | None]:
        """Return size, readability, and any source error."""

        try:
            size = path.stat().st_size
        except OSError as exc:
            return 0, False, f"Unable to read file: {exc}"

        try:
            with path.open("rb"):
                pass
        except OSError as exc:
            return size, False, f"Unable to read file: {exc}"

        return size, True, None
