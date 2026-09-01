from pathlib import Path

import pytest

from iksha.php.static_expression import (
    PHPStaticExpressionResolver,
)


def resolver():
    return PHPStaticExpressionResolver()


def test_plain_single_quoted_string():
    result = resolver().resolve("'header.php'")

    assert result.resolved is True
    assert result.value == "header.php"


def test_plain_double_quoted_string():
    result = resolver().resolve('"header.php"')

    assert result.resolved is True
    assert result.value == "header.php"


def test_dir_constant_with_single_quoted_suffix():
    result = resolver().resolve(
        "__DIR__ . '/includes/header.php'"
    )

    assert result.resolved is True
    assert result.value == "__DIR__ . '/includes/header.php'"


def test_dir_constant_with_double_quoted_suffix():
    result = resolver().resolve(
        '__DIR__ . "/includes/header.php"'
    )

    assert result.resolved is True
    assert result.value == '__DIR__ . "/includes/header.php"'


def test_dir_constant_with_parent_directory():
    result = resolver().resolve(
        "__DIR__ . '/../config/db.php'"
    )

    assert result.resolved is True
    assert result.value == "__DIR__ . '/../config/db.php'"


def test_file_constant_with_static_suffix():
    result = resolver().resolve(
        "__FILE__ . '/../config.php'"
    )

    assert result.resolved is True
    assert result.value == "__FILE__ . '/../config.php'"


def test_dirname_file_with_static_suffix():
    result = resolver().resolve(
        "dirname(__FILE__) . '/config.php'"
    )

    assert result.resolved is True
    assert result.value == (
        "dirname(__FILE__) . '/config.php'"
    )


def test_variable_is_dynamic():
    result = resolver().resolve(
        "$template"
    )

    assert result.resolved is False
    assert result.reason == "dynamic_expression"


def test_variable_concatenation_is_dynamic():
    result = resolver().resolve(
        "$base . '/header.php'"
    )

    assert result.resolved is False
    assert result.reason == "dynamic_expression"


def test_function_result_is_dynamic_except_known_static_forms():
    result = resolver().resolve(
        "getPath()"
    )

    assert result.resolved is False
    assert result.reason == "dynamic_expression"


def test_array_access_is_dynamic():
    result = resolver().resolve(
        "$config['file']"
    )

    assert result.resolved is False
    assert result.reason == "dynamic_expression"


def test_empty_expression_is_invalid():
    result = resolver().resolve("")

    assert result.resolved is False
    assert result.reason == "empty_expression"


def test_whitespace_expression_is_invalid():
    result = resolver().resolve("   ")

    assert result.resolved is False
    assert result.reason == "empty_expression"


def test_unquoted_bare_identifier_is_not_static_path():
    result = resolver().resolve(
        "header.php"
    )

    assert result.resolved is False
    assert result.reason == "unsupported_expression"


def test_arbitrary_constant_is_not_assumed_static():
    result = resolver().resolve(
        "BASE_PATH . '/header.php'"
    )

    assert result.resolved is False
    assert result.reason == "unsupported_expression"


def test_multiple_dynamic_parts_are_rejected():
    result = resolver().resolve(
        "__DIR__ . $folder . '/header.php'"
    )

    assert result.resolved is False
    assert result.reason == "dynamic_expression"


def test_php_comments_are_not_treated_as_part_of_path():
    result = resolver().resolve(
        "__DIR__ . '/header.php' // comment"
    )

    assert result.resolved is False
    assert result.reason == "unsupported_expression"
