"""
Represents the successfully or unsuccessfully loaded source of a file.
"""

from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

from iksha.domain.source_location import SourceLocation


def compute_line_offsets(text: str) -> tuple[int, ...]:
    """
    Return the 0-based character offset where each line starts.

    An empty document has no lines.
    """

    if not text:
        return ()

    offsets = [0]

    for index, character in enumerate(text):
        if character == "\n":
            offsets.append(index + 1)

    return tuple(offsets)


@dataclass(frozen=True)
class SourceDocument:
    """Immutable source document produced by SourceLoader."""

    path: Path
    text: str = ""
    encoding: str | None = None
    byte_size: int = 0
    success: bool = False
    error: str | None = None
    language: str | None = None
    minified: bool = False
    truncated: bool = False
    line_offsets: tuple[int, ...] = ()
    line_count: int = 0

    def __post_init__(self) -> None:
        offsets = compute_line_offsets(self.text)

        object.__setattr__(self, "line_offsets", offsets)

        object.__setattr__(
            self,
            "line_count",
            0 if not self.text else len(offsets),
        )

        if self.language is not None:
            object.__setattr__(
                self,
                "language",
                self.language.lower().strip() or None,
            )

    def location_at(self, offset: int) -> SourceLocation:
        """
        Convert a character offset into a source location.

        Offsets are clamped to the document text. Minified documents
        still report line, but mark column as imprecise and always
        include the character offset.
        """

        if offset < 0:
            offset = 0

        if offset > len(self.text):
            offset = len(self.text)

        starts = self.line_offsets or (0,)
        index = bisect_right(starts, offset) - 1
        index = max(index, 0)
        line_start = starts[index]
        line = index + 1
        column = offset - line_start + 1

        if column < 1:
            column = 1

        return SourceLocation(
            line=line,
            column=1 if self.minified else column,
            offset=offset,
            column_precise=not self.minified,
        )
