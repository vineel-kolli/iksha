"""
Filesystem case-sensitivity detection.

The probe never writes into the scanned project. It first tries to
stat a case-toggled name of an existing path, then falls back to a
temporary directory outside the project.
"""

from pathlib import Path
import tempfile

from .model import CaseSensitivity


def detect_filesystem_case_sensitivity(
    path: Path | None = None,
) -> CaseSensitivity:
    """
    Detect whether the filesystem treats names as case-sensitive.

    When detection fails, return SENSITIVE so files that differ only
    in case are not silently merged.
    """

    if path is not None:
        detected = _probe_existing(path)

        if detected is not None:
            return detected

    return _probe_temporary_directory()


def resolve_case_sensitivity(
    requested: CaseSensitivity,
    path: Path | None = None,
) -> CaseSensitivity:
    """Resolve AUTO against the filesystem; otherwise keep the request."""

    if requested is CaseSensitivity.AUTO:
        return detect_filesystem_case_sensitivity(path)

    return requested


def _probe_existing(path: Path) -> CaseSensitivity | None:
    """Probe an existing path by toggling alphabetic case in its name."""

    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return None

    try:
        if not resolved.exists():
            return None
    except OSError:
        return None

    name = resolved.name

    if not _can_toggle_case(name):
        return None

    alternate = resolved.with_name(name.swapcase())

    try:
        if not alternate.exists():
            return CaseSensitivity.SENSITIVE

        if alternate.resolve() == resolved:
            return CaseSensitivity.INSENSITIVE

        return CaseSensitivity.SENSITIVE
    except OSError:
        return None


def _probe_temporary_directory() -> CaseSensitivity:
    """Probe case behavior using a temporary directory, not the project."""

    try:
        with tempfile.TemporaryDirectory(
            prefix="iksha-case-probe-"
        ) as directory:
            path = Path(directory)
            return (
                _probe_existing(path)
                or CaseSensitivity.SENSITIVE
            )
    except OSError:
        return CaseSensitivity.SENSITIVE


def _can_toggle_case(name: str) -> bool:
    """Return whether swapping case produces a different name."""

    if not any(character.isalpha() for character in name):
        return False

    return name.swapcase() != name
