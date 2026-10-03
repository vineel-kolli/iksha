from pathlib import Path

from iksha.analysis.entry_points import EntryPointResolver
from iksha.domain.project import Project
from iksha.inventory.project_inventory import ProjectInventory


def create_project(
    tmp_path: Path,
) -> Project:
    """Create a project containing multiple possible entry points."""

    (tmp_path / "index.php").write_text(
        "<?php echo 1; ?>",
        encoding="utf-8",
    )

    (tmp_path / "admin.php").write_text(
        "<?php echo 2; ?>",
        encoding="utf-8",
    )

    (tmp_path / "unused.php").write_text(
        "<?php echo 3; ?>",
        encoding="utf-8",
    )

    return ProjectInventory(
        tmp_path,
    ).scan()


def test_resolves_configured_entry_points(
    tmp_path: Path,
) -> None:
    project = create_project(
        tmp_path,
    )

    resolver = EntryPointResolver(
        project,
    )

    result = resolver.resolve(
        (
            "index.php",
            "admin.php",
        )
    )

    index_file = project.get_by_relative_path(
        "index.php",
    )
    admin_file = project.get_by_relative_path(
        "admin.php",
    )

    assert index_file is not None
    assert admin_file is not None

    assert result == (
        index_file,
        admin_file,
    )


def test_preserves_configured_order(
    tmp_path: Path,
) -> None:
    project = create_project(
        tmp_path,
    )

    resolver = EntryPointResolver(
        project,
    )

    result = resolver.resolve(
        (
            "admin.php",
            "index.php",
        )
    )

    assert [file.relative_path for file in result] == [
        "admin.php",
        "index.php",
    ]


def test_ignores_missing_entry_points(
    tmp_path: Path,
) -> None:
    project = create_project(
        tmp_path,
    )

    resolver = EntryPointResolver(
        project,
    )

    result = resolver.resolve(
        (
            "index.php",
            "missing.php",
        )
    )

    assert [file.relative_path for file in result] == [
        "index.php",
    ]


def test_normalizes_windows_and_dot_paths(
    tmp_path: Path,
) -> None:
    project = create_project(
        tmp_path,
    )

    resolver = EntryPointResolver(
        project,
    )

    result = resolver.resolve(
        (
            ".\\index.php",
            "./admin.php",
        )
    )

    assert [file.relative_path for file in result] == [
        "index.php",
        "admin.php",
    ]


def test_removes_duplicate_entry_points(
    tmp_path: Path,
) -> None:
    project = create_project(
        tmp_path,
    )

    resolver = EntryPointResolver(
        project,
    )

    result = resolver.resolve(
        (
            "index.php",
            "./index.php",
            "index.php",
        )
    )

    assert len(result) == 1
    assert result[0].relative_path == "index.php"


def test_returns_empty_tuple_when_no_entry_points_are_configured(
    tmp_path: Path,
) -> None:
    project = create_project(
        tmp_path,
    )

    resolver = EntryPointResolver(
        project,
    )

    assert resolver.resolve(()) == ()