"""
Default dependency resolver registration for IKSHA.
"""

from iksha.dependency.css_resolver import CSSDependencyResolver
from iksha.dependency.php_resolver import PHPDependencyResolver
from iksha.dependency.registry import ResolverRegistry
from iksha.domain.project import Project


def register_default_resolvers(
    project: Project,
    registry: ResolverRegistry | None = None,
) -> ResolverRegistry:
    """Register the built-in PHP and CSS dependency resolvers."""

    if registry is None:
        registry = ResolverRegistry([])

    registry.add(
        PHPDependencyResolver(
            project.root,
        )
    )

    registry.add(
        CSSDependencyResolver(
            project,
        )
    )

    return registry