from pathlib import Path

from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.parsing.css import CssParser
from iksha.source.document import SourceDocument


def make_css(tmp_path: Path, content: str):
    path = tmp_path / "main.css"
    path.write_text(content, encoding="utf-8")

    file = File(
        path=path,
        relative_path="main.css",
        file_type="css",
        size=path.stat().st_size,
    )
    document = SourceDocument(
        path=file.path,
        text=content,
        encoding="utf-8",
        byte_size=file.size,
        success=True,
        language="css",
    )
    return file, document


def test_extracts_css_imports(tmp_path: Path):
    file, document = make_css(
        tmp_path,
        """
@import "components/header.css";
@import url("theme.css");
@import url(reset.css);
body { color: red; }
""",
    )

    result = CssParser().parse(file, document)
    values = [item.value for item in result.observations]

    assert result.success is True
    assert values == [
        "components/header.css",
        "theme.css",
        "reset.css",
    ]
    assert all(
        item.kind is ReferenceKind.IMPORT
        for item in result.observations
    )
    assert all(
        item.confidence is Confidence.CERTAIN
        for item in result.observations
    )


def test_css_import_preserves_location(tmp_path: Path):
    file, document = make_css(
        tmp_path,
        '@import "header.css";\n',
    )

    result = CssParser().parse(file, document)

    assert result.observations[0].location is not None
    assert result.observations[0].location.line == 1
