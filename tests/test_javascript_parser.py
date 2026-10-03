from pathlib import Path

from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.parsing.javascript import JavascriptParser
from iksha.source.document import SourceDocument


def make_js(tmp_path: Path, content: str):
    path = tmp_path / "app.js"
    path.write_text(content, encoding="utf-8")

    file = File(
        path=path,
        relative_path="app.js",
        file_type="javascript",
        size=path.stat().st_size,
    )
    document = SourceDocument(
        path=file.path,
        text=content,
        encoding="utf-8",
        byte_size=file.size,
        success=True,
        language="javascript",
    )
    return file, document


def test_extracts_js_imports_and_dom_usage(tmp_path: Path):
    file, document = make_js(
        tmp_path,
        """
import helper from "./utils.js";
import("./lazy.js");
document.querySelector(".sidebar-open");
document.getElementById("modal");
element.classList.add("active");
element.className = "hero";
element.setAttribute("class", "card");
""",
    )

    result = JavascriptParser().parse(file, document)
    kinds = {
        (item.kind, item.value)
        for item in result.observations
    }

    assert (ReferenceKind.IMPORT, "./utils.js") in kinds
    assert (ReferenceKind.IMPORT, "./lazy.js") in kinds
    assert (ReferenceKind.DOM_SELECTOR, ".sidebar-open") in kinds
    assert (ReferenceKind.ID, "modal") in kinds
    assert (ReferenceKind.CLASS, "active") in kinds
    assert (ReferenceKind.CLASS, "hero") in kinds
    assert (ReferenceKind.CLASS, "card") in kinds


def test_dynamic_classlist_is_preserved(tmp_path: Path):
    file, document = make_js(
        tmp_path,
        "element.classList.add(className);",
    )

    result = JavascriptParser().parse(file, document)

    assert len(result.observations) == 1
    observation = result.observations[0]
    assert observation.kind is ReferenceKind.CLASS
    assert observation.confidence is Confidence.UNKNOWN


def test_ternary_class_names_are_both_recorded(tmp_path: Path):
    file, document = make_js(
        tmp_path,
        'element.classList.add(on ? "active" : "hidden");',
    )

    result = JavascriptParser().parse(file, document)
    values = [item.value for item in result.observations]

    assert values == ["active", "hidden"]
    assert all(
        item.confidence is Confidence.LOW
        for item in result.observations
    )


def test_comments_are_ignored(tmp_path: Path):
    file, document = make_js(
        tmp_path,
        """
// document.querySelector(".nope")
/* classList.add("nope") */
document.querySelector(".yes");
""",
    )

    result = JavascriptParser().parse(file, document)

    assert [
        item.value for item in result.observations
    ] == [".yes"]
