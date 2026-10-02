import json
from pathlib import Path

from iksha.config.defaults import DEFAULT_IGNORE
from iksha.config.loader import CONFIG_FILENAME, load_config
from iksha.config.model import CaseSensitivity
from iksha.domain.states import Severity


def write_config(root: Path, payload: dict) -> None:
    (root / CONFIG_FILENAME).write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_defaults_match_prd_when_no_config_file(tmp_path: Path):
    loaded = load_config(tmp_path)

    assert loaded.config_path is None
    assert loaded.diagnostics == []
    assert loaded.config.extensions["php"] == (".php",)
    assert loaded.config.extensions["html"] == (".htm", ".html")
    assert loaded.config.extensions["css"] == (".css",)
    assert loaded.config.extensions["js"] == (".cjs", ".js", ".mjs")
    assert loaded.config.ignore == tuple(sorted(DEFAULT_IGNORE))
    assert loaded.config.entry_points == ()
    assert loaded.config.follow_symlinks is False
    assert loaded.config.case_sensitivity is CaseSensitivity.AUTO
    assert loaded.config.effective_case_sensitivity in {
        CaseSensitivity.SENSITIVE,
        CaseSensitivity.INSENSITIVE,
    }
    assert loaded.config.max_file_size_mb == 20.0
    assert (
        loaded.config.severity_threshold_for_exit_code
        is Severity.HIGH
    )


def test_project_config_file_overrides_defaults(tmp_path: Path):
    write_config(
        tmp_path,
        {
            "ignore": ["vendor", "custom_ignore"],
            "entryPoints": ["index.php", "admin/index.php"],
            "followSymlinks": True,
            "maxFileSizeMB": 5,
            "severityThresholdForExitCode": "medium",
        },
    )

    loaded = load_config(tmp_path)

    assert loaded.config_path == tmp_path / CONFIG_FILENAME
    assert loaded.config.ignore == (
        "custom_ignore",
        "vendor",
    )
    assert loaded.config.entry_points == (
        "index.php",
        "admin/index.php",
    )
    assert loaded.config.follow_symlinks is True
    assert loaded.config.max_file_size_mb == 5.0
    assert (
        loaded.config.severity_threshold_for_exit_code
        is Severity.MEDIUM
    )
    assert loaded.config.extensions["css"] == (".css",)


def test_cli_overrides_win_over_config_file(tmp_path: Path):
    write_config(
        tmp_path,
        {
            "ignore": ["vendor"],
            "maxFileSizeMB": 8,
            "entryPoints": ["index.php"],
        },
    )

    loaded = load_config(
        tmp_path,
        cli_overrides={
            "ignore": ["cli_only"],
            "maxFileSizeMB": 3,
        },
    )

    assert loaded.config.ignore == ("cli_only",)
    assert loaded.config.max_file_size_mb == 3.0
    assert loaded.config.entry_points == ("index.php",)


def test_extensions_merge_per_language(tmp_path: Path):
    write_config(
        tmp_path,
        {
            "extensions": {
                "php": [".php", ".phtml", "PHP"],
            }
        },
    )

    loaded = load_config(tmp_path)

    assert loaded.config.extensions["php"] == (".php", ".phtml")
    assert loaded.config.extensions["css"] == (".css",)
    assert loaded.config.extension_types()[".phtml"] == "php"
    assert loaded.config.extension_types()[".js"] == "javascript"


def test_unknown_config_keys_are_warnings_not_crashes(tmp_path: Path):
    write_config(
        tmp_path,
        {
            "ignore": ["vendor"],
            "experimental": True,
            "alsoUnknown": 1,
        },
    )

    loaded = load_config(tmp_path)

    messages = [
        diagnostic.message
        for diagnostic in loaded.diagnostics
    ]

    assert loaded.config.ignore == ("vendor",)
    assert any(
        "experimental" in message
        for message in messages
    )
    assert any(
        "alsoUnknown" in message
        for message in messages
    )
    assert all(
        diagnostic.severity == "warning"
        for diagnostic in loaded.diagnostics
    )


def test_invalid_json_keeps_defaults(tmp_path: Path):
    (tmp_path / CONFIG_FILENAME).write_text(
        "{ not json",
        encoding="utf-8",
    )

    loaded = load_config(tmp_path)

    assert loaded.config.ignore == tuple(sorted(DEFAULT_IGNORE))
    assert loaded.config.max_file_size_mb == 20.0
    assert len(loaded.diagnostics) == 1
    assert loaded.diagnostics[0].severity == "warning"
    assert "Invalid JSON" in loaded.diagnostics[0].message


def test_invalid_values_keep_previous_layer(tmp_path: Path):
    write_config(
        tmp_path,
        {
            "followSymlinks": "yes",
            "maxFileSizeMB": -1,
            "caseSensitivity": "sometimes",
            "severityThresholdForExitCode": "URGENT",
            "ignore": "vendor",
        },
    )

    loaded = load_config(tmp_path)

    assert loaded.config.follow_symlinks is False
    assert loaded.config.max_file_size_mb == 20.0
    assert loaded.config.case_sensitivity is CaseSensitivity.AUTO
    assert (
        loaded.config.severity_threshold_for_exit_code
        is Severity.HIGH
    )
    assert loaded.config.ignore == tuple(sorted(DEFAULT_IGNORE))
    assert loaded.diagnostics


def test_entry_points_preserve_order_and_normalize(tmp_path: Path):
    write_config(
        tmp_path,
        {
            "entryPoints": [
                r"admin\index.php",
                "./index.php",
                "index.php",
            ]
        },
    )

    loaded = load_config(tmp_path)

    assert loaded.config.entry_points == (
        "admin/index.php",
        "index.php",
    )


def test_serialized_config_is_deterministic(tmp_path: Path):
    first = load_config(tmp_path).config.to_dict()
    second = load_config(tmp_path).config.to_dict()

    assert first == second
    assert list(first.keys()) == [
        "extensions",
        "ignore",
        "entryPoints",
        "followSymlinks",
        "caseSensitivity",
        "effectiveCaseSensitivity",
        "maxFileSizeMB",
        "severityThresholdForExitCode",
    ]
    assert first["severityThresholdForExitCode"] == "HIGH"
    assert first["effectiveCaseSensitivity"] != "auto"


def test_explicit_case_sensitivity_is_not_probed_away(tmp_path: Path):
    write_config(
        tmp_path,
        {"caseSensitivity": "sensitive"},
    )

    loaded = load_config(tmp_path)

    assert loaded.config.case_sensitivity is CaseSensitivity.SENSITIVE
    assert (
        loaded.config.effective_case_sensitivity
        is CaseSensitivity.SENSITIVE
    )
