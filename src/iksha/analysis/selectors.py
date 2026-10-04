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

    Selectors containing combinators, attribute selectors, pseudo-classes,
    pseudo-elements, multiple compound components, or other unsupported
    syntax are preserved as COMPLEX or UNSUPPORTED rather than guessed.
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
        return ParsedSelector(
            raw=raw,
            kind=SelectorKind.COMPLEX,
        )

    parts = raw.split()

    if len(parts) > 1:
        return ParsedSelector(
            raw=raw,
            kind=SelectorKind.COMPLEX,
        )

    token = parts[0]

    if token.startswith(".") and len(token) > 1:
        return ParsedSelector(
            raw=raw,
            kind=SelectorKind.CLASS,
            value=token[1:],
        )

    if token.startswith("#") and len(token) > 1:
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