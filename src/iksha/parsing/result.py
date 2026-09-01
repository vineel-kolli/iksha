"""
Normalized results produced by IKSHA parsers.
"""

from dataclasses import dataclass, field

from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.domain.source_location import SourceLocation


@dataclass(frozen=True)
class Observation:
    """
    A normalized piece of evidence discovered while parsing a file.

    Observations are intentionally generic. Language-specific parsers
    can produce different kinds of observations without requiring
    separate result models.
    """

    source: File | None
    kind: ReferenceKind
    value: str
    location: SourceLocation | None = None
    confidence: Confidence = Confidence.UNKNOWN


@dataclass(frozen=True)
class Diagnostic:
    """A parser diagnostic associated with a source file."""

    message: str
    severity: str = "error"
    source: File | None = None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        allowed = {"info", "warning", "error"}

        if self.severity not in allowed:
            raise ValueError(
                f"severity must be one of {sorted(allowed)}"
            )


@dataclass
class ParseResult:
    """Normalized result returned by every parser."""

    observations: list[Observation] = field(
        default_factory=list
    )

    diagnostics: list[Diagnostic] = field(
        default_factory=list
    )

    @property
    def success(self) -> bool:
        """Return True when no error-level diagnostics exist."""

        return not any(
            diagnostic.severity == "error"
            for diagnostic in self.diagnostics
        )
