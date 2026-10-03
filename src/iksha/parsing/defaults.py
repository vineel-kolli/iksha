"""
Default parser registration for IKSHA.
"""

from iksha.parsing.css import CssParser
from iksha.parsing.html import HtmlParser
from iksha.parsing.javascript import JavascriptParser
from iksha.parsing.php import PHPParser
from iksha.parsing.registry import ParserRegistry


def register_default_parsers(
    registry: ParserRegistry | None = None,
) -> ParserRegistry:
    """Register the built-in PHP, HTML, CSS, and JavaScript parsers."""

    if registry is None:
        registry = ParserRegistry()

    registry.register("php", PHPParser())
    registry.register("html", HtmlParser())
    registry.register("css", CssParser())
    registry.register("javascript", JavascriptParser())

    return registry
