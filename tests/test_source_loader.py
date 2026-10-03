from pathlib import Path

import pytest

from iksha.domain.file import File
from iksha.source.loader import SourceLoader


def test_loads_utf8_text(tmp_path: Path):
    path = tmp_path / "index.php"
    path.write_text(
        "<?php echo 'hello'; ?>",
        encoding="utf-8",
    )

    document = SourceLoader().load(path)

    assert document.success is True
    assert document.text == "<?php echo 'hello'; ?>"
    assert document.encoding == "utf-8"
    assert document.path == path.resolve()


def test_loads_utf8_bom(tmp_path: Path):
    path = tmp_path / "index.php"

    path.write_bytes(
        b"\xef\xbb\xbf<?php echo 'hello'; ?>"
    )

    document = SourceLoader().load(path)

    assert document.success is True
    assert document.text == "<?php echo 'hello'; ?>"
    assert document.encoding == "utf-8-sig"


def test_loads_utf16(tmp_path: Path):
    path = tmp_path / "index.php"

    path.write_text(
        "<?php echo 'hello'; ?>",
        encoding="utf-16",
    )

    document = SourceLoader().load(path)

    assert document.success is True
    assert document.text == "<?php echo 'hello'; ?>"
    assert document.encoding == "utf-16"


def test_loads_empty_file(tmp_path: Path):
    path = tmp_path / "empty.css"
    path.write_bytes(b"")

    document = SourceLoader().load(path)

    assert document.success is True
    assert document.text == ""
    assert document.path == path.resolve()


def test_preserves_newlines(tmp_path: Path):
    path = tmp_path / "style.css"

    content = "body {\n    color: red;\n}\n"

    path.write_text(
        content,
        encoding="utf-8",
        newline="",
    )

    document = SourceLoader().load(path)

    assert document.success is True
    assert document.text == content


def test_missing_file_returns_failed_document(tmp_path: Path):
    path = tmp_path / "missing.php"

    document = SourceLoader().load(path)

    assert document.success is False
    assert document.path == path.resolve()
    assert document.text == ""
    assert document.error is not None


def test_invalid_utf8_does_not_silently_corrupt_source(
    tmp_path: Path,
):
    path = tmp_path / "broken.css"

    path.write_bytes(
        b"body { color: \xff\xfe; }"
    )

    document = SourceLoader().load(path)

    assert document.success is False
    assert document.text == ""
    assert document.error is not None


def test_document_contains_byte_size(tmp_path: Path):
    path = tmp_path / "app.js"

    content = "console.log('hello');"

    path.write_text(
        content,
        encoding="utf-8",
    )

    document = SourceLoader().load(path)

    assert document.success is True
    assert document.byte_size == len(
        content.encode("utf-8")
    )


def test_loader_accepts_string_path(tmp_path: Path):
    path = tmp_path / "index.html"

    path.write_text(
        "<html></html>",
        encoding="utf-8",
    )

    document = SourceLoader().load(str(path))

    assert document.success is True
    assert document.path == path.resolve()


def test_computes_line_offsets_and_count(tmp_path: Path):
    path = tmp_path / "style.css"
    content = "body {\n    color: red;\n}\n"

    path.write_text(
        content,
        encoding="utf-8",
        newline="",
    )

    document = SourceLoader().load(path)

    assert document.success is True
    assert document.line_count == 4
    assert document.line_offsets[0] == 0
    assert document.text[document.line_offsets[1]:].startswith(
        "    color: red;"
    )

    first = document.location_at(0)
    second = document.location_at(document.line_offsets[1])
    color = document.location_at(document.line_offsets[1] + 4)

    assert first.line == 1 and first.column == 1
    assert second.line == 2 and second.column == 1
    assert color.line == 2 and color.column == 5
    assert color.offset == document.line_offsets[1] + 4
    assert color.column_precise is True


def test_empty_document_has_no_lines(tmp_path: Path):
    path = tmp_path / "empty.css"
    path.write_bytes(b"")

    document = SourceLoader().load(path)
    location = document.location_at(0)

    assert document.line_count == 0
    assert document.line_offsets == ()
    assert location.line == 1
    assert location.column == 1
    assert location.offset == 0


def test_minified_locations_prefer_character_offset(tmp_path: Path):
    path = tmp_path / "app.min.js"
    path.write_text(
        "function x(){return 1;}",
        encoding="utf-8",
    )

    file = File(
        path=path,
        relative_path="app.min.js",
        file_type="javascript",
        minified=True,
    )

    document = SourceLoader().load(file)
    location = document.location_at(9)

    assert document.language == "javascript"
    assert document.minified is True
    assert location.line == 1
    assert location.column == 1
    assert location.offset == 9
    assert location.column_precise is False


def test_size_cap_truncates_without_failing(tmp_path: Path):
    path = tmp_path / "large.php"
    path.write_bytes(b"abcdef")

    document = SourceLoader(
        max_file_size_mb=1 / (1024 * 1024),
    ).load(path)

    assert document.success is True
    assert document.truncated is True
    assert document.text == "a"
    assert document.byte_size == 6


def test_loader_rejects_non_positive_size_cap():
    with pytest.raises(ValueError):
        SourceLoader(max_file_size_mb=0)

