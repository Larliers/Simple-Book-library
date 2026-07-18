from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from charset_normalizer import from_bytes

# Cap for full-file comic sidecar / safety; preview uses smaller max_chars.
_DEFAULT_MAX_BYTES = 2 * 1024 * 1024
_DETECT_SAMPLE_BYTES = 64 * 1024
# charset-normalizer coherence for CJK is often low; chaos is the sharper signal.
_MAX_TRUSTED_CHAOS = 0.25

TEXT_ENCODING_SIMPLIFIED = "simplified"
TEXT_ENCODING_TRADITIONAL = "traditional"
TEXT_ENCODING_AUTO = "auto"
TEXT_ENCODING_PREFERENCES = {
    TEXT_ENCODING_SIMPLIFIED,
    TEXT_ENCODING_TRADITIONAL,
    TEXT_ENCODING_AUTO,
}
TextEncodingPreference = Literal["simplified", "traditional", "auto"]

_BIG5_FAMILY = {"big5", "big5hkscs", "cp950"}
_GB_FAMILY = {"gb18030", "gbk", "gb2312", "cp936"}


@dataclass(slots=True)
class DecodeResult:
    text: str
    encoding: str
    confidence: float
    fallback_used: bool


def normalize_encoding_preference(value: str | None) -> TextEncodingPreference:
    text = str(value or "").strip().lower()
    if text in TEXT_ENCODING_PREFERENCES:
        return text  # type: ignore[return-value]
    return TEXT_ENCODING_SIMPLIFIED


def detect_and_decode(
    raw: bytes,
    *,
    preference: str = TEXT_ENCODING_SIMPLIFIED,
    detect_sample_bytes: int = _DETECT_SAMPLE_BYTES,
) -> DecodeResult:
    """Detect charset and decode bytes with optional简/繁 preference."""
    pref = normalize_encoding_preference(preference)
    if not raw:
        return DecodeResult("", "utf-8", 1.0, False)

    if raw.startswith(b"\xef\xbb\xbf"):
        return DecodeResult(raw.decode("utf-8-sig", errors="replace"), "utf-8-sig", 1.0, False)

    try:
        return DecodeResult(raw.decode("utf-8"), "utf-8", 1.0, False)
    except UnicodeDecodeError:
        pass

    sample = raw[: max(256, int(detect_sample_bytes or _DETECT_SAMPLE_BYTES))]
    chosen = _pick_encoding_from_normalizer(sample, pref)
    if chosen is not None:
        encoding, confidence = chosen
        text = raw.decode(encoding, errors="replace")
        if text.count("\ufffd") == 0:
            return DecodeResult(text.lstrip("\ufeff"), encoding, confidence, False)

    return _dual_candidate_decode(raw, pref)


def read_text_file(
    path: Path,
    *,
    max_chars: int | None = None,
    preference: str = TEXT_ENCODING_SIMPLIFIED,
) -> str:
    """Read a text file with charset detection (UTF-8 / GBK / Big5 / etc.)."""
    return read_text_file_detailed(path, max_chars=max_chars, preference=preference).text


def read_text_file_detailed(
    path: Path,
    *,
    max_chars: int | None = None,
    preference: str = TEXT_ENCODING_SIMPLIFIED,
) -> DecodeResult:
    try:
        full = path.read_bytes()
    except OSError:
        return DecodeResult("", "utf-8", 0.0, True)
    if not full:
        return DecodeResult("", "utf-8", 1.0, False)

    # Always keep enough head bytes for detection (64KB), even for short previews.
    if max_chars is not None:
        char_byte_limit = max(256, int(max_chars) * 4 + 64)
        byte_limit = max(_DETECT_SAMPLE_BYTES, char_byte_limit)
    else:
        byte_limit = _DEFAULT_MAX_BYTES
    raw = full[: min(len(full), byte_limit, _DEFAULT_MAX_BYTES)]

    result = detect_and_decode(raw, preference=preference)
    if max_chars is not None and max_chars > 0:
        return DecodeResult(
            result.text[: int(max_chars)],
            result.encoding,
            result.confidence,
            result.fallback_used,
        )
    return result


