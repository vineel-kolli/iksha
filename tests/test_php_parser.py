from pathlib import Path

from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.parsing.php import PHPParser
from iksha.source.document import SourceDocument


def make_source(tmp_path: Path, content: str):
    path = tmp_path / "index.php"
    path.write_text(content, encoding="utf-8")

    file = File(
        path=path,
        relative_path="index.php",
        file_type="php",
        size=path.stat().st_size,
    )

    document = SourceDocument(
        path=file.path,
        text=content,
        encoding="utf-8",
        byte_size=path.stat().st_size,
        success=True,
    )

    return file, document


def test_finds_include(tmp_path: Path):
    file, document = make_source(
        tmp_path,
        '<?php include "header.php"; ?>',
    )

    result = PHPParser().parse(file, document)

    assert result.success is True
    assert len(result.observations) == 1

    observation = result.observations[0]

    assert observation.kind == ReferenceKind.INCLUDE
    assert observation.value == "header.php"
    assert observation.source is file
    assert observation.confidence == Confidence.CERTAIN


def test_finds_include_once(tmp_path: Path):
    file, document = make_source(
        tmp_path,
        "<?php include_once 'header.php'; ?>",
    )

    result = PHPParser().parse(file, document)

    assert len(result.observations) == 1

    observation = result.observations[0]

    assert observation.kind == ReferenceKind.INCLUDE
    assert observation.value == "header.php"


def test_finds_require(tmp_path: Path):
    file, document = make_source(
        tmp_path,
        '<?php require "config.php"; ?>',
    )

    result = PHPParser().parse(file, document)

    assert len(result.observations) == 1

    observation = result.observations[0]

    assert observation.kind == ReferenceKind.REQUIRE
    assert observation.value == "config.php"


def test_finds_require_once(tmp_path: Path):
    file, document = make_source(
        tmp_path,
        "<?php require_once 'bootstrap.php'; ?>",
    )

    result = PHPParser().parse(file, document)

    assert len(result.observations) == 1

    observation = result.observations[0]

    assert observation.kind == ReferenceKind.REQUIRE
    assert observation.value == "bootstrap.php"


def test_finds_multiple_php_references(tmp_path: Path):
    content = """<?php
include "header.php";
include_once "nav.php";
require "config.php";
require_once "bootstrap.php";
?>"""

    file, document = make_source(
        tmp_path,
        content,
    )

    result = PHPParser().parse(file, document)

    assert len(result.observations) == 4

    assert [
        observation.kind
        for observation in result.observations
    ] == [
        ReferenceKind.INCLUDE,
        ReferenceKind.INCLUDE,
        ReferenceKind.REQUIRE,
        ReferenceKind.REQUIRE,
    ]

    assert [
        observation.value
        for observation in result.observations
    ] == [
        "header.php",
        "nav.php",
        "config.php",
        "bootstrap.php",
    ]


def test_preserves_source_location(tmp_path: Path):
    content = """<?php

echo "Hello";

include "header.php";

?>"""

    file, document = make_source(
        tmp_path,
        content,
    )

    result = PHPParser().parse(file, document)

    assert len(result.observations) == 1

    observation = result.observations[0]

    assert observation.location is not None
    assert observation.location.line == 5
    assert observation.location.column > 0


def test_handles_double_and_single_quotes(tmp_path: Path):
    content = """<?php
include "header.php";
require 'config.php';
?>"""

    file, document = make_source(
        tmp_path,
        content,
    )

    result = PHPParser().parse(file, document)

    assert len(result.observations) == 2

    assert result.observations[0].value == "header.php"
    assert result.observations[1].value == "config.php"


def test_ignores_similar_words_inside_strings(tmp_path: Path):
    content = """<?php
echo 'include "fake.php";';
echo "require 'fake2.php';";
?>"""

    file, document = make_source(
        tmp_path,
        content,
    )

    result = PHPParser().parse(file, document)

    assert result.observations == []


def test_ignores_comments(tmp_path: Path):
    content = """<?php
// include "fake.php";
/* require "fake2.php"; */

include "real.php";
?>"""

    file, document = make_source(
        tmp_path,
        content,
    )

    result = PHPParser().parse(file, document)

    assert len(result.observations) == 1
    assert result.observations[0].value == "real.php"


def test_dynamic_reference_is_not_claimed_as_resolved(
    tmp_path: Path,
):
    content = """<?php
$template = "header.php";
include $template;
?>"""

    file, document = make_source(
        tmp_path,
        content,
    )

    result = PHPParser().parse(file, document)

    assert len(result.observations) == 1

    observation = result.observations[0]

    assert observation.kind == ReferenceKind.INCLUDE
    assert observation.value == "$template"
    assert observation.confidence != Confidence.CERTAIN


def test_parser_does_not_resolve_files(tmp_path: Path):
    content = '<?php include "missing.php"; ?>'

    file, document = make_source(
        tmp_path,
        content,
    )

    result = PHPParser().parse(file, document)

    observation = result.observations[0]

    assert observation.value == "missing.php"
    assert observation.source is file


def test_parser_handles_empty_document(tmp_path: Path):
    file, document = make_source(
        tmp_path,
        "",
    )

    result = PHPParser().parse(file, document)

    assert result.success is True
    assert result.observations == []
    assert result.diagnostics == []


def test_parser_handles_php_and_html_mixed_content(
    tmp_path: Path,
):
    content = """<!DOCTYPE html>
<html>
<body>
<?php include "header.php"; ?>
<h1>Hello</h1>
<?php require_once "footer.php"; ?>
</body>
</html>"""

    file, document = make_source(
        tmp_path,
        content,
    )

    result = PHPParser().parse(file, document)

    assert len(result.observations) == 2

    assert result.observations[0].value == "header.php"
    assert result.observations[1].value == "footer.php"
