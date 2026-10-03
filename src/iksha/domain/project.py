"""
Project domain model for IKSHA.
"""

from dataclasses import dataclass, field
from pathlib import Path

from .file import File
from .identity import file_identity_key, normalize_reference_path


@dataclass
class Project:
    """
    Represents the complete project being analyzed.

    The project owns the authoritative collection of discovered files.
    """

    root: Path
    case_sensitive: bool = True
    files: dict[str, File] = field(default_factory=dict)
    _by_relative: dict[str, File] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _by_name: dict[str, list[File]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _by_extension: dict[str, list[File]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _by_type: dict[str, list[File]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        self.root = self.root.expanduser().resolve()

    @property
    def total_files(self) -> int:
        """Return the number of discovered files."""
        return len(self.files)

    def add_file(self, file: File) -> None:
        """
        Add a file using its canonical identity.

        Re-adding the same physical file replaces the existing
        representation instead of creating a duplicate.
        """

        key = self._identity_key(file.path)
        existing = self.files.get(key)

        if existing is not None:
            self._unindex(existing)

        self.files[key] = file
        self._index(file)

    def get_file(self, path: Path) -> File | None:
        """Return a file using its canonical path."""

        return self.files.get(self._identity_key(path))

    def contains(self, path: Path) -> bool:
        """Return whether the project contains this physical file."""

        return self.get_file(path) is not None

    def get_by_relative_path(
        self,
        relative_path: str,
    ) -> File | None:
        """Return a file by project-relative path."""

        normalized = normalize_reference_path(relative_path)

        if not normalized:
            normalized = relative_path.replace("\\", "/").lstrip("./")

        return self._by_relative.get(
            self._lookup_text(normalized)
        )

    def files_named(self, name: str) -> tuple[File, ...]:
        """Return files that share a filename, across directories."""

        files = self._by_name.get(self._lookup_text(name), [])

        return tuple(files)

    def files_with_extension(
        self,
        extension: str,
    ) -> tuple[File, ...]:
        """Return files with the given extension."""

        suffix = extension.lower().strip()

        if suffix and not suffix.startswith("."):
            suffix = f".{suffix}"

        return tuple(self._by_extension.get(suffix, []))

    def files_of_type(self, file_type: str) -> tuple[File, ...]:
        """Return files with the given language/type."""

        key = file_type.lower().strip()

        return tuple(self._by_type.get(key, []))

    def _identity_key(self, path: Path) -> str:
        """Return the case-aware identity key for a path."""

        return file_identity_key(
            Path(path),
            case_sensitive=self.case_sensitive,
        )

    def _lookup_text(self, value: str) -> str:
        """Normalize a lookup string according to case sensitivity."""

        if self.case_sensitive:
            return value

        return value.casefold()

    def _index(self, file: File) -> None:
        """Add a file to secondary lookup indexes."""

        self._by_relative[self._lookup_text(file.relative_path)] = file

        self._by_name.setdefault(
            self._lookup_text(file.name),
            [],
        ).append(file)

        self._by_extension.setdefault(
            file.extension,
            [],
        ).append(file)

        self._by_type.setdefault(
            file.file_type,
            [],
        ).append(file)

    def _unindex(self, file: File) -> None:
        """Remove a file from secondary lookup indexes."""

        self._by_relative.pop(
            self._lookup_text(file.relative_path),
            None,
        )

        self._remove_from_list(
            self._by_name,
            self._lookup_text(file.name),
            file,
        )
        self._remove_from_list(
            self._by_extension,
            file.extension,
            file,
        )
        self._remove_from_list(
            self._by_type,
            file.file_type,
            file,
        )

    @staticmethod
    def _remove_from_list(
        index: dict[str, list[File]],
        key: str,
        file: File,
    ) -> None:
        """Remove one file from a multi-value index."""

        entries = index.get(key)

        if not entries:
            return

        index[key] = [
            item
            for item in entries
            if item is not file
        ]

        if not index[key]:
            del index[key]
