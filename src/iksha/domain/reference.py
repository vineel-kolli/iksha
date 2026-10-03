"""
Reference model for IKSHA.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from .file import File
from .resolution import ResolutionStatus, ResolutionStrategy
from .source_location import SourceLocation
from .states import Confidence

if TYPE_CHECKING:
    from .evidence import Evidence

__all__ = [
    "Confidence",
    "FILE_DEPENDENCY_KINDS",
    "Reference",
    "ReferenceKind",
    "ResolutionStatus",
    "ResolutionStrategy",
]


class ReferenceKind(str, Enum):
    """Types of relationships discovered in source code."""

    DEPENDENCY = "dependency"
    IMPORT = "import"
    INCLUDE = "include"
    REQUIRE = "require"
    STYLESHEET = "stylesheet"
    SCRIPT = "script"
    DOM_SELECTOR = "dom_selector"
    CLASS = "class"
    ID = "id"
    UNKNOWN = "unknown"


FILE_DEPENDENCY_KINDS: frozenset[ReferenceKind] = frozenset(
    {
        ReferenceKind.INCLUDE,
        ReferenceKind.REQUIRE,
        ReferenceKind.IMPORT,
        ReferenceKind.STYLESHEET,
        ReferenceKind.SCRIPT,
    }
)


@dataclass(frozen=True)
class Reference:
    """
    Represents evidence that one source references another entity.

    Raw text is preserved. Normalization and resolution are recorded
    even when the target cannot be found.
    """

    source: File
    kind: ReferenceKind
    raw_target: str
    location: SourceLocation | None = None
    target: File | None = None
    confidence: Confidence = Confidence.UNKNOWN
    resolved: bool = False
    normalized: str | None = None
    resolution: ResolutionStrategy = ResolutionStrategy.UNKNOWN
    status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    candidates: tuple[File, ...] = ()
    evidence: Evidence | None = None
