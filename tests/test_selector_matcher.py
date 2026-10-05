from iksha.analysis.selector_matcher import match_selector
from iksha.parsing.html_document import (
    HtmlDocument,
    HtmlElement,
)


def make_document() -> HtmlDocument:
    document = HtmlDocument()

    main = HtmlElement(
        tag="main",
        attributes={},
    )

    card = HtmlElement(
        tag="div",
        attributes={
            "class": "card",
        },
    )

    title = HtmlElement(
        tag="h2",
        attributes={
            "class": "title",
        },
    )

    nested = HtmlElement(
        tag="span",
        attributes={
            "class": "title",
        },
    )

    card.add_child(title)
    title.add_child(nested)
    main.add_child(card)
    document.add_element(main)

    return document


def test_matches_element_selector():
    document = make_document()

    result = match_selector(
        "h2",
        document,
    )

    assert [element.tag for element in result] == [
        "h2",
    ]


def test_matches_class_selector():
    document = make_document()

    result = match_selector(
        ".title",
        document,
    )

    assert [element.tag for element in result] == [
        "h2",
        "span",
    ]


def test_matches_id_selector():
    document = HtmlDocument()

    element = HtmlElement(
        tag="div",
        attributes={
            "id": "hero",
        },
    )

    document.add_element(element)

    result = match_selector(
        "#hero",
        document,
    )

    assert result == (element,)


def test_matches_descendant_selector():
    document = make_document()

    result = match_selector(
        ".card .title",
        document,
    )

    assert [element.tag for element in result] == [
        "h2",
        "span",
    ]


def test_matches_direct_child_selector():
    document = make_document()

    result = match_selector(
        ".card > .title",
        document,
    )

    assert [element.tag for element in result] == [
        "h2",
    ]


def test_unsupported_selector_returns_no_matches():
    document = make_document()

    result = match_selector(
        '[data-state="open"]',
        document,
    )

    assert result == ()
def test_descendant_selector_does_not_match_ancestor():
    document = make_document()

    result = match_selector(
        ".title .card",
        document,
    )

    assert result == ()


def test_direct_child_selector_does_not_match_deeper_descendant():
    document = make_document()

    result = match_selector(
        ".card > .title",
        document,
    )

    assert [element.tag for element in result] == ["h2"]

    span = document.all_elements()[-1]

    assert span not in result


def test_multiple_matching_ancestors_do_not_duplicate_results():
    document = HtmlDocument()

    first_card = HtmlElement(
        tag="div",
        attributes={"class": "card"},
    )
    first_title = HtmlElement(
        tag="h2",
        attributes={"class": "title"},
    )
    first_card.add_child(first_title)

    second_card = HtmlElement(
        tag="div",
        attributes={"class": "card"},
    )
    second_title = HtmlElement(
        tag="h2",
        attributes={"class": "title"},
    )
    second_card.add_child(second_title)

    document.add_element(first_card)
    document.add_element(second_card)

    result = match_selector(
        ".card > .title",
        document,
    )

    assert result == (
        first_title,
        second_title,
    )


def test_unsupported_complex_selector_is_not_guessed():
    document = make_document()

    result = match_selector(
        ".card .title .missing",
        document,
    )

    assert result == ()