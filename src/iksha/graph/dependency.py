"""
Dependency graph for IKSHA.

Stores resolved relationships between authoritative project files
while preserving the source evidence that produced each relationship.
"""

from dataclasses import dataclass

from iksha.domain.file import File
from iksha.parsing.result import Observation


@dataclass(frozen=True)
class DependencyEdge:
    """
    One resolved dependency relationship.

    Multiple edges between the same source and target are allowed when
    they represent different pieces of source evidence.
    """

    source: File
    target: File
    observation: Observation


class DependencyGraph:
    """
    Bidirectional dependency graph.

    Forward:
        source -> dependencies

    Reverse:
        target -> dependents

    The graph stores authoritative File objects rather than paths or
    filenames so file identity remains consistent throughout IKSHA.
    """

    def __init__(self) -> None:
        self._edges: list[DependencyEdge] = []

        self._forward: dict[
            File,
            set[File],
        ] = {}

        self._reverse: dict[
            File,
            set[File],
        ] = {}

        self._edge_keys: dict[
            tuple[File, File, Observation],
            DependencyEdge,
        ] = {}

    @property
    def edge_count(self) -> int:
        """Return the number of unique evidence edges."""

        return len(self._edges)

    def add(
        self,
        source: File,
        target: File,
        observation: Observation,
    ) -> DependencyEdge:
        """
        Add a dependency edge.

        The same evidence cannot be inserted twice.

        Different observations between the same files are preserved.
        """

        key = (
            source,
            target,
            observation,
        )

        existing = self._edge_keys.get(key)

        if existing is not None:
            return existing

        edge = DependencyEdge(
            source=source,
            target=target,
            observation=observation,
        )

        self._edges.append(edge)
        self._edge_keys[key] = edge

        self._forward.setdefault(
            source,
            set(),
        ).add(target)

        self._reverse.setdefault(
            target,
            set(),
        ).add(source)

        return edge

    def dependencies_of(
        self,
        source: File,
    ) -> set[File]:
        """Return files directly depended upon by source."""

        return set(
            self._forward.get(
                source,
                set(),
            )
        )

    def dependents_of(
        self,
        target: File,
    ) -> set[File]:
        """Return files that directly depend on target."""

        return set(
            self._reverse.get(
                target,
                set(),
            )
        )

    def edges_between(
        self,
        source: File,
        target: File,
    ) -> list[DependencyEdge]:
        """
        Return all evidence edges between two files.

        Insertion order is preserved.
        """

        return [
            edge
            for edge in self._edges
            if (
                edge.source == source
                and edge.target == target
            )
        ]

    def edges(self) -> list[DependencyEdge]:
        """
        Return all graph edges in deterministic order.

        Edges are ordered by source path, target path, then source
        location/evidence.
        """

        return sorted(
            self._edges,
            key=self._edge_sort_key,
        )

    @staticmethod
    def _edge_sort_key(
        edge: DependencyEdge,
    ) -> tuple:
        """Create a deterministic ordering key."""

        location = edge.observation.location

        line = (
            location.line
            if location is not None
            else 0
        )

        column = (
            location.column
            if location is not None
            else 0
        )

        return (
            edge.source.path.as_posix().lower(),
            edge.target.path.as_posix().lower(),
            line,
            column,
            edge.observation.kind.value,
            edge.observation.value,
        )
