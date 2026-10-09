"""
CSS selector usage correlation for IKSHA.

Correlates simple CSS selectors with normalized CLASS and ID observations
produced by HTML and JavaScript parsers.

This module intentionally stays conservative. Unsupported selector
semantics are not guessed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from iksha.analysis.selector_evidence import SelectorMatchEvidence
from iksha.analysis.selector_matcher import match_selector
from iksha.analysis.selectors import (
    ParsedSelector,
    SelectorKind,
    parse_selector,
)
from iksha.domain.file import File
from iksha.domain.reference import ReferenceKind
from iksha.domain.states import Confidence, UsageState
from iksha.parsing.html_document import HtmlDocument
from iksha.parsing.result import Observation


@dataclass(frozen=True)
class SelectorUsage:
    """Usage result for one CSS selector."""

    selector: str
    state: UsageState
    evidence: tuple[Observation, ...] = ()
    semantic_matches: tuple[SelectorMatchEvidence, ...] = ()
    matched_files: tuple[File, ...] = ()


def analyze_selector_usage(
    selector: str,
    observations: list[Observation],
    html_documents: Mapping[File, HtmlDocument] | None = None,
    incomplete_files: set[File] | None = None,
) -> SelectorUsage:
    """
    Correlate one CSS selector with parser observations and HTML DOM matches.

    Supported currently:
      - .class ↔ CLASS observation
      - #id    ↔ ID observation
      - element selectors ↔ HTML DOM elements
      - complex selectors ↔ HTML DOM elements

    Unsupported selector semantics remain UNKNOWN.
    """
    parsed = parse_selector(selector)
    incomplete_files = incomplete_files or set()
    if not _is_semantically_supported(parsed):
        return SelectorUsage(
            selector=selector,
            state=UsageState.UNKNOWN,
        )

    semantic_matches = _semantic_matches(
        selector,
        html_documents,
    )

    if parsed.kind is SelectorKind.CLASS:
        usage = _analyze_simple_selector(
            parsed,
            ReferenceKind.CLASS,
            observations,
            html_documents,
            incomplete_files,
        )
        return _combine_usage_results(
            usage,
            semantic_matches,
        )

    if parsed.kind is SelectorKind.ID:
        usage = _analyze_simple_selector(
            parsed,
            ReferenceKind.ID,
            observations,
            html_documents,
            incomplete_files,
        )
        return _combine_usage_results(
            usage,
            semantic_matches,
        )

    if parsed.kind in {
        SelectorKind.ELEMENT,
        SelectorKind.COMPLEX,
    }:
        if html_documents is None:
            return SelectorUsage(
                selector=selector,
                state=UsageState.UNKNOWN,
            )

        if semantic_matches:
            return SelectorUsage(
                selector=selector,
                state=UsageState.DEFINITELY_USED,
                semantic_matches=semantic_matches,
                matched_files=_matched_files_from_semantic_matches(
                    semantic_matches,
                ),
            )

        if _html_usage_is_incomplete(
            html_documents,
            incomplete_files,
        ):
            return SelectorUsage(
                selector=selector,
                state=UsageState.UNKNOWN,
            )

        return SelectorUsage(
            selector=selector,
            state=UsageState.STATICALLY_UNUSED,
        )

    return SelectorUsage(
        selector=selector,
        state=UsageState.UNKNOWN,
    )

def _is_semantically_supported(
    parsed: ParsedSelector,
) -> bool:
    """Return whether this selector kind is supported semantically."""
    return parsed.kind in {
        SelectorKind.CLASS,
        SelectorKind.ID,
        SelectorKind.ELEMENT,
        SelectorKind.COMPLEX,
    }


def _semantic_matches(
    selector: str,
    html_documents: Mapping[File, HtmlDocument] | None,
) -> tuple[SelectorMatchEvidence, ...]:
    if html_documents is None:
        return ()

    matches: list[SelectorMatchEvidence] = []

    for source, document in html_documents.items():
        for element in match_selector(selector, document):
            matches.append(
                SelectorMatchEvidence(
                    source=source,
                    location=element.location,
                    element_tag=element.tag,
                    element_id=element.element_id,
                    element_classes=tuple(sorted(element.classes)),
                )
            )

    return tuple(matches)


def _combine_usage_results(
    usage: SelectorUsage,
    semantic_matches: tuple[SelectorMatchEvidence, ...],
) -> SelectorUsage:
    if not semantic_matches:
        return usage

    semantic_files = _matched_files_from_semantic_matches(
        semantic_matches,
    )

    matched_files = tuple(
        dict.fromkeys(
            (*usage.matched_files, *semantic_files),
        )
    )

    return SelectorUsage(
        selector=usage.selector,
        state=UsageState.DEFINITELY_USED,
        evidence=usage.evidence,
        semantic_matches=semantic_matches,
        matched_files=matched_files,
    )


def _matched_files_from_semantic_matches(
    semantic_matches: tuple[SelectorMatchEvidence, ...],
) -> tuple[File, ...]:
    return tuple(
        dict.fromkeys(
            match.source
            for match in semantic_matches
        )
    )


def _analyze_dom_selector_usage(
    selector: str,
    observations: list[Observation],
) -> SelectorUsage:
    """Correlate exact JavaScript DOM selector observations."""

    matching = tuple(
        observation
        for observation in observations
        if observation.kind is ReferenceKind.DOM_SELECTOR
        and observation.value == selector
    )

    if not matching:
        return SelectorUsage(
            selector=selector,
            state=UsageState.STATICALLY_UNUSED,
        )

    state = _usage_state_for_confidence(
        observation.confidence
        for observation in matching
    )

    matched_files = tuple(
        dict.fromkeys(
            observation.source
            for observation in matching
            if observation.source is not None
        )
    )

    return SelectorUsage(
        selector=selector,
        state=state,
        evidence=matching,
        matched_files=matched_files,
    )


def _analyze_simple_selector(
    selector: ParsedSelector,
    observation_kind: ReferenceKind,
    observations: list[Observation],
    html_documents: Mapping[File, HtmlDocument] | None,
    incomplete_files: set[File],
) -> SelectorUsage:
    dom_selector_usage = _analyze_dom_selector_usage(
        selector.raw,
        observations,
    )

    matching = tuple(
        observation
        for observation in observations
        if observation.kind is observation_kind
        and observation.value == selector.value
    )
    combined_evidence = matching + dom_selector_usage.evidence

    if not combined_evidence:
        if _html_usage_is_incomplete(
            html_documents,
            incomplete_files,
        ):
            return SelectorUsage(
                selector=selector.raw,
                state=UsageState.UNKNOWN,
            )

        return SelectorUsage(
            selector=selector.raw,
            state=UsageState.STATICALLY_UNUSED,
        )

    state = _usage_state_for_confidence(
        observation.confidence
        for observation in combined_evidence
    )

    matched_files = tuple(
        dict.fromkeys(
            observation.source
            for observation in combined_evidence
            if observation.source is not None
        )
    )

    return SelectorUsage(
        selector=selector.raw,
        state=state,
        evidence=combined_evidence,
        matched_files=matched_files,
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


def _html_usage_is_incomplete(
    html_documents: Mapping[File, HtmlDocument] | None,
    incomplete_files: set[File],
) -> bool:
    """Return whether available HTML evidence is incomplete."""
    incomplete_html_sources = {
        source
        for source in incomplete_files
        if source.file_type in {"html", "php"}
    }

    if html_documents is None:
        return bool(incomplete_html_sources)

    return bool(
        incomplete_html_sources
        or incomplete_files.intersection(html_documents)
    )
