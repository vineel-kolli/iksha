import pytest

from iksha.domain.dead_code import (
    all_selectors_statically_unused,
    derive_dead_code_state,
    most_selectors_statically_unused,
)
from iksha.domain.states import (
    DeadCodeState,
    ReachabilityState,
    UsageState,
)


def unused(count: int) -> list[UsageState]:
    return [UsageState.STATICALLY_UNUSED] * count


def mixed(
    *states: UsageState,
) -> list[UsageState]:
    return list(states)


def test_all_selectors_unused_is_vacuous_for_empty_file():
    assert all_selectors_statically_unused([]) is True


def test_most_selectors_requires_strict_majority():
    assert most_selectors_statically_unused([]) is True
    assert most_selectors_statically_unused(unused(1)) is True
    assert most_selectors_statically_unused(
        mixed(
            UsageState.STATICALLY_UNUSED,
            UsageState.DEFINITELY_USED,
        )
    ) is False
    assert most_selectors_statically_unused(
        mixed(
            UsageState.STATICALLY_UNUSED,
            UsageState.STATICALLY_UNUSED,
            UsageState.DEFINITELY_USED,
        )
    ) is True


def test_unreachable_unused_file_is_definitely_dead():
    assert (
        derive_dead_code_state(
            ReachabilityState.UNREACHABLE,
            unused(18),
            dynamic_evidence_present=False,
        )
        is DeadCodeState.DEFINITELY_DEAD
    )


def test_dynamic_evidence_blocks_definitely_dead():
    assert (
        derive_dead_code_state(
            ReachabilityState.UNREACHABLE,
            unused(18),
            dynamic_evidence_present=True,
        )
        is DeadCodeState.POSSIBLY_DEAD
    )


def test_prd_example_legacy_css_is_possibly_dead():
    selectors = unused(17) + [UsageState.UNKNOWN]

    assert (
        derive_dead_code_state(
            ReachabilityState.UNREACHABLE,
            selectors,
            dynamic_evidence_present=True,
        )
        is DeadCodeState.POSSIBLY_DEAD
    )


def test_unreachable_majority_unused_is_probably_dead():
    selectors = unused(17) + [UsageState.POSSIBLY_USED]

    assert (
        derive_dead_code_state(
            ReachabilityState.UNREACHABLE,
            selectors,
            dynamic_evidence_present=False,
        )
        is DeadCodeState.PROBABLY_DEAD
    )


def test_unknown_reachability_majority_unused_is_probably_dead():
    selectors = unused(3) + [UsageState.UNKNOWN]

    assert (
        derive_dead_code_state(
            ReachabilityState.UNKNOWN,
            selectors,
            dynamic_evidence_present=False,
        )
        is DeadCodeState.PROBABLY_DEAD
    )


def test_potentially_reachable_is_possibly_dead():
    assert (
        derive_dead_code_state(
            ReachabilityState.POTENTIALLY_REACHABLE,
            unused(10),
            dynamic_evidence_present=False,
        )
        is DeadCodeState.POSSIBLY_DEAD
    )


def test_reachable_file_is_not_dead():
    assert (
        derive_dead_code_state(
            ReachabilityState.REACHABLE,
            unused(4),
            dynamic_evidence_present=False,
        )
        is DeadCodeState.NOT_DEAD
    )


def test_used_selector_makes_file_not_dead():
    selectors = unused(1) + [UsageState.DEFINITELY_USED]

    assert (
        derive_dead_code_state(
            ReachabilityState.UNKNOWN,
            selectors,
            dynamic_evidence_present=False,
        )
        is DeadCodeState.NOT_DEAD
    )


def test_majority_unused_outranks_one_used_selector():
    selectors = unused(3) + [UsageState.DEFINITELY_USED]

    assert (
        derive_dead_code_state(
            ReachabilityState.UNKNOWN,
            selectors,
            dynamic_evidence_present=False,
        )
        is DeadCodeState.PROBABLY_DEAD
    )


def test_probably_used_selector_makes_file_not_dead():
    selectors = unused(1) + [UsageState.PROBABLY_USED]

    assert (
        derive_dead_code_state(
            ReachabilityState.UNKNOWN,
            selectors,
            dynamic_evidence_present=False,
        )
        is DeadCodeState.NOT_DEAD
    )


def test_incomplete_usage_without_majority_is_unknown():
    assert (
        derive_dead_code_state(
            ReachabilityState.UNKNOWN,
            [UsageState.UNKNOWN],
            dynamic_evidence_present=False,
        )
        is DeadCodeState.UNKNOWN
    )


def test_possibly_used_only_is_unknown_without_other_evidence():
    assert (
        derive_dead_code_state(
            ReachabilityState.UNKNOWN,
            [UsageState.POSSIBLY_USED],
            dynamic_evidence_present=False,
        )
        is DeadCodeState.UNKNOWN
    )


@pytest.mark.parametrize(
    (
        "reachability",
        "selectors",
        "dynamic",
        "expected",
    ),
    [
        (
            ReachabilityState.UNREACHABLE,
            [],
            False,
            DeadCodeState.DEFINITELY_DEAD,
        ),
        (
            ReachabilityState.REACHABLE,
            [UsageState.DEFINITELY_USED],
            True,
            DeadCodeState.POSSIBLY_DEAD,
        ),
        (
            ReachabilityState.POTENTIALLY_REACHABLE,
            [UsageState.DEFINITELY_USED],
            False,
            DeadCodeState.POSSIBLY_DEAD,
        ),
    ],
)
def test_derivation_rule_pinned_combinations(
    reachability,
    selectors,
    dynamic,
    expected,
):
    assert (
        derive_dead_code_state(
            reachability,
            selectors,
            dynamic_evidence_present=dynamic,
        )
        is expected
    )
