"""
CSS selector semantics for IKSHA.

This module converts authored CSS selectors into a conservative,
normalized representation that later analysis stages can correlate
with HTML/JavaScript usage evidence.

It does not build a DOM and does not decide file-level dead-code state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SelectorKind(str, Enum):
    """Supported semantic selector categories."""

    CLASS = "class"
    ID = "id"
    ELEMENT = "element"
    COMPLEX = "complex"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class ParsedSelector:
    """Normalized representation of a CSS selector."""

    raw: str
    kind: SelectorKind
    value: str | None = None


def parse_selector(selector: str) -> ParsedSelector:
    """
    Parse a CSS selector conservatively.

    The current semantic layer recognizes only:
      - .class
      - #id
      - element
      - two-component descendant selectors
      - two-component direct-child selectors

    Selectors containing combinators, attribute selectors, pseudo-classes,
    pseudo-elements, compound selectors, multiple components, or other
    unsupported syntax are preserved as UNSUPPORTED or COMPLEX.
    """
    raw = selector.strip()

    if not raw:
        return ParsedSelector(
            raw=raw,
            kind=SelectorKind.UNSUPPORTED,
        )

    if any(token in raw for token in (",", "[", "]", ":", "*", "+", "~")):
        return ParsedSelector(
            raw=raw,
            kind=SelectorKind.UNSUPPORTED,
        )

    if ">" in raw:
        parts = tuple(
            part.strip()
            for part in raw.split(">")
        )

        if len(parts) != 2 or not all(parts):
            return ParsedSelector(
                raw=raw,
                kind=SelectorKind.UNSUPPORTED,
            )

        if not all(_is_simple_selector(part) for part in parts):
            return ParsedSelector(
                raw=raw,
                kind=SelectorKind.UNSUPPORTED,
            )

        return ParsedSelector(
            raw=raw,
            kind=SelectorKind.COMPLEX,
        )

    parts = tuple(
        part
        for part in raw.split()
        if part
    )

    if len(parts) > 2:
        return ParsedSelector(
            raw=raw,
            kind=SelectorKind.UNSUPPORTED,
        )

    if len(parts) == 2:
        if not all(_is_simple_selector(part) for part in parts):
            return ParsedSelector(
                raw=raw,
                kind=SelectorKind.UNSUPPORTED,
            )

        return ParsedSelector(
            raw=raw,
            kind=SelectorKind.COMPLEX,
        )

    token = parts[0]

    if token.startswith(".") and _is_class_selector(token):
        return ParsedSelector(
            raw=raw,
            kind=SelectorKind.CLASS,
            value=token[1:],
        )

    if token.startswith("#") and _is_id_selector(token):
        return ParsedSelector(
            raw=raw,
            kind=SelectorKind.ID,
            value=token[1:],
        )

    if _is_element_name(token):
        return ParsedSelector(
            raw=raw,
            kind=SelectorKind.ELEMENT,
            value=token.lower(),
        )

    return ParsedSelector(
        raw=raw,
        kind=SelectorKind.UNSUPPORTED,
    )


def _is_element_name(value: str) -> bool:
    """Return whether value is a simple CSS element name."""
    if not value:
        return False

    first = value[0]

    if not (first.isalpha() or first == "_"):
        return False

    return all(
        character.isalnum() or character in {"-", "_"}
        for character in value
    )


def _is_simple_selector(value: str) -> bool:
    """Return whether value is one supported simple selector."""
    return (
        _is_class_selector(value)
        or _is_id_selector(value)
        or _is_element_name(value)
    )


def _is_class_selector(value: str) -> bool:
    """Return whether value is a simple class selector."""
    if not value.startswith(".") or len(value) == 1:
        return False

    return _is_identifier(value[1:])


def _is_id_selector(value: str) -> bool:
    """Return whether value is a simple ID selector."""
    if not value.startswith("#") or len(value) == 1:
        return False

    return _is_identifier(value[1:])


def _is_identifier(value: str) -> bool:
    """Return whether value is a supported CSS identifier."""
    if not value:
        return False

    first = value[0]

    if not (first.isalpha() or first in {"_", "-"}):
        return False

    return all(
        character.isalnum() or character in {"-", "_"}
        for character in value
    )