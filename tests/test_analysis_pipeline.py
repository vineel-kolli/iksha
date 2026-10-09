from pathlib import Path

from iksha.analysis.factory import create_analysis_pipeline
from iksha.analysis.pipeline import AnalysisPipeline
from iksha.config.loader import load_config
from iksha.domain.project import Project
from iksha.domain.reference import ReferenceKind
from iksha.inventory.project_inventory import ProjectInventory
from iksha.parsing.defaults import register_default_parsers
from iksha.parsing.php import PHPParser
from iksha.parsing.registry import ParserRegistry
from iksha.source.loader import SourceLoader
from iksha.domain.states import ReachabilityState, UsageState


def create_project(tmp_path: Path) -> Project:
    """Create a project containing a simple PHP dependency."""

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


def make_pipeline(
    project: Project,
    *,
    source_loader: SourceLoader | None = None,
) -> AnalysisPipeline:
    return create_analysis_pipeline(
        project,
        source_loader=source_loader,
    )


def test_pipeline_builds_php_dependency_graph(
    tmp_path: Path,
) -> None:
    project = create_project(
        tmp_path,
    )

    pipeline = make_pipeline(
        project,
    )

    result = pipeline.run()

    index_file = project.get_by_relative_path(
        "index.php",
    )
    header_file = project.get_by_relative_path(
        "header.php",
    )

    assert index_file is not None
    assert header_file is not None

    edges = list(
        result.graph.edges()
    )

    assert len(edges) == 1
    assert edges[0].source is index_file
    assert edges[0].target is header_file


