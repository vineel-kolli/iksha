"""
Developer inspection utility.

Runs the current IKSHA analysis engine against a local project
and prints its dependency graph.
"""

from pathlib import Path
import sys

from iksha.analysis.pipeline import AnalysisPipeline
from iksha.config.loader import load_config
from iksha.dependency.php_resolver import PHPDependencyResolver
from iksha.inventory.project_inventory import ProjectInventory
from iksha.parsing.defaults import register_default_parsers
from iksha.source.loader import SourceLoader


def build_pipeline(root: Path) -> AnalysisPipeline:
    """Build the current analysis pipeline."""

    loaded = load_config(root)

    project = ProjectInventory(
        root,
        config=loaded.config,
    ).scan()

    registry = register_default_parsers()

    resolver = PHPDependencyResolver(
        project.root,
    )

    resolver.index_files(
        list(project.files.values())
    )

    return AnalysisPipeline(
        project=project,
        source_loader=SourceLoader(
            max_file_size_mb=loaded.config.max_file_size_mb,
        ),
        parser_registry=registry,
        dependency_resolver=resolver,
        config=loaded.config,
        config_diagnostics=loaded.diagnostics,
    )


def main() -> int:
    """Run project inspection."""

    if len(sys.argv) != 2:
        print(
            "Usage: python scripts/inspect_project.py <project-path>"
        )
        return 1

    root = Path(sys.argv[1]).expanduser().resolve()

    if not root.is_dir():
        print(f"Project directory does not exist: {root}")
        return 1

    pipeline = build_pipeline(root)

    project = pipeline.project
    result = pipeline.run()

    print()
    print("=" * 70)
    print("IKSHA PROJECT INSPECTION")
    print("=" * 70)

    print(f"Root:              {project.root}")
    print(f"Files:             {project.total_files}")
    print(f"Dependencies:      {result.graph.edge_count}")
    print(f"Unresolved:        {len(result.unresolved)}")
    print(f"Diagnostics:       {len(result.diagnostics)}")

    if result.config is not None:
        print(
            "Case sensitivity:  "
            f"{result.config.case_sensitivity.value}"
            f" ({result.config.effective_case_sensitivity.value})"
        )
        print(
            "Follow symlinks:   "
            f"{result.config.follow_symlinks}"
        )

    print()
    print("-" * 70)
    print("DEPENDENCY GRAPH")
    print("-" * 70)

    edges = result.graph.edges()

    if not edges:
        print("No resolved dependencies found.")
    else:
        for edge in edges:
            source = edge.source.relative_path
            target = edge.target.relative_path

            location = edge.observation.location

            if location is not None:
                location_text = (
                    f"line {location.line}, "
                    f"column {location.column}"
                )
            else:
                location_text = "unknown location"

            print(
                f"{source}"
                f"  --[{edge.observation.kind.value}]-->  "
                f"{target}"
                f"  ({location_text})"
            )

    print()
    print("-" * 70)
    print("UNRESOLVED REFERENCES")
    print("-" * 70)

    if not result.unresolved:
        print("None.")
    else:
        for unresolved in result.unresolved:
            observation = unresolved.observation

            source = observation.source.relative_path

            location = observation.location

            if location is not None:
                location_text = (
                    f"{location.line}:{location.column}"
                )
            else:
                location_text = "unknown"

            print(
                f"{source}"
                f"  --[{observation.kind.value}]-->  "
                f"{observation.value}"
                f"  ({location_text})"
            )

    print()
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
