"""
CSS parser for IKSHA.

Extracts @import references while preserving source locations.
This parser does not interpret selectors as HTML usage evidence.
"""

from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.parsing.result import Diagnostic, Observation, ParseResult
from iksha.parsing.support import failed_source_result, looks_dynamic
from iksha.source.document import SourceDocument

try:
    import tinycss2
except ImportError:  # pragma: no cover
    tinycss2 = None


class CssParser:
    """Extract CSS @import observations from a document."""

    def parse(
        self,
        file: File,
        document: SourceDocument,
    ) -> ParseResult:
        """Parse one CSS source document."""

        failed = failed_source_result(file, document)

        if failed is not None:
            return failed

        result = ParseResult()

        if tinycss2 is None:
            result.diagnostics.append(
                Diagnostic(
                    message="tinycss2 is required to parse CSS",
                    severity="error",
                    source=file,
                )
            )
            return result

        rules = tinycss2.parse_stylesheet(
            document.text,
            skip_comments=True,
            skip_whitespace=True,
        )

        for rule in rules:
            if getattr(rule, "type", None) == "error":
                location = document.location_at(
                    _rule_offset(document, rule)
                )
                result.diagnostics.append(
                    Diagnostic(
                        message=(
                            getattr(rule, "message", None)
                            or "CSS parse error"
                        ),
                        severity="warning",
                        source=file,
                        location=location,
                    )
                )
                continue

            if getattr(rule, "type", None) != "at-rule":
                continue

            if getattr(rule, "lower_at_keyword", "") != "import":
                continue

            value = _import_target(rule)

            if value is None:
                continue

            offset = _rule_offset(document, rule)
            confidence = (
                Confidence.UNKNOWN
                if looks_dynamic(value)
                else Confidence.CERTAIN
            )

            result.observations.append(
                Observation(
                    source=file,
                    kind=ReferenceKind.IMPORT,
                    value=value,
                    location=document.location_at(offset),
                    confidence=confidence,
                )
            )

        return result


def _rule_offset(document: SourceDocument, rule: object) -> int:
    """Convert a tinycss2 source position into a character offset."""

    line = getattr(rule, "source_line", 1) or 1
    column = getattr(rule, "source_column", 1) or 1
    starts = document.line_offsets

    if starts and 1 <= line <= len(starts):
        return starts[line - 1] + max(column - 1, 0)

    return 0


def _import_target(rule: object) -> str | None:
    """Return the imported URL or path from an @import prelude."""

    prelude = getattr(rule, "prelude", None)

    if not prelude:
        return None

    for token in prelude:
        token_type = getattr(token, "type", "")

        if token_type == "string":
            value = getattr(token, "value", "")
            if value:
                return value

        if token_type == "url":
            value = getattr(token, "value", "")
            if value:
                return value

        if token_type == "function":
            if getattr(token, "lower_name", "") != "url":
                continue

            for argument in getattr(token, "arguments", ()):
                argument_type = getattr(argument, "type", "")

                if argument_type in {"string", "url"}:
                    value = getattr(argument, "value", "")
                    if value:
                        return value

    return None
