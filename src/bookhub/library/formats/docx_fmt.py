from __future__ import annotations

import zipfile
from pathlib import Path

from natsort import natsorted

from bookhub.library.formats.common import (
    bytes_to_thumbnail,
    clean_text,
    title_placeholder_thumbnail,
)
from bookhub.library.formats.zip_safety import ZipBombError, open_zip_safely, read_zip_member_safely
from bookhub.library.models import ParsedMetadata

_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")


def extract_docx_metadata(file_path: Path) -> ParsedMetadata:
    try:
        from docx import Document  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("python-docx is required for DOCX import. Install: python-docx.") from exc

    try:
        document = Document(str(file_path))
    except Exception:  # noqa: BLE001
        return ParsedMetadata(title=file_path.stem)

    props = document.core_properties
    title = clean_text(props.title) or file_path.stem
    author = clean_text(props.author)
    return ParsedMetadata(title=title, author=author)


def _first_docx_image_bytes(file_path: Path) -> bytes | None:
    try:
        with open_zip_safely(file_path) as zip_file:
            members = [
                info.filename
                for info in zip_file.infolist()
                if (not info.is_dir())
                and info.filename.replace("\\", "/").lower().startswith("word/media/")
                and Path(info.filename).suffix.lower() in _IMAGE_SUFFIXES
            ]
            if not members:
                return None
            members = natsorted(members, key=lambda item: item.lower())
            return read_zip_member_safely(zip_file, members[0])
    except (OSError, ZipBombError, zipfile.BadZipFile, KeyError):
        return None


def generate_docx_thumbnail(file_path: Path, output_path: Path, title_fallback: str) -> str:
    metadata = extract_docx_metadata(file_path)
    title = metadata.title or title_fallback or file_path.stem
    cover_bytes = _first_docx_image_bytes(file_path)
    if cover_bytes:
        return bytes_to_thumbnail(cover_bytes, output_path, title)
    return title_placeholder_thumbnail(output_path, title)
