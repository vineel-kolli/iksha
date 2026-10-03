"""
Confidence scoring for IKSHA.

Numeric percentage (0–100) is the source of truth. The categorical
band is derived from that percentage using a versioned mapping.
"""

from dataclasses import dataclass

from .states import Confidence

CONFIDENCE_MAPPING_VERSION = "1.0"

_BAND_PERCENT: dict[Confidence, float | None] = {
    Confidence.CERTAIN: 96.0,
    Confidence.HIGH: 87.0,
    Confidence.MEDIUM: 65.0,
    Confidence.LOW: 35.0,
    Confidence.UNKNOWN: None,
}


def confidence_band(percent: float | None) -> Confidence:
    """
    Map a numeric confidence score to a categorical band.

    Mapping (inclusive lower bounds except UNKNOWN):

        CERTAIN   95–100
        HIGH      80–94
        MEDIUM    50–79
        LOW       20–49
        UNKNOWN    0–19, None, or not computable
    """

    if percent is None:
        return Confidence.UNKNOWN

    if percent < 0 or percent > 100:
        raise ValueError("confidence percent must be between 0 and 100")

    if percent < 20:
        return Confidence.UNKNOWN

    if percent < 50:
        return Confidence.LOW

    if percent < 80:
        return Confidence.MEDIUM

    if percent < 95:
        return Confidence.HIGH

    return Confidence.CERTAIN


@dataclass(frozen=True)
class ConfidenceScore:
    """Numeric confidence plus its derived categorical band."""

    percent: float | None
    band: Confidence
    mapping_version: str = CONFIDENCE_MAPPING_VERSION

    @classmethod
    def from_percent(
        cls,
        percent: float | None,
    ) -> "ConfidenceScore":
        """Build a score, deriving the band from the percentage."""

        return cls(
            percent=percent,
            band=confidence_band(percent),
        )

    @classmethod
    def from_band(
        cls,
        band: Confidence,
    ) -> "ConfidenceScore":
        """Build a score from a categorical band using the default mapping."""

        return cls(
            percent=_BAND_PERCENT[band],
            band=band,
        )

    @classmethod
    def unknown(cls) -> "ConfidenceScore":
        """Return a non-computable unknown confidence."""

        return cls(
            percent=None,
            band=Confidence.UNKNOWN,
        )
