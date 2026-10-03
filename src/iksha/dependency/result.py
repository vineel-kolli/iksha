"""
Common reference-resolution result model for IKSHA.
"""

from dataclasses import dataclass

from iksha.domain.file import File
from iksha.parsing.result import Observation


@dataclass(frozen=True)
class ResolutionResult:
    """Result of resolving one dependency observation."""

    observation: Observation
    target: File | None = None

    @property
    def resolved(self) -> bool:
        """Return whether the dependency resolved."""
        return self.target is not None