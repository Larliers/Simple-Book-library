from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from bookhub.library.media_sanitizer import sanitize_image_for_ui


def save_thumbnail_image(image: Image.Image, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    webp_path = output_path.with_suffix(".webp")
    thumb = image.convert("RGB")
    thumb.thumbnail((360, 540), Image.Resampling.LANCZOS)
    thumb.save(webp_path, format="WEBP", quality=80, method=4)
    return webp_path.resolve(strict=False).as_uri()


def title_placeholder_thumbnail(output_path: Path, label: str) -> str:
    placeholder = Image.new("RGB", (360, 540), color=(232, 238, 248))
    draw = ImageDraw.Draw(placeholder)
    text = (label or "Untitled")[:80]
    draw.text((20, 24), text, fill=(55, 65, 86))
    return save_thumbnail_image(placeholder, output_path)


def bytes_to_thumbnail(cover_bytes: bytes, output_path: Path, title_fallback: str) -> str:
    safe_png_path = output_path.with_suffix(".cover_sanitized.png")
    try:
        with Image.open(BytesIO(cover_bytes)) as cover_image:
            cover_image.save(safe_png_path, format="PNG", icc_profile=None, optimize=True)
    except Exception:  # noqa: BLE001
        return title_placeholder_thumbnail(output_path, title_fallback)

    sanitized = sanitize_image_for_ui(safe_png_path, safe_png_path)
    if sanitized.ok and sanitized.output_path:
        with Image.open(Path(sanitized.output_path)) as safe_cover_image:
            return save_thumbnail_image(safe_cover_image, output_path)
    try:
        with Image.open(safe_png_path) as cover_image:
            return save_thumbnail_image(cover_image, output_path)
    except Exception:  # noqa: BLE001
        return title_placeholder_thumbnail(output_path, title_fallback)


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip()
    return text or None
