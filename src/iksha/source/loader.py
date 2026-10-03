"""
Robust source-file loader for IKSHA.
"""

from pathlib import Path

from iksha.domain.file import File
from iksha.source.document import SourceDocument


class SourceLoader:
    """
    Loads source files without silently discarding invalid bytes.

    Large files are capped at max_file_size_mb when configured. The
    truncated prefix is still returned so analysis can continue.
    """

    def __init__(
        self,
        max_file_size_mb: float | None = None,
    ) -> None:
        if max_file_size_mb is not None and max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be greater than 0")

        self.max_file_size_mb = max_file_size_mb

        if max_file_size_mb is None:
            self.max_file_size_bytes = None
        else:
            self.max_file_size_bytes = max(
                1,
                int(max_file_size_mb * 1024 * 1024),
            )

    def load(
        self,
        source: str | Path | File,
        *,
        language: str | None = None,
        minified: bool | None = None,
    ) -> SourceDocument:
        """Load a source file or authoritative project File."""

        if isinstance(source, File):
            resolved_path = source.path
            language = language or source.file_type
            is_minified = (
                source.minified
                if minified is None
                else minified
            )
        else:
            resolved_path = Path(source).expanduser().resolve()
            is_minified = bool(minified)

        try:
            data, truncated = self._read_bytes(resolved_path)
        except OSError as exc:
            return SourceDocument(
                path=resolved_path,
                success=False,
                error=f"Unable to read file: {exc}",
                language=language,
                minified=is_minified,
            )

        byte_size = (
            self._stat_size(resolved_path)
            if truncated
            else len(data)
        )

        encoding = self._detect_encoding(data)

        if encoding is None:
            return SourceDocument(
                path=resolved_path,
                byte_size=byte_size,
                success=False,
                error="Unable to determine a supported text encoding",
                language=language,
                minified=is_minified,
                truncated=truncated,
            )

        try:
            text = self._decode(data, encoding)
        except UnicodeDecodeError as exc:
            return SourceDocument(
                path=resolved_path,
                byte_size=byte_size,
                success=False,
                error=f"Unable to decode file as {encoding}: {exc}",
                language=language,
                minified=is_minified,
                truncated=truncated,
            )

        return SourceDocument(
            path=resolved_path,
            text=text,
            encoding=encoding,
            byte_size=byte_size,
            success=True,
            language=language,
            minified=is_minified,
            truncated=truncated,
        )

    def _read_bytes(self, path: Path) -> tuple[bytes, bool]:
        """Read file bytes, optionally capped by configured size."""

        limit = self.max_file_size_bytes

        if limit is None:
            return path.read_bytes(), False

        with path.open("rb") as handle:
            data = handle.read(limit + 1)

        if len(data) > limit:
            return data[:limit], True

        return data, False

    @staticmethod
    def _stat_size(path: Path) -> int:
        """Return on-disk size when the loaded prefix was truncated."""

        try:
            return path.stat().st_size
        except OSError:
            return 0

    @staticmethod
    def _detect_encoding(data: bytes) -> str | None:
        """Detect supported encoding."""

        if data.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"

        if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
            return "utf-16"

        if SourceLoader._looks_like_utf8(data):
            return "utf-8"

        return None

    @staticmethod
    def _looks_like_utf8(data: bytes) -> bool:
        """Return whether data is UTF-8, ignoring a truncated tail."""

        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            return True

        for drop in range(1, 4):
            if len(data) <= drop:
                break

            try:
                data[:-drop].decode("utf-8")
            except UnicodeDecodeError:
                continue

            return True

        return False

    @staticmethod
    def _decode(data: bytes, encoding: str) -> str:
        """
        Decode bytes, trimming a truncated multibyte sequence if needed.
        """

        trimmed = data

        while trimmed:
            try:
                return trimmed.decode(encoding)
            except UnicodeDecodeError as exc:
                if exc.start < len(trimmed) - 4:
                    raise

                trimmed = trimmed[:-1]

        return ""
