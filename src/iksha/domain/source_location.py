"""
Source location model for IKSHA.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceLocation:
    """Identifies an exact location inside a source file."""

    line: int
    column: int

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError("line must be >= 1")

        if self.column < 1:
            raise ValueError("column must be >= 1")
