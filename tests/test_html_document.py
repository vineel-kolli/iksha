from iksha.domain.source_location import SourceLocation
from iksha.parsing.html_document import (
    HtmlDocument,
    HtmlElement,
)
from iksha.parsing.html import HtmlParser
from iksha.domain.file import File
from iksha.source.document import SourceDocument
from pathlib import Path



def test_element_stores_tag_attributes_and_location():
    location = SourceLocation(
        line=2,
        column=5,
        offset=10,
    )

    element = HtmlElement(
        tag="div",
        attributes={
            "class": "card panel",
            "id": "hero",
        },
        location=location,
    )

    assert element.tag == "div"
    assert element.attributes["class"] == "card panel"
    assert element.location == location


def test_classes_are_normalized():
    element = HtmlElement(
        tag="div",
        attributes={
            "class": "card panel card",
        },
    )

    assert element.classes == frozenset({"card", "panel"})


def test_element_id_returns_value():
    element = HtmlElement(
        tag="div",
        attributes={
            "id": "hero",
        },
    )

    assert element.element_id == "hero"


def test_missing_element_id_returns_none():
    element = HtmlElement(
        tag="div",
        attributes={},
    )

    assert element.element_id is None


def test_add_child_establishes_parent_relationship():
    parent = HtmlElement(
        tag="section",
        attributes={},
    )
    child = HtmlElement(
        tag="div",
        attributes={},
    )

    parent.add_child(child)

    assert parent.children == [child]
    assert child.parent is parent


def test_document_returns_elements_in_document_order():
    root = HtmlElement(
        tag="main",
        attributes={},
    )
    first = HtmlElement(
        tag="section",
        attributes={},
    )
    nested = HtmlElement(
        tag="div",
        attributes={},
    )
    second = HtmlElement(
        tag="footer",
        attributes={},
    )

    root.add_child(first)
    first.add_child(nested)

    document = HtmlDocument(
        elements=[root, second],
    )

    assert document.all_elements() == (
        root,
        first,
        nested,
        second,
    )


def make_source(tmp_path: Path, content: str):
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


def test_html_parser_builds_nested_document(tmp_path: Path):
    file, document = make_source(
        tmp_path,
        "<main><section><div class='card'></div></section></main>",
    )

    html_document = HtmlParser().parse_document(
        file,
        document,
    )

    elements = html_document.all_elements()

    assert [element.tag for element in elements] == [
        "main",
        "section",
        "div",
    ]

    assert elements[0].children == [elements[1]]
    assert elements[1].parent is elements[0]
    assert elements[1].children == [elements[2]]
    assert elements[2].parent is elements[1]

    assert elements[2].classes == frozenset({"card"})


def test_html_parser_handles_void_elements(tmp_path: Path):
    file, document = make_source(
        tmp_path,
        "<main><img src='x.png'><div class='card'></div></main>",
    )

    html_document = HtmlParser().parse_document(
        file,
        document,
    )

    elements = html_document.all_elements()

    assert [element.tag for element in elements] == [
        "main",
        "img",
        "div",
    ]

    assert elements[1].parent is elements[0]
    assert elements[2].parent is elements[0]


def test_parse_document_preserves_element_attributes(tmp_path: Path):
    file, document = make_source(
        tmp_path,
        '<div id="hero" class="card panel"></div>',
    )

    html_document = HtmlParser().parse_document(
        file,
        document,
    )

    element = html_document.all_elements()[0]

    assert element.tag == "div"
    assert element.attributes["id"] == "hero"
    assert element.attributes["class"] == "card panel"