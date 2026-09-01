"""
Common parser protocol for IKSHA.
"""

from typing import Protocol, runtime_checkable

from iksha.domain.file import File
from iksha.parsing.result import ParseResult
from iksha.source.document import SourceDocument


@runtime_checkable
class Parser(Protocol):
    """
    Common interface implemented by every language parser.

    Parsers receive:
        File
        SourceDocument

    Parsers return:
        ParseResult
    """

    def parse(
        self,
        file: File,
        document: SourceDocument,
    ) -> ParseResult:
        """Parse one source document."""
        ...
