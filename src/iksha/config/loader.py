"""
Load and merge IKSHA configuration layers.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from .case_sensitivity import resolve_case_sensitivity
from .defaults import default_config_data
from .model import (
    KNOWN_CONFIG_KEYS,
    CaseSensitivity,
    Config,
)
from iksha.domain.states import Severity
from iksha.parsing.result import Diagnostic

CONFIG_FILENAME = "iksha.config.json"


@dataclass
class ConfigLoadResult:
    """Resolved configuration plus load-time diagnostics."""

    config: Config
    diagnostics: list[Diagnostic]
    config_path: Path | None = None


def load_config(
    project_root: str | Path,
    *,
    cli_overrides: dict[str, Any] | None = None,
) -> ConfigLoadResult:
    """
    Load configuration for a project.

    Precedence, highest first: CLI overrides, iksha.config.json,
    built-in defaults.
    """

    root = Path(project_root).expanduser().resolve()
    diagnostics: list[Diagnostic] = []
    data = default_config_data()
    config_path: Path | None = None

    file_path = root / CONFIG_FILENAME

    file_data = _read_config_file(
        file_path,
        diagnostics,
    )

    if file_data is not None:
        config_path = file_path
        _apply_overlay(data, file_data, diagnostics)

    if cli_overrides is not None:
        _apply_overlay(data, cli_overrides, diagnostics)

    config = _build_config(
        data,
        root,
    )

    diagnostics.sort(key=lambda item: item.message)

    return ConfigLoadResult(
        config=config,
        diagnostics=diagnostics,
        config_path=config_path,
    )


def _read_config_file(
    path: Path,
    diagnostics: list[Diagnostic],
) -> dict[str, Any] | None:
    """Read iksha.config.json if it exists."""

    try:
        if not path.is_file():
            return None
    except OSError as exc:
        diagnostics.append(
            Diagnostic(
                message=f"Unable to access {CONFIG_FILENAME}: {exc}",
                severity="warning",
            )
        )
        return None

    try:
        text = path.read_text(encoding="utf-8")
        parsed = json.loads(text)
    except OSError as exc:
        diagnostics.append(
            Diagnostic(
                message=f"Unable to read {CONFIG_FILENAME}: {exc}",
                severity="warning",
            )
        )
        return None
    except json.JSONDecodeError as exc:
        diagnostics.append(
            Diagnostic(
                message=(
                    f"Invalid JSON in {CONFIG_FILENAME}: {exc.msg}"
                ),
                severity="warning",
            )
        )
        return None

    if not isinstance(parsed, dict):
        diagnostics.append(
            Diagnostic(
                message=(
                    f"{CONFIG_FILENAME} must contain a JSON object"
                ),
                severity="warning",
            )
        )
        return None

    return parsed


def _apply_overlay(
    data: dict[str, Any],
    overlay: dict[str, Any],
    diagnostics: list[Diagnostic],
) -> None:
    """Apply one configuration layer onto the working values."""

    unknown = sorted(
        key
        for key in overlay
        if key not in KNOWN_CONFIG_KEYS
    )

    for key in unknown:
        diagnostics.append(
            Diagnostic(
                message=f"Unknown configuration key '{key}' was ignored",
                severity="warning",
            )
        )

    if "extensions" in overlay:
        merged = _merge_extensions(
            data["extensions"],
            overlay["extensions"],
            diagnostics,
        )

        if merged is not None:
            data["extensions"] = merged

    if "ignore" in overlay:
        ignore = _as_string_list(
            overlay["ignore"],
            "ignore",
            diagnostics,
        )

        if ignore is not None:
            data["ignore"] = ignore

    if "entryPoints" in overlay:
        entry_points = _as_string_list(
            overlay["entryPoints"],
            "entryPoints",
            diagnostics,
        )

        if entry_points is not None:
            data["entryPoints"] = entry_points

    if "followSymlinks" in overlay:
        value = overlay["followSymlinks"]

        if isinstance(value, bool):
            data["followSymlinks"] = value
        else:
            diagnostics.append(
                Diagnostic(
                    message=(
                        "followSymlinks must be a boolean; "
                        "keeping previous value"
                    ),
                    severity="warning",
                )
            )

    if "caseSensitivity" in overlay:
        value = overlay["caseSensitivity"]
        parsed = _parse_case_sensitivity(value)

        if parsed is None:
            diagnostics.append(
                Diagnostic(
                    message=(
                        "caseSensitivity must be 'auto', 'sensitive', "
                        "or 'insensitive'; keeping previous value"
                    ),
                    severity="warning",
                )
            )
        else:
            data["caseSensitivity"] = parsed.value

    if "maxFileSizeMB" in overlay:
        value = overlay["maxFileSizeMB"]

        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            diagnostics.append(
                Diagnostic(
                    message=(
                        "maxFileSizeMB must be a positive number; "
                        "keeping previous value"
                    ),
                    severity="warning",
                )
            )
        elif value <= 0:
            diagnostics.append(
                Diagnostic(
                    message=(
                        "maxFileSizeMB must be greater than 0; "
                        "keeping previous value"
                    ),
                    severity="warning",
                )
            )
        else:
            data["maxFileSizeMB"] = float(value)

    if "severityThresholdForExitCode" in overlay:
        parsed = _parse_severity(
            overlay["severityThresholdForExitCode"]
        )

        if parsed is None:
            diagnostics.append(
                Diagnostic(
                    message=(
                        "severityThresholdForExitCode must be one of "
                        "CRITICAL, HIGH, MEDIUM, LOW, INFO; "
                        "keeping previous value"
                    ),
                    severity="warning",
                )
            )
        else:
            data["severityThresholdForExitCode"] = parsed.name


def _merge_extensions(
    current: dict[str, list[str]],
    overlay: Any,
    diagnostics: list[Diagnostic],
) -> dict[str, list[str]] | None:
    """Merge language extension lists. Each listed language replaces."""

    if not isinstance(overlay, dict):
        diagnostics.append(
            Diagnostic(
                message=(
                    "extensions must be an object; "
                    "keeping previous value"
                ),
                severity="warning",
            )
        )
        return None

    merged = {
        language: list(extensions)
        for language, extensions in current.items()
    }

    for language, extensions in overlay.items():
        if not isinstance(language, str) or not language.strip():
            diagnostics.append(
                Diagnostic(
                    message=(
                        "extensions language keys must be non-empty "
                        "strings; skipping invalid key"
                    ),
                    severity="warning",
                )
            )
            continue

        parsed = _as_string_list(
            extensions,
            f"extensions.{language}",
            diagnostics,
        )

        if parsed is None:
            continue

        merged[language.strip().lower()] = parsed

    return merged


def _as_string_list(
    value: Any,
    key: str,
    diagnostics: list[Diagnostic],
) -> list[str] | None:
    """Validate a list of strings."""

    if not isinstance(value, list) or isinstance(value, str):
        diagnostics.append(
            Diagnostic(
                message=(
                    f"{key} must be an array of strings; "
                    "keeping previous value"
                ),
                severity="warning",
            )
        )
        return None

    items: list[str] = []

    for item in value:
        if not isinstance(item, str):
            diagnostics.append(
                Diagnostic(
                    message=(
                        f"{key} must be an array of strings; "
                        "keeping previous value"
                    ),
                    severity="warning",
                )
            )
            return None

        stripped = item.strip()

        if stripped:
            items.append(stripped)

    return items


def _parse_case_sensitivity(value: Any) -> CaseSensitivity | None:
    """Parse a caseSensitivity config value."""

    if not isinstance(value, str):
        return None

    try:
        return CaseSensitivity(value.strip().lower())
    except ValueError:
        return None


def _parse_severity(value: Any) -> Severity | None:
    """Parse a severity threshold config value."""

    if not isinstance(value, str):
        return None

    name = value.strip().upper()

    try:
        return Severity[name]
    except KeyError:
        return None


def _build_config(
    data: dict[str, Any],
    root: Path,
) -> Config:
    """Normalize merged data into a Config object."""

    requested = _parse_case_sensitivity(
        data["caseSensitivity"]
    ) or CaseSensitivity.AUTO

    effective = resolve_case_sensitivity(
        requested,
        root,
    )

    if effective is CaseSensitivity.AUTO:
        effective = CaseSensitivity.SENSITIVE

    severity = _parse_severity(
        data["severityThresholdForExitCode"]
    ) or Severity.HIGH

    return Config(
        extensions=_normalize_extensions(data["extensions"]),
        ignore=_unique_sorted(data["ignore"]),
        entry_points=_normalize_entry_points(data["entryPoints"]),
        follow_symlinks=bool(data["followSymlinks"]),
        case_sensitivity=requested,
        effective_case_sensitivity=effective,
        max_file_size_mb=float(data["maxFileSizeMB"]),
        severity_threshold_for_exit_code=severity,
    )


def _normalize_extensions(
    extensions: dict[str, list[str]],
) -> dict[str, tuple[str, ...]]:
    """Normalize language extensions to dotted lowercase tuples."""

    normalized: dict[str, tuple[str, ...]] = {}

    for language in sorted(extensions):
        items: list[str] = []
        seen: set[str] = set()

        for raw in extensions[language]:
            extension = raw.strip().lower()

            if not extension:
                continue

            if not extension.startswith("."):
                extension = f".{extension}"

            if extension in seen:
                continue

            seen.add(extension)
            items.append(extension)

        if items:
            normalized[language] = tuple(sorted(items))

    return normalized


def _unique_sorted(values: list[str]) -> tuple[str, ...]:
    """Return unique values in sorted order."""

    return tuple(sorted(set(values)))


def _normalize_entry_points(values: list[str]) -> tuple[str, ...]:
    """Normalize entry points while preserving configured order."""

    normalized: list[str] = []
    seen: set[str] = set()

    for raw in values:
        path = raw.replace("\\", "/").lstrip("./")

        if not path or path in seen:
            continue

        seen.add(path)
        normalized.append(path)

    return tuple(normalized)
