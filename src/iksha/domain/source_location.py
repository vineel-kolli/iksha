"""
Source location model for IKSHA.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceLocation:
    """
    Identifies an exact location inside a source file.

    Line and column are 1-based. offset is a 0-based character index
    into the decoded source text. For minified files, column is not
    treated as precise; callers should prefer offset.
    """

    line: int
    column: int
    offset: int | None = None
    column_precise: bool = True

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError("line must be >= 1")

        if self.column < 1:
            raise ValueError("column must be >= 1")

        if self.offset is not None and self.offset < 0:
            raise ValueError("offset must be >= 0")
