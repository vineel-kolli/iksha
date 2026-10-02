"""
Evidence model for IKSHA.

Every important conclusion traces to recorded evidence: what was
found, where, how it was resolved, what it points to, and how certain
the observation is.
"""

from dataclasses import dataclass, field
from enum import Enum

from .confidence import ConfidenceScore
from .file import File
from .reference import ReferenceKind
from .source_location import SourceLocation
from .states import Confidence


class ResolutionStrategy(str, Enum):
    """Method used to turn a raw reference string into a target."""

    SOURCE_RELATIVE = "source-relative"
    PROJECT_RELATIVE = "project-relative"
    ABSOLUTE = "absolute"
    IMPORT_RELATIVE = "import-relative"
    URL = "url"
    DYNAMIC = "dynamic"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Evidence:
    """
    One attributable fact supporting an analysis conclusion.

    Raw evidence is preserved even when the target cannot be resolved.
    """

    source: File
    raw: str
    kind: ReferenceKind
    location: SourceLocation | None = None
    normalized: str | None = None
    resolution: ResolutionStrategy = ResolutionStrategy.UNKNOWN
    target: File | None = None
    target_identity: str | None = None
    confidence: ConfidenceScore = field(
        default_factory=ConfidenceScore.unknown,
    )

    def __post_init__(self) -> None:
        if self.normalized is None:
            object.__setattr__(
                self,
                "normalized",
                self.raw,
            )

        if self.target is not None and self.target_identity is None:
            object.__setattr__(
                self,
                "target_identity",
                self.target.relative_path,
            )

    @property
    def line(self) -> int | None:
        """Return the source line when a location is present."""

        if self.location is None:
            return None

        return self.location.line

    @property
    def confidence_percent(self) -> float | None:
        """Return the numeric confidence percentage."""

        return self.confidence.percent

    @property
    def confidence_band(self) -> Confidence:
        """Return the categorical confidence band."""

        return self.confidence.band
