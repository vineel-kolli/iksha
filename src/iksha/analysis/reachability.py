"""
Reachability analysis for IKSHA.
"""

from collections import deque

from iksha.domain.file import File
from iksha.graph.dependency import DependencyGraph


class ReachabilityAnalyzer:
    """
    Determine which project files are reachable from known entry points.

    Reachability is deliberately separate from entry-point discovery.
    The caller supplies the entry points explicitly.
    """

    def __init__(
        self,
        graph: DependencyGraph,
    ) -> None:
        self.graph = graph

    def reachable_from(
        self,
        entry_points: list[File],
    ) -> set[File]:
        """
        Return all files reachable from the supplied entry points.

        Entry points themselves are considered reachable.
        Traversal follows resolved dependency edges only.
        """

        reachable: set[File] = set()
        queue: deque[File] = deque(
            sorted(
                entry_points,
                key=self._file_sort_key,
            )
        )

        while queue:
            current = queue.popleft()

            if current in reachable:
                continue

            reachable.add(current)

            neighbors = sorted(
                self.graph.dependencies_of(current),
                key=self._file_sort_key,
            )

            for neighbor in neighbors:
                if neighbor not in reachable:
                    queue.append(neighbor)

        return reachable

    def is_reachable(
        self,
        file: File,
        entry_points: list[File],
    ) -> bool:
        """Return whether a file is reachable from the entry points."""

        return file in self.reachable_from(
            entry_points,
        )

    @staticmethod
    def _file_sort_key(
        file: File,
    ) -> tuple[str, str]:
        """Return a deterministic file ordering key."""

        return (
            file.relative_path.lower(),
            file.relative_path,
        )