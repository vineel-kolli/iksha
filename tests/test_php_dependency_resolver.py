from pathlib import Path

from iksha.dependency.php_resolver import PHPDependencyResolver
from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.domain.source_location import SourceLocation
from iksha.parsing.result import Observation


def make_file(
    root: Path,
    relative_path: str,
) -> File:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")

    return File(
        path=path,
        relative_path=relative_path,
        file_type="php",
        size=path.stat().st_size,
    )


def make_observation(
    source: File,
    value: str,
) -> Observation:
    return Observation(
        source=source,
        kind=ReferenceKind.INCLUDE,
        value=value,
        location=SourceLocation(
            line=10,
            column=5,
        ),
        confidence=Confidence.CERTAIN,
    )


def make_resolver(
    root: Path,
    files: list[File],
) -> PHPDependencyResolver:
    resolver = PHPDependencyResolver(root)
    resolver.index_files(files)
    return resolver


def test_resolves_relative_php_reference(tmp_path: Path):
    source = make_file(
        tmp_path,
        "pages/index.php",
    )

    target = make_file(
        tmp_path,
        "pages/header.php",
    )

    resolver = make_resolver(
        tmp_path,
        [source, target],
    )

    result = resolver.resolve(
        make_observation(source, "header.php")
    )

    assert result.resolved is True
    assert result.target is target


def test_resolves_parent_directory_reference(tmp_path: Path):
    source = make_file(
        tmp_path,
        "admin/pages/index.php",
    )

    target = make_file(
        tmp_path,
        "admin/header.php",
    )

    resolver = make_resolver(
        tmp_path,
        [source, target],
    )

    result = resolver.resolve(
        make_observation(source, "../header.php")
    )

    assert result.resolved is True
    assert result.target is target


def test_resolves_dot_reference(tmp_path: Path):
    source = make_file(
        tmp_path,
        "pages/index.php",
    )

    target = make_file(
        tmp_path,
        "pages/header.php",
    )

    resolver = make_resolver(
        tmp_path,
        [source, target],
    )

    result = resolver.resolve(
        make_observation(source, "./header.php")
    )

    assert result.resolved is True
    assert result.target is target


def test_does_not_confuse_same_filename_in_other_directory(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "pages/index.php",
    )

    target = make_file(
        tmp_path,
        "pages/header.php",
    )

    other = make_file(
        tmp_path,
        "admin/header.php",
    )

    resolver = make_resolver(
        tmp_path,
        [source, target, other],
    )

    result = resolver.resolve(
        make_observation(source, "header.php")
    )

    assert result.resolved is True
    assert result.target is target
    assert result.target is not other


def test_resolves_normalized_parent_segments(tmp_path: Path):
    source = make_file(
        tmp_path,
        "pages/index.php",
    )

    target = make_file(
        tmp_path,
        "header.php",
    )

    resolver = make_resolver(
        tmp_path,
        [source, target],
    )

    result = resolver.resolve(
        make_observation(
            source,
            "../pages/../header.php",
        )
    )

    assert result.resolved is True
    assert result.target is target


def test_missing_dependency_is_unresolved(tmp_path: Path):
    source = make_file(
        tmp_path,
        "index.php",
    )

    resolver = make_resolver(
        tmp_path,
        [source],
    )

    result = resolver.resolve(
        make_observation(
            source,
            "missing.php",
        )
    )

    assert result.resolved is False
    assert result.target is None


def test_dynamic_expression_is_not_resolved(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    resolver = make_resolver(
        tmp_path,
        [source],
    )

    result = resolver.resolve(
        Observation(
            source=source,
            kind=ReferenceKind.INCLUDE,
            value="$template",
            location=SourceLocation(
                line=5,
                column=1,
            ),
            confidence=Confidence.LOW,
        )
    )

    assert result.resolved is False
    assert result.target is None


def test_preserves_original_observation_evidence(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    target = make_file(
        tmp_path,
        "header.php",
    )

    observation = make_observation(
        source,
        "header.php",
    )

    resolver = make_resolver(
        tmp_path,
        [source, target],
    )

    result = resolver.resolve(observation)

    assert result.observation is observation
    assert result.observation.source is source
    assert result.observation.location.line == 10
    assert result.observation.location.column == 5
    assert result.observation.value == "header.php"

    # Resolver must return the authoritative File object.
    assert result.target is target


def test_does_not_resolve_outside_project(
    tmp_path: Path,
):
    project = tmp_path / "project"
    outside = tmp_path / "outside"

    project.mkdir()
    outside.mkdir()

    source = make_file(
        project,
        "index.php",
    )

    outside_target = outside / "secret.php"
    outside_target.write_text(
        "",
        encoding="utf-8",
    )

    resolver = make_resolver(
        project,
        [source],
    )

    result = resolver.resolve(
        make_observation(
            source,
            "../outside/secret.php",
        )
    )

    assert result.resolved is False
    assert result.target is None


def test_non_php_target_is_not_selected(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    css = tmp_path / "style.css"
    css.write_text(
        "",
        encoding="utf-8",
    )

    resolver = make_resolver(
        tmp_path,
        [source],
    )

    result = resolver.resolve(
        make_observation(
            source,
            "style.css",
        )
    )

    assert result.resolved is False
    assert result.target is None


def test_php_extension_can_be_explicit(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "pages/index.php",
    )

    target = make_file(
        tmp_path,
        "pages/header.php",
    )

    resolver = make_resolver(
        tmp_path,
        [source, target],
    )

    result = resolver.resolve(
        make_observation(
            source,
            "header.php",
        )
    )

    assert result.resolved is True
    assert result.target is target
