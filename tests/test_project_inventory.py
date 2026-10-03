from pathlib import Path

import pytest

from iksha.config.loader import load_config
from iksha.inventory.project_inventory import ProjectInventory


def create_file(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_discovers_supported_files(tmp_path: Path):
    create_file(tmp_path / "index.php")
    create_file(tmp_path / "page.html")
    create_file(tmp_path / "styles.css")
    create_file(tmp_path / "app.js")

    project = ProjectInventory(tmp_path).scan()

    assert project.total_files == 4

    assert project.get_file(tmp_path / "index.php") is not None
    assert project.get_file(tmp_path / "page.html") is not None
    assert project.get_file(tmp_path / "styles.css") is not None
    assert project.get_file(tmp_path / "app.js") is not None


def test_ignores_default_directories(tmp_path: Path):
    create_file(tmp_path / "index.php")

    create_file(tmp_path / ".git" / "config")
    create_file(tmp_path / ".venv" / "test.py")
    create_file(tmp_path / "node_modules" / "package.js")
    create_file(tmp_path / "dist" / "bundle.js")
    create_file(tmp_path / "build" / "output.css")
    create_file(tmp_path / "logs" / "app.js")
    create_file(tmp_path / "output" / "site.css")

    project = ProjectInventory(tmp_path).scan()

    assert project.total_files == 1
    assert project.get_file(tmp_path / "index.php") is not None


def test_ignores_unsupported_extensions(tmp_path: Path):
    create_file(tmp_path / "index.php")
    create_file(tmp_path / "image.png")
    create_file(tmp_path / "document.pdf")
    create_file(tmp_path / "notes.txt")

    project = ProjectInventory(tmp_path).scan()

    assert project.total_files == 1
    assert project.get_file(tmp_path / "index.php") is not None


def test_discovers_nested_files(tmp_path: Path):
    create_file(tmp_path / "admin" / "pages" / "dashboard.php")
    create_file(tmp_path / "assets" / "css" / "main.css")
    create_file(tmp_path / "assets" / "js" / "app.js")

    project = ProjectInventory(tmp_path).scan()

    assert project.total_files == 3


def test_preserves_same_filename_in_different_directories(
    tmp_path: Path,
):
    root_css = tmp_path / "css" / "main.css"
    admin_css = tmp_path / "admin" / "css" / "main.css"

    create_file(root_css)
    create_file(admin_css)

    project = ProjectInventory(tmp_path).scan()

    assert project.total_files == 2

    root_file = project.get_file(root_css)
    admin_file = project.get_file(admin_css)

    assert root_file is not None
    assert admin_file is not None
    assert root_file is not admin_file
    assert root_file.path != admin_file.path
    assert root_file.relative_path == "css/main.css"
    assert admin_file.relative_path == "admin/css/main.css"


def test_classifies_file_types(tmp_path: Path):
    create_file(tmp_path / "index.php")
    create_file(tmp_path / "page.html")
    create_file(tmp_path / "style.css")
    create_file(tmp_path / "app.js")

    project = ProjectInventory(tmp_path).scan()

    assert project.get_file(tmp_path / "index.php").file_type == "php"
    assert project.get_file(tmp_path / "page.html").file_type == "html"
    assert project.get_file(tmp_path / "style.css").file_type == "css"
    assert project.get_file(tmp_path / "app.js").file_type == "javascript"


def test_records_file_size(tmp_path: Path):
    content = "body { color: red; }"
    css = tmp_path / "style.css"

    create_file(css, content)

    project = ProjectInventory(tmp_path).scan()

    file = project.get_file(css)

    assert file is not None
    assert file.size == len(content.encode("utf-8"))


def test_inventory_results_are_deterministic(tmp_path: Path):
    create_file(tmp_path / "z.css")
    create_file(tmp_path / "a.php")
    create_file(tmp_path / "nested" / "m.js")

    first = ProjectInventory(tmp_path).scan()
    second = ProjectInventory(tmp_path).scan()

    first_paths = [
        file.relative_path
        for file in first.files.values()
    ]

    second_paths = [
        file.relative_path
        for file in second.files.values()
    ]

    assert first_paths == second_paths
    assert first_paths == sorted(first_paths)


def test_scan_root_is_canonicalized(tmp_path: Path):
    non_normalized = tmp_path / "nested" / ".."

    project = ProjectInventory(non_normalized).scan()

    assert project.root == tmp_path.resolve()


def test_empty_project_returns_empty_inventory(tmp_path: Path):
    project = ProjectInventory(tmp_path).scan()

    assert project.total_files == 0
    assert project.files == {}


def test_inventory_uses_configured_ignore_directories(tmp_path: Path):
    create_file(tmp_path / "index.php")
    create_file(tmp_path / "skip_me" / "hidden.php")
    create_file(tmp_path / "vendor" / "lib.php")

    config = load_config(
        tmp_path,
        cli_overrides={"ignore": ["skip_me"]},
    ).config

    project = ProjectInventory(
        tmp_path,
        config=config,
    ).scan()

    assert project.get_file(tmp_path / "index.php") is not None
    assert project.get_file(tmp_path / "skip_me" / "hidden.php") is None
    assert project.get_file(tmp_path / "vendor" / "lib.php") is not None


def test_inventory_uses_configured_extensions(tmp_path: Path):
    create_file(tmp_path / "index.php")
    create_file(tmp_path / "template.phtml")
    create_file(tmp_path / "style.css")

    config = load_config(
        tmp_path,
        cli_overrides={
            "extensions": {
                "php": [".php", ".phtml"],
            }
        },
    ).config

    project = ProjectInventory(
        tmp_path,
        config=config,
    ).scan()

    phtml = project.get_file(tmp_path / "template.phtml")

    assert phtml is not None
    assert phtml.file_type == "php"
    assert project.get_file(tmp_path / "style.css") is not None


def test_inventory_flags_minified_and_generated_files(tmp_path: Path):
    create_file(tmp_path / "css" / "app.min.css", "body{color:red}")
    create_file(tmp_path / "js" / "app.min.js", "console.log(1)")
    create_file(
        tmp_path / "css" / "wide.css",
        "a" * 2001,
    )
    create_file(tmp_path / "normal.css", "body { color: red; }\n")
    create_file(tmp_path / "generated" / "theme.css", ".ok{}")
    create_file(tmp_path / "cards.generated.css", ".card{}")

    project = ProjectInventory(tmp_path).scan()

    min_css = project.get_file(tmp_path / "css" / "app.min.css")
    min_js = project.get_file(tmp_path / "js" / "app.min.js")
    wide = project.get_file(tmp_path / "css" / "wide.css")
    normal = project.get_file(tmp_path / "normal.css")
    generated_dir = project.get_file(tmp_path / "generated" / "theme.css")
    generated_name = project.get_file(tmp_path / "cards.generated.css")

    assert min_css is not None and min_css.minified is True
    assert min_js is not None and min_js.minified is True
    assert wide is not None and wide.minified is True
    assert normal is not None and normal.minified is False
    assert generated_dir is not None
    assert generated_dir.generated is True
    assert generated_dir.ignored is False
    assert generated_name is not None and generated_name.generated is True
    assert project.total_files == 6


def test_inventory_lookups_use_project_indexes(tmp_path: Path):
    create_file(tmp_path / "css" / "main.css")
    create_file(tmp_path / "admin" / "css" / "main.css")
    create_file(tmp_path / "index.php")

    project = ProjectInventory(tmp_path).scan()

    assert project.get_by_relative_path("index.php") is not None
    assert len(project.files_named("main.css")) == 2
    assert len(project.files_with_extension("css")) == 2
    assert len(project.files_of_type("php")) == 1


def test_symlink_file_identity_is_the_real_path(tmp_path: Path):
    create_file(tmp_path / "real.php", "<?php echo 1;")
    alias = tmp_path / "alias.php"

    try:
        alias.symlink_to(tmp_path / "real.php")
    except OSError:
        pytest.skip("symlinks are not available on this system")

    project = ProjectInventory(tmp_path).scan()

    real = project.get_file(tmp_path / "real.php")

    assert real is not None
    assert project.total_files == 1
    assert project.get_file(alias) is real
    assert real.relative_path == "real.php"


def test_symlink_directories_are_not_followed_by_default(tmp_path: Path):
    create_file(tmp_path / "real" / "inside.php", "<?php")
    link = tmp_path / "linked"

    try:
        link.symlink_to(tmp_path / "real", target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are not available on this system")

    project = ProjectInventory(tmp_path).scan()

    assert project.get_file(tmp_path / "real" / "inside.php") is not None
    assert project.get_by_relative_path("linked/inside.php") is None
    assert project.total_files == 1


