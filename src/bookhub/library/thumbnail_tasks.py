from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import os

from PIL import Image

from bookhub.library.media_sanitizer import sanitize_image_for_ui
from bookhub.library.metadata import regenerate_thumbnail_for_record
from bookhub.library.models import ThumbnailTaskResult
from bookhub.library.preview_paths import build_preview_path, is_preview_variant_uri, uri_to_path
from bookhub.library.repository import LibraryRepository


def build_thumbnail_output_path(preview_dir: Path, source_path: str) -> Path:
    return build_preview_path(
        preview_root=preview_dir,
        resource_type="book",
        variant="compressed",
        source_key=source_path,
        extension=".webp",
    )


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
        thumb_file = uri_to_path(record.get("thumbnail_path"))
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
        thumb_file = uri_to_path(record.get("thumbnail_path"))
        cover_source = Path(str(record.get("cover_image_path") or ""))
        original_file = build_preview_path(
            preview_root=repository.preview_dir,
            resource_type="comic",
            variant="original",
            source_key=str(record.get("cover_image_path") or ""),
            extension=cover_source.suffix,
        )
        compressed_file = build_preview_path(
            preview_root=repository.preview_dir,
            resource_type="comic",
            variant="compressed",
            source_key=str(record.get("cover_image_path") or ""),
            extension=".webp",
        )
        try:
            for candidate in (thumb_file, original_file, compressed_file):
                if candidate is not None:
                    candidate.unlink(missing_ok=True)
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
    only_missing: bool = False,
    workers: int | None = None,
    progress_cb=None,
) -> ThumbnailTaskResult:
    task_kind = "regenerate_missing" if only_missing else "regenerate"
    result = ThumbnailTaskResult(task_kind=task_kind, task_scope="comic")
    records = repository.list_active_comics_for_thumbnail_task(roots=roots)
    selected = [record for record in records if _should_regenerate_comic_record(record, only_missing=only_missing)]
    result.total = len(selected)
    if result.total <= 0:
        return result

    worker_count = _normalize_worker_count(workers)
    futures = {}
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        for record in selected:
            future = executor.submit(_render_comic_thumbnail, repository.preview_dir, record)
            futures[future] = record

        completed = 0
        for future in as_completed(futures):
            record = futures[future]
            completed += 1
            comic_id = int(record["id"])
            source_path = str(record.get("cover_image_path") or "")
            display_path = str(record.get("path") or source_path)
            if progress_cb is not None:
                progress_cb(completed, result.total, display_path)
            try:
                payload = future.result()
            except Exception as exc:  # noqa: BLE001
                result.failed += 1
                result.errors.append(f"Comic regenerate failed: {source_path} -> {exc}")
                continue

            status = str(payload.get("status") or "failed")
            if status == "skipped":
                result.skipped += 1
                repository.update_comic_thumbnail_path(comic_id, None)
                continue
            if status == "failed":
                result.failed += 1
                error_message = str(payload.get("error") or "unknown error")
                result.errors.append(f"Comic regenerate failed: {source_path} -> {error_message}")
                fallback_uri = payload.get("fallback_uri")
                if isinstance(fallback_uri, str) and fallback_uri.strip():
                    repository.update_comic_thumbnail_path(comic_id, fallback_uri)
                else:
                    repository.update_comic_thumbnail_path(comic_id, None)
                continue

            thumbnail_uri = str(payload.get("thumbnail_uri") or "")
            cover_fingerprint = str(payload.get("cover_fingerprint") or "")
            repository.update_comic_thumbnail_state(
                comic_id,
                thumbnail_path=thumbnail_uri or None,
                cover_fingerprint=cover_fingerprint or None,
            )
            original_path = payload.get("original_path")
            if isinstance(original_path, str) and original_path.strip():
                try:
                    Path(original_path).unlink(missing_ok=True)
                except OSError:
                    pass
            result.succeeded += 1
    return result


def _normalize_worker_count(workers: int | None) -> int:
    if isinstance(workers, int) and workers > 0:
        return min(16, max(1, workers))
    cpu = os.cpu_count() or 4
    return max(2, min(8, cpu - 1))


def _cover_fingerprint(path: Path) -> str:
    stat = path.stat()
    return f"{int(stat.st_size)}:{int(stat.st_mtime)}"


def _should_regenerate_comic_record(record: dict[str, object], *, only_missing: bool) -> bool:
    source_path = str(record.get("cover_image_path") or "")
    source = Path(source_path)
    if not source.exists() or not source.is_file():
        return True
    if not only_missing:
        return True

    thumbnail_uri = str(record.get("thumbnail_path") or "")
    if not thumbnail_uri:
        return True
    if is_preview_variant_uri(thumbnail_uri, resource_type="comic", variant="original"):
        return True
    thumb_path = uri_to_path(thumbnail_uri)
    if thumb_path is None or not thumb_path.exists() or not thumb_path.is_file():
        return True

    stored_fingerprint = str(record.get("cover_fingerprint") or "")
    if stored_fingerprint.startswith("manual:"):
        return False
    try:
        current_fingerprint = _cover_fingerprint(source)
    except OSError:
        return True
    if not stored_fingerprint or stored_fingerprint != current_fingerprint:
        return True
    return False


def _render_comic_thumbnail(preview_dir: Path, record: dict[str, object]) -> dict[str, str]:
    source_path = str(record.get("cover_image_path") or "")
    source = Path(source_path)
    thumbnail_uri = str(record.get("thumbnail_path") or "")
    if not source.exists() or not source.is_file():
        return {"status": "skipped"}

    output_path = build_preview_path(
        preview_root=preview_dir,
        resource_type="comic",
        variant="compressed",
        source_key=source_path,
        extension=".webp",
    )
    original_path = build_preview_path(
        preview_root=preview_dir,
        resource_type="comic",
        variant="original",
        source_key=source_path,
        extension=source.suffix,
    )
    sanitized_source = output_path.with_suffix(".comic_cover_sanitized.png")
    try:
        sanitize_result = sanitize_image_for_ui(source, sanitized_source)
        source_for_thumb = Path(sanitize_result.output_path) if sanitize_result.ok and sanitize_result.output_path else source
        with Image.open(str(source_for_thumb)) as img:
            img = img.convert("RGB")
            img.thumbnail((420, 620))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, format="WEBP", quality=80, method=4)
        return {
            "status": "ok",
            "thumbnail_uri": output_path.resolve(strict=False).as_uri(),
            "cover_fingerprint": _cover_fingerprint(source),
            "original_path": str(original_path),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "error": str(exc),
            "fallback_uri": thumbnail_uri,
        }
