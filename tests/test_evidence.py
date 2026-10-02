from pathlib import Path

from iksha.domain.confidence import ConfidenceScore
from iksha.domain.evidence import Evidence, ResolutionStrategy
from iksha.domain.file import File
from iksha.domain.reference import ReferenceKind
from iksha.domain.source_location import SourceLocation
from iksha.domain.states import Confidence


def make_file(relative_path: str, file_type: str = "php") -> File:
    root = Path("project").resolve()

    return File(
        path=(root / relative_path).resolve(),
        relative_path=relative_path,
        file_type=file_type,
    )


def test_resolution_strategies_match_prd():
    assert ResolutionStrategy.SOURCE_RELATIVE.value == "source-relative"
    assert ResolutionStrategy.PROJECT_RELATIVE.value == "project-relative"
    assert ResolutionStrategy.ABSOLUTE.value == "absolute"
    assert ResolutionStrategy.IMPORT_RELATIVE.value == "import-relative"
    assert ResolutionStrategy.URL.value == "url"
    assert ResolutionStrategy.DYNAMIC.value == "dynamic"
    assert ResolutionStrategy.UNKNOWN.value == "unknown"


def test_evidence_preserves_what_where_how_and_confidence():
    source = make_file("index.php")
    target = make_file("css/main.css", file_type="css")

    evidence = Evidence(
        source=source,
        location=SourceLocation(line=12, column=5),
        raw="css/main.css",
        kind=ReferenceKind.STYLESHEET,
        resolution=ResolutionStrategy.SOURCE_RELATIVE,
        target=target,
        confidence=ConfidenceScore.from_percent(96),
    )

    assert evidence.source is source
    assert evidence.line == 12
    assert evidence.raw == "css/main.css"
    assert evidence.normalized == "css/main.css"
    assert evidence.kind is ReferenceKind.STYLESHEET
    assert evidence.resolution is ResolutionStrategy.SOURCE_RELATIVE
    assert evidence.target is target
    assert evidence.target_identity == "css/main.css"
    assert evidence.confidence_percent == 96
    assert evidence.confidence_band is Confidence.CERTAIN


def test_unresolved_dynamic_evidence_is_preserved():
    source = make_file("index.php")

    evidence = Evidence(
        source=source,
        location=SourceLocation(line=8, column=1),
        raw="$template",
        kind=ReferenceKind.INCLUDE,
        resolution=ResolutionStrategy.DYNAMIC,
        confidence=ConfidenceScore.unknown(),
    )

    assert evidence.target is None
    assert evidence.target_identity is None
    assert evidence.raw == "$template"
    assert evidence.resolution is ResolutionStrategy.DYNAMIC
    assert evidence.confidence_percent is None
    assert evidence.confidence_band is Confidence.UNKNOWN


def test_evidence_keeps_normalized_form_when_provided():
    source = make_file("admin/index.php")
    target = make_file("css/main.css", file_type="css")

    evidence = Evidence(
        source=source,
        raw="../css/../css/main.css",
        normalized="css/main.css",
        kind=ReferenceKind.STYLESHEET,
        resolution=ResolutionStrategy.SOURCE_RELATIVE,
        target=target,
    )

    assert evidence.raw == "../css/../css/main.css"
    assert evidence.normalized == "css/main.css"
    assert evidence.target_identity == "css/main.css"
