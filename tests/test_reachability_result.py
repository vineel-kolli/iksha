from pathlib import Path

from iksha.analysis.reachability_result import (
    FileReachability,
    ReachabilityResult,
)
from iksha.domain.file import File
from iksha.domain.states import ReachabilityState


def make_file(
    relative_path: str,
) -> File:
    """Create a test file."""

    path = Path(relative_path)

    return File(
        path=path,
        relative_path=relative_path,
        file_type=path.suffix.lstrip("."),
    )


def test_state_for_returns_file_state() -> None:
    file = make_file("index.php")

    result = ReachabilityResult(
        files=[
            FileReachability(
                file=file,
                state=ReachabilityState.REACHABLE,
            )
        ]
    )

    assert result.state_for(file) is ReachabilityState.REACHABLE


def test_state_for_returns_unknown_for_missing_file() -> None:
    file = make_file("index.php")

    result = ReachabilityResult()

    assert result.state_for(file) is ReachabilityState.UNKNOWN


def test_reachable_files_returns_only_reachable_files() -> None:
    reachable = make_file("index.php")
    unreachable = make_file("unused.php")

    result = ReachabilityResult(
        files=[
            FileReachability(
                file=reachable,
                state=ReachabilityState.REACHABLE,
            ),
            FileReachability(
                file=unreachable,
                state=ReachabilityState.UNREACHABLE,
            ),
        ]
    )

    assert result.reachable_files == (
        reachable,
    )


def test_unreachable_files_returns_only_unreachable_files() -> None:
    reachable = make_file("index.php")
    unreachable = make_file("unused.php")

    result = ReachabilityResult(
        files=[
            FileReachability(
                file=reachable,
                state=ReachabilityState.REACHABLE,
            ),
            FileReachability(
                file=unreachable,
                state=ReachabilityState.UNREACHABLE,
            ),
        ]
    )

    assert result.unreachable_files == (
        unreachable,
    )


def test_entry_points_are_preserved() -> None:
    first = make_file("index.php")
    second = make_file("admin.php")

    result = ReachabilityResult(
        entry_points=(
            first,
            second,
        )
    )

    assert result.entry_points == (
        first,
        second,
    )