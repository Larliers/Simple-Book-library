from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from PIL import Image

from bookhub.library.media_sanitizer import sanitize_image_for_ui
from bookhub.library.metadata import regenerate_thumbnail_for_record
from bookhub.library.models import ThumbnailTaskResult
from bookhub.library.repository import LibraryRepository


def build_thumbnail_output_path(preview_dir: Path, source_path: str) -> Path:
    token = hashlib.sha1(source_path.encode("utf-8")).hexdigest()  # noqa: S324
    return preview_dir / f"{token}.webp"


def _thumbnail_file_from_url(value: str | None) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.startswith("file://"):
        parsed = urlparse(text)
        return Path(url2pathname(parsed.path))
    return Path(text)


def cleanup_library_thumbnails(
    repository: LibraryRepository,
    *,
    roots: list[str] | None = None,
    progress_cb=None,
) -> ThumbnailTaskResult:
    result = ThumbnailTaskResult(task_kind="cleanup", task_scope="library")
    records = repository.list_active_books_for_thumbnail_task(roots=roots)
    result.total = len(records)

    for index, record in enumerate(records, start=1):
        source_path = str(record.get("path") or "")
        if progress_cb is not None:
            progress_cb(index, result.total, source_path)
        thumb_file = _thumbnail_file_from_url(record.get("thumbnail_path"))
        try:
            if thumb_file is not None:
                thumb_file.unlink(missing_ok=True)
            result.succeeded += 1
        except OSError as exc:
            result.failed += 1
            result.errors.append(f"Delete failed: {thumb_file} -> {exc}")

    try:
        repository.clear_all_thumbnail_paths(roots=roots)
    except Exception as exc:  # noqa: BLE001
        result.failed += 1
        result.errors.append(f"Database thumbnail_path cleanup failed: {exc}")

    return result


def regenerate_library_thumbnails(
    repository: LibraryRepository,
    *,
    roots: list[str] | None = None,
    progress_cb=None,
) -> ThumbnailTaskResult:
    result = ThumbnailTaskResult(task_kind="regenerate", task_scope="library")
    records = repository.list_active_books_for_thumbnail_task(roots=roots)
    result.total = len(records)

    for index, record in enumerate(records, start=1):
        book_id = int(record["id"])
        source_path = str(record["path"])
        extension = str(record["extension"] or "").lower()
        title_fallback = str(record.get("title") or record.get("file_name") or "")

        if progress_cb is not None:
            progress_cb(index, result.total, source_path)

        source = Path(source_path)
        if not source.exists() or not source.is_file():
            result.skipped += 1
            continue

        if extension not in {".pdf", ".epub"}:
            result.skipped += 1
            continue

        output_path = build_thumbnail_output_path(repository.preview_dir, source_path)
        try:
            thumbnail_path = regenerate_thumbnail_for_record(
                extension=extension,
                source_path=source_path,
                output_path=str(output_path),
                title_fallback=title_fallback,
            )
            repository.update_book_thumbnail_path(book_id, thumbnail_path)
            result.succeeded += 1
        except Exception as exc:  # noqa: BLE001
            result.failed += 1
            repository.update_book_thumbnail_path(book_id, None)
            result.errors.append(f"Regenerate failed: {source_path} -> {exc}")

    return result


def cleanup_comic_thumbnails(
    repository: LibraryRepository,
    *,
    roots: list[str] | None = None,
    progress_cb=None,
) -> ThumbnailTaskResult:
    result = ThumbnailTaskResult(task_kind="cleanup", task_scope="comic")
    records = repository.list_active_comics_for_thumbnail_task(roots=roots)
    result.total = len(records)

    for index, record in enumerate(records, start=1):
        source_path = str(record.get("path") or "")
        if progress_cb is not None:
            progress_cb(index, result.total, source_path)
        thumb_file = _thumbnail_file_from_url(record.get("thumbnail_path"))
        try:
            if thumb_file is not None:
                thumb_file.unlink(missing_ok=True)
            result.succeeded += 1
        except OSError as exc:
            result.failed += 1
            result.errors.append(f"Delete failed: {thumb_file} -> {exc}")

    try:
        repository.clear_all_comic_thumbnail_paths(roots=roots)
    except Exception as exc:  # noqa: BLE001
        result.failed += 1
        result.errors.append(f"Comic thumbnail_path cleanup failed: {exc}")

    return result


def regenerate_comic_thumbnails(
    repository: LibraryRepository,
    *,
    roots: list[str] | None = None,
    progress_cb=None,
) -> ThumbnailTaskResult:
    result = ThumbnailTaskResult(task_kind="regenerate", task_scope="comic")
    records = repository.list_active_comics_for_thumbnail_task(roots=roots)
    result.total = len(records)

    for index, record in enumerate(records, start=1):
        comic_id = int(record["id"])
        display_path = str(record.get("path") or "")
        if progress_cb is not None:
            progress_cb(index, result.total, display_path)

        source_path = str(record.get("cover_image_path") or "")
        source = Path(source_path)
        if not source.exists() or not source.is_file():
            result.skipped += 1
            repository.update_comic_thumbnail_path(comic_id, None)
            continue

        output_path = build_thumbnail_output_path(repository.preview_dir, source_path)
        sanitized_source = output_path.with_suffix(".comic_cover_sanitized.png")
        try:
            sanitize_result = sanitize_image_for_ui(source, sanitized_source)
            source_for_thumb = Path(sanitize_result.output_path) if sanitize_result.ok and sanitize_result.output_path else source
            with Image.open(str(source_for_thumb)) as img:
                img = img.convert("RGB")
                img.thumbnail((420, 620))
                output_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(output_path, format="WEBP", quality=80, method=4)
            repository.update_comic_thumbnail_path(comic_id, output_path.resolve(strict=False).as_uri())
            result.succeeded += 1
        except Exception as exc:  # noqa: BLE001
            result.failed += 1
            repository.update_comic_thumbnail_path(comic_id, None)
            result.errors.append(f"Comic regenerate failed: {source_path} -> {exc}")

    return result
