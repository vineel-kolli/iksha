from pathlib import Path

from iksha.analysis.pipeline import AnalysisPipeline
from iksha.config.loader import load_config
from iksha.dependency.php_resolver import PHPDependencyResolver
from iksha.domain.reference import ReferenceKind
from iksha.inventory.project_inventory import ProjectInventory
from iksha.parsing.defaults import register_default_parsers
from iksha.parsing.php import PHPParser
from iksha.parsing.registry import ParserRegistry
from iksha.source.loader import SourceLoader
from iksha.domain.project import Project


def create_project(tmp_path: Path) -> Project:
    (tmp_path / "index.php").write_text(
        '<?php include "header.php"; ?>',
        encoding="utf-8",
    )

    (tmp_path / "header.php").write_text(
        '<?php echo "Header"; ?>',
        encoding="utf-8",
    )

    (tmp_path / "admin").mkdir()

    (tmp_path / "admin" / "index.php").write_text(
        '<?php require "../header.php"; ?>',
        encoding="utf-8",
    )

    return ProjectInventory(tmp_path).scan()


def make_pipeline(
    project: Project,
) -> AnalysisPipeline:
    registry = ParserRegistry()

    registry.register(
        "php",
        PHPParser(),
    )

    resolver = PHPDependencyResolver(
        project.root,
    )

    resolver.index_files(
        list(project.files.values())
    )

    return AnalysisPipeline(
        project=project,
        source_loader=SourceLoader(),
        parser_registry=registry,
        dependency_resolver=resolver,
    )


def get_file(
    project: Project,
    path: Path,
):
    file = project.get_file(path)

    assert file is not None

    return file


def test_pipeline_builds_php_dependency_graph(
    tmp_path: Path,
):
    project = create_project(tmp_path)

    pipeline = make_pipeline(project)

    result = pipeline.run()

    index = get_file(
        project,
        tmp_path / "index.php",
    )

    header = get_file(
        project,
        tmp_path / "header.php",
    )

    assert result.graph.edge_count == 2

    assert header in result.graph.dependencies_of(
        index,
    )


def test_pipeline_resolves_nested_relative_reference(
    tmp_path: Path,
):
    project = create_project(tmp_path)

    pipeline = make_pipeline(project)

    result = pipeline.run()

    admin_index = get_file(
        project,
        tmp_path / "admin" / "index.php",
    )

    header = get_file(
        project,
        tmp_path / "header.php",
    )

    assert header in result.graph.dependencies_of(
        admin_index,
    )


def test_pipeline_preserves_authoritative_file_objects(
    tmp_path: Path,
):
    project = create_project(tmp_path)

    pipeline = make_pipeline(project)

    result = pipeline.run()

    index = get_file(
        project,
        tmp_path / "index.php",
    )

    header = get_file(
        project,
        tmp_path / "header.php",
    )

    edges = result.graph.edges_between(
        index,
        header,
    )

    assert len(edges) == 1

    edge = edges[0]

    assert edge.source is index
    assert edge.target is header


def test_pipeline_collects_unresolved_references(
    tmp_path: Path,
):
    (tmp_path / "index.php").write_text(
        '<?php include "missing.php"; ?>',
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    pipeline = make_pipeline(project)

    result = pipeline.run()

    assert result.graph.edge_count == 0

    assert len(result.unresolved) == 1

    assert (
        result.unresolved[0].observation.value
        == "missing.php"
    )


def test_pipeline_does_not_create_edges_for_dynamic_paths(
    tmp_path: Path,
):
    (tmp_path / "index.php").write_text(
        '<?php include $template; ?>',
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    pipeline = make_pipeline(project)

    result = pipeline.run()

    assert result.graph.edge_count == 0

    assert len(result.unresolved) == 1


def test_pipeline_ignores_unsupported_file_types(
    tmp_path: Path,
):
    (tmp_path / "index.php").write_text(
        '<?php include "header.php"; ?>',
        encoding="utf-8",
    )

    (tmp_path / "README.txt").write_text(
        "documentation",
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    pipeline = make_pipeline(project)

    result = pipeline.run()

    assert result.graph.edge_count == 0


def test_pipeline_is_repeatable(
    tmp_path: Path,
):
    project = create_project(tmp_path)

    pipeline = make_pipeline(project)

    first = pipeline.run()
    second = pipeline.run()

    assert (
        first.graph.edge_count
        == second.graph.edge_count
    )

    assert (
        len(first.unresolved)
        == len(second.unresolved)
    )


def test_pipeline_records_resolved_config(tmp_path: Path):
    project = create_project(tmp_path)
    loaded = load_config(
        tmp_path,
        cli_overrides={"maxFileSizeMB": 7},
    )

    pipeline = AnalysisPipeline(
        project=project,
        source_loader=SourceLoader(),
        parser_registry=ParserRegistry(),
        dependency_resolver=PHPDependencyResolver(project.root),
        config=loaded.config,
        config_diagnostics=loaded.diagnostics,
    )

    result = pipeline.run()

    assert result.config is loaded.config
    assert result.config.max_file_size_mb == 7.0
    assert result.diagnostics == loaded.diagnostics


def test_pipeline_keeps_html_observations_without_php_unresolved(
    tmp_path: Path,
):
    (tmp_path / "index.html").write_text(
        '<link rel="stylesheet" href="css/main.css">',
        encoding="utf-8",
    )
    (tmp_path / "css").mkdir()
    (tmp_path / "css" / "main.css").write_text(
        "body {}",
        encoding="utf-8",
    )

    project = ProjectInventory(tmp_path).scan()
    pipeline = AnalysisPipeline(
        project=project,
        source_loader=SourceLoader(),
        parser_registry=register_default_parsers(),
        dependency_resolver=PHPDependencyResolver(project.root),
    )

    result = pipeline.run()
    kinds = [item.kind for item in result.observations]

    assert ReferenceKind.STYLESHEET in kinds
    assert result.unresolved == []
    assert result.graph.edge_count == 1
    assert any(
        item.status.value == "resolved"
        for item in result.references
    )



def test_pipeline_warns_when_source_is_truncated(tmp_path: Path):
    (tmp_path / "index.php").write_text(
        '<?php include "header.php"; ?>',
        encoding="utf-8",
    )
    (tmp_path / "header.php").write_text(
        "<?php echo 1; ?>",
        encoding="utf-8",
    )

    project = ProjectInventory(tmp_path).scan()
    registry = ParserRegistry()
    registry.register("php", PHPParser())

    pipeline = AnalysisPipeline(
        project=project,
        source_loader=SourceLoader(
            max_file_size_mb=1 / (1024 * 1024),
        ),
        parser_registry=registry,
        dependency_resolver=PHPDependencyResolver(project.root),
    )

    result = pipeline.run()

    warnings = [
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.severity == "warning"
        and "truncated" in diagnostic.message
    ]

    assert warnings
    assert all(
        diagnostic.source is not None
        for diagnostic in warnings
    )