def read_text_first_line(path: Path, *, preference: str = TEXT_ENCODING_SIMPLIFIED) -> str:
    text = read_text_file(path, max_chars=8000, preference=preference)
    if not text:
        return ""
    return (text.splitlines()[0] if text.splitlines() else text).strip()


def _normalize_encoding_name(name: str) -> str:
    return str(name or "").lower().replace("-", "_").strip()


def _canonical_decode_encoding(name: str) -> str:
    enc = _normalize_encoding_name(name)
    if enc in _GB_FAMILY:
        return "gb18030"
    if enc in _BIG5_FAMILY:
        return "big5"
    if enc in {"utf_8", "utf8"}:
        return "utf-8"
    return enc.replace("_", "-") if enc else "gb18030"


def _pick_encoding_from_normalizer(
    sample: bytes,
    preference: TextEncodingPreference,
) -> tuple[str, float] | None:
    try:
        matches = list(from_bytes(sample))
    except Exception:  # noqa: BLE001
        return None
    if not matches:
        return None

    ranked: list[tuple[tuple[float, int, float], object]] = []
    for match in matches:
        enc_raw = _normalize_encoding_name(str(getattr(match, "encoding", "") or ""))
        if not enc_raw:
            continue
        chaos = float(getattr(match, "chaos", 1.0) or 1.0)
        coherence = float(getattr(match, "coherence", 0.0) or 0.0)
        preference_penalty = 0
        if preference == TEXT_ENCODING_SIMPLIFIED:
            if enc_raw in _BIG5_FAMILY:
                preference_penalty = 2
            elif enc_raw in _GB_FAMILY:
                preference_penalty = -1
        elif preference == TEXT_ENCODING_TRADITIONAL:
            if enc_raw in _BIG5_FAMILY:
                preference_penalty = -1
            elif enc_raw in _GB_FAMILY:
                preference_penalty = 2
        # auto: trust normalizer order via chaos/coherence only
        ranked.append(((chaos, preference_penalty, -coherence), match))

    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0])
    best_key, best_match = ranked[0]
    chaos = best_key[0]
    if chaos > _MAX_TRUSTED_CHAOS:
        return None

    enc_raw = _normalize_encoding_name(str(getattr(best_match, "encoding", "") or ""))
    if preference == TEXT_ENCODING_SIMPLIFIED and enc_raw in _BIG5_FAMILY:
        # Mainland default: never keep Big5 mis-detect.
        return "gb18030", max(0.0, 1.0 - chaos)
    encoding = _canonical_decode_encoding(enc_raw)
    confidence = max(0.0, min(1.0, float(getattr(best_match, "coherence", 0.0) or 0.0)))
    if confidence <= 0.0:
        confidence = max(0.0, 1.0 - chaos)
    return encoding, confidence


def _dual_candidate_decode(raw: bytes, preference: TextEncodingPreference) -> DecodeResult:
    if preference == TEXT_ENCODING_TRADITIONAL:
        candidates = ("big5", "gb18030", "utf-8")
    elif preference == TEXT_ENCODING_AUTO:
        candidates = ("gb18030", "big5", "utf-8")
    else:
        # simplified: never consider Big5 (avoids GBK↔Big5 mojibake with 0 U+FFFD).
        candidates = ("gb18030", "utf-8")

    best: DecodeResult | None = None
    best_score: tuple[int, int, int] | None = None
    for index, encoding in enumerate(candidates):
        try:
            text = raw.decode(encoding, errors="replace")
        except LookupError:
            continue
        replacements = text.count("\ufffd")
        junk = sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\r\t")
        score = (replacements, junk, index)
        if best_score is None or score < best_score:
            best_score = score
            best = DecodeResult(text.lstrip("\ufeff"), encoding, 0.35, True)
    if best is None:
        text = raw.decode("gb18030", errors="replace")
        return DecodeResult(text.lstrip("\ufeff"), "gb18030", 0.1, True)
    return best
