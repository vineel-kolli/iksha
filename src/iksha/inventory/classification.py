"""
Inventory classification helpers for generated and minified files.
"""

from pathlib import Path

MINIFIED_LINE_THRESHOLD = 2000
MINIFIED_PEEK_BYTES = 1_048_576

_MINIFIED_SUFFIXES = (
    ".min.css",
    ".min.js",
    ".min.mjs",
    ".min.cjs",
)


def is_generated_source(relative_path: str) -> bool:
    """
    Return whether a project-relative path looks generated.

    Generated files stay in the inventory; they are not ignored.
    """

    posix = relative_path.replace("\\", "/").strip("/")
    lowered = posix.lower()
    name = Path(posix).name.lower()

    if ".generated." in name:
        return True

    if name.endswith(".generated"):
        return True

    return "generated" in lowered.split("/")


def is_minified_filename(name: str) -> bool:
    """Return whether a filename matches a common minified pattern."""

    lowered = name.lower()

    return any(
        lowered.endswith(suffix)
        for suffix in _MINIFIED_SUFFIXES
    )


def has_minified_line(
    path: Path,
    *,
    size: int,
    threshold: int = MINIFIED_LINE_THRESHOLD,
    max_bytes: int = MINIFIED_PEEK_BYTES,
) -> bool:
    """
    Peek at file bytes for a single over-long line.

    Unreadable files return False; callers record the read error.
    """

    if size <= 0:
        return False

    limit = min(size, max_bytes)

    try:
        with path.open("rb") as handle:
            data = handle.read(limit)
    except OSError:
        return False

    for line in data.splitlines():
        if len(line) > threshold:
            return True

    if (
        b"\n" not in data
        and b"\r" not in data
        and size > threshold
    ):
        return True

    return False
