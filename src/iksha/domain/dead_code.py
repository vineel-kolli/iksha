"""
Dead-code state derivation for IKSHA.

This implements the deterministic file-level rule from the product
requirements. Callers supply already-classified reachability, selector
usage, and whether relevant dynamic evidence exists.
"""

from collections.abc import Sequence

from .states import (
    DeadCodeState,
    ReachabilityState,
    UsageState,
)

_USED_STATES = frozenset(
    {
        UsageState.DEFINITELY_USED,
        UsageState.PROBABLY_USED,
    }
)


def all_selectors_statically_unused(
    selector_usage: Sequence[UsageState],
) -> bool:
    """Return whether every selector is statically unused."""

    return all(
        state is UsageState.STATICALLY_UNUSED
        for state in selector_usage
    )


def most_selectors_statically_unused(
    selector_usage: Sequence[UsageState],
) -> bool:
    """
    Return whether a strict majority of selectors are statically unused.

    An empty selector list is treated as vacuously unused.
    """

    total = len(selector_usage)

    if total == 0:
        return True

    unused = sum(
        1
        for state in selector_usage
        if state is UsageState.STATICALLY_UNUSED
    )

    return unused * 2 > total


def any_selector_in_active_use(
    selector_usage: Sequence[UsageState],
) -> bool:
    """Return whether any selector is definitely or probably used."""

    return any(
        state in _USED_STATES
        for state in selector_usage
    )


def derive_dead_code_state(
    reachability: ReachabilityState,
    selector_usage: Sequence[UsageState],
    *,
    dynamic_evidence_present: bool,
) -> DeadCodeState:
    """
    Derive file-level dead-code state.

    Rule (must stay exact):

        IF reachability == UNREACHABLE
           AND all selectors == STATICALLY_UNUSED
           AND no dynamic evidence:
            DEFINITELY_DEAD
        ELIF reachability in (UNREACHABLE, UNKNOWN)
           AND most selectors == STATICALLY_UNUSED
           AND no dynamic evidence:
            PROBABLY_DEAD
        ELIF dynamic evidence present
           OR reachability == POTENTIALLY_REACHABLE:
            POSSIBLY_DEAD
        ELIF reachability == REACHABLE
           OR any selector in (DEFINITELY_USED, PROBABLY_USED):
            NOT_DEAD
        ELSE:
            UNKNOWN
    """

    if (
        reachability is ReachabilityState.UNREACHABLE
        and all_selectors_statically_unused(selector_usage)
        and not dynamic_evidence_present
    ):
        return DeadCodeState.DEFINITELY_DEAD

    if (
        reachability
        in {
            ReachabilityState.UNREACHABLE,
            ReachabilityState.UNKNOWN,
        }
        and most_selectors_statically_unused(selector_usage)
        and not dynamic_evidence_present
    ):
        return DeadCodeState.PROBABLY_DEAD

    if (
        dynamic_evidence_present
        or reachability is ReachabilityState.POTENTIALLY_REACHABLE
    ):
        return DeadCodeState.POSSIBLY_DEAD

    if (
        reachability is ReachabilityState.REACHABLE
        or any_selector_in_active_use(selector_usage)
    ):
        return DeadCodeState.NOT_DEAD

    return DeadCodeState.UNKNOWN
