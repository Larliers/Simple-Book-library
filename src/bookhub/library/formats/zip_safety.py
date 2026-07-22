from __future__ import annotations

import zipfile
from pathlib import Path

MAX_ZIP_MEMBERS = 5_000
MAX_ZIP_MEMBER_UNCOMPRESSED = 80 * 1024 * 1024
MAX_ZIP_TOTAL_UNCOMPRESSED = 400 * 1024 * 1024


class ZipBombError(RuntimeError):
    """Raised when a zip archive exceeds configured safety limits."""


def open_zip_safely(file_path: Path) -> zipfile.ZipFile:
    zip_file = zipfile.ZipFile(file_path, "r")
    try:
        infos = zip_file.infolist()
        if len(infos) > MAX_ZIP_MEMBERS:
            raise ZipBombError(f"Too many zip members ({len(infos)} > {MAX_ZIP_MEMBERS})")
        total = 0
        for info in infos:
            if info.is_dir():
                continue
            if info.file_size > MAX_ZIP_MEMBER_UNCOMPRESSED:
                raise ZipBombError(
                    f"Zip member too large: {info.filename} ({info.file_size} bytes)"
                )
            total += int(info.file_size)
            if total > MAX_ZIP_TOTAL_UNCOMPRESSED:
                raise ZipBombError(
                    f"Zip total uncompressed size too large ({total} > {MAX_ZIP_TOTAL_UNCOMPRESSED})"
                )
    except Exception:
        zip_file.close()
        raise
    return zip_file


def read_zip_member_safely(zip_file: zipfile.ZipFile, member_name: str) -> bytes:
    info = zip_file.getinfo(member_name)
    if info.file_size > MAX_ZIP_MEMBER_UNCOMPRESSED:
        raise ZipBombError(f"Zip member too large: {member_name} ({info.file_size} bytes)")
    return zip_file.read(member_name)
