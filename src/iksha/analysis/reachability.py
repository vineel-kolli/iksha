"""
Reachability analysis for IKSHA.
"""

from collections import deque

from iksha.analysis.reachability_result import (
    FileReachability,
    ReachabilityResult,
)
from iksha.domain.file import File
from iksha.domain.states import ReachabilityState
from iksha.graph.dependency import DependencyGraph


class ReachabilityAnalyzer:
    """
    Determine file reachability from known entry points.

    Entry-point discovery remains separate from graph traversal.
    """

    def __init__(
        self,
        graph: DependencyGraph,
    ) -> None:
        self.graph = graph

    def analyze(
        self,
        entry_points: tuple[File, ...],
        files: list[File],
    ) -> ReachabilityResult:
        """
        Classify every supplied project file.

        Files reachable from at least one entry point are marked
        REACHABLE. Files not reached are marked UNREACHABLE.
        """

        reachable = self._reachable_files(
            entry_points,
        )

        classifications = [
            FileReachability(
                file=file,
                state=(
                    ReachabilityState.REACHABLE
                    if file in reachable
                    else ReachabilityState.UNREACHABLE
                ),
            )
            for file in self._sorted_files(files)
        ]

        return ReachabilityResult(
            entry_points=entry_points,
            files=classifications,
        )

    def reachable_from(
        self,
        entry_points: list[File],
    ) -> set[File]:
        """
        Return all files reachable from the supplied entry points.

        This lower-level traversal API is retained for graph algorithms
        that need the raw reachable set.
        """

        return self._reachable_files(
            tuple(entry_points),
        )

    def is_reachable(
        self,
        file: File,
        entry_points: list[File],
    ) -> bool:
        """Return whether a file is reachable from the entry points."""

        return file in self._reachable_files(
            tuple(entry_points),
        )

    def _reachable_files(
        self,
        entry_points: tuple[File, ...],
    ) -> set[File]:
        """Traverse the dependency graph from the supplied entry points."""

        reachable: set[File] = set()

        queue: deque[File] = deque(
            self._sorted_files(
                list(entry_points),
            )
        )

        while queue:
            current = queue.popleft()

            if current in reachable:
                continue

            reachable.add(current)

            neighbors = self._sorted_files(
                list(
                    self.graph.dependencies_of(
                        current,
                    )
                )
            )

            for neighbor in neighbors:
                if neighbor not in reachable:
                    queue.append(neighbor)

        return reachable

    @staticmethod
    def _sorted_files(
        files: list[File],
    ) -> list[File]:
        """Return files in deterministic order."""

        return sorted(
            files,
            key=ReachabilityAnalyzer._file_sort_key,
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