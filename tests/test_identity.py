from pathlib import Path

from iksha.domain.identity import (
    file_identity_key,
    is_external_reference,
    normalize_reference_path,
)


def test_reference_strips_query_strings_and_fragments():
    assert normalize_reference_path("css/main.css?v=1") == "css/main.css"
    assert normalize_reference_path("css/main.css#theme") == "css/main.css"


def test_reference_collapses_dot_segments_and_separators():
    assert (
        normalize_reference_path(r"css\..\css\./main.css")
        == "css/main.css"
    )
    assert normalize_reference_path("/css/main.css") == "css/main.css"
    assert normalize_reference_path("./admin/index.php") == "admin/index.php"


def test_external_references_are_not_local_paths():
    assert is_external_reference("https://cdn.example.com/main.css")
    assert is_external_reference("//cdn.example.com/main.css")
    assert is_external_reference("data:text/css,body{}")
    assert normalize_reference_path("https://cdn.example.com/main.css") is None
    assert normalize_reference_path("data:text/css,body{}") is None


def test_local_references_are_not_external():
    assert not is_external_reference("css/main.css")
    assert not is_external_reference("C:/project/css/main.css")


def test_identity_key_is_casefold_when_insensitive(tmp_path: Path):
    path = tmp_path / "css" / "Main.css"
    path.parent.mkdir()
    path.write_text("body{}", encoding="utf-8")

    sensitive = file_identity_key(path, case_sensitive=True)
    insensitive = file_identity_key(path, case_sensitive=False)
    other_case = file_identity_key(
        tmp_path / "css" / "main.css",
        case_sensitive=False,
    )

    assert sensitive.endswith("Main.css") or "Main.css" in sensitive
    assert insensitive == other_case
    assert insensitive == sensitive.casefold()
