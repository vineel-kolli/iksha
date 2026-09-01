from pathlib import Path

from iksha.domain.file import File
from iksha.domain.reference import (
    Confidence,
    ReferenceKind,
)
from iksha.domain.source_location import SourceLocation
from iksha.parsing.result import (
    Diagnostic,
    Observation,
    ParseResult,
)


def make_file(
    tmp_path: Path,
    relative_path: str,
    file_type: str = "php",
) -> File:
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")

    return File(
        path=path,
        relative_path=relative_path,
        file_type=file_type,
        size=path.stat().st_size,
    )


def test_reference_kinds_are_string_enums():
    assert ReferenceKind.INCLUDE.value == "include"
    assert ReferenceKind.REQUIRE.value == "require"
    assert ReferenceKind.IMPORT.value == "import"
    assert ReferenceKind.STYLESHEET.value == "stylesheet"
    assert ReferenceKind.SCRIPT.value == "script"
    assert ReferenceKind.DOM_SELECTOR.value == "dom_selector"
    assert ReferenceKind.CLASS.value == "class"
    assert ReferenceKind.ID.value == "id"


def test_confidence_levels_are_string_enums():
    assert Confidence.CERTAIN.value == "certain"
    assert Confidence.HIGH.value == "high"
    assert Confidence.MEDIUM.value == "medium"
    assert Confidence.LOW.value == "low"
    assert Confidence.UNKNOWN.value == "unknown"


def test_observation_preserves_authoritative_source(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    observation = Observation(
        source=source,
        kind=ReferenceKind.INCLUDE,
        value="header.php",
        location=SourceLocation(
            line=10,
            column=5,
        ),
        confidence=Confidence.CERTAIN,
    )

    assert observation.source is source


def test_observation_preserves_reference_kind(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    observation = Observation(
        source=source,
        kind=ReferenceKind.INCLUDE,
        value="header.php",
        location=SourceLocation(
            line=10,
            column=5,
        ),
        confidence=Confidence.CERTAIN,
    )

    assert observation.kind is ReferenceKind.INCLUDE


def test_observation_preserves_raw_reference_value(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    raw_value = '__DIR__ . "/includes/header.php"'

    observation = Observation(
        source=source,
        kind=ReferenceKind.INCLUDE,
        value=raw_value,
        location=SourceLocation(
            line=20,
            column=3,
        ),
        confidence=Confidence.MEDIUM,
    )

    assert observation.value == raw_value


def test_observation_preserves_location_and_confidence(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    location = SourceLocation(
        line=42,
        column=17,
    )

    observation = Observation(
        source=source,
        kind=ReferenceKind.REQUIRE,
        value="config.php",
        location=location,
        confidence=Confidence.HIGH,
    )

    assert observation.location is location
    assert observation.location.line == 42
    assert observation.location.column == 17
    assert observation.confidence is Confidence.HIGH


def test_observation_can_represent_stylesheet_reference(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    observation = Observation(
        source=source,
        kind=ReferenceKind.STYLESHEET,
        value="css/main.css",
        location=SourceLocation(
            line=25,
            column=10,
        ),
        confidence=Confidence.CERTAIN,
    )

    assert observation.kind is ReferenceKind.STYLESHEET
    assert observation.value == "css/main.css"


def test_observation_can_represent_script_reference(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    observation = Observation(
        source=source,
        kind=ReferenceKind.SCRIPT,
        value="js/app.js",
        location=SourceLocation(
            line=30,
            column=10,
        ),
        confidence=Confidence.CERTAIN,
    )

    assert observation.kind is ReferenceKind.SCRIPT
    assert observation.value == "js/app.js"


def test_observation_can_represent_generic_import(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "module.js",
        file_type="javascript",
    )

    observation = Observation(
        source=source,
        kind=ReferenceKind.IMPORT,
        value="./utils.js",
        location=SourceLocation(
            line=1,
            column=1,
        ),
        confidence=Confidence.CERTAIN,
    )

    assert observation.kind is ReferenceKind.IMPORT
    assert observation.value == "./utils.js"


def test_observation_can_represent_css_like_reference_without_new_model(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "main.css",
        file_type="css",
    )

    observation = Observation(
        source=source,
        kind=ReferenceKind.IMPORT,
        value="components/header.css",
        location=SourceLocation(
            line=3,
            column=1,
        ),
        confidence=Confidence.CERTAIN,
    )

    assert observation.source is source
    assert observation.kind is ReferenceKind.IMPORT
    assert observation.value == "components/header.css"


def test_parse_result_can_hold_mixed_reference_kinds(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    result = ParseResult()

    include = Observation(
        source=source,
        kind=ReferenceKind.INCLUDE,
        value="header.php",
        location=SourceLocation(
            line=1,
            column=1,
        ),
        confidence=Confidence.CERTAIN,
    )

    stylesheet = Observation(
        source=source,
        kind=ReferenceKind.STYLESHEET,
        value="css/main.css",
        location=SourceLocation(
            line=2,
            column=1,
        ),
        confidence=Confidence.CERTAIN,
    )

    script = Observation(
        source=source,
        kind=ReferenceKind.SCRIPT,
        value="js/app.js",
        location=SourceLocation(
            line=3,
            column=1,
        ),
        confidence=Confidence.CERTAIN,
    )

    result.observations.extend(
        [
            include,
            stylesheet,
            script,
        ]
    )

    assert len(result.observations) == 3
    assert result.observations[0].kind is ReferenceKind.INCLUDE
    assert result.observations[1].kind is ReferenceKind.STYLESHEET
    assert result.observations[2].kind is ReferenceKind.SCRIPT


def test_unknown_reference_kind_is_available_for_future_parsers():
    assert ReferenceKind.UNKNOWN.value == "unknown"


def test_diagnostic_and_reference_are_separate_concepts(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    observation = Observation(
        source=source,
        kind=ReferenceKind.INCLUDE,
        value="missing.php",
        location=SourceLocation(
            line=10,
            column=1,
        ),
        confidence=Confidence.CERTAIN,
    )

    diagnostic = Diagnostic(
        message="Target could not be resolved",
        severity="warning",
        source=source,
        location=observation.location,
    )

    assert observation.kind is ReferenceKind.INCLUDE
    assert diagnostic.message == "Target could not be resolved"
    assert diagnostic.severity == "warning"
    assert diagnostic.source is source
    assert diagnostic.location is observation.location
