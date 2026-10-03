"""
Factories for constructing the IKSHA analysis engine.
"""

from iksha.analysis.pipeline import AnalysisPipeline
from iksha.config.model import Config
from iksha.dependency.defaults import register_default_resolvers
from iksha.domain.project import Project
from iksha.parsing.defaults import register_default_parsers
from iksha.parsing.registry import ParserRegistry
from iksha.source.loader import SourceLoader


def create_analysis_pipeline(
    project: Project,
    *,
    config: Config | None = None,
    parser_registry: ParserRegistry | None = None,
    source_loader: SourceLoader | None = None,
) -> AnalysisPipeline:
    """
    Construct an analysis pipeline with the built-in components.

    Custom parser registries and source loaders can be supplied when
    callers need to override the default application configuration.
    """

    if parser_registry is None:
        parser_registry = register_default_parsers()

    if source_loader is None:
        source_loader = SourceLoader()

    resolver_registry = register_default_resolvers(
        project,
    )

    return AnalysisPipeline(
        project=project,
        source_loader=source_loader,
        parser_registry=parser_registry,
        resolver_registry=resolver_registry,
        config=config,
    )