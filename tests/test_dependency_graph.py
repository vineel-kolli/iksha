from pathlib import Path

import pytest

from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.domain.source_location import SourceLocation
from iksha.parsing.result import Observation
from iksha.graph.dependency import DependencyGraph


def make_file(
    root: Path,
    relative_path: str,
    file_type: str = "php",
) -> File:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")

    return File(
        path=path,
        relative_path=relative_path,
        file_type=file_type,
        size=path.stat().st_size,
    )


def make_observation(
    source: File,
    value: str,
    kind: ReferenceKind = ReferenceKind.INCLUDE,
) -> Observation:
    return Observation(
        source=source,
        kind=kind,
        value=value,
        location=SourceLocation(
            line=10,
            column=5,
        ),
        confidence=Confidence.CERTAIN,
    )


def test_empty_graph_contains_no_edges():
    graph = DependencyGraph()

    assert graph.edge_count == 0
    assert graph.edges() == []


def test_add_dependency_edge(tmp_path: Path):
    source = make_file(
        tmp_path,
        "index.php",
    )

    target = make_file(
        tmp_path,
        "header.php",
    )

    observation = make_observation(
        source,
        "header.php",
    )

    graph = DependencyGraph()

    edge = graph.add(
        source=source,
        target=target,
        observation=observation,
    )

    assert graph.edge_count == 1
    assert edge.source is source
    assert edge.target is target
    assert edge.observation is observation


def test_dependencies_of_returns_targets(tmp_path: Path):
    source = make_file(
        tmp_path,
        "index.php",
    )

    header = make_file(
        tmp_path,
        "header.php",
    )

    footer = make_file(
        tmp_path,
        "footer.php",
    )

    graph = DependencyGraph()

    graph.add(
        source=source,
        target=header,
        observation=make_observation(
            source,
            "header.php",
        ),
    )

    graph.add(
        source=source,
        target=footer,
        observation=make_observation(
            source,
            "footer.php",
        ),
    )

    assert graph.dependencies_of(source) == {
        header,
        footer,
    }


def test_dependents_of_returns_sources(tmp_path: Path):
    index = make_file(
        tmp_path,
        "index.php",
    )

    page = make_file(
        tmp_path,
        "page.php",
    )

    graph = DependencyGraph()

    graph.add(
        source=index,
        target=page,
        observation=make_observation(
            index,
            "page.php",
        ),
    )

    assert graph.dependents_of(page) == {
        index,
    }


def test_same_target_can_have_multiple_dependents(
    tmp_path: Path,
):
    index = make_file(
        tmp_path,
        "index.php",
    )

    admin = make_file(
        tmp_path,
        "admin.php",
    )

    header = make_file(
        tmp_path,
        "header.php",
    )

    graph = DependencyGraph()

    graph.add(
        source=index,
        target=header,
        observation=make_observation(
            index,
            "header.php",
        ),
    )

    graph.add(
        source=admin,
        target=header,
        observation=make_observation(
            admin,
            "header.php",
        ),
    )

    assert graph.dependents_of(header) == {
        index,
        admin,
    }


def test_duplicate_dependency_is_not_added_twice(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    target = make_file(
        tmp_path,
        "header.php",
    )

    observation = make_observation(
        source,
        "header.php",
    )

    graph = DependencyGraph()

    first = graph.add(
        source=source,
        target=target,
        observation=observation,
    )

    second = graph.add(
        source=source,
        target=target,
        observation=observation,
    )

    assert graph.edge_count == 1
    assert first is second


def test_same_files_can_have_multiple_evidence_edges(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    target = make_file(
        tmp_path,
        "header.php",
    )

    first = make_observation(
        source,
        "header.php",
    )

    second = Observation(
        source=source,
        kind=ReferenceKind.REQUIRE,
        value="header.php",
        location=SourceLocation(
            line=20,
            column=3,
        ),
        confidence=Confidence.CERTAIN,
    )

    graph = DependencyGraph()

    graph.add(
        source=source,
        target=target,
        observation=first,
    )

    graph.add(
        source=source,
        target=target,
        observation=second,
    )

    assert graph.edge_count == 2
    assert len(graph.edges_between(source, target)) == 2


def test_self_dependency_is_allowed(tmp_path: Path):
    source = make_file(
        tmp_path,
        "index.php",
    )

    graph = DependencyGraph()

    graph.add(
        source=source,
        target=source,
        observation=make_observation(
            source,
            "index.php",
        ),
    )

    assert graph.edge_count == 1
    assert source in graph.dependencies_of(source)
    assert source in graph.dependents_of(source)


def test_edges_preserve_observation_evidence(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    target = make_file(
        tmp_path,
        "header.php",
    )

    observation = make_observation(
        source,
        "header.php",
    )

    graph = DependencyGraph()

    edge = graph.add(
        source=source,
        target=target,
        observation=observation,
    )

    assert edge.observation.value == "header.php"
    assert edge.observation.location is not None
    assert edge.observation.location.line == 10
    assert edge.observation.location.column == 5
    assert edge.observation.confidence == Confidence.CERTAIN


def test_edges_between_preserves_insertion_order(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    target = make_file(
        tmp_path,
        "header.php",
    )

    first = make_observation(
        source,
        "header.php",
    )

    second = Observation(
        source=source,
        kind=ReferenceKind.REQUIRE,
        value="header.php",
        location=SourceLocation(
            line=20,
            column=1,
        ),
        confidence=Confidence.CERTAIN,
    )

    graph = DependencyGraph()

    graph.add(
        source=source,
        target=target,
        observation=first,
    )

    graph.add(
        source=source,
        target=target,
        observation=second,
    )

    edges = graph.edges_between(
        source,
        target,
    )

    assert edges[0].observation is first
    assert edges[1].observation is second


def test_unknown_file_has_no_dependencies(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    unknown = make_file(
        tmp_path,
        "unknown.php",
    )

    graph = DependencyGraph()

    assert graph.dependencies_of(source) == set()
    assert graph.dependents_of(unknown) == set()


def test_all_edges_returns_deterministic_order(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    header = make_file(
        tmp_path,
        "header.php",
    )

    footer = make_file(
        tmp_path,
        "footer.php",
    )

    graph = DependencyGraph()

    graph.add(
        source=source,
        target=footer,
        observation=make_observation(
            source,
            "footer.php",
        ),
    )

    graph.add(
        source=source,
        target=header,
        observation=make_observation(
            source,
            "header.php",
        ),
    )

    edges = graph.edges()

    assert len(edges) == 2
    assert edges[0].target is footer
    assert edges[1].target is header
