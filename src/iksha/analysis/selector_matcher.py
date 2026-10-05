"""
Semantic CSS selector matching against structured HTML documents.

This module determines whether supported CSS selectors match elements
in an HtmlDocument. Unsupported selector semantics are handled
conservatively and never guessed.
"""

from __future__ import annotations

from iksha.analysis.selectors import (
    SelectorKind,
    parse_selector,
)
from iksha.parsing.html_document import (
    HtmlDocument,
    HtmlElement,
)


def match_selector(
    selector: str,
    document: HtmlDocument,
) -> tuple[HtmlElement, ...]:
    """
    Return HTML elements matched by a supported CSS selector.

    Supported selectors:
      - element
      - .class
      - #id
      - descendant selectors
      - direct-child selectors

    Unsupported selectors return no matches.
    """

    parsed = parse_selector(selector)

    if parsed.kind is SelectorKind.CLASS:
        return tuple(
            element
            for element in document.all_elements()
            if parsed.value in element.classes
        )

    if parsed.kind is SelectorKind.ID:
        return tuple(
            element
            for element in document.all_elements()
            if element.element_id == parsed.value
        )

    if parsed.kind is SelectorKind.ELEMENT:
        return tuple(
            element
            for element in document.all_elements()
            if element.tag == parsed.value
        )

    if parsed.kind is SelectorKind.COMPLEX:
        return _match_complex_selector(
            parsed.raw,
            document,
        )

    return ()


def _match_complex_selector(
    selector: str,
    document: HtmlDocument,
) -> tuple[HtmlElement, ...]:
    """Match supported descendant and direct-child selectors."""

    if ">" in selector:
        parts = tuple(
            part.strip()
            for part in selector.split(">")
        )

        if len(parts) != 2 or not all(parts):
            return ()

        ancestor_selector, child_selector = parts

        ancestor_matches = _match_simple_selector(
            ancestor_selector,
            document,
        )

        child_matches: list[HtmlElement] = []

        for ancestor in ancestor_matches:
            for child in ancestor.children:
                if _matches_simple_selector(
                    child_selector,
                    child,
                ):
                    child_matches.append(child)

        return _unique_elements(child_matches)
        

    parts = tuple(
        part
        for part in selector.split()
        if part
    )

    if len(parts) != 2:
        return ()

    ancestor_selector, descendant_selector = parts

    ancestor_matches = _match_simple_selector(
        ancestor_selector,
        document,
    )

    descendant_matches: list[HtmlElement] = []

    for ancestor in ancestor_matches:
        for element in _descendants(ancestor):
            if _matches_simple_selector(
                descendant_selector,
                element,
            ):
                descendant_matches.append(element)

    return _unique_elements(descendant_matches)


def _match_simple_selector(
    selector: str,
    document: HtmlDocument,
) -> tuple[HtmlElement, ...]:
    """Match one simple selector against a document."""

    parsed = parse_selector(selector)

    if parsed.kind is SelectorKind.CLASS:
        return tuple(
            element
            for element in document.all_elements()
            if parsed.value in element.classes
        )

    if parsed.kind is SelectorKind.ID:
        return tuple(
            element
            for element in document.all_elements()
            if element.element_id == parsed.value
        )

    if parsed.kind is SelectorKind.ELEMENT:
        return tuple(
            element
            for element in document.all_elements()
            if element.tag == parsed.value
        )

    return ()


def _matches_simple_selector(
    selector: str,
    element: HtmlElement,
) -> bool:
    """Return whether one element matches a simple selector."""

    parsed = parse_selector(selector)

    if parsed.kind is SelectorKind.CLASS:
        return parsed.value in element.classes

    if parsed.kind is SelectorKind.ID:
        return element.element_id == parsed.value

    if parsed.kind is SelectorKind.ELEMENT:
        return element.tag == parsed.value

    return False


def _descendants(
    element: HtmlElement,
) -> tuple[HtmlElement, ...]:
    """Return all descendants in document order."""

    result: list[HtmlElement] = []

    def visit(current: HtmlElement) -> None:
        for child in current.children:
            result.append(child)
            visit(child)

    visit(element)

    return tuple(result)

def _unique_elements(
    elements: list[HtmlElement],
) -> tuple[HtmlElement, ...]:
    """Return elements in order without duplicating object identities."""

    result: list[HtmlElement] = []
    seen: set[int] = set()

    for element in elements:
        identity = id(element)

        if identity in seen:
            continue

        seen.add(identity)
        result.append(element)

    return tuple(result)