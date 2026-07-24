from __future__ import annotations

import hashlib
import shutil
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


def _safe_archive_member_path(member: str) -> Path | None:
    normalized = Path(member.replace("\\", "/"))
    if normalized.is_absolute():
        return None
    if any(part in {"..", ""} for part in normalized.parts):
        return None
    return normalized


def _cbz_read_cache_dir(preview_dir: Path, cbz_path: Path) -> Path | None:
    try:
        stat = cbz_path.stat()
    except OSError:
        return None
    token = hashlib.sha1(f"{cbz_path.resolve()}:{stat.st_mtime_ns}".encode("utf-8")).hexdigest()  # noqa: S324
    return preview_dir / "comic" / "read" / token


def _cbz_read_cache_is_valid(cache_dir: Path, cbz_path: Path, members: list[str]) -> bool:
    marker = cache_dir / ".cbz_source"
    if not marker.is_file():
        return False
    try:
        if marker.read_text(encoding="utf-8").strip() != str(cbz_path.stat().st_mtime_ns):
            return False
    except OSError:
        return False
    for member in members:
        member_path = _safe_archive_member_path(member)
        if member_path is None:
            return False
        if not (cache_dir / member_path).is_file():
            return False
    return True


def _extract_cbz_members_to_cache(cbz_path: Path, cache_dir: Path, members: list[str]) -> bool:
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        with open_zip_safely(cbz_path) as zip_file:
            for member in members:
                member_path = _safe_archive_member_path(member)
                if member_path is None:
                    return False
                output_path = cache_dir / member_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(read_zip_member_safely(zip_file, member))
    except (OSError, ZipBombError, zipfile.BadZipFile, KeyError):
        shutil.rmtree(cache_dir, ignore_errors=True)
        return False
    try:
        (cache_dir / ".cbz_source").write_text(str(cbz_path.stat().st_mtime_ns), encoding="utf-8")
    except OSError:
        shutil.rmtree(cache_dir, ignore_errors=True)
        return False
    return True


def prepare_cbz_for_external_viewer(cbz_path: Path, preview_dir: Path) -> Path | None:
    """Extract CBZ pages to read cache and return the first page for the default image viewer."""
    if not cbz_path.is_file():
        return None
    try:
        members = list_cbz_image_members(cbz_path)
    except (OSError, ZipBombError, zipfile.BadZipFile):
        return None
    if not members:
        return None
    cache_dir = _cbz_read_cache_dir(preview_dir, cbz_path)
    if cache_dir is None:
        return None
    if not _cbz_read_cache_is_valid(cache_dir, cbz_path, members):
        if not _extract_cbz_members_to_cache(cbz_path, cache_dir, members):
            return None
    first_member_path = _safe_archive_member_path(members[0])
    if first_member_path is None:
        return None
    first_page = cache_dir / first_member_path
    return first_page if first_page.is_file() else None