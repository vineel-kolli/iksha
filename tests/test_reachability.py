from pathlib import Path

from iksha.analysis.reachability import ReachabilityAnalyzer
from iksha.domain.file import File
from iksha.domain.reference import ReferenceKind
from iksha.domain.states import ReachabilityState
from iksha.graph.dependency import DependencyGraph
from iksha.parsing.result import Observation


def make_file(
    relative_path: str,
) -> File:
    """Create a test File."""

    return File(
        path=Path(relative_path),
        relative_path=relative_path,
        file_type=Path(relative_path).suffix.lstrip("."),
    )


def make_observation(
    source: File,
) -> Observation:
    """Create a minimal dependency observation."""

    return Observation(
        source=source,
        kind=ReferenceKind.IMPORT,
        value="dependency",
    )


def test_reachability_includes_entry_points() -> None:
    entry = make_file("index.php")

    graph = DependencyGraph()
    analyzer = ReachabilityAnalyzer(graph)

    result = analyzer.analyze(
        entry_points=(entry,),
        files=[entry],
    )

    assert result.state_for(entry) is ReachabilityState.REACHABLE


def test_reachability_follows_dependency_edges() -> None:
    entry = make_file("index.php")
    header = make_file("header.php")
    config = make_file("config.php")

    graph = DependencyGraph()

    graph.add(
        source=entry,
        target=header,
        observation=make_observation(entry),
    )

    graph.add(
        source=header,
        target=config,
        observation=make_observation(header),
    )

    analyzer = ReachabilityAnalyzer(graph)

    result = analyzer.analyze(
        entry_points=(entry,),
        files=[
            entry,
            header,
            config,
        ],
    )

    assert result.state_for(entry) is ReachabilityState.REACHABLE
    assert result.state_for(header) is ReachabilityState.REACHABLE
    assert result.state_for(config) is ReachabilityState.REACHABLE


def test_reachability_marks_disconnected_files_unreachable() -> None:
    entry = make_file("index.php")
    used = make_file("used.php")
    unused = make_file("unused.php")

    graph = DependencyGraph()

    graph.add(
        source=entry,
        target=used,
        observation=make_observation(entry),
    )

    analyzer = ReachabilityAnalyzer(graph)

    result = analyzer.analyze(
        entry_points=(entry,),
        files=[
            entry,
            used,
            unused,
        ],
    )

    assert result.state_for(used) is ReachabilityState.REACHABLE
    assert result.state_for(unused) is ReachabilityState.UNREACHABLE


def test_reachability_supports_multiple_entry_points() -> None:
    first = make_file("index.php")
    second = make_file("admin.php")
    first_dep = make_file("layout.php")
    second_dep = make_file("admin-layout.php")

    graph = DependencyGraph()

    graph.add(
        source=first,
        target=first_dep,
        observation=make_observation(first),
    )

    graph.add(
        source=second,
        target=second_dep,
        observation=make_observation(second),
    )

    analyzer = ReachabilityAnalyzer(graph)

    result = analyzer.analyze(
        entry_points=(first, second),
        files=[
            first,
            second,
            first_dep,
            second_dep,
        ],
    )

    assert result.state_for(first) is ReachabilityState.REACHABLE
    assert result.state_for(second) is ReachabilityState.REACHABLE
    assert result.state_for(first_dep) is ReachabilityState.REACHABLE
    assert result.state_for(second_dep) is ReachabilityState.REACHABLE


def test_is_reachable_returns_expected_result() -> None:
    entry = make_file("index.php")
    dependency = make_file("header.php")
    disconnected = make_file("unused.php")

    graph = DependencyGraph()

    graph.add(
        source=entry,
        target=dependency,
        observation=make_observation(entry),
    )

    analyzer = ReachabilityAnalyzer(graph)

    assert analyzer.is_reachable(
        dependency,
        [entry],
    ) is True

    assert analyzer.is_reachable(
        disconnected,
        [entry],
    ) is False


def test_analyze_preserves_deterministic_file_order() -> None:
    first = make_file("z.php")
    second = make_file("a.php")

    graph = DependencyGraph()

    analyzer = ReachabilityAnalyzer(graph)

    result = analyzer.analyze(
        entry_points=(first,),
        files=[
            first,
            second,
        ],
    )

    assert [
        item.file.relative_path
        for item in result.files
    ] == [
        "a.php",
        "z.php",
    ]