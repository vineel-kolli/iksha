"""
Resolver registry for IKSHA dependency resolution.
"""

from iksha.dependency.protocol import ReferenceResolver
from iksha.dependency.result import ResolutionResult
from iksha.domain.file import File
from iksha.parsing.result import Observation


class ResolverRegistry:
    """Selects the resolver responsible for each observation."""

    def __init__(
        self,
        resolvers: list[ReferenceResolver],
    ) -> None:
        self._resolvers = list(resolvers)

    def add(
        self,
        resolver: ReferenceResolver,
    ) -> None:
        """Register one dependency resolver."""

        self._resolvers.append(resolver)

    def handles(
        self,
        observation: Observation,
    ) -> bool:
        """Return whether any registered resolver handles the observation."""

        return any(
            resolver.handles(observation)
            for resolver in self._resolvers
        )

    def resolve(
        self,
        observation: Observation,
    ) -> ResolutionResult:
        """Resolve an observation using the first matching resolver."""

        for resolver in self._resolvers:
            if resolver.handles(observation):
                return resolver.resolve(observation)

        return ResolutionResult(
            observation=observation,
        )

    def index_files(
        self,
        files: list[File],
    ) -> None:
        """Index project files in every registered resolver."""

        for resolver in self._resolvers:
            resolver.index_files(files)