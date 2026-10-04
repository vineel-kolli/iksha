"""
CSS selector usage correlation for IKSHA.

Correlates simple CSS selectors with normalized CLASS and ID observations
produced by HTML and JavaScript parsers.

This module intentionally stays conservative. Unsupported selector
semantics are not guessed.
"""

from __future__ import annotations

from dataclasses import dataclass

from iksha.analysis.selectors import (
    ParsedSelector,
    SelectorKind,
    parse_selector,
)
from iksha.domain.reference import ReferenceKind
from iksha.domain.states import Confidence, UsageState
from iksha.parsing.result import Observation


@dataclass(frozen=True)
class SelectorUsage:
    """Usage result for one CSS selector."""

    selector: str
    state: UsageState
    evidence: tuple[Observation, ...] = ()


def analyze_selector_usage(
    selector: str,
    observations: list[Observation],
) -> SelectorUsage:
    """
    Correlate one CSS selector with usage observations.

    Supported currently:
      - .class ↔ CLASS observation
      - #id    ↔ ID observation

    Element and complex selectors remain UNKNOWN until DOM-aware
    semantic matching is implemented.
    """
    parsed = parse_selector(selector)

    if parsed.kind is SelectorKind.CLASS:
        return _analyze_simple_selector(
            parsed,
            ReferenceKind.CLASS,
            observations,
        )

    if parsed.kind is SelectorKind.ID:
        return _analyze_simple_selector(
            parsed,
            ReferenceKind.ID,
            observations,
        )

    if parsed.kind in {
        SelectorKind.ELEMENT,
        SelectorKind.COMPLEX,
        SelectorKind.UNSUPPORTED,
    }:
        return SelectorUsage(
            selector=selector,
            state=UsageState.UNKNOWN,
        )

    return SelectorUsage(
        selector=selector,
        state=UsageState.UNKNOWN,
    )


def _analyze_simple_selector(
    selector: ParsedSelector,
    observation_kind: ReferenceKind,
    observations: list[Observation],
) -> SelectorUsage:
    matching = tuple(
        observation
        for observation in observations
        if observation.kind is observation_kind
        and observation.value == selector.value
    )

    if not matching:
        return SelectorUsage(
            selector=selector.raw,
            state=UsageState.STATICALLY_UNUSED,
        )

    state = _usage_state_for_confidence(
        observation.confidence
        for observation in matching
    )

    return SelectorUsage(
        selector=selector.raw,
        state=state,
        evidence=matching,
    )


def _usage_state_for_confidence(
    confidences: object,
) -> UsageState:
    values = tuple(confidences)

    if any(value is Confidence.CERTAIN for value in values):
        return UsageState.DEFINITELY_USED

    if any(value is Confidence.HIGH for value in values):
        return UsageState.PROBABLY_USED

    if any(value in {Confidence.MEDIUM, Confidence.LOW} for value in values):
        return UsageState.POSSIBLY_USED

    return UsageState.UNKNOWN