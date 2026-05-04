from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from bookhub.library.error_logs import append_conflict_if_new


@dataclass(slots=True)
class SanitizeResult:
    ok: bool
    output_path: str | None
    message: str = ""


def sanitize_image_for_ui(input_path: str | Path, output_path: str | Path) -> SanitizeResult:
    src = Path(input_path)
    dst = Path(output_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not src.exists() or not src.is_file():
        return SanitizeResult(ok=False, output_path=None, message=f"missing file: {src}")

    try:
        with Image.open(src) as img:
            normalized = img.convert("RGB")
            normalized.save(dst, format="PNG", icc_profile=None, optimize=True)
        return SanitizeResult(ok=True, output_path=str(dst), message="sanitized")
    except Exception as exc:  # noqa: BLE001
        append_conflict_if_new(f"image_sanitize_failed | path={src} | error={exc}")
        return SanitizeResult(ok=False, output_path=None, message=str(exc))


def sanitize_cover_with_fallback(image_path: str | Path, fallback_output: str | Path) -> str | None:
    result = sanitize_image_for_ui(image_path, fallback_output)
    return result.output_path if result.ok else None


def build_text_cover_bundle(txt_path: str | Path, cover_path: str | Path, sanitized_cover_path: str | Path) -> dict[str, str]:
    safe_cover = sanitize_cover_with_fallback(cover_path, sanitized_cover_path)
    return {
        "txt_path": str(Path(txt_path)),
        "cover_path": safe_cover or str(Path(cover_path)),
    }