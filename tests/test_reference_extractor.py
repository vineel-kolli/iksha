from pathlib import Path

from iksha.dependency.php_resolver import PHPDependencyResolver
from iksha.domain.file import File
from iksha.domain.reference import (
    Confidence,
    ReferenceKind,
    ResolutionStatus,
    ResolutionStrategy,
)
from iksha.domain.source_location import SourceLocation
from iksha.inventory.project_inventory import ProjectInventory
from iksha.parsing.result import Observation
from iksha.references.extractor import ReferenceExtractor


def make_observation(
    source: File,
    kind: ReferenceKind,
    value: str,
    confidence: Confidence = Confidence.CERTAIN,
) -> Observation:
    return Observation(
        source=source,
        kind=kind,
        value=value,
        location=SourceLocation(line=1, column=1),
        confidence=confidence,
    )


def make_extractor(tmp_path: Path) -> tuple[ReferenceExtractor, object]:
    project = ProjectInventory(tmp_path).scan()
    resolver = PHPDependencyResolver(project.root)
    resolver.index_files(list(project.files.values()))
    return ReferenceExtractor(project, resolver), project


def test_resolves_html_stylesheet_source_relative(tmp_path: Path):
    (tmp_path / "index.html").write_text(
        '<link rel="stylesheet" href="css/main.css">',
        encoding="utf-8",
    )
    (tmp_path / "css").mkdir()
    (tmp_path / "css" / "main.css").write_text(
        "body{}",
        encoding="utf-8",
    )

    extractor, project = make_extractor(tmp_path)
    source = project.get_file(tmp_path / "index.html")
    target = project.get_file(tmp_path / "css" / "main.css")

    reference = extractor.extract(
        make_observation(
            source,
            ReferenceKind.STYLESHEET,
            "css/main.css?v=2",
        )
    )

    assert reference is not None
    assert reference.status is ResolutionStatus.RESOLVED
    assert reference.resolution is ResolutionStrategy.SOURCE_RELATIVE
    assert reference.normalized == "css/main.css"
    assert reference.target is target
    assert reference.resolved is True


def test_resolves_css_import_relative_to_stylesheet(tmp_path: Path):
    (tmp_path / "css").mkdir()
    (tmp_path / "css" / "main.css").write_text(
        '@import "header.css";',
        encoding="utf-8",
    )
    (tmp_path / "css" / "header.css").write_text(
        "h1{}",
        encoding="utf-8",
    )

    extractor, project = make_extractor(tmp_path)
    source = project.get_file(tmp_path / "css" / "main.css")
    target = project.get_file(tmp_path / "css" / "header.css")

    reference = extractor.extract(
        make_observation(
            source,
            ReferenceKind.IMPORT,
            "header.css",
        )
    )

    assert reference is not None
    assert reference.status is ResolutionStatus.RESOLVED
    assert reference.resolution is ResolutionStrategy.IMPORT_RELATIVE
    assert reference.target is target


def test_resolves_js_import(tmp_path: Path):
    (tmp_path / "js").mkdir()
    (tmp_path / "js" / "app.js").write_text(
        'import "./utils.js";',
        encoding="utf-8",
    )
    (tmp_path / "js" / "utils.js").write_text(
        "export {};",
        encoding="utf-8",
    )

    extractor, project = make_extractor(tmp_path)
    source = project.get_file(tmp_path / "js" / "app.js")
    target = project.get_file(tmp_path / "js" / "utils.js")

    reference = extractor.extract(
        make_observation(
            source,
            ReferenceKind.IMPORT,
            "./utils.js",
        )
    )

    assert reference is not None
    assert reference.status is ResolutionStatus.RESOLVED
    assert reference.target is target


def test_external_stylesheet_is_not_a_local_file(tmp_path: Path):
    (tmp_path / "index.html").write_text(
        "<html></html>",
        encoding="utf-8",
    )

    extractor, project = make_extractor(tmp_path)
    source = project.get_file(tmp_path / "index.html")

    reference = extractor.extract(
        make_observation(
            source,
            ReferenceKind.STYLESHEET,
            "https://cdn.example.com/main.css",
        )
    )

    assert reference is not None
    assert reference.status is ResolutionStatus.EXTERNAL
    assert reference.resolution is ResolutionStrategy.URL
    assert reference.target is None
    assert reference.resolved is False


