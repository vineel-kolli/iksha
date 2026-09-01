from pathlib import Path

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
