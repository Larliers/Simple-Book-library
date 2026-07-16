from __future__ import annotations

from pathlib import Path

from charset_normalizer import from_bytes

# Cap for full-file comic sidecar / safety; preview uses smaller max_chars.
_DEFAULT_MAX_BYTES = 2 * 1024 * 1024
_BIG5_FAMILY = {"big5", "big5hkscs", "cp950"}


def read_text_file(path: Path, *, max_chars: int | None = None) -> str:
    """Read a text file with charset detection (UTF-8 / GBK / etc.).

    When ``max_chars`` is set, only enough bytes for roughly that many characters
    are decoded (plus a small margin). Detection runs on the read bytes.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    if not raw:
        return ""

    if max_chars is not None:
        # Multi-byte encodings need headroom beyond char count.
        byte_limit = max(256, int(max_chars) * 4 + 64)
        raw = raw[:byte_limit]
    elif len(raw) > _DEFAULT_MAX_BYTES:
        raw = raw[:_DEFAULT_MAX_BYTES]

    text = _decode_bytes(raw)
    if max_chars is not None and max_chars > 0:
        return text[: int(max_chars)]
    return text


def read_text_first_line(path: Path) -> str:
    text = read_text_file(path, max_chars=8000)
    if not text:
        return ""
    return (text.splitlines()[0] if text.splitlines() else text).strip()


def _decode_bytes(raw: bytes) -> str:
    # UTF-8 BOM
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="replace")

    # Prefer strict UTF-8 when the file is valid UTF-8 (common for modern novels).
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass

    # charset-normalizer for remaining cases; bias mainland Chinese away from Big5 misdetect.
    try:
        match = from_bytes(raw).best()
    except Exception:  # noqa: BLE001
        match = None
    if match is not None:
        encoding = str(getattr(match, "encoding", "") or "").lower().replace("-", "_")
        if encoding in _BIG5_FAMILY:
            return raw.decode("gb18030", errors="replace")
        try:
            decoded = str(match).lstrip("\ufeff")
            if decoded:
                return decoded
        except Exception:  # noqa: BLE001
            pass

    return raw.decode("gb18030", errors="replace")
