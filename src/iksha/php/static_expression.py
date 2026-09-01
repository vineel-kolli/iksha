"""
Static PHP expression analysis.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StaticExpressionResult:
    """
    Result of classifying a PHP dependency expression.
    """

    resolved: bool
    value: str | None = None
    reason: str | None = None


class PHPStaticExpressionResolver:
    """
    Classify PHP dependency expressions.

    This component answers one question:

        Can this expression be proven to represent a static value?

    It does not perform filesystem resolution.

    Supported expressions:

        'header.php'
        "header.php"

        __DIR__ . '/header.php'
        __DIR__ . "/header.php"

        __FILE__ . '/../config.php'

        dirname(__FILE__) . '/config.php'

    Dynamic expressions:

        $template
        $base . '/header.php'
        $config['file']

    Unsupported static expressions:

        BASE_PATH . '/header.php'
        SOME_CONSTANT
        arbitrary unsupported syntax
    """

    def resolve(
        self,
        expression: str,
    ) -> StaticExpressionResult:
        """Analyze one PHP expression."""

        if not expression or not expression.strip():
            return StaticExpressionResult(
                resolved=False,
                reason="empty_expression",
            )

        value = expression.strip()

        if self._contains_comment(value):
            return StaticExpressionResult(
                resolved=False,
                reason="unsupported_expression",
            )

        if self._contains_variable(value):
            return StaticExpressionResult(
                resolved=False,
                reason="dynamic_expression",
            )

        if self._is_quoted_string(value):
            decoded = self._decode_string(value)

            if decoded is None:
                return StaticExpressionResult(
                    resolved=False,
                    reason="unsupported_expression",
                )

            return StaticExpressionResult(
                resolved=True,
                value=decoded,
            )

        if self._is_supported_static_expression(value):
            return StaticExpressionResult(
                resolved=True,
                value=value,
            )

        if self._contains_unsupported_constant(value):
            return StaticExpressionResult(
                resolved=False,
                reason="unsupported_expression",
            )

        if self._looks_like_dynamic_expression(value):
            return StaticExpressionResult(
                resolved=False,
                reason="dynamic_expression",
            )

        return StaticExpressionResult(
            resolved=False,
            reason="unsupported_expression",
        )

    @staticmethod
    def _contains_variable(
        value: str,
    ) -> bool:
        """Return whether the expression contains a PHP variable."""

        return "$" in value

    @staticmethod
    def _contains_comment(
        value: str,
    ) -> bool:
        """Return whether obvious PHP comments are present."""

        return (
            "//" in value
            or "/*" in value
            or "*/" in value
        )

    @staticmethod
    def _is_quoted_string(
        value: str,
    ) -> bool:
        """Return whether value is one complete quoted string."""

        if len(value) < 2:
            return False

        quote = value[0]

        if quote not in {"'", '"'}:
            return False

        return value[-1] == quote

    @staticmethod
    def _decode_string(
        value: str,
    ) -> str | None:
        """
        Decode a simple PHP string literal.

        This intentionally handles only the escape sequences needed
        for static dependency paths.
        """

        if len(value) < 2:
            return None

        quote = value[0]

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
                # Preserve unknown escapes conservatively.
                result.append(escaped)

            index += 2

        return "".join(result)

    @staticmethod
    def _is_supported_static_expression(
        value: str,
    ) -> bool:
        """
        Return whether the expression is composed of known static
        PHP constructs.
        """

        prefixes = (
            "__DIR__ . ",
            "__FILE__ . ",
            "dirname(__FILE__) . ",
        )

        for prefix in prefixes:
            if not value.startswith(prefix):
                continue

            suffix = value[len(prefix):].strip()

            if (
                len(suffix) >= 2
                and suffix[0] in {"'", '"'}
                and suffix[-1] == suffix[0]
            ):
                return True

        return False

    @staticmethod
    def _contains_unsupported_constant(
        value: str,
    ) -> bool:
        """
        Detect arbitrary constant-based expressions.

        Known static constants are handled separately.
        """

        if " . " not in value:
            return False

        left_side = value.split(
            " . ",
            1,
        )[0].strip()

        if not left_side:
            return False

        if left_side in {
            "__DIR__",
            "__FILE__",
            "dirname(__FILE__)",
        }:
            return False

        if (
            left_side.isidentifier()
            or (
                left_side.isupper()
                and left_side.replace(
                    "_",
                    "",
                ).isalnum()
            )
        ):
            return True

        return False

    @staticmethod
    def _looks_like_dynamic_expression(
        value: str,
    ) -> bool:
        """Detect expressions requiring runtime evaluation."""

        if "(" in value or ")" in value:
            return True

        if "[" in value or "]" in value:
            return True

        return False
