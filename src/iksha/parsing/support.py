"""
Shared helpers for language parsers.
"""

from iksha.domain.file import File
from iksha.parsing.result import Diagnostic, ParseResult
from iksha.source.document import SourceDocument


def failed_source_result(
    file: File,
    document: SourceDocument,
) -> ParseResult | None:
    """Return a failed parse result when the source could not be loaded."""

    if document.success:
        return None

    result = ParseResult()
    result.diagnostics.append(
        Diagnostic(
            message=(
                document.error
                or "Source document could not be loaded"
            ),
            severity="error",
            source=file,
        )
    )
    return result


def looks_dynamic(value: str) -> bool:
    """Return whether an attribute or literal looks dynamically produced."""

    lowered = value.lower()

    if "<?" in value or "?>" in value:
        return True

    if "${" in value:
        return True

    if "`" in value:
        return True

    if "$" in value:
        return True

    return "<?=" in lowered
