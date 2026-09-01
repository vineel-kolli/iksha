"""
Represents the successfully or unsuccessfully loaded source of a file.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceDocument:
    """Immutable source document produced by SourceLoader."""

    path: Path
    text: str = ""
    encoding: str | None = None
    byte_size: int = 0
    success: bool = False
    error: str | None = None
