"""
CSS parser for IKSHA.

Extracts @import references and CSS selector observations while preserving
source locations. Selector observations are raw authored selectors and are
not interpreted as usage evidence here.
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
    """Extract CSS references and selector observations from a document."""

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

            rule_type = getattr(rule, "type", None)

            if rule_type == "at-rule":
                self._extract_import(
                    file=file,
                    document=document,
                    rule=rule,
                    result=result,
                )
                continue

            if rule_type == "qualified-rule":
                self._extract_selector(
                    file=file,
                    document=document,
                    rule=rule,
                    result=result,
                )

        return result

    @staticmethod
    def _extract_import(
        file: File,
        document: SourceDocument,
        rule: object,
        result: ParseResult,
    ) -> None:
        """Extract a CSS @import observation."""

        if getattr(rule, "lower_at_keyword", "") != "import":
            return

        value = _import_target(rule)

        if value is None:
            return

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

    @staticmethod
    def _extract_selector(
        file: File,
        document: SourceDocument,
        rule: object,
        result: ParseResult,
    ) -> None:
        """Extract the raw selector prelude from a qualified CSS rule."""

        prelude = getattr(rule, "prelude", None)

        if not prelude:
            return

        selector = tinycss2.serialize(prelude).strip()

        if not selector:
            return

        offset = _rule_offset(document, rule)

        result.observations.append(
            Observation(
                source=file,
                kind=ReferenceKind.DOM_SELECTOR,
                value=selector,
                location=document.location_at(offset),
                confidence=Confidence.CERTAIN,
            )
        )


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