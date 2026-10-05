"""
HTML parser for IKSHA.

Extracts stylesheet links, script sources, class names, IDs, and a
structured HTML document for downstream semantic analysis.

Dynamic attribute values are preserved as low-confidence evidence.
"""

from html.parser import HTMLParser

from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.domain.source_location import SourceLocation
from iksha.parsing.html_document import HtmlDocument, HtmlElement
from iksha.parsing.result import Diagnostic, Observation, ParseResult
from iksha.parsing.support import failed_source_result, looks_dynamic
from iksha.source.document import SourceDocument


class HtmlParser:
    """Extract HTML references, usage evidence, and document structure."""

    def parse_document(
        self,
        file: File,
        document: SourceDocument,
    ) -> HtmlDocument:
        """Parse HTML into a structured document."""

        failed = failed_source_result(file, document)

        if failed is not None:
            return HtmlDocument()

        html_document = HtmlDocument()

        extractor = _HtmlExtractor(
            file=file,
            document=document,
            result=ParseResult(),
            html_document=html_document,
        )

        try:
            extractor.feed(document.text)
            extractor.close()
        except Exception:
            # Structural parsing is best-effort. The existing parse()
            # method remains responsible for diagnostics.
            return html_document

        return html_document

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
    """html.parser callback adapter that emits observations."""

    def __init__(
        self,
        file: File,
        document: SourceDocument,
        result: ParseResult,
        html_document: HtmlDocument | None = None,
    ) -> None:
        super().__init__(convert_charrefs=True)

        self._file = file
        self._document = document
        self._result = result
        self._html_document = (
            html_document
            if html_document is not None
            else HtmlDocument()
        )
        self._element_stack: list[HtmlElement] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """Extract observations and add the element to the HTML tree."""

        location = self._location()

        attributes = {
            name.lower(): (value or "")
            for name, value in attrs
        }

        tag = tag.lower()

        element = HtmlElement(
            tag=tag,
            attributes=attributes,
            location=location,
        )

        if self._element_stack:
            self._element_stack[-1].add_child(element)
        else:
            self._html_document.add_element(element)

        if not self._is_void_element(tag):
            self._element_stack.append(element)

        if tag == "link":
            self._handle_link(
                attributes,
                location,
            )

        if tag == "script":
            self._handle_script(
                attributes,
                location,
            )

        self._handle_class(
            attributes,
            location,
        )
        self._handle_id(
            attributes,
            location,
        )

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """Handle explicitly self-closing elements."""

        self.handle_starttag(
            tag,
            attrs,
        )

        if self._element_stack:
            current = self._element_stack[-1]

            if current.tag == tag.lower():
                self._element_stack.pop()

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        """Close the nearest matching open element."""

        tag = tag.lower()

        for index in range(
            len(self._element_stack) - 1,
            -1,
            -1,
        ):
            if self._element_stack[index].tag == tag:
                del self._element_stack[index:]
                return

    def _handle_link(
        self,
        attributes: dict[str, str],
        location: SourceLocation,
    ) -> None:
        rel = attributes.get(
            "rel",
            "",
        ).lower().split()

        href = attributes.get(
            "href",
            "",
        ).strip()

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
        src = attributes.get(
            "src",
            "",
        ).strip()

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
    def _confidence(
        value: str,
    ) -> Confidence:
        if looks_dynamic(value):
            return Confidence.UNKNOWN

        return Confidence.CERTAIN

    @staticmethod
    def _is_void_element(
        tag: str,
    ) -> bool:
        """Return whether an HTML element is void."""

        return tag in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }