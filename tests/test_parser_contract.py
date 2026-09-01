from pathlib import Path

from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.domain.source_location import SourceLocation
from iksha.parsing.protocol import Parser
from iksha.parsing.result import (
    Diagnostic,
    Observation,
    ParseResult,
)
from iksha.source.document import SourceDocument


def make_file(tmp_path: Path) -> File:
    path = tmp_path / "index.php"
    path.write_text(
        "<?php echo 'hello'; ?>",
        encoding="utf-8",
    )

    return File(
        path=path,
        relative_path="index.php",
        file_type="php",
        size=path.stat().st_size,
    )


def make_document(file: File) -> SourceDocument:
    return SourceDocument(
        path=file.path,
        text="<?php echo 'hello'; ?>",
        encoding="utf-8",
        byte_size=file.size,
        success=True,
    )


def test_observation_preserves_source_evidence(tmp_path: Path):
    file = make_file(tmp_path)

    observation = Observation(
        source=file,
        kind=ReferenceKind.INCLUDE,
        value="header.php",
        location=SourceLocation(
            line=10,
            column=5,
        ),
        confidence=Confidence.HIGH,
    )

    assert observation.source is file
    assert observation.kind == ReferenceKind.INCLUDE
    assert observation.value == "header.php"
    assert observation.location.line == 10
    assert observation.location.column == 5
    assert observation.confidence == Confidence.HIGH


def test_observation_can_have_no_location():
    observation = Observation(
        source=None,
        kind=ReferenceKind.UNKNOWN,
        value="unknown",
    )

    assert observation.location is None


def test_parse_result_starts_empty():
    result = ParseResult()

    assert result.observations == []
    assert result.diagnostics == []
    assert result.success is True


def test_parse_result_stores_observations(tmp_path: Path):
    file = make_file(tmp_path)

    observation = Observation(
        source=file,
        kind=ReferenceKind.CLASS,
        value="card",
    )

    result = ParseResult(
        observations=[observation],
    )

    assert len(result.observations) == 1
    assert result.observations[0] is observation


def test_parse_result_stores_diagnostics():
    diagnostic = Diagnostic(
        message="Unexpected token",
        severity="error",
    )

    result = ParseResult(
        diagnostics=[diagnostic],
    )

    assert len(result.diagnostics) == 1
    assert result.diagnostics[0] is diagnostic
    assert result.success is False


def test_diagnostic_supports_location(tmp_path: Path):
    file = make_file(tmp_path)

    diagnostic = Diagnostic(
        message="Malformed source",
        severity="warning",
        source=file,
        location=SourceLocation(
            line=4,
            column=8,
        ),
    )

    assert diagnostic.source is file
    assert diagnostic.location.line == 4
    assert diagnostic.location.column == 8
    assert diagnostic.severity == "warning"


def test_parser_protocol_requires_parse_method():
    assert hasattr(Parser, "parse")


def test_parser_protocol_is_runtime_checkable():
    class FakeParser:
        def parse(
            self,
            file: File,
            document: SourceDocument,
        ) -> ParseResult:
            return ParseResult()

    parser = FakeParser()

    assert isinstance(parser, Parser)


def test_parser_protocol_rejects_missing_parse_method():
    class NotAParser:
        pass

    assert not isinstance(NotAParser(), Parser)


def test_parser_receives_file_and_document(tmp_path: Path):
    class FakeParser:
        def parse(
            self,
            file: File,
            document: SourceDocument,
        ) -> ParseResult:
            assert file.path == document.path

            return ParseResult()

    file = make_file(tmp_path)
    document = make_document(file)

    result = FakeParser().parse(
        file,
        document,
    )

    assert isinstance(result, ParseResult)


def test_parse_result_can_contain_multiple_observation_types(
    tmp_path: Path,
):
    file = make_file(tmp_path)

    observations = [
        Observation(
            source=file,
            kind=ReferenceKind.CLASS,
            value="card",
        ),
        Observation(
            source=file,
            kind=ReferenceKind.ID,
            value="main",
        ),
        Observation(
            source=file,
            kind=ReferenceKind.STYLESHEET,
            value="style.css",
        ),
    ]

    result = ParseResult(
        observations=observations,
    )

    assert len(result.observations) == 3
    assert {
        observation.kind
        for observation in result.observations
    } == {
        ReferenceKind.CLASS,
        ReferenceKind.ID,
        ReferenceKind.STYLESHEET,
    }
