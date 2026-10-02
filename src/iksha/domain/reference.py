"""
Reference model for IKSHA.
"""

from dataclasses import dataclass
from enum import Enum

from .file import File
from .source_location import SourceLocation
from .states import Confidence

__all__ = [
    "Confidence",
    "Reference",
    "ReferenceKind",
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


@dataclass(frozen=True)
class Reference:
    """
    Represents evidence that one source references another entity.
    """

    source: File
    kind: ReferenceKind
    location: SourceLocation
    raw_target: str
    target: File | None = None
    confidence: Confidence = Confidence.UNKNOWN
    resolved: bool = False
