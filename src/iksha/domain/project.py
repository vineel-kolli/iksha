"""
Project domain model for IKSHA.
"""

from dataclasses import dataclass, field
from pathlib import Path

from .file import File


@dataclass
class Project:
    """
    Represents the complete project being analyzed.

    The project owns the authoritative collection of discovered files.
    """

    root: Path

    files: dict[Path, File] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.root = self.root.expanduser().resolve()

    @property
    def total_files(self) -> int:
        """Return the number of discovered files."""
        return len(self.files)

    def add_file(self, file: File) -> None:
        """
        Add a file using its canonical path as identity.

        Re-adding the same physical file replaces the existing
        representation instead of creating a duplicate.
        """
        canonical_path = file.path.resolve()

        self.files[canonical_path] = file

    def get_file(self, path: Path) -> File | None:
        """Return a file using its canonical path."""
        canonical_path = Path(path).expanduser().resolve()

        return self.files.get(canonical_path)

    def contains(self, path: Path) -> bool:
        """Return whether the project contains this physical file."""
        return self.get_file(path) is not None
