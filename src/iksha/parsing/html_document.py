"""
parsing/html_document.py
Structured HTML document model used by CSS semantic analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from iksha.domain.source_location import SourceLocation


@dataclass
class HtmlElement:
    """One HTML element in a parsed document."""

    tag: str
    attributes: dict[str, str]
    location: SourceLocation | None = None
    parent: HtmlElement | None = None
    children: list[HtmlElement] = field(default_factory=list)

    def add_child(self, child: HtmlElement) -> None:
        """Attach a child element and establish its parent."""
        child.parent = self
        self.children.append(child)

    @property
    def classes(self) -> frozenset[str]:
        """Return normalized class names on the element."""
        value = self.attributes.get("class", "")
        return frozenset(value.split())

    @property
    def element_id(self) -> str | None:
        """Return the element ID when present."""
        value = self.attributes.get("id", "").strip()
        return value or None


@dataclass
class HtmlDocument:
    """Structured representation of one HTML source document."""

    elements: list[HtmlElement] = field(default_factory=list)

    def add_element(self, element: HtmlElement) -> None:
        """Register a top-level element."""
        self.elements.append(element)

    def all_elements(self) -> tuple[HtmlElement, ...]:
        """Return all elements in deterministic document order."""

        result: list[HtmlElement] = []

        def visit(element: HtmlElement) -> None:
            result.append(element)

            for child in element.children:
                visit(child)

        for element in self.elements:
            visit(element)

        return tuple(result)