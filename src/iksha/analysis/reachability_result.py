"""
Results produced by IKSHA reachability analysis.
"""

from dataclasses import dataclass, field

from iksha.domain.file import File
from iksha.domain.states import ReachabilityState


@dataclass(frozen=True)
class FileReachability:
    """Reachability classification for one project file."""

    file: File
    state: ReachabilityState


@dataclass
class ReachabilityResult:
    """Complete reachability result for one analysis."""

    entry_points: tuple[File, ...] = ()
    files: list[FileReachability] = field(
        default_factory=list,
    )

    def state_for(
        self,
        file: File,
    ) -> ReachabilityState:
        """Return the reachability state for a file."""

        for result in self.files:
            if result.file is file:
                return result.state

        return ReachabilityState.UNKNOWN

    @property
    def reachable_files(self) -> tuple[File, ...]:
        """Return files classified as reachable."""

        return tuple(
            result.file
            for result in self.files
            if result.state is ReachabilityState.REACHABLE
        )

    @property
    def unreachable_files(self) -> tuple[File, ...]:
        """Return files classified as unreachable."""

        return tuple(
            result.file
            for result in self.files
            if result.state is ReachabilityState.UNREACHABLE
        )