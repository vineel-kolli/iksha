"""
Canonical analysis-state enums for IKSHA.

These values are the single source of truth for reachability, usage,
dead-code classification, confidence bands, and finding severity.
"""

from enum import Enum


class ReachabilityState(str, Enum):
    """File-level reachability from known entry points."""

    REACHABLE = "reachable"
    POTENTIALLY_REACHABLE = "potentially_reachable"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


class UsageState(str, Enum):
    """Selector/class/ID-level usage classification."""

    DEFINITELY_USED = "definitely_used"
    PROBABLY_USED = "probably_used"
    POSSIBLY_USED = "possibly_used"
    STATICALLY_UNUSED = "statically_unused"
    UNKNOWN = "unknown"


class DeadCodeState(str, Enum):
    """File-level dead-code classification for CSS candidates."""

    NOT_DEAD = "not_dead"
    POSSIBLY_DEAD = "possibly_dead"
    PROBABLY_DEAD = "probably_dead"
    DEFINITELY_DEAD = "definitely_dead"
    UNKNOWN = "unknown"


class Confidence(str, Enum):
    """
    Categorical confidence band.

    The numeric percentage is the source of truth. This band is the
    derived, user-facing label.
    """

    CERTAIN = "certain"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    """Finding severity. Independent from confidence."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
