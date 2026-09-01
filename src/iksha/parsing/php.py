"""
PHP parser for IKSHA.

Extracts static include/require references from PHP source while
avoiding references that occur inside strings or comments.

This parser extracts evidence only. It does not resolve the referenced
path against the project filesystem.
"""

from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.domain.source_location import SourceLocation
from iksha.parsing.result import Observation, ParseResult
from iksha.source.document import SourceDocument


class PHPParser:
    """Extract include and require references from PHP source."""

    _KEYWORDS = {
        "include": ReferenceKind.INCLUDE,
        "include_once": ReferenceKind.INCLUDE,
        "require": ReferenceKind.REQUIRE,
        "require_once": ReferenceKind.REQUIRE,
    }

    def parse(
        self,
        file: File,
        document: SourceDocument,
    ) -> ParseResult:
        """Parse one PHP source document."""

        result = ParseResult()

        if not document.success:
            result.diagnostics.append(
                __import__(
                    "iksha.parsing.result",
                    fromlist=["Diagnostic"],
                ).Diagnostic(
                    message=document.error or "Source document could not be loaded",
                    severity="error",
                    source=file,
                )
            )
            return result

        text = document.text

        i = 0
        length = len(text)

        while i < length:
            character = text[i]

            # -----------------------------------------
            # Skip quoted strings
            # -----------------------------------------

            if character in ("'", '"'):
                i = self._skip_string(text, i)
                continue

            # -----------------------------------------
            # Skip line comments
            # -----------------------------------------

            if text.startswith("//", i):
                i = self._skip_line_comment(text, i)
                continue

            if character == "#":
                i = self._skip_line_comment(text, i)
                continue

            # -----------------------------------------
            # Skip block comments
            # -----------------------------------------

            if text.startswith("/*", i):
                i = self._skip_block_comment(text, i)
                continue

            # -----------------------------------------
            # PHP keyword detection
            # -----------------------------------------

            if self._is_identifier_start(character):
                start = i

                while (
                    i < length
                    and self._is_identifier_part(text[i])
                ):
                    i += 1

                word = text[start:i].lower()

                if word in self._KEYWORDS:
                    observation = self._parse_reference(
                        text=text,
                        keyword_start=start,
                        keyword_end=i,
                        kind=self._KEYWORDS[word],
                        file=file,
                    )

                    if observation is not None:
                        result.observations.append(
                            observation
                        )

                continue

            i += 1

        return result

    def _parse_reference(
        self,
        text: str,
        keyword_start: int,
        keyword_end: int,
        kind: ReferenceKind,
        file: File,
    ) -> Observation | None:
        """Parse the expression immediately following a PHP keyword."""

        i = keyword_end
        length = len(text)

        # Skip whitespace.
        while i < length and text[i].isspace():
            i += 1

        if i >= length:
            return None

        # Optional opening parenthesis.
        if text[i] == "(":
            i += 1

            while i < length and text[i].isspace():
                i += 1

        if i >= length:
            return None

        location = self._location(
            text,
            keyword_start,
        )

        # -----------------------------------------
        # Static quoted path
        # -----------------------------------------

        if text[i] in ("'", '"'):
            quote = text[i]
            value_start = i + 1

            i = value_start

            escaped = False

            while i < length:
                character = text[i]

                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == quote:
                    break

                i += 1

            if i >= length:
                return Observation(
                    source=file,
                    kind=kind,
                    value=text[value_start:],
                    location=location,
                    confidence=Confidence.LOW,
                )

            value = text[value_start:i]

            return Observation(
                source=file,
                kind=kind,
                value=value,
                location=location,
                confidence=Confidence.CERTAIN,
            )

        # -----------------------------------------
        # Dynamic expression
        # -----------------------------------------

        expression_start = i

        while i < length:
            character = text[i]

            if character in (";", "\n", "\r", ")"):
                break

            i += 1

        expression = text[
            expression_start:i
        ].strip()

        if not expression:
            return None

        return Observation(
            source=file,
            kind=kind,
            value=expression,
            location=location,
            confidence=Confidence.LOW,
        )

    @staticmethod
    def _skip_string(text: str, start: int) -> int:
        """Skip a single- or double-quoted PHP string."""

        quote = text[start]
        i = start + 1
        length = len(text)
        escaped = False

        while i < length:
            character = text[i]

            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                return i + 1

            i += 1

        return length

    @staticmethod
    def _skip_line_comment(text: str, start: int) -> int:
        """Skip until the next newline."""

        newline = text.find("\n", start)

        if newline == -1:
            return len(text)

        return newline + 1

    @staticmethod
    def _skip_block_comment(text: str, start: int) -> int:
        """Skip a block comment."""

        end = text.find("*/", start + 2)

        if end == -1:
            return len(text)

        return end + 2

    @staticmethod
    def _is_identifier_start(character: str) -> bool:
        """Return whether a character can start a PHP identifier."""

        return character.isalpha() or character == "_"

    @staticmethod
    def _is_identifier_part(character: str) -> bool:
        """Return whether a character can continue an identifier."""

        return (
            character.isalnum()
            or character == "_"
        )

    @staticmethod
    def _location(
        text: str,
        offset: int,
    ) -> SourceLocation:
        """Convert a character offset into a source location."""

        line = text.count("\n", 0, offset) + 1

        last_newline = text.rfind(
            "\n",
            0,
            offset,
        )

        column = (
            offset + 1
            if last_newline == -1
            else offset - last_newline
        )

        return SourceLocation(
            line=line,
            column=column,
        )
