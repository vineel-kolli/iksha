from pathlib import Path

import pytest

from iksha.domain.file import File
from iksha.parsing.protocol import Parser
from iksha.parsing.registry import ParserRegistry
from iksha.parsing.result import ParseResult
from iksha.source.document import SourceDocument


class FakeParser:
    def parse(
        self,
        file: File,
        document: SourceDocument,
    ) -> ParseResult:
        return ParseResult()


class AnotherParser:
    def parse(
        self,
        file: File,
        document: SourceDocument,
    ) -> ParseResult:
        return ParseResult()


def test_register_and_get_parser():
    registry = ParserRegistry()
    parser = FakeParser()

    registry.register("php", parser)

    assert registry.get("php") is parser


def test_supports_registered_file_type():
    registry = ParserRegistry()

    registry.register("php", FakeParser())

    assert registry.supports("php") is True
    assert registry.supports("css") is False


def test_file_type_lookup_is_case_insensitive():
    registry = ParserRegistry()
    parser = FakeParser()

    registry.register("PHP", parser)

    assert registry.get("php") is parser
    assert registry.get("Php") is parser
    assert registry.supports("PHP") is True


def test_file_type_whitespace_is_normalized():
    registry = ParserRegistry()
    parser = FakeParser()

    registry.register(" php ", parser)

    assert registry.get("php") is parser


def test_get_unsupported_parser_returns_none():
    registry = ParserRegistry()

    assert registry.get("javascript") is None
    assert registry.get("unknown") is None


def test_duplicate_registration_replaces_parser():
    registry = ParserRegistry()

    first = FakeParser()
    second = AnotherParser()

    registry.register("php", first)
    registry.register("php", second)

    assert registry.get("php") is second


def test_registered_parser_must_follow_protocol():
    registry = ParserRegistry()

    class InvalidParser:
        pass

    with pytest.raises(TypeError):
        registry.register(
            "php",
            InvalidParser(),
        )


def test_empty_file_type_is_rejected():
    registry = ParserRegistry()

    with pytest.raises(ValueError):
        registry.register(
            "",
            FakeParser(),
        )


def test_whitespace_only_file_type_is_rejected():
    registry = ParserRegistry()

    with pytest.raises(ValueError):
        registry.register(
            "   ",
            FakeParser(),
        )


def test_invalid_parser_type_is_rejected():
    registry = ParserRegistry()

    with pytest.raises(TypeError):
        registry.register(
            "php",
            object(),
        )


def test_registered_types_are_deterministic():
    registry = ParserRegistry()

    registry.register("javascript", FakeParser())
    registry.register("css", FakeParser())
    registry.register("php", FakeParser())
    registry.register("html", FakeParser())

    assert registry.types() == [
        "css",
        "html",
        "javascript",
        "php",
    ]


def test_unregister_parser():
    registry = ParserRegistry()
    parser = FakeParser()

    registry.register("php", parser)

    removed = registry.unregister("php")

    assert removed is parser
    assert registry.get("php") is None
    assert registry.supports("php") is False


def test_unregister_missing_parser_returns_none():
    registry = ParserRegistry()

    assert registry.unregister("php") is None


def test_registry_does_not_parse_files():
    registry = ParserRegistry()
    parser = FakeParser()

    registry.register("php", parser)

    file = File(
        path=Path("index.php"),
        relative_path="index.php",
        file_type="php",
    )

    document = SourceDocument(
        path=file.path,
        text="<?php ?>",
        encoding="utf-8",
        byte_size=8,
        success=True,
    )

    assert registry.get("php") is parser
    assert registry.get("php") is not None

    # Registry only resolves parsers. It does not execute them.
    result = registry.get("php").parse(
        file,
        document,
    )

    assert isinstance(result, ParseResult)
