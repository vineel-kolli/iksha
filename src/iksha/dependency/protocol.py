"""
Common resolver contract for IKSHA.
"""

from typing import Protocol

from iksha.dependency.result import ResolutionResult
from iksha.domain.file import File
from iksha.parsing.result import Observation


class ReferenceResolver(Protocol):
    """Contract implemented by all reference resolvers."""

    def handles(
        self,
        observation: Observation,
    ) -> bool:
        """Return whether this resolver owns the observation."""
        ...

    def index_files(
        self,
        files: list[File],
    ) -> None:
        """Index authoritative project files."""
        ...

    def resolve(
        self,
        observation: Observation,
    ) -> ResolutionResult:
        """Resolve one observation."""
        ...