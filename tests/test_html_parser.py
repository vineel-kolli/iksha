from pathlib import Path

from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.parsing.html import HtmlParser
from iksha.source.document import SourceDocument


def make_html(tmp_path: Path, content: str):
    path = tmp_path / "index.html"
    path.write_text(content, encoding="utf-8")

    file = File(
        path=path,
        relative_path="index.html",
        file_type="html",
        size=path.stat().st_size,
    )
    document = SourceDocument(
        path=file.path,
        text=content,
        encoding="utf-8",
        byte_size=file.size,
        success=True,
        language="html",
    )
    return file, document


def test_extracts_stylesheet_script_class_and_id(tmp_path: Path):
    file, document = make_html(
        tmp_path,
        """
<link rel="stylesheet" href="css/main.css">
<script src="js/app.js"></script>
<div id="hero" class="card panel"></div>
""",
    )

    result = HtmlParser().parse(file, document)
    kinds = {
        (item.kind, item.value, item.confidence)
        for item in result.observations
    }

    assert (
        ReferenceKind.STYLESHEET,
        "css/main.css",
        Confidence.CERTAIN,
    ) in kinds
    assert (
        ReferenceKind.SCRIPT,
        "js/app.js",
        Confidence.CERTAIN,
    ) in kinds
    assert (ReferenceKind.ID, "hero", Confidence.CERTAIN) in kinds
    assert (ReferenceKind.CLASS, "card", Confidence.CERTAIN) in kinds
    assert (ReferenceKind.CLASS, "panel", Confidence.CERTAIN) in kinds


def test_dynamic_class_is_not_certain(tmp_path: Path):
    file, document = make_html(
        tmp_path,
        '<div class="<?= $class ?>"></div>',
    )

    result = HtmlParser().parse(file, document)

    assert len(result.observations) == 1
    observation = result.observations[0]
    assert observation.kind is ReferenceKind.CLASS
    assert observation.confidence is Confidence.UNKNOWN
    assert "<?=" in observation.value
