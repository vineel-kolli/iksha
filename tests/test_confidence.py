import pytest

from iksha.domain.confidence import (
    CONFIDENCE_MAPPING_VERSION,
    ConfidenceScore,
    confidence_band,
)
from iksha.domain.states import Confidence


@pytest.mark.parametrize(
    ("percent", "expected"),
    [
        (None, Confidence.UNKNOWN),
        (0, Confidence.UNKNOWN),
        (19, Confidence.UNKNOWN),
        (19.9, Confidence.UNKNOWN),
        (20, Confidence.LOW),
        (49, Confidence.LOW),
        (49.9, Confidence.LOW),
        (50, Confidence.MEDIUM),
        (79, Confidence.MEDIUM),
        (79.9, Confidence.MEDIUM),
        (80, Confidence.HIGH),
        (94, Confidence.HIGH),
        (94.9, Confidence.HIGH),
        (95, Confidence.CERTAIN),
        (96, Confidence.CERTAIN),
        (100, Confidence.CERTAIN),
    ],
)
def test_confidence_band_mapping(percent, expected):
    assert confidence_band(percent) is expected


def test_confidence_band_rejects_out_of_range_scores():
    with pytest.raises(ValueError):
        confidence_band(-0.1)

    with pytest.raises(ValueError):
        confidence_band(100.1)


def test_confidence_score_reports_percent_and_band_together():
    score = ConfidenceScore.from_percent(96)

    assert score.percent == 96
    assert score.band is Confidence.CERTAIN
    assert score.mapping_version == CONFIDENCE_MAPPING_VERSION


def test_unknown_confidence_has_no_computable_percent():
    score = ConfidenceScore.unknown()

    assert score.percent is None
    assert score.band is Confidence.UNKNOWN


def test_confidence_score_from_band_uses_default_percent():
    score = ConfidenceScore.from_band(Confidence.CERTAIN)

    assert score.band is Confidence.CERTAIN
    assert score.percent == 96.0
    assert (
        ConfidenceScore.from_band(Confidence.UNKNOWN).percent is None
    )
