from pathlib import Path

from iksha.analysis.factory import create_analysis_pipeline
from iksha.domain.project import Project
from iksha.inventory.project_inventory import ProjectInventory
from iksha.parsing.defaults import register_default_parsers
from iksha.source.loader import SourceLoader


def create_project(tmp_path: Path) -> Project:
    """Create a minimal project for factory tests."""

    (tmp_path / "index.php").write_text(
        '<?php include "header.php"; ?>',
        encoding="utf-8",
    )

    (tmp_path / "header.php").write_text(
        "<?php echo 1; ?>",
        encoding="utf-8",
    )

    return ProjectInventory(
        tmp_path,
    ).scan()


def test_factory_creates_analysis_pipeline(
    tmp_path: Path,
) -> None:
    project = create_project(
        tmp_path,
    )

    pipeline = create_analysis_pipeline(
        project,
    )

    result = pipeline.run()

    assert result.config is not None
    assert len(result.references) == 1

    edge_list = list(
        result.graph.edges()
    )

    assert len(edge_list) == 1


def test_factory_accepts_custom_components(
    tmp_path: Path,
) -> None:
    project = create_project(
        tmp_path,
    )

    parser_registry = register_default_parsers()
    source_loader = SourceLoader(
        max_file_size_mb=1,
    )

    pipeline = create_analysis_pipeline(
        project,
        parser_registry=parser_registry,
        source_loader=source_loader,
    )

    assert pipeline.project is project
    assert pipeline.parser_registry is parser_registry
    assert pipeline.source_loader is source_loader