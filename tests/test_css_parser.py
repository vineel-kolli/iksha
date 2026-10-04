from pathlib import Path

from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.parsing.css import CssParser
from iksha.source.document import SourceDocument


def make_css(
    tmp_path: Path,
    content: str,
) -> tuple[File, SourceDocument]:
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


def test_extracts_css_imports(tmp_path: Path) -> None:
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

    values = [
        item.value
        for item in result.observations
        if item.kind is ReferenceKind.IMPORT
    ]

    assert result.success is True
    assert values == [
        "components/header.css",
        "theme.css",
        "reset.css",
    ]

    import_observations = [
        item
        for item in result.observations
        if item.kind is ReferenceKind.IMPORT
    ]

    assert all(
        item.confidence is Confidence.CERTAIN
        for item in import_observations
    )


def test_css_import_preserves_location(tmp_path: Path) -> None:
    file, document = make_css(
        tmp_path,
        '@import "header.css";\n',
    )

    result = CssParser().parse(file, document)

    import_observation = next(
        item
        for item in result.observations
        if item.kind is ReferenceKind.IMPORT
    )

    assert import_observation.location is not None
    assert import_observation.location.line == 1


def test_extracts_css_selectors(tmp_path: Path) -> None:
    file, document = make_css(
        tmp_path,
        """
.card,
#login {
    color: red;
}

body.dark .card:hover {
    background: black;
}
""",
    )

    result = CssParser().parse(file, document)

    selectors = [
        item.value
        for item in result.observations
        if item.kind is ReferenceKind.DOM_SELECTOR
    ]

    assert selectors == [
        ".card,\n#login",
        "body.dark .card:hover",
    ]

    selector_observations = [
        item
        for item in result.observations
        if item.kind is ReferenceKind.DOM_SELECTOR
    ]

    assert all(
        item.confidence is Confidence.CERTAIN
        for item in selector_observations
    )


def test_css_selector_preserves_location(tmp_path: Path) -> None:
    file, document = make_css(
        tmp_path,
        """
@import "theme.css";

.card {
    color: red;
}
""",
    )

    result = CssParser().parse(file, document)

    selector = next(
        item
        for item in result.observations
        if item.kind is ReferenceKind.DOM_SELECTOR
    )

    assert selector.location is not None
    assert selector.location.line == 4