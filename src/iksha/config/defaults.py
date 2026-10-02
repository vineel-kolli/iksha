"""
Built-in configuration defaults.
"""

from .model import CaseSensitivity, Config
from iksha.domain.states import Severity


DEFAULT_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "php": (".php",),
    "html": (".html", ".htm"),
    "css": (".css",),
    "js": (".js", ".mjs", ".cjs"),
}

DEFAULT_IGNORE: tuple[str, ...] = (
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "logs",
    "output",
)

DEFAULT_MAX_FILE_SIZE_MB = 20.0


def default_config_data() -> dict:
    """Return mutable default values used while merging layers."""

    return {
        "extensions": {
            language: list(extensions)
            for language, extensions in DEFAULT_EXTENSIONS.items()
        },
        "ignore": list(DEFAULT_IGNORE),
        "entryPoints": [],
        "followSymlinks": False,
        "caseSensitivity": CaseSensitivity.AUTO.value,
        "maxFileSizeMB": DEFAULT_MAX_FILE_SIZE_MB,
        "severityThresholdForExitCode": Severity.HIGH.name,
    }


def built_in_config(
    effective_case_sensitivity: CaseSensitivity,
) -> Config:
    """Return the built-in default Config."""

    return Config(
        extensions=dict(DEFAULT_EXTENSIONS),
        ignore=DEFAULT_IGNORE,
        entry_points=(),
        follow_symlinks=False,
        case_sensitivity=CaseSensitivity.AUTO,
        effective_case_sensitivity=effective_case_sensitivity,
        max_file_size_mb=DEFAULT_MAX_FILE_SIZE_MB,
        severity_threshold_for_exit_code=Severity.HIGH,
    )
