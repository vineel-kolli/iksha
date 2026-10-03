from pathlib import Path

from iksha.dependency.css_resolver import CSSDependencyResolver
from iksha.domain.project import Project
from iksha.domain.reference import ReferenceKind, ResolutionStatus
from iksha.inventory.project_inventory import ProjectInventory
from iksha.parsing.result import Observation


def create_css_project(tmp_path: Path) -> Project:
    """Create a project containing a CSS import relationship."""

    (tmp_path / "css").mkdir()

    (tmp_path / "css" / "main.css").write_text(
        '@import "theme.css";',
        encoding="utf-8",
    )

    (tmp_path / "css" / "theme.css").write_text(
        "body {}",
        encoding="utf-8",
    )

    return ProjectInventory(
        tmp_path,
    ).scan()


def make_import_observation(
    project: Project,
    value: str,
) -> Observation:
    """Create a CSS @import observation."""

    source = project.get_by_relative_path(
        "css/main.css",
    )

    assert source is not None

    return Observation(
        source=source,
        kind=ReferenceKind.IMPORT,
        value=value,
    )


def test_css_resolver_handles_static_local_import(
    tmp_path: Path,
) -> None:
    project = create_css_project(
        tmp_path,
    )

    resolver = CSSDependencyResolver(
        project,
    )

    observation = make_import_observation(
        project,
        "theme.css",
    )

    assert resolver.handles(observation) is True


def test_css_resolver_resolves_relative_import(
    tmp_path: Path,
) -> None:
    project = create_css_project(
        tmp_path,
    )

    resolver = CSSDependencyResolver(
        project,
    )

    resolver.index_files(
        list(project.files.values())
    )

    observation = make_import_observation(
        project,
        "theme.css",
    )

    result = resolver.resolve(
        observation,
    )

    target = project.get_by_relative_path(
        "css/theme.css",
    )

    assert target is not None
    assert result.observation is observation
    assert result.resolved is True
    assert result.target is target


def test_css_resolver_does_not_handle_external_import(
    tmp_path: Path,
) -> None:
    project = create_css_project(
        tmp_path,
    )

    resolver = CSSDependencyResolver(
        project,
    )

    observation = make_import_observation(
        project,
        "https://example.com/theme.css",
    )

    assert resolver.handles(observation) is False

    result = resolver.resolve(
        observation,
    )

    assert result.observation is observation
    assert result.resolved is False
    assert result.target is None


def test_css_resolver_does_not_handle_non_css_source(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.php").write_text(
        '<?php echo 1; ?>',
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    source = project.get_by_relative_path(
        "index.php",
    )

    assert source is not None

    resolver = CSSDependencyResolver(
        project,
    )

    observation = Observation(
        source=source,
        kind=ReferenceKind.IMPORT,
        value="theme.css",
    )

    assert resolver.handles(observation) is False


def test_css_resolver_does_not_handle_non_import_observation(
    tmp_path: Path,
) -> None:
    project = create_css_project(
        tmp_path,
    )

    resolver = CSSDependencyResolver(
        project,
    )

    source = project.get_by_relative_path(
        "css/main.css",
    )

    assert source is not None

    observation = Observation(
        source=source,
        kind=ReferenceKind.CLASS,
        value="button",
    )

    assert resolver.handles(observation) is False


def test_css_resolver_returns_unresolved_for_missing_import(
    tmp_path: Path,
) -> None:
    project = create_css_project(
        tmp_path,
    )

    resolver = CSSDependencyResolver(
        project,
    )

    resolver.index_files(
        list(project.files.values())
    )

    observation = make_import_observation(
        project,
        "missing.css",
    )

    result = resolver.resolve(
        observation,
    )

    assert result.observation is observation
    assert result.resolved is False
    assert result.target is None