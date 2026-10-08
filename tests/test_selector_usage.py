from pathlib import Path

from iksha.analysis.selector_usage import (
    analyze_selector_usage,
)
from iksha.domain.file import File
from iksha.domain.reference import ReferenceKind
from iksha.domain.states import Confidence, UsageState
from iksha.parsing.html_document import HtmlDocument, HtmlElement
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

def make_html_document() -> HtmlDocument:
    document = HtmlDocument()

    card = HtmlElement(
        tag="div",
        attributes={
            "class": "card active",
        },
    )

    title = HtmlElement(
        tag="h2",
        attributes={
            "class": "title",
        },
    )

    card.add_child(title)
    document.add_element(card)

    return document


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


def test_unsupported_compound_selector_is_unknown(
    tmp_path: Path,
):
    observation = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "card",
        Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        ".card.active",
        [observation],
    )

    assert result.state is UsageState.UNKNOWN
    assert result.evidence == ()
    assert result.matched_files == ()

def test_unsupported_multi_component_selector_is_unknown(
    tmp_path: Path,
):
    html_file = File(
        path=tmp_path / "index.html",
        relative_path="index.html",
        file_type="html",
        size=0,
    )

    document = make_html_document()

    result = analyze_selector_usage(
        ".card .title .missing",
        [],
        {html_file: document},
    )

    assert result.state is UsageState.UNKNOWN
    assert result.semantic_matches == ()
    assert result.matched_files == ()

def test_matched_files_contains_evidence_sources(
    tmp_path: Path,
):
    first = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "card",
        Confidence.CERTAIN,
    )

    second_path = tmp_path / "app.js"
    second_file = File(
        path=second_path,
        relative_path="app.js",
        file_type="javascript",
        size=0,
    )
    second = Observation(
        source=second_file,
        kind=ReferenceKind.CLASS,
        value="card",
        confidence=Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        ".card",
        [first, second],
    )

    assert result.matched_files == (
        first.source,
        second.source,
    )


def test_matched_files_are_deduplicated(
    tmp_path: Path,
):
    first = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "card",
        Confidence.CERTAIN,
    )

    second = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "card",
        Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        ".card",
        [first, second],
    )

    assert result.matched_files == (first.source,)


def test_no_match_has_no_matched_files(
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

    assert result.matched_files == ()


def test_unknown_selector_has_no_matched_files(
    tmp_path: Path,
):
    observation = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "card",
        Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        ".card .title",
        [observation],
    )

    assert result.state is UsageState.UNKNOWN
    assert result.matched_files == ()

def test_class_selector_is_definitely_used_when_dom_matches(
    tmp_path: Path,
):
    html_file = File(
        path=tmp_path / "index.html",
        relative_path="index.html",
        file_type="html",
        size=0,
    )

    document = make_html_document()

    result = analyze_selector_usage(
        ".card",
        [],
        {html_file: document},
    )

    assert result.state is UsageState.DEFINITELY_USED
    assert result.evidence == ()
    assert len(result.semantic_matches) == 1
    assert result.matched_files == (html_file,)

def test_element_selector_is_definitely_used_when_dom_matches(
    tmp_path: Path,
):
    html_file = File(
        path=tmp_path / "index.html",
        relative_path="index.html",
        file_type="html",
        size=0,
    )

    document = make_html_document()

    result = analyze_selector_usage(
        "h2",
        [],
        {html_file: document},
    )

    assert result.state is UsageState.DEFINITELY_USED
    assert len(result.semantic_matches) == 1
    assert result.matched_files == (html_file,)

def test_complex_selector_is_definitely_used_when_dom_matches(
    tmp_path: Path,
):
    html_file = File(
        path=tmp_path / "index.html",
        relative_path="index.html",
        file_type="html",
        size=0,
    )

    document = make_html_document()

    result = analyze_selector_usage(
        ".card > .title",
        [],
        {html_file: document},
    )

    assert result.state is UsageState.DEFINITELY_USED
    assert len(result.semantic_matches) == 1
    assert result.matched_files == (html_file,)

def test_element_selector_is_unknown_when_dom_analysis_is_unavailable():
    result = analyze_selector_usage(
        "button",
        [],
        None,
    )

    assert result.state is UsageState.UNKNOWN

def test_element_selector_is_statically_unused_when_dom_is_empty():
    result = analyze_selector_usage(
        "button",
        [],
        {},
    )

    assert result.state is UsageState.STATICALLY_UNUSED

