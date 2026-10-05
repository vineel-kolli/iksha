from pathlib import Path

from iksha.analysis.selector_evidence import SelectorMatchEvidence
from iksha.domain.file import File
from iksha.analysis.selector_usage import SelectorUsage
from iksha.domain.states import UsageState

def test_selector_match_evidence_stores_semantic_match() -> None:
    source = File(
        path=Path("index.html"),
        relative_path="index.html",
        file_type="html",
        size=100,
        readable=True,
        parseable=True,
        ignored=False,
        generated=False,
        minified=False,
    )

    evidence = SelectorMatchEvidence(
        source=source,
        element_tag="div",
        element_id="main",
        element_classes=("card", "active"),
    )

    assert evidence.source is source
    assert evidence.element_tag == "div"
    assert evidence.element_id == "main"
    assert evidence.element_classes == ("card", "active")

def test_selector_usage_stores_semantic_matches() -> None:
    source = File(
        path=Path("index.html"),
        relative_path="index.html",
        file_type="html",
        size=100,
        readable=True,
        parseable=True,
        ignored=False,
        generated=False,
        minified=False,
    )

    semantic_match = SelectorMatchEvidence(
        source=source,
        element_tag="div",
        element_classes=("card",),
    )

    usage = SelectorUsage(
        selector=".card",
        state=UsageState.DEFINITELY_USED,
        semantic_matches=(semantic_match,),
    )

    assert usage.semantic_matches == (semantic_match,)