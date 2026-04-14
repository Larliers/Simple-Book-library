from __future__ import annotations

import hashlib
from pathlib import Path

from bookhub.library.metadata import regenerate_thumbnail_for_record
from bookhub.library.models import ThumbnailTaskResult
from bookhub.library.repository import LibraryRepository


def build_thumbnail_output_path(preview_dir: Path, source_path: str) -> Path:
    token = hashlib.sha1(source_path.encode("utf-8")).hexdigest()  # noqa: S324
    # Extension is .webp; _save_thumbnail_image will enforce this anyway.
    return preview_dir / f"{token}.webp"


def cleanup_all_thumbnails(repository: LibraryRepository, progress_cb=None) -> ThumbnailTaskResult:
    result = ThumbnailTaskResult(task_kind="cleanup")
    # Collect both legacy .png files and current .webp files
    files = sorted(
        path
        for pattern in ("*.png", "*.webp")
        for path in repository.preview_dir.glob(pattern)
        if path.name != ".gitkeep"
    )
    result.total = len(files)

    for index, file_path in enumerate(files, start=1):
        if progress_cb is not None:
            progress_cb(index, result.total, str(file_path))
        try:
            file_path.unlink(missing_ok=True)
            result.succeeded += 1
        except OSError as exc:
            result.failed += 1
            result.errors.append(f"Delete failed: {file_path} -> {exc}")

    try:
        repository.clear_all_thumbnail_paths()
    except Exception as exc:  # noqa: BLE001
        result.failed += 1
        result.errors.append(f"Database thumbnail_path cleanup failed: {exc}")

    return result


def regenerate_all_thumbnails(
    repository: LibraryRepository,
    progress_cb=None,
) -> ThumbnailTaskResult:
    result = ThumbnailTaskResult(task_kind="regenerate")
    records = repository.list_active_books_for_thumbnail_task()
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
