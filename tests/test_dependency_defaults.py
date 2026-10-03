from pathlib import Path

from iksha.dependency.css_resolver import CSSDependencyResolver
from iksha.dependency.defaults import register_default_resolvers
from iksha.dependency.php_resolver import PHPDependencyResolver
from iksha.domain.project import Project
from iksha.domain.reference import ReferenceKind
from iksha.inventory.project_inventory import ProjectInventory
from iksha.parsing.result import Observation


def test_register_default_resolvers_registers_built_in_resolvers(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.php").write_text(
        '<?php include "header.php"; ?>',
        encoding="utf-8",
    )

    (tmp_path / "header.php").write_text(
        "<?php echo 1; ?>",
        encoding="utf-8",
    )

    (tmp_path / "main.css").write_text(
        '@import "theme.css";',
        encoding="utf-8",
    )

    (tmp_path / "theme.css").write_text(
        "body {}",
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    registry = register_default_resolvers(
        project,
    )

    php_source = project.get_by_relative_path(
        "index.php",
    )
    css_source = project.get_by_relative_path(
        "main.css",
    )

    assert php_source is not None
    assert css_source is not None

    php_observation = Observation(
        source=php_source,
        kind=ReferenceKind.INCLUDE,
        value="header.php",
    )

    css_observation = Observation(
        source=css_source,
        kind=ReferenceKind.IMPORT,
        value="theme.css",
    )

    assert registry.handles(
        php_observation,
    ) is True

    assert registry.handles(
        css_observation,
    ) is True


def test_register_default_resolvers_accepts_existing_registry(
    tmp_path: Path,
) -> None:
    project = ProjectInventory(
        tmp_path,
    ).scan()

    registry = register_default_resolvers(
        project,
    )

    same_registry = register_default_resolvers(
        project,
        registry,
    )

    assert same_registry is registry
    assert len(registry._resolvers) == 4


def test_default_resolver_types_are_registered(
    tmp_path: Path,
) -> None:
    project = ProjectInventory(
        tmp_path,
    ).scan()

    registry = register_default_resolvers(
        project,
    )

    resolvers = registry._resolvers

    assert len(resolvers) == 2
    assert isinstance(
        resolvers[0],
        PHPDependencyResolver,
    )
    assert isinstance(
        resolvers[1],
        CSSDependencyResolver,
    )