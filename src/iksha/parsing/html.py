"""
HTML parser for IKSHA.

Extracts stylesheet links, script sources, class names, and IDs.
Dynamic attribute values are preserved as low-confidence evidence.
"""

from html.parser import HTMLParser

from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.domain.source_location import SourceLocation
from iksha.parsing.result import Diagnostic, Observation, ParseResult
from iksha.parsing.support import failed_source_result, looks_dynamic
from iksha.source.document import SourceDocument


class HtmlParser:
    """Extract HTML references and usage evidence from a document."""

    def parse(
        self,
        file: File,
        document: SourceDocument,
    ) -> ParseResult:
        """Parse one HTML source document."""

        failed = failed_source_result(file, document)

        if failed is not None:
            return failed

        result = ParseResult()
        extractor = _HtmlExtractor(
            file=file,
            document=document,
            result=result,
        )

        try:
            extractor.feed(document.text)
            extractor.close()
        except Exception as exc:
            result.diagnostics.append(
                Diagnostic(
                    message=f"HTML parse error: {exc}",
                    severity="warning",
                    source=file,
                )
            )

        return result


class _HtmlExtractor(HTMLParser):
    """html.parser callback adapter that emits Observations."""

    def __init__(
        self,
        file: File,
        document: SourceDocument,
        result: ParseResult,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self._file = file
        self._document = document
        self._result = result

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """Extract references from an opening tag."""

        location = self._location()
        attributes = {
            name.lower(): (value or "")
            for name, value in attrs
        }
        tag = tag.lower()

        if tag == "link":
            self._handle_link(attributes, location)

        if tag == "script":
            self._handle_script(attributes, location)

        self._handle_class(attributes, location)
        self._handle_id(attributes, location)

    def _handle_link(
        self,
        attributes: dict[str, str],
        location: SourceLocation,
    ) -> None:
        rel = attributes.get("rel", "").lower().split()
        href = attributes.get("href", "").strip()

        if "stylesheet" not in rel or not href:
            return

        self._result.observations.append(
            Observation(
                source=self._file,
                kind=ReferenceKind.STYLESHEET,
                value=href,
                location=location,
                confidence=self._confidence(href),
            )
        )

    def _handle_script(
        self,
        attributes: dict[str, str],
        location: SourceLocation,
    ) -> None:
        src = attributes.get("src", "").strip()

        if not src:
            return

        self._result.observations.append(
            Observation(
                source=self._file,
                kind=ReferenceKind.SCRIPT,
                value=src,
                location=location,
                confidence=self._confidence(src),
            )
        )

    def _handle_class(
        self,
        attributes: dict[str, str],
        location: SourceLocation,
    ) -> None:
        raw = attributes.get("class")

        if raw is None:
            return

        value = raw.strip()

        if not value:
            return

        if looks_dynamic(value):
            self._result.observations.append(
                Observation(
                    source=self._file,
                    kind=ReferenceKind.CLASS,
                    value=value,
                    location=location,
                    confidence=Confidence.UNKNOWN,
                )
            )
            return

        for name in value.split():
            self._result.observations.append(
                Observation(
                    source=self._file,
                    kind=ReferenceKind.CLASS,
                    value=name,
                    location=location,
                    confidence=Confidence.CERTAIN,
                )
            )

    def _handle_id(
        self,
        attributes: dict[str, str],
        location: SourceLocation,
    ) -> None:
        raw = attributes.get("id")

        if raw is None:
            return

        value = raw.strip()

        if not value:
            return

        confidence = (
            Confidence.UNKNOWN
            if looks_dynamic(value)
            else Confidence.CERTAIN
        )

        self._result.observations.append(
            Observation(
                source=self._file,
                kind=ReferenceKind.ID,
                value=value,
                location=location,
                confidence=confidence,
            )
        )

    def _location(self) -> SourceLocation:
        line, column_offset = self.getpos()
        starts = self._document.line_offsets

        if starts and 1 <= line <= len(starts):
            offset = starts[line - 1] + column_offset
            return self._document.location_at(offset)

        return SourceLocation(
            line=line,
            column=max(column_offset + 1, 1),
        )

    @staticmethod
    def _confidence(value: str) -> Confidence:
        if looks_dynamic(value):
            return Confidence.UNKNOWN

        return Confidence.CERTAIN
