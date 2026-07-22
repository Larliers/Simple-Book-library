from __future__ import annotations

import zipfile
from pathlib import Path

from natsort import natsorted

from bookhub.library.formats.zip_safety import ZipBombError, open_zip_safely, read_zip_member_safely
from bookhub.library.models import COMIC_IMAGE_EXTENSIONS


def list_cbz_image_members(file_path: Path) -> list[str]:
    with open_zip_safely(file_path) as zip_file:
        members = [
            info.filename
            for info in zip_file.infolist()
            if (not info.is_dir()) and Path(info.filename).suffix.lower() in COMIC_IMAGE_EXTENSIONS
        ]
    return natsorted(members, key=lambda item: item.lower())


def read_cbz_cover_bytes(file_path: Path) -> tuple[str | None, bytes | None, int]:
    """Return (cover_member_name, cover_bytes, image_count)."""
    try:
        members = list_cbz_image_members(file_path)
    except (OSError, ZipBombError, zipfile.BadZipFile):
        return None, None, 0
    if not members:
        return None, None, 0
    cover_name = members[0]
    try:
        with open_zip_safely(file_path) as zip_file:
            cover_bytes = read_zip_member_safely(zip_file, cover_name)
    except (OSError, ZipBombError, zipfile.BadZipFile, KeyError):
        return cover_name, None, len(members)
    return cover_name, cover_bytes, len(members)
