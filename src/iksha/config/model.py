"""
Resolved IKSHA configuration.
"""

from dataclasses import dataclass
from enum import Enum

from iksha.domain.states import Severity


class CaseSensitivity(str, Enum):
    """Configured filesystem case-sensitivity behavior."""

    AUTO = "auto"
    SENSITIVE = "sensitive"
    INSENSITIVE = "insensitive"


LANGUAGE_FILE_TYPES: dict[str, str] = {
    "js": "javascript",
}

KNOWN_CONFIG_KEYS: frozenset[str] = frozenset(
    {
        "extensions",
        "ignore",
        "entryPoints",
        "followSymlinks",
        "caseSensitivity",
        "maxFileSizeMB",
        "severityThresholdForExitCode",
    }
)


@dataclass(frozen=True)
class Config:
    """
    Fully resolved configuration used for one analysis run.

    This object is part of the deterministic analysis identity.
    """

    extensions: dict[str, tuple[str, ...]]
    ignore: tuple[str, ...]
    entry_points: tuple[str, ...]
    follow_symlinks: bool
    case_sensitivity: CaseSensitivity
    effective_case_sensitivity: CaseSensitivity
    max_file_size_mb: float
    severity_threshold_for_exit_code: Severity

    def extension_types(self) -> dict[str, str]:
        """Return lowercase extension -> file type."""

        mapping: dict[str, str] = {}

        for language, extensions in self.extensions.items():
            file_type = LANGUAGE_FILE_TYPES.get(
                language,
                language,
            )

            for extension in extensions:
                mapping[extension] = file_type

        return mapping

    def to_dict(self) -> dict:
        """
        Serialize in the public JSON schema.

        Keys are emitted in a stable order so identical configs produce
        identical dictionaries.
        """

        return {
            "extensions": {
                language: list(extensions)
                for language, extensions in sorted(
                    self.extensions.items()
                )
            },
            "ignore": list(self.ignore),
            "entryPoints": list(self.entry_points),
            "followSymlinks": self.follow_symlinks,
            "caseSensitivity": self.case_sensitivity.value,
            "effectiveCaseSensitivity": (
                self.effective_case_sensitivity.value
            ),
            "maxFileSizeMB": self.max_file_size_mb,
            "severityThresholdForExitCode": (
                self.severity_threshold_for_exit_code.name
            ),
        }