def test_pipeline_resolves_nested_relative_reference(
    tmp_path: Path,
) -> None:
    (tmp_path / "pages").mkdir()
    (tmp_path / "includes").mkdir()

    (tmp_path / "pages" / "index.php").write_text(
        '<?php include "../includes/header.php"; ?>',
        encoding="utf-8",
    )

    (tmp_path / "includes" / "header.php").write_text(
        "<?php echo 1; ?>",
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    pipeline = make_pipeline(
        project,
    )

    result = pipeline.run()

    page_file = project.get_by_relative_path(
        "pages/index.php",
    )
    header_file = project.get_by_relative_path(
        "includes/header.php",
    )

    assert page_file is not None
    assert header_file is not None

    edges = list(
        result.graph.edges()
    )

    assert len(edges) == 1
    assert edges[0].source is page_file
    assert edges[0].target is header_file


def test_pipeline_preserves_authoritative_file_objects(
    tmp_path: Path,
) -> None:
    project = create_project(
        tmp_path,
    )

    pipeline = make_pipeline(
        project,
    )

    result = pipeline.run()

    index_file = project.get_by_relative_path(
        "index.php",
    )
    header_file = project.get_by_relative_path(
        "header.php",
    )

    assert index_file is not None
    assert header_file is not None

    reference = result.references[0]

    assert reference.source is index_file
    assert reference.target is header_file


def test_pipeline_collects_unresolved_references(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.php").write_text(
        '<?php include "missing.php"; ?>',
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    pipeline = make_pipeline(
        project,
    )

    result = pipeline.run()

    assert len(result.unresolved) == 1
    assert result.unresolved[0].observation.kind in {
        ReferenceKind.INCLUDE,
        ReferenceKind.REQUIRE,
    }

    assert result.unresolved[0].target is None


def test_pipeline_does_not_create_edges_for_dynamic_paths(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.php").write_text(
        '<?php include $template; ?>',
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    pipeline = make_pipeline(
        project,
    )

    result = pipeline.run()

    assert list(
        result.graph.edges()
    ) == []


def test_pipeline_ignores_unsupported_file_types(
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

    (tmp_path / "README.txt").write_text(
        "documentation",
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    pipeline = make_pipeline(
        project,
    )

    result = pipeline.run()

    assert len(result.references) == 1
    assert len(result.graph.edges()) == 1
    assert result.diagnostics == []


def test_pipeline_is_repeatable(
    tmp_path: Path,
) -> None:
    project = create_project(
        tmp_path,
    )

    pipeline = make_pipeline(
        project,
    )

    first = pipeline.run()
    second = pipeline.run()

    assert first.observations == second.observations
    assert first.references == second.references
    assert first.unresolved == second.unresolved
    assert list(first.graph.edges()) == list(
        second.graph.edges()
    )
    assert first.diagnostics == second.diagnostics


def test_pipeline_records_resolved_config(
    tmp_path: Path,
) -> None:
    project = create_project(
        tmp_path,
    )

    loaded = load_config(
        tmp_path,
        cli_overrides={
            "maxFileSizeMB": 7,
        },
    )

    pipeline = create_analysis_pipeline(
        project,
        config=loaded.config,
    )

    result = pipeline.run()

    assert result.config == loaded.config
    assert result.config.max_file_size_mb == 7
    assert result.diagnostics == []


def test_pipeline_keeps_html_observations_without_php_unresolved(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.html").write_text(
        '<link rel="stylesheet" href="css/main.css">',
        encoding="utf-8",
    )

    (tmp_path / "css").mkdir()

    (tmp_path / "css" / "main.css").write_text(
        "body {}",
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    pipeline = make_pipeline(
        project,
    )

    result = pipeline.run()

    assert any(
        observation.kind
        is ReferenceKind.STYLESHEET
        for observation in result.observations
    )

    assert not any(
        unresolved.observation.kind
        in {
            ReferenceKind.INCLUDE,
            ReferenceKind.REQUIRE,
        }
        for unresolved in result.unresolved
    )


def test_pipeline_warns_when_source_is_truncated(
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

    project = ProjectInventory(
        tmp_path,
    ).scan()

    registry = ParserRegistry()
    registry.register(
        "php",
        PHPParser(),
    )

    source_loader = SourceLoader(
        max_file_size_mb=1 / (1024 * 1024),
    )

    pipeline = create_analysis_pipeline(
        project,
        parser_registry=registry,
        source_loader=source_loader,
    )

    result = pipeline.run()

    assert any(
        diagnostic.severity == "warning"
        and "truncated" in diagnostic.message.lower()
        for diagnostic in result.diagnostics
    )
def test_pipeline_records_reachability_for_configured_entry_points(
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

    (tmp_path / "unused.php").write_text(
        "<?php echo 2; ?>",
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    loaded = load_config(
        tmp_path,
        cli_overrides={
            "entryPoints": [
                "index.php",
            ],
        },
    )

    pipeline = create_analysis_pipeline(
        project,
        config=loaded.config,
    )

    result = pipeline.run()

    assert result.reachability is not None

    index_file = project.get_by_relative_path(
        "index.php",
    )
    header_file = project.get_by_relative_path(
        "header.php",
    )
    unused_file = project.get_by_relative_path(
        "unused.php",
    )

    assert index_file is not None
    assert header_file is not None
    assert unused_file is not None

    assert result.reachability.state_for(
        index_file,
    ) is ReachabilityState.REACHABLE

    assert result.reachability.state_for(
        header_file,
    ) is ReachabilityState.REACHABLE

    assert result.reachability.state_for(
        unused_file,
    ) is ReachabilityState.UNREACHABLE


def test_pipeline_keeps_reachability_unknown_without_entry_points(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.php").write_text(
        "<?php echo 1; ?>",
        encoding="utf-8",
    )

    (tmp_path / "style.css").write_text(
        "body {}",
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    pipeline = create_analysis_pipeline(
        project,
    )

    result = pipeline.run()

    assert result.reachability is not None
    assert result.reachability.entry_points == ()

    for file in project.files.values():
        assert result.reachability.state_for(
            file,
        ) is ReachabilityState.UNKNOWN

def test_pipeline_correlates_css_selector_with_html_class_usage(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.html").write_text(
        '<div class="card"></div>',
        encoding="utf-8",
    )

    (tmp_path / "style.css").write_text(
        ".card { color: red; }",
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    pipeline = make_pipeline(
        project,
    )

    result = pipeline.run()

    css_file = project.get_by_relative_path(
        "style.css",
    )

    assert css_file is not None

    usages = result.selector_usage.usages_for(
        css_file,
    )

    assert len(usages) == 1
    assert usages[0].selector == ".card"
    assert usages[0].state.value == "definitely_used"
    assert len(usages[0].evidence) == 1
    assert usages[0].evidence[0].kind is ReferenceKind.CLASS
    assert usages[0].evidence[0].value == "card"
def test_pipeline_retains_parsed_html_documents(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.html").write_text(
        '<main><div id="hero" class="card"></div></main>',
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    pipeline = make_pipeline(
        project,
    )

    result = pipeline.run()

    html_file = project.get_by_relative_path(
        "index.html",
    )

    assert html_file is not None
    assert html_file in result.html_documents

    document = result.html_documents[html_file]
    elements = document.all_elements()

    assert [element.tag for element in elements] == [
        "main",
        "div",
    ]

    assert elements[1].element_id == "hero"
    assert elements[1].classes == frozenset({"card"})
    assert elements[1].parent is elements[0]
def test_pipeline_correlates_css_selector_with_html_dom(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.html").write_text(
        '<main><div class="card"></div></main>',
        encoding="utf-8",
    )

    (tmp_path / "style.css").write_text(
        ".card { color: red; }",
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    pipeline = make_pipeline(
        project,
    )

    result = pipeline.run()

    css_file = project.get_by_relative_path(
        "style.css",
    )

    html_file = project.get_by_relative_path(
        "index.html",
    )

    assert css_file is not None
    assert html_file is not None
    assert html_file in result.html_documents

    document = result.html_documents[html_file]
    elements = document.all_elements()

    assert len(elements) == 2
    assert elements[1].tag == "div"
    assert elements[1].classes == frozenset({"card"})
    assert len(elements) == 2
    assert elements[1].tag == "div"
    assert elements[1].classes == frozenset({"card"})

    usages = result.selector_usage.usages_for(
        css_file,
    )

    assert len(usages) == 1

    usage = usages[0]

    assert usage.selector == ".card"
    assert usage.state.value == "definitely_used"
    assert len(usage.semantic_matches) == 1
    assert usage.semantic_matches[0].source is html_file
    assert usage.semantic_matches[0].element_tag == "div"
    assert usage.semantic_matches[0].element_classes == ("card",)
    assert usage.matched_files == (html_file,)


def test_pipeline_does_not_mark_selector_unused_when_html_is_truncated(
    tmp_path: Path,
) -> None:
    html_prefix = '<main><div class="other"></div>'
    html_tail = '<div class="card"></div></main>'
    html = html_prefix + html_tail

    (tmp_path / "index.html").write_text(
        html,
        encoding="utf-8",
    )

    (tmp_path / "style.css").write_text(
        ".card { color: red; }",
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    max_file_size_mb = (
        len(html_prefix.encode("utf-8"))
        / (1024 * 1024)
    )

    pipeline = make_pipeline(
        project,
        source_loader=SourceLoader(
            max_file_size_mb=max_file_size_mb,
        ),
    )

    result = pipeline.run()

    css_file = project.get_by_relative_path(
        "style.css",
    )

    html_file = project.get_by_relative_path(
        "index.html",
    )

    assert css_file is not None
    assert html_file is not None

    assert any(
        diagnostic.severity == "warning"
        and "truncated" in diagnostic.message.lower()
        and diagnostic.source is html_file
        for diagnostic in result.diagnostics
    )

    usages = result.selector_usage.usages_for(
        css_file,
    )

    assert len(usages) == 1
    assert usages[0].selector == ".card"
    assert usages[0].state is UsageState.UNKNOWN


def test_pipeline_keeps_selector_usage_found_before_html_truncation(
    tmp_path: Path,
) -> None:
    html_prefix = '<main><div class="card"></div>'
    html_tail = '<div class="other"></div></main>'
    html = html_prefix + html_tail

    (tmp_path / "index.html").write_text(
        html,
        encoding="utf-8",
    )

    (tmp_path / "style.css").write_text(
        ".card { color: red; }",
        encoding="utf-8",
    )

    project = ProjectInventory(
        tmp_path,
    ).scan()

    max_file_size_mb = (
        len(html_prefix.encode("utf-8"))
        / (1024 * 1024)
    )

    pipeline = make_pipeline(
        project,
        source_loader=SourceLoader(
            max_file_size_mb=max_file_size_mb,
        ),
    )

    result = pipeline.run()

    css_file = project.get_by_relative_path(
        "style.css",
    )

    html_file = project.get_by_relative_path(
        "index.html",
    )

    assert css_file is not None
    assert html_file is not None

    assert any(
        diagnostic.severity == "warning"
        and "truncated" in diagnostic.message.lower()
        and diagnostic.source is html_file
        for diagnostic in result.diagnostics
    )

    usages = result.selector_usage.usages_for(
        css_file,
    )

    assert len(usages) == 1

    usage = usages[0]

    assert usage.selector == ".card"
    assert usage.state is UsageState.DEFINITELY_USED
    assert usage.matched_files == (html_file,)


def test_pipeline_correlates_css_selector_with_javascript_dom_selector(
    tmp_path: Path,
) -> None:
    (tmp_path / "app.js").write_text(
        'document.querySelector(".card");',
        encoding="utf-8",
    )

    (tmp_path / "style.css").write_text(
        ".card { color: red; }",
        encoding="utf-8",
    )

    project = ProjectInventory(tmp_path).scan()
    pipeline = make_pipeline(project)

    result = pipeline.run()

    css_file = project.get_by_relative_path("style.css")
    js_file = project.get_by_relative_path("app.js")

    assert css_file is not None
    assert js_file is not None

    usages = result.selector_usage.usages_for(css_file)

    assert len(usages) == 1

    usage = usages[0]

    assert usage.selector == ".card"
    assert usage.state is UsageState.DEFINITELY_USED
    assert any(
        evidence.kind is ReferenceKind.DOM_SELECTOR
        and evidence.source is js_file
        and evidence.value == ".card"
        for evidence in usage.evidence
    )


def test_pipeline_correlates_css_selector_with_php_template_usage(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.php").write_text(
        '<div class="card">Product</div>',
        encoding="utf-8",
    )

    (tmp_path / "style.css").write_text(
        ".card { color: red; }",
        encoding="utf-8",
    )

    project = ProjectInventory(tmp_path).scan()
    pipeline = make_pipeline(project)

    result = pipeline.run()

    css_file = project.get_by_relative_path("style.css")
    php_file = project.get_by_relative_path("index.php")

    assert css_file is not None
    assert php_file is not None

    usages = result.selector_usage.usages_for(css_file)

    assert len(usages) == 1
    assert usages[0].selector == ".card"
    assert usages[0].state is UsageState.DEFINITELY_USED
    assert php_file in usages[0].matched_files



def test_pipeline_preserves_php_dependencies_and_template_usage(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.php").write_text(
        '<?php require "header.php"; ?>\n'
        '<div class="card">Product</div>',
        encoding="utf-8",
    )

    (tmp_path / "header.php").write_text(
        "<header>Site</header>",
        encoding="utf-8",
    )

    (tmp_path / "style.css").write_text(
        ".card { color: red; }",
        encoding="utf-8",
    )

    project = ProjectInventory(tmp_path).scan()
    pipeline = make_pipeline(project)

    result = pipeline.run()

    css_file = project.get_by_relative_path("style.css")
    php_file = project.get_by_relative_path("index.php")
    header_file = project.get_by_relative_path("header.php")

    assert css_file is not None
    assert php_file is not None
    assert header_file is not None

    usages = result.selector_usage.usages_for(css_file)

    assert len(usages) == 1
    assert usages[0].selector == ".card"
    assert usages[0].state is UsageState.DEFINITELY_USED
    assert php_file in usages[0].matched_files

    assert any(
        reference.source is php_file
        and reference.target is header_file
        and reference.resolved
        for reference in result.references
    )


def test_pipeline_does_not_treat_php_string_as_template_markup(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.php").write_text(
        '<?php $template = \'<div class="card">Product</div>\'; ?>',
        encoding="utf-8",
    )

    (tmp_path / "style.css").write_text(
        ".card { color: red; }",
        encoding="utf-8",
    )

    project = ProjectInventory(tmp_path).scan()
    pipeline = make_pipeline(project)

    result = pipeline.run()

    css_file = project.get_by_relative_path("style.css")

    assert css_file is not None

    usages = result.selector_usage.usages_for(css_file)

    assert len(usages) == 1
    assert usages[0].selector == ".card"
    assert usages[0].state is UsageState.STATICALLY_UNUSED


def test_pipeline_returns_unknown_when_html_source_cannot_be_loaded(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.html").write_text(
        '<div class="card">Product</div>',
        encoding="utf-8",
    )

    (tmp_path / "style.css").write_text(
        ".card { color: red; }",
        encoding="utf-8",
    )

    project = ProjectInventory(tmp_path).scan()
    html_file = project.get_by_relative_path("index.html")
    css_file = project.get_by_relative_path("style.css")

    assert html_file is not None
    assert css_file is not None

    html_file.path.unlink()

    pipeline = make_pipeline(project)
    result = pipeline.run()

    usages = result.selector_usage.usages_for(css_file)

    assert len(usages) == 1
    assert usages[0].selector == ".card"
    assert usages[0].state is UsageState.UNKNOWN
