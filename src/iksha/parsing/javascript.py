"""
JavaScript parser for IKSHA.

Extracts static import paths and DOM class/ID/selector evidence.
Dynamic arguments are recorded, never discarded.
"""

from iksha.domain.file import File
from iksha.domain.reference import Confidence, ReferenceKind
from iksha.parsing.result import Observation, ParseResult
from iksha.parsing.support import failed_source_result
from iksha.source.document import SourceDocument

_SELECTOR_METHODS = {
    "queryselector",
    "queryselectorall",
    "matches",
    "closest",
}

_ID_METHODS = {
    "getelementbyid",
}

_CLASS_METHODS = {
    "getelementsbyclassname",
}

_CLASSLIST_METHODS = {
    "add",
    "remove",
    "toggle",
    "contains",
    "replace",
}


class JavascriptParser:
    """Extract JavaScript dependency and usage observations."""

    def parse(
        self,
        file: File,
        document: SourceDocument,
    ) -> ParseResult:
        """Parse one JavaScript source document."""

        failed = failed_source_result(file, document)

        if failed is not None:
            return failed

        result = ParseResult()
        text = document.text
        i = 0
        length = len(text)
        previous = ""

        while i < length:
            character = text[i]

            if character in ("'", '"', "`"):
                i = _skip_string(text, i)
                continue

            if text.startswith("//", i):
                i = _skip_line_comment(text, i)
                continue

            if text.startswith("/*", i):
                i = _skip_block_comment(text, i)
                continue

            if _is_identifier_start(character):
                start = i

                while i < length and _is_identifier_part(text[i]):
                    i += 1

                word = text[start:i]
                lowered = word.lower()

                if lowered == "import":
                    _parse_import(
                        document=document,
                        file=file,
                        text=text,
                        start=start,
                        index=i,
                        result=result,
                    )
                elif (
                    previous.lower() == "classlist"
                    and lowered in _CLASSLIST_METHODS
                ):
                    _parse_call_arguments(
                        document=document,
                        file=file,
                        text=text,
                        index=i,
                        location_offset=start,
                        kind=ReferenceKind.CLASS,
                        result=result,
                    )
                elif lowered == "setattribute":
                    _parse_set_attribute(
                        document=document,
                        file=file,
                        text=text,
                        index=i,
                        location_offset=start,
                        result=result,
                    )
                elif lowered in _SELECTOR_METHODS:
                    _parse_call_arguments(
                        document=document,
                        file=file,
                        text=text,
                        index=i,
                        location_offset=start,
                        kind=ReferenceKind.DOM_SELECTOR,
                        result=result,
                    )
                elif lowered in _ID_METHODS:
                    _parse_call_arguments(
                        document=document,
                        file=file,
                        text=text,
                        index=i,
                        location_offset=start,
                        kind=ReferenceKind.ID,
                        result=result,
                    )
                elif lowered in _CLASS_METHODS:
                    _parse_call_arguments(
                        document=document,
                        file=file,
                        text=text,
                        index=i,
                        location_offset=start,
                        kind=ReferenceKind.CLASS,
                        result=result,
                    )
                elif lowered == "classname":
                    _parse_assignment(
                        document=document,
                        file=file,
                        text=text,
                        index=i,
                        location_offset=start,
                        kind=ReferenceKind.CLASS,
                        result=result,
                    )

                previous = word
                continue

            i += 1

        return result


def _parse_import(
    document: SourceDocument,
    file: File,
    text: str,
    start: int,
    index: int,
    result: ParseResult,
) -> None:
    """Extract an import path from import or import() syntax."""

    i = index
    length = len(text)

    while i < length and text[i].isspace():
        i += 1

    if i < length and text[i] == "(":
        values, dynamic = _read_call_string_values(text, i)
        _emit_strings(
            document,
            file,
            start,
            values,
            dynamic,
            ReferenceKind.IMPORT,
            result,
        )
        return

    while i < length and text[i] not in (";", "\n"):
        if text[i] in ("'", '"', "`"):
            value, next_index, interpolated = _read_string(text, i)
            confidence = (
                Confidence.UNKNOWN
                if interpolated
                else Confidence.CERTAIN
            )
            result.observations.append(
                Observation(
                    source=file,
                    kind=ReferenceKind.IMPORT,
                    value=value,
                    location=document.location_at(start),
                    confidence=confidence,
                )
            )
            return

        i += 1


def _parse_call_arguments(
    document: SourceDocument,
    file: File,
    text: str,
    index: int,
    location_offset: int,
    kind: ReferenceKind,
    result: ParseResult,
) -> None:
    """Extract string arguments from a function call if present."""

    i = index
    length = len(text)

    while i < length and text[i].isspace():
        i += 1

    if i >= length or text[i] != "(":
        return

    values, dynamic = _read_call_string_values(text, i)
    _emit_strings(
        document,
        file,
        location_offset,
        values,
        dynamic,
        kind,
        result,
    )


