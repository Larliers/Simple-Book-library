from __future__ import annotations

from pathlib import Path

from PIL import Image

from bookhub.library.preview_paths import build_preview_path
from bookhub.library.repository import LibraryRepository

TEXT_COVER_EXTENSIONS = (".webp", ".png", ".jpg", ".jpeg")


def find_text_cover(txt_path: Path) -> Path | None:
    for extension in TEXT_COVER_EXTENSIONS:
        candidate = txt_path.with_suffix(extension)
        if candidate.is_file():
            return candidate
    return None


def text_cover_fingerprint(cover_path: Path | None) -> str:
    if cover_path is None:
        return ""
    stat = cover_path.stat()
    return f"{cover_path.name}:{stat.st_size}:{stat.st_mtime_ns}"


def text_thumbnail_output_path(repository: LibraryRepository, normalized_path: str) -> Path:
    return build_preview_path(
        preview_root=repository.preview_dir,
        resource_type="text_novel",
        variant="compressed",
        source_key=normalized_path,
        extension=".webp",
    )


def generate_text_cover_thumbnail(cover_path: Path, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    resampling = getattr(Image, "Resampling", None)
    lanczos = resampling.LANCZOS if resampling is not None else Image.LANCZOS
    with Image.open(cover_path) as image:
        try:
            image.seek(0)
        except EOFError:
            pass
        thumbnail = image.convert("RGB")
        thumbnail.thumbnail((360, 540), lanczos)
        thumbnail.save(output_path, format="WEBP", quality=80, method=4)
    return output_path.resolve(strict=False).as_uri()
