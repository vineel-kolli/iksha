"""
Canonical path identity and reference-string normalization.
"""

from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse


def file_identity_key(
    path: Path,
    *,
    case_sensitive: bool,
) -> str:
    """
    Return the canonical identity string for a filesystem path.

    Identity is the resolved absolute POSIX path. On a case-insensitive
    filesystem the key is casefolded so Main.css and main.css match,
    without lowercasing the stored File path used for display.
    """

    try:
        resolved = path.expanduser().resolve()
    except OSError:
        resolved = Path(path)

    identity = resolved.as_posix()

    if case_sensitive:
        return identity

    return identity.casefold()


def normalize_reference_path(raw: str) -> str | None:
    """
    Normalize a raw reference string to a project path candidate.

    Returns None when the reference is external (http, https, data, or
    protocol-relative) and must not be treated as a local file.
    """

    value = raw.strip()

    if not value:
        return None

    if _is_external_reference(value):
        return None

    if value.startswith("file:"):
        parsed = urlparse(value)
        value = unquote(parsed.path or "")

        if parsed.netloc and parsed.netloc != "localhost":
            value = f"//{parsed.netloc}{value}"

        if os_nt_file_url(value):
            value = value.lstrip("/")

    value = _strip_query_and_fragment(value)
    value = unquote(value)
    value = value.replace("\\", "/")

    if _is_external_reference(value):
        return None

    return _collapse_path(value)


def is_external_reference(raw: str) -> bool:
    """Return whether a raw reference points outside the local project."""

    value = raw.strip()

    if not value:
        return False

    return _is_external_reference(value)


def _is_external_reference(value: str) -> bool:
    lowered = value.strip().lower()

    if lowered.startswith("//"):
        return True

    if lowered.startswith("data:"):
        return True

    parsed = urlparse(value)

    if parsed.scheme in {"http", "https", "data"}:
        return True

    return False


def os_nt_file_url(path: str) -> bool:
    """Return whether a file URL path looks like /C:/..."""

    if len(path) >= 3 and path[0] == "/" and path[2] == ":":
        return True

    return False


def _strip_query_and_fragment(value: str) -> str:
    """Remove URL query strings and fragments from a reference."""

    for separator in ("?", "#"):
        index = value.find(separator)

        if index != -1:
            value = value[:index]

    return value


def _collapse_path(value: str) -> str:
    """
    Collapse . and .. segments without touching the filesystem.

    Leading slashes are removed so URL paths like /css/main.css map to
    a project-relative candidate. Absolute Windows paths are preserved.
    """

    if _is_windows_absolute(value):
        posix = PurePosixPath(value.replace("\\", "/"))
        collapsed = posix.as_posix()
        return collapsed

    while value.startswith("./"):
        value = value[2:]

    is_absolute = value.startswith("/")
    parts: list[str] = []

    for part in value.split("/"):
        if part in ("", "."):
            continue

        if part == "..":
            if parts:
                parts.pop()
            continue

        parts.append(part)

    collapsed = "/".join(parts)

    if is_absolute and _is_windows_absolute(collapsed):
        return collapsed

    return collapsed


def _is_windows_absolute(value: str) -> bool:
    """Return whether a path looks like a Windows absolute path."""

    return len(value) >= 2 and value[1] == ":" and value[0].isalpha()
