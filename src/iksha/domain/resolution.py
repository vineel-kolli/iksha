"""
Reference resolution vocabulary for IKSHA.
"""

from enum import Enum


class ResolutionStrategy(str, Enum):
    """Method used to turn a raw reference string into a target."""

    SOURCE_RELATIVE = "source-relative"
    PROJECT_RELATIVE = "project-relative"
    ABSOLUTE = "absolute"
    IMPORT_RELATIVE = "import-relative"
    URL = "url"
    DYNAMIC = "dynamic"
    UNKNOWN = "unknown"


class ResolutionStatus(str, Enum):
    """Outcome of attempting to resolve a reference."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"
    DYNAMIC = "dynamic"
    EXTERNAL = "external"
