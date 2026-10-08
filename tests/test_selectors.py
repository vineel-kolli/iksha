from iksha.analysis.selectors import (
    SelectorKind,
    parse_selector,
)


def test_parses_class_selector():
    result = parse_selector(".card")

    assert result.raw == ".card"
    assert result.kind is SelectorKind.CLASS
    assert result.value == "card"


def test_parses_id_selector():
    result = parse_selector("#hero")

    assert result.raw == "#hero"
    assert result.kind is SelectorKind.ID
    assert result.value == "hero"


def test_parses_element_selector():
    result = parse_selector("button")

    assert result.raw == "button"
    assert result.kind is SelectorKind.ELEMENT
    assert result.value == "button"


def test_parses_descendant_selector_as_complex():
    result = parse_selector(".card .title")

    assert result.raw == ".card .title"
    assert result.kind is SelectorKind.COMPLEX
    assert result.value is None


def test_parses_child_selector_as_complex():
    result = parse_selector(".card > .title")

    assert result.raw == ".card > .title"
    assert result.kind is SelectorKind.COMPLEX
    assert result.value is None


def test_unsupported_selector_is_not_guessed():
    result = parse_selector('[data-state="open"]')

    assert result.raw == '[data-state="open"]'
    assert result.kind is SelectorKind.UNSUPPORTED
    assert result.value is None


def test_empty_selector_is_unsupported():
    result = parse_selector("   ")

    assert result.kind is SelectorKind.UNSUPPORTED
    assert result.value is None


def test_element_names_are_normalized_to_lowercase():
    result = parse_selector("BUTTON")

    assert result.kind is SelectorKind.ELEMENT
    assert result.value == "button"

def test_compound_class_selector_is_unsupported():
    result = parse_selector(".card.active")

    assert result.raw == ".card.active"
    assert result.kind is SelectorKind.UNSUPPORTED
    assert result.value is None


def test_compound_id_selector_is_unsupported():
    result = parse_selector("#main.active")

    assert result.raw == "#main.active"
    assert result.kind is SelectorKind.UNSUPPORTED
    assert result.value is None


def test_selector_with_more_than_two_components_is_unsupported():
    result = parse_selector(".card .title .label")

    assert result.raw == ".card .title .label"
    assert result.kind is SelectorKind.UNSUPPORTED
    assert result.value is None