def _parse_set_attribute(
    document: SourceDocument,
    file: File,
    text: str,
    index: int,
    location_offset: int,
    result: ParseResult,
) -> None:
    """Extract class or id values from setAttribute calls."""

    i = index
    length = len(text)

    while i < length and text[i].isspace():
        i += 1

    if i >= length or text[i] != "(":
        return

    values, dynamic = _read_call_string_values(text, i)

    if not values:
        if dynamic:
            result.observations.append(
                Observation(
                    source=file,
                    kind=ReferenceKind.UNKNOWN,
                    value="",
                    location=document.location_at(location_offset),
                    confidence=Confidence.UNKNOWN,
                )
            )
        return

    attribute = values[0].lower()
    kind = None

    if attribute == "class":
        kind = ReferenceKind.CLASS
    elif attribute == "id":
        kind = ReferenceKind.ID

    if kind is None:
        return

    remaining = values[1:]

    if not remaining:
        result.observations.append(
            Observation(
                source=file,
                kind=kind,
                value="",
                location=document.location_at(location_offset),
                confidence=Confidence.UNKNOWN,
            )
        )
        return

    _emit_strings(
        document,
        file,
        location_offset,
        remaining,
        dynamic,
        kind,
        result,
    )


def _parse_assignment(
    document: SourceDocument,
    file: File,
    text: str,
    index: int,
    location_offset: int,
    kind: ReferenceKind,
    result: ParseResult,
) -> None:
    """Extract a string assigned to a property such as className."""

    i = index
    length = len(text)

    while i < length and text[i].isspace():
        i += 1

    if i >= length or text[i] != "=":
        return

    i += 1

    while i < length and text[i].isspace():
        i += 1

    if i >= length:
        return

    if text[i] in ("'", '"', "`"):
        value, _, interpolated = _read_string(text, i)
        result.observations.append(
            Observation(
                source=file,
                kind=kind,
                value=value,
                location=document.location_at(location_offset),
                confidence=(
                    Confidence.UNKNOWN
                    if interpolated
                    else Confidence.CERTAIN
                ),
            )
        )
        return

    result.observations.append(
        Observation(
            source=file,
            kind=kind,
            value=text[i:i + 32].split(";")[0].strip(),
            location=document.location_at(location_offset),
            confidence=Confidence.UNKNOWN,
        )
    )


def _emit_strings(
    document: SourceDocument,
    file: File,
    offset: int,
    values: list[str],
    dynamic: bool,
    kind: ReferenceKind,
    result: ParseResult,
) -> None:
    """Emit observations for extracted string values."""

    if not values:
        if dynamic:
            result.observations.append(
                Observation(
                    source=file,
                    kind=kind,
                    value="",
                    location=document.location_at(offset),
                    confidence=Confidence.UNKNOWN,
                )
            )
        return

    if dynamic:
        confidence = Confidence.UNKNOWN
    elif len(values) > 1:
        confidence = Confidence.LOW
    else:
        confidence = Confidence.CERTAIN

    for value in values:
        result.observations.append(
            Observation(
                source=file,
                kind=kind,
                value=value,
                location=document.location_at(offset),
                confidence=confidence,
            )
        )


def _read_call_string_values(
    text: str,
    open_paren: int,
) -> tuple[list[str], bool]:
    """
    Read string literals from a call, including simple ternaries.

    Returns (values, saw_dynamic).
    """

    i = open_paren + 1
    length = len(text)
    values: list[str] = []
    interpolated = False
    saw_identifier = False
    depth = 1

    while i < length and depth > 0:
        character = text[i]

        if character in ("'", '"', "`"):
            value, i, string_interpolated = _read_string(text, i)
            values.append(value)
            if string_interpolated:
                interpolated = True
            continue

        if character == "(":
            depth += 1
            i += 1
            continue

        if character == ")":
            depth -= 1
            if depth == 0:
                break
            i += 1
            continue

        if _is_identifier_start(character):
            saw_identifier = True
            while i < length and _is_identifier_part(text[i]):
                i += 1
            continue

        i += 1

    dynamic = interpolated or (saw_identifier and not values)
    return values, dynamic


def _read_string(text: str, start: int) -> tuple[str, int, bool]:
    """Read a JS string or template literal. Returns value, next index, interpolated."""

    quote = text[start]
    i = start + 1
    length = len(text)
    escaped = False
    interpolated = False
    chars: list[str] = []

    while i < length:
        character = text[i]

        if quote == "`" and not escaped and text.startswith("${", i):
            interpolated = True
            i += 2
            depth = 1
            while i < length and depth:
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                i += 1
            continue

        if escaped:
            chars.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == quote:
            return "".join(chars), i + 1, interpolated
        else:
            chars.append(character)

        i += 1

    return "".join(chars), length, interpolated


def _skip_string(text: str, start: int) -> int:
    """Skip a quoted string or template literal."""

    _, end, _ = _read_string(text, start)
    return end


def _skip_line_comment(text: str, start: int) -> int:
    newline = text.find("\n", start)

    if newline == -1:
        return len(text)

    return newline + 1


def _skip_block_comment(text: str, start: int) -> int:
    end = text.find("*/", start + 2)

    if end == -1:
        return len(text)

    return end + 2


def _is_identifier_start(character: str) -> bool:
    return character.isalpha() or character in ("_", "$")


def _is_identifier_part(character: str) -> bool:
    return character.isalnum() or character in ("_", "$")
