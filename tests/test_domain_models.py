from pathlib import Path

import pytest

from iksha.domain.file import File
from iksha.domain.project import Project
from iksha.domain.reference import (
    Confidence,
    Reference,
    ReferenceKind,
)
from iksha.domain.source_location import SourceLocation


def test_file_identity_uses_full_path():
    root = Path("project").resolve()

    main = File(
        path=(root / "css" / "main.css").resolve(),
        relative_path="css/main.css",
        file_type="css",
    )

    admin = File(
        path=(root / "css" / "admin" / "css" / "main.css").resolve(),
        relative_path="css/admin/css/main.css",
        file_type="css",
    )

    assert main.path != admin.path
    assert main.name == admin.name
    assert main.relative_path != admin.relative_path


def test_project_stores_files_by_canonical_path():
    root = Path("project").resolve()

    file = File(
        path=(root / "css" / "main.css").resolve(),
        relative_path="css/main.css",
        file_type="css",
    )

    project = Project(root=root)
    project.add_file(file)

    assert project.total_files == 1
    assert project.get_file(file.path) is file


def test_file_normalizes_parent_directory_segments(tmp_path: Path):
    css = tmp_path / "css"
    css.mkdir()

    main = css / "main.css"
    main.write_text("", encoding="utf-8")

    non_normalized = css / ".." / "css" / "main.css"

    file = File(
        path=non_normalized,
        relative_path="css/../css/main.css",
        file_type="css",
    )

    assert file.path == main.resolve()


def test_project_lookup_normalizes_parent_directory_segments(
    tmp_path: Path,
):
    css = tmp_path / "css"
    css.mkdir()

    main = css / "main.css"
    main.write_text("", encoding="utf-8")

    project = Project(root=tmp_path)

    file = File(
        path=main,
        relative_path="css/main.css",
        file_type="css",
    )

    project.add_file(file)

    lookup_path = css / ".." / "css" / "main.css"

    assert project.get_file(lookup_path) is file
    assert project.contains(lookup_path)


def test_same_filename_in_different_directories_is_not_merged(
    tmp_path: Path,
):
    root_css = tmp_path / "css"
    admin_css = tmp_path / "css" / "admin" / "css"

    root_css.mkdir(parents=True)
    admin_css.mkdir(parents=True)

    root_main = root_css / "main.css"
    admin_main = admin_css / "main.css"

    root_main.write_text("", encoding="utf-8")
    admin_main.write_text("", encoding="utf-8")

    project = Project(root=tmp_path)

    root_file = File(
        path=root_main,
        relative_path="css/main.css",
        file_type="css",
    )

    admin_file = File(
        path=admin_main,
        relative_path="css/admin/css/main.css",
        file_type="css",
    )

    project.add_file(root_file)
    project.add_file(admin_file)

    assert project.total_files == 2
    assert project.get_file(root_main) is root_file
    assert project.get_file(admin_main) is admin_file


def test_adding_same_physical_file_does_not_create_duplicate(
    tmp_path: Path,
):
    css = tmp_path / "css"
    css.mkdir()

    main = css / "main.css"
    main.write_text("", encoding="utf-8")

    project = Project(root=tmp_path)

    first = File(
        path=main,
        relative_path="css/main.css",
        file_type="css",
    )

    second = File(
        path=css / ".." / "css" / "main.css",
        relative_path="css/../css/main.css",
        file_type="css",
    )

    project.add_file(first)
    project.add_file(second)

    assert project.total_files == 1
    assert project.get_file(main) is second


def test_file_stores_size():
    file = File(
        path=Path("style.css"),
        relative_path="style.css",
        file_type="css",
        size=1234,
    )

    assert file.size == 1234


def test_file_rejects_negative_size():
    with pytest.raises(ValueError):
        File(
            path=Path("style.css"),
            relative_path="style.css",
            file_type="css",
            size=-1,
        )


def test_source_location_requires_positive_values():
    location = SourceLocation(
        line=10,
        column=5,
    )

    assert location.line == 10
    assert location.column == 5


def test_source_location_rejects_invalid_line():
    with pytest.raises(ValueError):
        SourceLocation(
            line=0,
            column=1,
        )


def test_reference_preserves_evidence():
    root = Path("project").resolve()

    source = File(
        path=(root / "index.php").resolve(),
        relative_path="index.php",
        file_type="php",
    )

    target = File(
        path=(root / "header.php").resolve(),
        relative_path="header.php",
        file_type="php",
    )

    reference = Reference(
        source=source,
        target=target,
        kind=ReferenceKind.INCLUDE,
        location=SourceLocation(
            line=12,
            column=5,
        ),
        raw_target="header.php",
        confidence=Confidence.CERTAIN,
        resolved=True,
    )

    assert reference.source is source
    assert reference.target is target
    assert reference.kind == ReferenceKind.INCLUDE
    assert reference.raw_target == "header.php"
    assert reference.location.line == 12
    assert reference.confidence == Confidence.CERTAIN
    assert reference.resolved is True
