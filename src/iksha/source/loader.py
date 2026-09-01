"""
Robust source-file loader for IKSHA.
"""

from pathlib import Path

from iksha.source.document import SourceDocument


class SourceLoader:
    """
    Loads source files without silently discarding invalid bytes.
    """

    def load(self, path: str | Path) -> SourceDocument:
        """Load a source file."""

        resolved_path = Path(path).expanduser().resolve()

        try:
            data = resolved_path.read_bytes()
        except OSError as exc:
            return SourceDocument(
                path=resolved_path,
                success=False,
                error=f"Unable to read file: {exc}",
            )

        byte_size = len(data)

        encoding = self._detect_encoding(data)

        if encoding is None:
            return SourceDocument(
                path=resolved_path,
                byte_size=byte_size,
                success=False,
                error="Unable to determine a supported text encoding",
            )

        try:
            text = data.decode(encoding)
        except UnicodeDecodeError as exc:
            return SourceDocument(
                path=resolved_path,
                byte_size=byte_size,
                success=False,
                error=f"Unable to decode file as {encoding}: {exc}",
            )

        return SourceDocument(
            path=resolved_path,
            text=text,
            encoding=encoding,
            byte_size=byte_size,
            success=True,
        )

    @staticmethod
    def _detect_encoding(data: bytes) -> str | None:
        """Detect supported encoding."""

        if data.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"

        if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
            return "utf-16"

        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            return None

        return "utf-8"
