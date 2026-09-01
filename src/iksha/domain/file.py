"""
Core file identity model for IKSHA.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class File:
    """
    Represents one exact file in the analyzed project.

    File identity is the canonical absolute path.
    Filename alone is never used as identity.
    """

    path: Path
    relative_path: str
    file_type: str
    size: int = 0

    def __post_init__(self) -> None:
        canonical = self.path.expanduser().resolve()

        object.__setattr__(
            self,
            "path",
            canonical,
        )

        normalized_relative = (
            self.relative_path
            .replace("\\", "/")
            .lstrip("./")
        )

        object.__setattr__(
            self,
            "relative_path",
            normalized_relative,
        )

        object.__setattr__(
            self,
            "file_type",
            self.file_type.lower().strip(),
        )

        if self.size < 0:
            raise ValueError("size must be >= 0")

    @property
    def name(self) -> str:
        """Return the filename."""
        return self.path.name

    @property
    def extension(self) -> str:
        """Return the lowercase file extension."""
        return self.path.suffix.lower()
