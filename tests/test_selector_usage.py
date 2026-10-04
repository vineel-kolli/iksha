from pathlib import Path

from iksha.analysis.selector_usage import (
    analyze_selector_usage,
)
from iksha.domain.file import File
from iksha.domain.reference import ReferenceKind
from iksha.domain.states import Confidence, UsageState
from iksha.parsing.result import Observation


def make_observation(
    tmp_path: Path,
    kind: ReferenceKind,
    value: str,
    confidence: Confidence,
) -> Observation:
    path = tmp_path / "index.html"

    file = File(
        path=path,
        relative_path="index.html",
        file_type="html",
        size=0,
    )

    return Observation(
        source=file,
        kind=kind,
        value=value,
        confidence=confidence,
    )


def test_class_selector_matches_certain_class_usage(
    tmp_path: Path,
):
    observation = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "card",
        Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        ".card",
        [observation],
    )

    assert result.state is UsageState.DEFINITELY_USED
    assert result.evidence == (observation,)


def test_id_selector_matches_certain_id_usage(
    tmp_path: Path,
):
    observation = make_observation(
        tmp_path,
        ReferenceKind.ID,
        "hero",
        Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        "#hero",
        [observation],
    )

    assert result.state is UsageState.DEFINITELY_USED
    assert result.evidence == (observation,)


def test_high_confidence_usage_is_probably_used(
    tmp_path: Path,
):
    observation = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "card",
        Confidence.HIGH,
    )

    result = analyze_selector_usage(
        ".card",
        [observation],
    )

    assert result.state is UsageState.PROBABLY_USED


def test_medium_confidence_usage_is_possibly_used(
    tmp_path: Path,
):
    observation = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "card",
        Confidence.MEDIUM,
    )

    result = analyze_selector_usage(
        ".card",
        [observation],
    )

    assert result.state is UsageState.POSSIBLY_USED


def test_low_confidence_usage_is_possibly_used(
    tmp_path: Path,
):
    observation = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "card",
        Confidence.LOW,
    )

    result = analyze_selector_usage(
        ".card",
        [observation],
    )

    assert result.state is UsageState.POSSIBLY_USED


def test_unknown_confidence_usage_is_unknown(
    tmp_path: Path,
):
    observation = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "card",
        Confidence.UNKNOWN,
    )

    result = analyze_selector_usage(
        ".card",
        [observation],
    )

    assert result.state is UsageState.UNKNOWN


def test_missing_class_usage_is_statically_unused(
    tmp_path: Path,
):
    observation = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "other",
        Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        ".card",
        [observation],
    )

    assert result.state is UsageState.STATICALLY_UNUSED
    assert result.evidence == ()


def test_unrelated_id_does_not_match_class_selector(
    tmp_path: Path,
):
    observation = make_observation(
        tmp_path,
        ReferenceKind.ID,
        "card",
        Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        ".card",
        [observation],
    )

    assert result.state is UsageState.STATICALLY_UNUSED


def test_element_selector_is_conservatively_unknown(
    tmp_path: Path,
):
    observation = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "button",
        Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        "button",
        [observation],
    )

    assert result.state is UsageState.UNKNOWN
    assert result.evidence == ()


def test_complex_selector_is_conservatively_unknown(
    tmp_path: Path,
):
    observation = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "title",
        Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        ".card .title",
        [observation],
    )

    assert result.state is UsageState.UNKNOWN
    assert result.evidence == ()