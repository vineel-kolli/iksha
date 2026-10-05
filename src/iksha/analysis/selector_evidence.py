"""
Semantic evidence produced by CSS selector matching for IKSHA.

This module represents evidence that comes from matching an authored
CSS selector against a structured HTML document.

Semantic DOM evidence is intentionally separate from parser observations.
"""

from __future__ import annotations

from dataclasses import dataclass

from iksha.domain.file import File
from iksha.domain.source_location import SourceLocation


@dataclass(frozen=True)
class SelectorMatchEvidence:
    """Evidence that a CSS selector matched an HTML element."""

    source: File
    location: SourceLocation | None = None
    element_tag: str | None = None
    element_id: str | None = None
    element_classes: tuple[str, ...] = ()