def test_unsupported_selector_remains_unknown_with_dom(
    tmp_path: Path,
):
    html_file = File(
        path=tmp_path / "index.html",
        relative_path="index.html",
        file_type="html",
        size=0,
    )

    document = make_html_document()

    result = analyze_selector_usage(
        '[data-state="open"]',
        [],
        {html_file: document},
    )

    assert result.state is UsageState.UNKNOWN
    assert result.semantic_matches == ()
    assert result.matched_files == ()

def test_semantic_matches_include_all_matching_html_files(
    tmp_path: Path,
):
    first_file = File(
        path=tmp_path / "index.html",
        relative_path="index.html",
        file_type="html",
        size=0,
    )

    second_file = File(
        path=tmp_path / "about.html",
        relative_path="about.html",
        file_type="html",
        size=0,
    )

    first_document = make_html_document()
    second_document = make_html_document()

    result = analyze_selector_usage(
        ".card",
        [],
        {
            first_file: first_document,
            second_file: second_document,
        },
    )

    assert result.state is UsageState.DEFINITELY_USED
    assert len(result.semantic_matches) == 2
    assert result.matched_files == (
        first_file,
        second_file,
    )


def test_class_selector_matches_each_class_token(
    tmp_path: Path,
):
    html_file = File(
        path=tmp_path / "index.html",
        relative_path="index.html",
        file_type="html",
        size=0,
    )

    document = make_html_document()

    card_result = analyze_selector_usage(
        ".card",
        [],
        {html_file: document},
    )

    active_result = analyze_selector_usage(
        ".active",
        [],
        {html_file: document},
    )

    assert card_result.state is UsageState.DEFINITELY_USED
    assert active_result.state is UsageState.DEFINITELY_USED

def test_malformed_selector_does_not_crash_with_dom(
    tmp_path: Path,
):
    html_file = File(
        path=tmp_path / "index.html",
        relative_path="index.html",
        file_type="html",
        size=0,
    )

    document = make_html_document()

    for selector in (
        "",
        ".",
        "#",
        ".card[",
        ".card:",
        ".card + .title",
        ".card ~ .title",
        "*",
    ):
        result = analyze_selector_usage(
            selector,
            [],
            {html_file: document},
        )

        assert result.state is UsageState.UNKNOWN


def make_dom_selector_observation(
    tmp_path: Path,
    value: str,
    confidence: Confidence,
) -> Observation:
    path = tmp_path / "app.js"

    file = File(
        path=path,
        relative_path="app.js",
        file_type="javascript",
        size=0,
    )

    return Observation(
        source=file,
        kind=ReferenceKind.DOM_SELECTOR,
        value=value,
        confidence=confidence,
    )


def test_css_selector_is_definitely_used_by_js_dom_selector(
    tmp_path: Path,
):
    observation = make_dom_selector_observation(
        tmp_path,
        ".card",
        Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        ".card",
        [observation],
    )

    assert result.state is UsageState.DEFINITELY_USED
    assert result.evidence == (observation,)
    assert result.matched_files == (observation.source,)


def test_unrelated_js_dom_selector_does_not_match(
    tmp_path: Path,
):
    observation = make_dom_selector_observation(
        tmp_path,
        ".other",
        Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        ".card",
        [observation],
    )

    assert result.state is UsageState.STATICALLY_UNUSED
    assert result.evidence == ()
    assert result.matched_files == ()


def test_unknown_js_dom_selector_does_not_prove_specific_css_usage(
    tmp_path: Path,
):
    observation = make_dom_selector_observation(
        tmp_path,
        ".card",
        Confidence.UNKNOWN,
    )

    result = analyze_selector_usage(
        ".card",
        [observation],
    )

    assert result.state is UsageState.UNKNOWN


def test_js_dom_selector_evidence_is_combined_with_class_evidence(
    tmp_path: Path,
):
    class_observation = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "card",
        Confidence.CERTAIN,
    )

    js_observation = make_dom_selector_observation(
        tmp_path,
        ".card",
        Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        ".card",
        [class_observation, js_observation],
    )

    assert result.state is UsageState.DEFINITELY_USED
    assert result.evidence == (
        class_observation,
        js_observation,
    )
    assert result.matched_files == (
        class_observation.source,
        js_observation.source,
    )


def test_js_dom_selector_confidence_is_preserved_with_class_evidence(
    tmp_path: Path,
):
    class_observation = make_observation(
        tmp_path,
        ReferenceKind.CLASS,
        "card",
        Confidence.HIGH,
    )

    js_observation = make_dom_selector_observation(
        tmp_path,
        ".card",
        Confidence.CERTAIN,
    )

    result = analyze_selector_usage(
        ".card",
        [class_observation, js_observation],
    )

    assert result.state is UsageState.DEFINITELY_USED
    assert result.evidence == (
        class_observation,
        js_observation,
    )
