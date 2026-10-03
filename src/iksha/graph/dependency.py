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

    def outgoing_edges(
        self,
        source: File,
    ) -> list[DependencyEdge]:
        """Return evidence edges leaving a file, in deterministic order."""

        return [
            edge
            for edge in self.edges()
            if edge.source == source
        ]

    def incoming_edges(
        self,
        target: File,
    ) -> list[DependencyEdge]:
        """Return evidence edges entering a file, in deterministic order."""

        return [
            edge
            for edge in self.edges()
            if edge.target == target
        ]

    def path(
        self,
        source: File,
        target: File,
    ) -> list[File] | None:
        """
        Return a shortest dependency path from source to target.

        The path includes both endpoints. Neighbors are visited in
        deterministic order so the chosen path is stable.
        """

        if source == target:
            return [source]

        queue: list[File] = [source]
        previous: dict[File, File | None] = {source: None}

        while queue:
            current = queue.pop(0)
            neighbors = sorted(
                self._forward.get(current, ()),
                key=self._file_sort_key,
            )

            for neighbor in neighbors:
                if neighbor in previous:
                    continue

                previous[neighbor] = current

                if neighbor == target:
                    return self._reconstruct_path(
                        previous,
                        target,
                    )

                queue.append(neighbor)

        return None

    def has_cycle(self) -> bool:
        """Return whether the graph contains at least one cycle."""

        return bool(self.cycles())

    def cycles(self) -> list[tuple[File, ...]]:
        """
        Return simple cycles in deterministic order.

        Each cycle is rotated so it starts at the file with the
        lowest relative path.
        """

        found: set[tuple[File, ...]] = set()

        nodes = sorted(
            set(self._forward) | set(self._reverse),
            key=self._file_sort_key,
        )

        for start in nodes:
            stack: list[File] = []
            on_stack: set[File] = set()

            def visit(node: File) -> None:
                stack.append(node)
                on_stack.add(node)

                neighbors = sorted(
                    self._forward.get(node, ()),
                    key=self._file_sort_key,
                )

                for neighbor in neighbors:
                    if neighbor in on_stack:
                        index = stack.index(neighbor)
                        found.add(
                            self._canonicalize_cycle(
                                stack[index:]
                            )
                        )
                    elif neighbor not in stack:
                        visit(neighbor)

                stack.pop()
                on_stack.remove(node)

            visit(start)

        return sorted(
            found,
            key=lambda cycle: tuple(
                file.relative_path.lower()
                for file in cycle
            ),
        )

    def _reconstruct_path(
        self,
        previous: dict[File, File | None],
        target: File,
    ) -> list[File]:
        """Rebuild a BFS path from the predecessor map."""

        path: list[File] = [target]
        current = target

        while previous[current] is not None:
            current = previous[current]
            path.append(current)

        path.reverse()
        return path

    @staticmethod
    def _canonicalize_cycle(
        nodes: list[File],
    ) -> tuple[File, ...]:
        """Rotate a cycle so it starts at a stable file."""

        if not nodes:
            return ()

        start = min(
            range(len(nodes)),
            key=lambda index: (
                nodes[index].relative_path.lower(),
                nodes[index].relative_path,
            ),
        )

        return tuple(nodes[start:] + nodes[:start])

    @staticmethod
    def _file_sort_key(file: File) -> tuple[str, str]:
        """Stable ordering for files during graph walks."""

        return (
            file.relative_path.lower(),
            file.relative_path,
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
