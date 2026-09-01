"""
Static PHP filesystem path evaluation.
"""

from dataclasses import dataclass
from pathlib import Path

from iksha.php.static_expression import (
    PHPStaticExpressionResolver,
)


@dataclass(frozen=True)
class StaticPathResult:
    """Result of evaluating a PHP expression into a filesystem path."""

    resolved: bool
    path: Path | None = None
    reason: str | None = None


class PHPStaticPathEvaluator:
    """
    Evaluate the statically supported PHP path expressions.

    This class evaluates expressions but does not check whether
    the resulting file exists.

    Supported forms:

        'header.php'
        "header.php"

        __DIR__ . '/includes/header.php'

        __FILE__ . '/../config.php'

        dirname(__FILE__) . '/config.php'
    """

    def __init__(self) -> None:
        self._expression_resolver = (
            PHPStaticExpressionResolver()
        )

    def evaluate(
        self,
        expression: str,
        source: str | Path,
    ) -> StaticPathResult:
        """Evaluate one PHP expression."""

        source_path = Path(source).expanduser().resolve()

        classification = self._expression_resolver.resolve(
            expression
        )

        if not classification.resolved:
            return StaticPathResult(
                resolved=False,
                reason=classification.reason,
            )

        value = classification.value

        if value is None:
            return StaticPathResult(
                resolved=False,
                reason="unsupported_expression",
            )

        try:
            path = self._evaluate_value(
                value,
                source_path,
            )
        except (OSError, RuntimeError, ValueError):
            return StaticPathResult(
                resolved=False,
                reason="invalid_path",
            )

        if path is None:
            return StaticPathResult(
                resolved=False,
                reason="unsupported_expression",
            )

        return StaticPathResult(
            resolved=True,
            path=path,
        )

    def _evaluate_value(
        self,
        value: str,
        source_path: Path,
    ) -> Path | None:
        """Evaluate a classified static expression."""

        # The expression resolver has already decoded a plain
        # quoted string into its actual string value.
        if not value.startswith(
            (
                "__DIR__ . ",
                "__FILE__ . ",
                "dirname(__FILE__) . ",
            )
        ):
            return (
                source_path.parent / value
            ).resolve()

        if value.startswith("__DIR__ . "):
            suffix = value[
                len("__DIR__ . "):
            ].strip()

            suffix = self._decode_suffix(suffix)

            if suffix is None:
                return None

            return self._join_php_path(
                source_path.parent,
                suffix,
            )

        if value.startswith("__FILE__ . "):
            suffix = value[
                len("__FILE__ . "):
            ].strip()

            suffix = self._decode_suffix(suffix)

            if suffix is None:
                return None

            return self._join_php_path(
                source_path,
                suffix,
            )

        if value.startswith(
            "dirname(__FILE__) . "
        ):
            suffix = value[
                len("dirname(__FILE__) . "):
            ].strip()

            suffix = self._decode_suffix(suffix)

            if suffix is None:
                return None

            return self._join_php_path(
                source_path.parent,
                suffix,
            )

        return None

    @staticmethod
    def _decode_suffix(
        value: str,
    ) -> str | None:
        """
        Decode the quoted suffix from a static expression.

        The expression resolver has intentionally retained the
        expression structure for __DIR__/__FILE__ expressions.
        """

        if len(value) < 2:
            return None

        quote = value[0]

        if quote not in {"'", '"'}:
            return None

        if value[-1] != quote:
            return None

        content = value[1:-1]

        result: list[str] = []

        index = 0

        while index < len(content):
            character = content[index]

            if character != "\\":
                result.append(character)
                index += 1
                continue

            if index + 1 >= len(content):
                return None

            escaped = content[index + 1]

            if escaped in {"\\", "'", '"'}:
                result.append(escaped)
            elif escaped == "n":
                result.append("\n")
            elif escaped == "r":
                result.append("\r")
            elif escaped == "t":
                result.append("\t")
            else:
                result.append(escaped)

            index += 2

        return "".join(result)

    @staticmethod
    def _join_php_path(
        base: Path,
        suffix: str,
    ) -> Path:
        """
        Join using PHP string-concatenation semantics.

        A suffix beginning with '/' is still part of the string
        concatenation and must not cause pathlib to discard the
        base path.
        """

        suffix = suffix.replace(
            "\\",
            "/",
        )

        suffix = suffix.lstrip("/")

        return (
            base / suffix
        ).resolve()
