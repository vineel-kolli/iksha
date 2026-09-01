"""
Parser registry for IKSHA.

The registry maps normalized file types to parser implementations.
It is responsible only for registration and lookup.
"""

from iksha.parsing.protocol import Parser


class ParserRegistry:
    """Registry of parsers keyed by normalized file type."""

    def __init__(self) -> None:
        self._parsers: dict[str, Parser] = {}

    @staticmethod
    def _normalize(file_type: str) -> str:
        """Normalize a parser file-type key."""

        if not isinstance(file_type, str):
            raise TypeError("file_type must be a string")

        normalized = file_type.strip().lower()

        if not normalized:
            raise ValueError("file_type cannot be empty")

        return normalized

    def register(
        self,
        file_type: str,
        parser: Parser,
    ) -> None:
        """
        Register a parser for a file type.

        Registering the same type again intentionally replaces the
        previous parser. This makes explicit parser configuration
        possible without maintaining duplicate registrations.
        """

        normalized_type = self._normalize(file_type)

        if not isinstance(parser, Parser):
            raise TypeError(
                "parser must implement the Parser protocol"
            )

        self._parsers[normalized_type] = parser

    def get(
        self,
        file_type: str,
    ) -> Parser | None:
        """Return the parser registered for a file type."""

        normalized_type = self._normalize(file_type)

        return self._parsers.get(normalized_type)

    def supports(
        self,
        file_type: str,
    ) -> bool:
        """Return whether a parser is registered."""

        normalized_type = self._normalize(file_type)

        return normalized_type in self._parsers

    def unregister(
        self,
        file_type: str,
    ) -> Parser | None:
        """Remove and return a registered parser, if present."""

        normalized_type = self._normalize(file_type)

        return self._parsers.pop(
            normalized_type,
            None,
        )

    def types(self) -> list[str]:
        """Return registered file types in deterministic order."""

        return sorted(self._parsers)