def test_duplicate_filenames_are_ambiguous_without_path(tmp_path: Path):
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "css").mkdir()
    (tmp_path / "admin").mkdir()
    (tmp_path / "css" / "main.css").write_text("a{}", encoding="utf-8")
    (tmp_path / "admin" / "main.css").write_text("b{}", encoding="utf-8")

    extractor, project = make_extractor(tmp_path)
    source = project.get_file(tmp_path / "index.html")

    reference = extractor.extract(
        make_observation(
            source,
            ReferenceKind.STYLESHEET,
            "main.css",
        )
    )

    assert reference is not None
    assert reference.status is ResolutionStatus.AMBIGUOUS
    assert reference.target is None
    assert len(reference.candidates) == 2


def test_dynamic_class_usage_is_not_a_file_target(tmp_path: Path):
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")

    extractor, project = make_extractor(tmp_path)
    source = project.get_file(tmp_path / "index.html")

    reference = extractor.extract(
        make_observation(
            source,
            ReferenceKind.CLASS,
            "<?= $class ?>",
            confidence=Confidence.UNKNOWN,
        )
    )

    assert reference is not None
    assert reference.status is ResolutionStatus.DYNAMIC
    assert reference.target is None


def test_project_relative_url_path(tmp_path: Path):
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "css").mkdir()
    (tmp_path / "css" / "main.css").write_text("{}", encoding="utf-8")

    extractor, project = make_extractor(tmp_path)
    source = project.get_file(tmp_path / "index.html")
    target = project.get_file(tmp_path / "css" / "main.css")

    reference = extractor.extract(
        make_observation(
            source,
            ReferenceKind.STYLESHEET,
            "/css/main.css",
        )
    )

    assert reference is not None
    assert reference.status is ResolutionStatus.RESOLVED
    assert reference.resolution is ResolutionStrategy.PROJECT_RELATIVE
    assert reference.target is target


def test_resolves_php_include(tmp_path: Path):
    (tmp_path / "index.php").write_text(
        '<?php include "header.php"; ?>',
        encoding="utf-8",
    )
    (tmp_path / "header.php").write_text(
        "<?php",
        encoding="utf-8",
    )

    extractor, project = make_extractor(tmp_path)
    source = project.get_file(tmp_path / "index.php")
    target = project.get_file(tmp_path / "header.php")

    reference = extractor.extract(
        make_observation(
            source,
            ReferenceKind.INCLUDE,
            "header.php",
        )
    )

    assert reference is not None
    assert reference.status is ResolutionStatus.RESOLVED
    assert reference.resolution is ResolutionStrategy.SOURCE_RELATIVE
    assert reference.target is target
    assert reference.evidence is not None
    assert reference.evidence.raw == "header.php"
    assert reference.evidence.target is target


def test_missing_local_stylesheet_is_unresolved(tmp_path: Path):
    (tmp_path / "index.html").write_text(
        "<html></html>",
        encoding="utf-8",
    )

    extractor, project = make_extractor(tmp_path)
    source = project.get_file(tmp_path / "index.html")

    reference = extractor.extract(
        make_observation(
            source,
            ReferenceKind.STYLESHEET,
            "css/missing.css",
        )
    )

    assert reference is not None
    assert reference.status is ResolutionStatus.UNRESOLVED
    assert reference.resolved is False
    assert reference.target is None
    assert reference.normalized == "css/missing.css"


def test_static_class_usage_has_no_file_target(tmp_path: Path):
    (tmp_path / "index.html").write_text(
        '<div class="card"></div>',
        encoding="utf-8",
    )

    extractor, project = make_extractor(tmp_path)
    source = project.get_file(tmp_path / "index.html")

    reference = extractor.extract(
        make_observation(
            source,
            ReferenceKind.CLASS,
            "card",
        )
    )

    assert reference is not None
    assert reference.raw_target == "card"
    assert reference.target is None
    assert reference.status is not ResolutionStatus.EXTERNAL
    assert reference.evidence is not None
    assert reference.evidence.kind is ReferenceKind.CLASS
