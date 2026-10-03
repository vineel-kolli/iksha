from pathlib import Path

from iksha.dependency.registry import ResolverRegistry
from iksha.dependency.result import ResolutionResult
from iksha.domain.file import File
from iksha.domain.reference import ReferenceKind
from iksha.parsing.result import Observation


class FakeResolver:
    """Test resolver implementation used by the registry tests."""

    def __init__(
        self,
        handled: bool,
        target: File | None = None,
    ) -> None:
        self.handled = handled
        self.target = target
        self.index_calls = 0
        self.resolve_calls = 0

    def handles(
        self,
        observation: Observation,
    ) -> bool:
        return self.handled

    def index_files(
        self,
        files: list[File],
    ) -> None:
        self.index_calls += 1

    def resolve(
        self,
        observation: Observation,
    ) -> ResolutionResult:
        self.resolve_calls += 1

        return ResolutionResult(
            observation=observation,
            target=self.target,
        )


def make_observation() -> Observation:
    """Create a minimal observation for registry tests."""

    return Observation(
        source=None,
        kind=ReferenceKind.UNKNOWN,
        value="example.php",
    )


def test_registry_uses_first_matching_resolver() -> None:
    observation = make_observation()

    first = FakeResolver(handled=True)
    second = FakeResolver(handled=True)

    registry = ResolverRegistry(
        [first, second],
    )

    result = registry.resolve(observation)

    assert result.observation is observation
    assert first.resolve_calls == 1
    assert second.resolve_calls == 0


def test_registry_returns_unresolved_when_no_resolver_matches() -> None:
    observation = make_observation()

    resolver = FakeResolver(handled=False)

    registry = ResolverRegistry(
        [resolver],
    )

    result = registry.resolve(observation)

    assert result.observation is observation
    assert result.target is None
    assert result.resolved is False
    assert resolver.resolve_calls == 0


def test_registry_indexes_all_resolvers() -> None:
    file = File(
        path=Path("example.php"),
        relative_path="example.php",
        file_type="php",
        size=10,
    )

    first = FakeResolver(handled=False)
    second = FakeResolver(handled=False)

    registry = ResolverRegistry(
        [first, second],
    )

    registry.index_files([file])

    assert first.index_calls == 1
    assert second.index_calls == 1