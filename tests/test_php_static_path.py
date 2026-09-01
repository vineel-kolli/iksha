from pathlib import Path

from iksha.php.static_path import (
    PHPStaticPathEvaluator,
)


def make_file(tmp_path: Path, relative_path: str) -> Path:
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


def test_quoted_path_is_resolved_relative_to_source_directory(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "pages/index.php",
    )

    evaluator = PHPStaticPathEvaluator()

    result = evaluator.evaluate(
        "'header.php'",
        source,
    )

    assert result.resolved is True
    assert result.path == (
        tmp_path / "pages" / "header.php"
    ).resolve()


def test_dir_expression_is_resolved_relative_to_source_directory(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    evaluator = PHPStaticPathEvaluator()

    result = evaluator.evaluate(
        "__DIR__ . '/includes/header.php'",
        source,
    )

    assert result.resolved is True
    assert result.path == (
        tmp_path / "includes" / "header.php"
    ).resolve()


def test_dir_expression_handles_parent_directory(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "admin/index.php",
    )

    evaluator = PHPStaticPathEvaluator()

    result = evaluator.evaluate(
        "__DIR__ . '/../config/db.php'",
        source,
    )

    assert result.resolved is True
    assert result.path == (
        tmp_path / "config" / "db.php"
    ).resolve()


def test_file_expression_uses_source_file_directory(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "admin/index.php",
    )

    evaluator = PHPStaticPathEvaluator()

    result = evaluator.evaluate(
        "__FILE__ . '/../config.php'",
        source,
    )

    assert result.resolved is True
    assert result.path == (
        tmp_path / "admin" / "config.php"
    ).resolve()


def test_dirname_file_expression_is_supported(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "admin/index.php",
    )

    evaluator = PHPStaticPathEvaluator()

    result = evaluator.evaluate(
        "dirname(__FILE__) . '/config.php'",
        source,
    )

    assert result.resolved is True
    assert result.path == (
        tmp_path / "admin" / "config.php"
    ).resolve()


def test_dynamic_expression_is_not_evaluated(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    evaluator = PHPStaticPathEvaluator()

    result = evaluator.evaluate(
        "$base . '/header.php'",
        source,
    )

    assert result.resolved is False
    assert result.path is None
    assert result.reason == "dynamic_expression"


def test_unsupported_constant_is_not_evaluated(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    evaluator = PHPStaticPathEvaluator()

    result = evaluator.evaluate(
        "BASE_PATH . '/header.php'",
        source,
    )

    assert result.resolved is False
    assert result.path is None
    assert result.reason == "unsupported_expression"


def test_empty_expression_is_rejected(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    evaluator = PHPStaticPathEvaluator()

    result = evaluator.evaluate(
        "",
        source,
    )

    assert result.resolved is False
    assert result.path is None
    assert result.reason == "empty_expression"


def test_path_normalization_removes_parent_segments(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "admin/pages/index.php",
    )

    evaluator = PHPStaticPathEvaluator()

    result = evaluator.evaluate(
        "__DIR__ . '/../../header.php'",
        source,
    )

    assert result.resolved is True
    assert result.path == (
        tmp_path / "header.php"
    ).resolve()


def test_path_can_be_missing_but_still_static(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "index.php",
    )

    evaluator = PHPStaticPathEvaluator()

    result = evaluator.evaluate(
        "__DIR__ . '/missing.php'",
        source,
    )

    assert result.resolved is True
    assert result.path == (
        tmp_path / "missing.php"
    ).resolve()

    assert not result.path.exists()

