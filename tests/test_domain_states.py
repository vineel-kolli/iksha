from iksha.domain.reference import Confidence as ReferenceConfidence
from iksha.domain.states import (
    Confidence,
    DeadCodeState,
    ReachabilityState,
    Severity,
    UsageState,
)


def test_reachability_states_match_prd():
    assert ReachabilityState.REACHABLE.value == "reachable"
    assert (
        ReachabilityState.POTENTIALLY_REACHABLE.value
        == "potentially_reachable"
    )
    assert ReachabilityState.UNREACHABLE.value == "unreachable"
    assert ReachabilityState.UNKNOWN.value == "unknown"


def test_usage_states_match_prd():
    assert UsageState.DEFINITELY_USED.value == "definitely_used"
    assert UsageState.PROBABLY_USED.value == "probably_used"
    assert UsageState.POSSIBLY_USED.value == "possibly_used"
    assert UsageState.STATICALLY_UNUSED.value == "statically_unused"
    assert UsageState.UNKNOWN.value == "unknown"


def test_dead_code_states_match_prd():
    assert DeadCodeState.NOT_DEAD.value == "not_dead"
    assert DeadCodeState.POSSIBLY_DEAD.value == "possibly_dead"
    assert DeadCodeState.PROBABLY_DEAD.value == "probably_dead"
    assert DeadCodeState.DEFINITELY_DEAD.value == "definitely_dead"
    assert DeadCodeState.UNKNOWN.value == "unknown"


def test_severity_is_independent_of_confidence():
    assert Severity.CRITICAL.value == "critical"
    assert Severity.HIGH.value == "high"
    assert Severity.MEDIUM.value == "medium"
    assert Severity.LOW.value == "low"
    assert Severity.INFO.value == "info"

    assert Confidence.HIGH.value == "high"
    assert Severity.HIGH is not Confidence.HIGH


def test_confidence_remains_available_from_reference_module():
    assert ReferenceConfidence is Confidence
    assert Confidence.CERTAIN.value == "certain"
