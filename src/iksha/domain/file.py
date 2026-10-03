"""
Core file identity model for IKSHA.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class File:
    """
    Represents one exact file in the analyzed project.

    File identity is the canonical absolute path, never the filename.
    Display paths preserve on-disk casing via relative_path.
    """

    path: Path
    relative_path: str
    file_type: str
    size: int = 0
    readable: bool = True
    parseable: bool = True
    ignored: bool = False
    generated: bool = False
    minified: bool = False
    source_error: str | None = None

    def __post_init__(self) -> None:
        try:
            canonical = self.path.expanduser().resolve()
        except OSError:
            canonical = Path(self.path)

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
        """Return the on-disk filename."""

        name = Path(self.relative_path).name

        if name:
            return name

        return self.path.name

    @property
    def extension(self) -> str:
        """Return the lowercase file extension."""

        suffix = Path(self.relative_path).suffix.lower()

        if suffix:
            return suffix

        return self.path.suffix.lower()
