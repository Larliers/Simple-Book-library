from __future__ import annotations

"""Directory scan / index update for Library, Comic, and Text Novel.

Indexer contract alignment (Agent-rule/contracts/indexer-contract.md):
- Each scan walks configured roots fully.
- Local skip only: Library/Text hash_strategy fingerprints; Comic folder_size_mtime.
- Missing sources are deleted from DB and logged (no Missed restore path).
- No last_checkpoint / next_checkpoint API.
"""

import importlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from bookhub.library.metadata import (
    build_metadata_tags,
    compute_fingerprints,
    extract_epub_metadata,
    extract_pdf_metadata,
    extension_lower,
    file_name,
    generate_epub_thumbnail,
    generate_pdf_thumbnail,
)
from bookhub.library.error_logs import append_scan_log
from bookhub.library.models import (
    COMIC_IMAGE_EXTENSIONS,
    COMIC_TITLE_CONFLICT_POLICIES,
    COMIC_TITLE_CONFLICT_PREFER_NEWER,
    COMIC_TITLE_CONFLICT_SKIP_INCOMING,
    SUPPORTED_EXTENSIONS,
    ComicScanRequest,
    HashStrategy,
    ScanConflict,
    ScanRequest,
    ScanResult,
    TEXT_FILE_EXTENSION,
    TextScanRequest,
)
from bookhub.library.preview_paths import build_preview_path, is_preview_variant_uri, uri_to_path
from bookhub.library.repository import LibraryRepository
from bookhub.library.text_rules import ImportRule, RuleContext, apply_rule_chain, load_rules_from_json
from bookhub.library.text_rules.rule_examples import default_text_title_rule_chain
from bookhub.library.text_encoding import (
    TEXT_ENCODING_SIMPLIFIED,
    normalize_encoding_preference,
    read_text_file,
    read_text_first_line,
)

ScanProgressCallback = Callable[[int, int, str, dict[str, object]], None]


def _lanczos_resample() -> object:
    resampling = getattr(Image, "Resampling", None)
    if resampling is not None and hasattr(resampling, "LANCZOS"):
        return resampling.LANCZOS
    return getattr(Image, "LANCZOS", getattr(Image, "BICUBIC", 3))


def _iter_files_with_depth(root: Path, depth: int):
    root_parts = len(root.parts)
    for current_dir, dir_names, file_names in os.walk(root):
        current_path = Path(current_dir)
        relative_depth = len(current_path.parts) - root_parts
        if relative_depth >= depth:
            dir_names[:] = []
            continue
        dir_names[:] = sorted(dir_names)
        for current_file in sorted(file_names):
            yield current_path / current_file


def _thumbnail_path_for(repo: LibraryRepository, normalized_path: str) -> Path:
    return build_preview_path(
        preview_root=repo.preview_dir,
        resource_type="book",
        variant="compressed",
        source_key=normalized_path,
        extension=".webp",
    )


def _extract_metadata_by_extension(file_path: Path, extension: str):
    if extension == ".pdf":
        return extract_pdf_metadata(file_path)
    return extract_epub_metadata(file_path)


def _build_thumbnail_by_extension(
    file_path: Path,
    extension: str,
    output_path: Path,
    title_fallback: str,
) -> str:
    if extension == ".pdf":
        return generate_pdf_thumbnail(file_path, output_path)
    return generate_epub_thumbnail(file_path, output_path, title_fallback)


def _probe_pdf_backend() -> tuple[bool, str | None]:
    try:
        importlib.import_module("fitz")
    except Exception as exc:  # noqa: BLE001
        reason = f"{exc.__class__.__name__}: {exc}"
        return False, reason
    return True, None


def _build_payload(
    normalized_path: str,
    file_path: Path,
    extension: str,
    title: str | None,
    author: str | None,
    publisher: str | None,
    language: str | None,
    tags: list[str],
    thumbnail_path: str | None,
    fingerprints,
    ) -> dict[str, str | None]:
    return {
        "path": normalized_path,
        "file_name": file_name(file_path),
        "extension": extension,
        "title": title,
        "author": author,
        "publisher": publisher,
        "language": language,
        "tags_json": json.dumps(tags, ensure_ascii=False),
        "status": "UNREAD",
        "resource_type": extension.lstrip("."),
        "thumbnail_path": thumbnail_path,
        "fingerprint_sha256": fingerprints.sha256,
        "fingerprint_size_mtime": fingerprints.size_mtime,
        "fingerprint_quick": fingerprints.quick,
    }


def _log_missing_entry(*, resource_type: str, title: str, path_value: str, reason: str) -> None:
    append_scan_log(
        f"missing_removed | type={resource_type} | title={title} | path={path_value} | reason={reason}"
    )


def _remove_missing_books_in_scope(
    repository: LibraryRepository,
    roots: list[str],
    *,
    resource_type: str | None,
    exclude_text_novel: bool = False,
) -> int:
    records = repository.list_books_in_roots(roots=roots, resource_type=resource_type)
    stale_ids: list[int] = []
    for record in records:
        if exclude_text_novel and str(record.get("resource_type") or "") == "text_novel":
            continue
        path_value = str(record.get("path") or "")
        if not path_value:
            continue
        source = Path(path_value)
        if source.exists() and source.is_file():
            continue
        book_id = repository.get_book_int_id(str(record.get("resource_id") or ""))
        if book_id is None:
            continue
        stale_ids.append(book_id)
        title = str(record.get("title") or record.get("file_name") or "Unknown")
        _log_missing_entry(
            resource_type=str(record.get("resource_type") or "book"),
            title=title,
            path_value=path_value,
            reason="source file missing during scan",
        )
    return repository.delete_books_by_ids(stale_ids)


def _remove_missing_comics_in_scope(repository: LibraryRepository, roots: list[str]) -> int:
    records = repository.list_comics_in_roots(roots=roots)
    stale_ids: list[int] = []
    for record in records:
        path_value = str(record.get("path") or "")
        if not path_value:
            continue
        source = Path(path_value)
        if source.exists() and source.is_dir():
            continue
        comic_id = repository.get_comic_int_id(str(record.get("resource_id") or ""))
        if comic_id is None:
            continue
        stale_ids.append(comic_id)
        title = str(record.get("title") or "Unknown")
        _log_missing_entry(
            resource_type="comic_folder",
            title=title,
            path_value=path_value,
            reason="source folder missing during scan",
        )
    return repository.delete_comics_by_ids(stale_ids)


def _cleanup_stale_duplicate_if_needed(
    repository: LibraryRepository,
    duplicate: dict[str, Any] | None,
) -> bool:
    if not duplicate:
        return False
    stale_path = str(duplicate.get("path") or "")
    stale_id = duplicate.get("id")
    if not stale_path or not isinstance(stale_id, int):
        return False
    stale_file = Path(stale_path)
    if stale_file.exists():
        return False
    repository.delete_book_by_id(stale_id)
    _log_missing_entry(
        resource_type=str(duplicate.get("resource_type") or "book"),
        title=str(duplicate.get("title") or duplicate.get("file_name") or "Unknown"),
        path_value=stale_path,
        reason="stale duplicate removed before import",
    )
    return True


def _read_txt_first_line(file_path: Path, *, preference: str = TEXT_ENCODING_SIMPLIFIED) -> str:
    return read_text_first_line(file_path, preference=preference)


def _read_txt_head_text(
    file_path: Path,
    preview_chars: int,
    *,
    preference: str = TEXT_ENCODING_SIMPLIFIED,
) -> str:
    safe_limit = max(100, int(preview_chars))
    return read_text_file(file_path, max_chars=safe_limit, preference=preference).strip()


def _parse_rule_map(raw_rules_json: str, errors: list[str], path_for_error: str) -> dict[str, list[ImportRule]]:
    if not str(raw_rules_json or "").strip():
        return {}
    try:
        decoded = json.loads(raw_rules_json)
    except json.JSONDecodeError as exc:
        errors.append(f"Text rule json invalid for {path_for_error}: {exc}")
        return {}
    return load_rules_from_json(decoded)


def _natural_sort_key(path: Path) -> list[object]:
    parts = re.split(r"(\d+)", path.name.lower())
    return [int(part) if part.isdigit() else part for part in parts]


def _collect_comic_folder_metrics(file_names: list[str], folder_path: Path) -> tuple[Path | None, int, str, int, int]:
    image_names = [name for name in file_names if Path(name).suffix.lower() in COMIC_IMAGE_EXTENSIONS]
    if not image_names:
        return None, 0, "", 0, 0
    sorted_names = sorted(image_names, key=lambda name: _natural_sort_key(Path(name)))
    image_count = len(sorted_names)
    total_size = 0
    max_mtime = 0
    for name in sorted_names:
        image_path = folder_path / name
        try:
            stat = image_path.stat()
        except OSError:
            continue
        total_size += int(stat.st_size)
        max_mtime = max(max_mtime, int(stat.st_mtime))
    snapshot = f"{total_size}:{max_mtime}:{image_count}"
    try:
        folder_modified_at = int(folder_path.stat().st_mtime)
    except OSError:
        folder_modified_at = max_mtime
    return folder_path / sorted_names[0], image_count, snapshot, max_mtime, folder_modified_at


def _collect_comic_info_text(folder: Path, *, preference: str = TEXT_ENCODING_SIMPLIFIED) -> str | None:
    txt_paths = sorted(
        [child for child in folder.iterdir() if child.is_file() and child.suffix.lower() == ".txt"],
        key=_natural_sort_key,
    )
    if not txt_paths:
        return None
    parts: list[str] = []
    for txt_path in txt_paths:
        content = read_text_file(txt_path, preference=preference).strip()
        if content:
            parts.append(content)
    if not parts:
        return None
    return "\n\n".join(parts)


def _iter_dirs_with_depth(root: Path, depth: int):
    root_parts = len(root.parts)
    for current_dir, dir_names, file_names in os.walk(root):
        current_path = Path(current_dir)
        relative_depth = len(current_path.parts) - root_parts
        if relative_depth >= depth:
            dir_names[:] = []
        dir_names[:] = sorted(dir_names)
        yield current_path, relative_depth, list(file_names)


def _cover_fingerprint(path: Path) -> str:
    stat = path.stat()
    return f"{int(stat.st_size)}:{int(stat.st_mtime)}"


def _collect_leaf_comic_candidates(
    root: Path,
    max_depth: int,
) -> tuple[list[tuple[Path, Path, int, str, int, int]], int]:
    candidates: list[tuple[Path, Path, int, str, int, int, int]] = []
    scanned_dirs = 0
    for folder_path, relative_depth, file_names in _iter_dirs_with_depth(root, max_depth):
        scanned_dirs += 1
        if relative_depth > max_depth:
            continue
        cover_path, image_count, folder_snapshot, folder_mtime, folder_modified_at = _collect_comic_folder_metrics(
            file_names,
            folder_path,
        )
        if cover_path is None or image_count <= 0:
            continue
        candidates.append(
            (folder_path, cover_path, image_count, folder_snapshot, folder_mtime, folder_modified_at, relative_depth)
        )

    candidate_paths = {item[0] for item in candidates}
    has_image_children: dict[Path, bool] = {item[0]: False for item in candidates}
    for folder_path, _cover_path, _count, _snapshot, _mtime, _folder_modified_at, _depth in candidates:
        for parent in folder_path.parents:
            if parent == root.parent:
                break
            if parent in candidate_paths:
                has_image_children[parent] = True
    leaf = [
        (folder, cover, count, snapshot, folder_mtime, folder_modified_at)
        for folder, cover, count, snapshot, folder_mtime, folder_modified_at, _depth in candidates
        if not has_image_children[folder]
    ]
    leaf.sort(key=lambda item: str(item[0]).lower())
    return leaf, scanned_dirs


_RASTERIZE_COVER_EXTENSIONS = {".gif", ".bmp", ".tif", ".tiff"}


def _copy_or_downscale_comic_placeholder(
    cover_path: Path,
    placeholder_path: Path,
    *,
    max_decode_bytes: int,
) -> tuple[Path, bool]:
    placeholder_path.parent.mkdir(parents=True, exist_ok=True)
    downscaled_path = placeholder_path.with_suffix(".png")
    suffix = cover_path.suffix.lower()
    must_rasterize = suffix in _RASTERIZE_COVER_EXTENSIONS
    try:
        with Image.open(str(cover_path)) as img:
            # Animated GIF / multi-frame TIFF: first frame only as static cover.
            try:
                img.seek(0)
            except EOFError:
                pass
            width, height = img.size
            projected_bytes = int(width) * int(height) * 4
            if (not must_rasterize) and projected_bytes <= max_decode_bytes:
                shutil.copy2(cover_path, placeholder_path)
                return placeholder_path, False
            safe_img = img.convert("RGB")
            downscaled = False
            if projected_bytes > max_decode_bytes:
                safe_img.thumbnail((1400, 2000), _lanczos_resample())
                downscaled = True
            safe_img.save(downscaled_path, format="PNG", icc_profile=None, optimize=True)
            return downscaled_path, downscaled
    except Exception as exc:
        if must_rasterize:
            raise OSError(f"rasterize cover failed for {cover_path}: {exc}") from exc
        shutil.copy2(cover_path, placeholder_path)
        return placeholder_path, False


def _extract_text_fields(
    *,
    rule_map: dict[str, list[ImportRule]],
    context: RuleContext,
) -> dict[str, str]:
    values: dict[str, str] = {}
    for field_name in ("title", "author", "series", "tag"):
        rules = rule_map.get(field_name, [])
        if not rules:
            continue
        result = apply_rule_chain(rules, context)
        if result.success and result.value.strip():
            values[field_name] = result.value.strip()
    return values


def _split_text_rule_tags(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").splitlines() if item.strip()]


_TEXT_AUTHOR_PLACEHOLDERS = {"unknown", "unkown", "未知", "未知作者", "none", "null", "n/a"}
_TEXT_AUTHOR_SEPARATOR_RE = re.compile(r"\s*(?:/|／|\||、|,|，|;|；)\s*")


def _clean_text_rule_author(value: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    parts = [part.strip() for part in _TEXT_AUTHOR_SEPARATOR_RE.split(raw) if part.strip()]
    if not parts:
        return None
    cleaned = [part for part in parts if part.strip().lower() not in _TEXT_AUTHOR_PLACEHOLDERS]
    if not cleaned:
        return None
    return " / ".join(cleaned)


def _emit_scan_progress(
    progress_cb: ScanProgressCallback | None,
    current: int,
    total: int,
    label: str,
    result: ScanResult,
) -> None:
    if progress_cb is None:
        return
    snapshot = result.to_summary()
    progress_cb(current, total, label, snapshot)


def _count_library_scan_files(roots: list[str], scan_depth: int) -> int:
    total = 0
    for raw_root in roots:
        root = Path(raw_root)
        if not root.exists() or not root.is_dir():
            continue
        try:
            total += sum(1 for _ in _iter_files_with_depth(root, scan_depth))
        except OSError:
            continue
    return total


def _count_text_scan_files(roots: list[TextScanRoot]) -> int:
    total = 0
    for root in roots:
        root_path = Path(str(root.path or ""))
        if not root_path.exists() or not root_path.is_dir():
            continue
        try:
            for _dir_path, _dir_names, file_names in os.walk(root_path):
                total += sum(1 for name in file_names if Path(name).suffix.lower() == TEXT_FILE_EXTENSION)
        except OSError:
            continue
    return total


def scan_comic_roots(
    repository: LibraryRepository,
    request: ComicScanRequest,
    progress_cb: ScanProgressCallback | None = None,
) -> ScanResult:
    result = ScanResult()
    max_depth = min(5, max(1, int(request.max_depth or 5)))
    placeholder_copy_enabled = bool(request.placeholder_copy_enabled)
    max_image_decode_bytes = max(1, int(request.max_image_decode_bytes or 0))
    title_conflict_policy = str(request.title_conflict_policy or COMIC_TITLE_CONFLICT_SKIP_INCOMING)
    if title_conflict_policy not in COMIC_TITLE_CONFLICT_POLICIES:
        title_conflict_policy = COMIC_TITLE_CONFLICT_SKIP_INCOMING
    encoding_preference = normalize_encoding_preference(request.encoding_preference)
    scanned_roots = [repository.normalize_path(path) for path in request.roots]
    removed_missing = _remove_missing_comics_in_scope(repository, scanned_roots)
    repository.backfill_comic_folder_modified_at()
    if removed_missing > 0:
        result.removed_missing_count += removed_missing
        result.removed_missing_comic_count += removed_missing
    existing_records = repository.list_comics_in_roots(scanned_roots)
    existing_by_path: dict[str, dict[str, Any]] = {
        str(record.get("path") or ""): record for record in existing_records if str(record.get("path") or "").strip()
    }

    for raw_root in scanned_roots:
        root = Path(raw_root)
        if not root.exists() or not root.is_dir():
            result.comic_errors.append(f"Comic root unavailable: {raw_root}")
            continue
        try:
            leaf_candidates, scanned_dir_count = _collect_leaf_comic_candidates(root, max_depth=max_depth)
        except OSError as exc:
            result.comic_errors.append(f"Comic root traversal failed for {raw_root}: {exc}")
            continue
        result.comic_scanned_dirs += scanned_dir_count
        total = len(leaf_candidates)
        for index, (folder_path, cover_path, image_count, folder_snapshot, folder_mtime, folder_modified_at) in enumerate(
            leaf_candidates,
            start=1,
        ):
            result.comic_detected_folders += 1
            normalized_folder = repository.normalize_path(folder_path)
            normalized_root = repository.normalize_path(root)
            normalized_cover = repository.normalize_path(cover_path)

            existing = existing_by_path.get(normalized_folder)
            existing_thumb = str(existing.get("thumbnail_path") or "") if isinstance(existing, dict) else ""
            existing_fingerprint = str(existing.get("cover_fingerprint") or "") if isinstance(existing, dict) else ""
            existing_snapshot = str(existing.get("folder_size_mtime") or "") if isinstance(existing, dict) else ""
            thumb_file = uri_to_path(existing_thumb)
            has_valid_thumb = bool(thumb_file and thumb_file.exists() and thumb_file.is_file())
            points_to_original = is_preview_variant_uri(
                existing_thumb,
                resource_type="comic",
                variant="original",
            )
            snapshot_unchanged = bool(existing) and existing_snapshot == folder_snapshot
            current_fingerprint = existing_fingerprint or None
            if snapshot_unchanged and has_valid_thumb and not points_to_original:
                need_regenerate = False
            else:
                try:
                    current_fingerprint = _cover_fingerprint(cover_path)
                except OSError as exc:
                    result.comic_errors.append(f"Comic cover stat failed for {normalized_cover}: {exc}")
                    current_fingerprint = None
                need_regenerate = (
                    existing is None
                    or not existing_thumb
                    or not has_valid_thumb
                    or points_to_original
                    or not current_fingerprint
                    or existing_fingerprint != current_fingerprint
                    or not snapshot_unchanged
                )

            thumbnail_path = existing_thumb or None
            if need_regenerate and placeholder_copy_enabled:
                placeholder_path = build_preview_path(
                    preview_root=repository.preview_dir,
                    resource_type="comic",
                    variant="original",
                    source_key=normalized_cover,
                    extension=cover_path.suffix,
                )
                try:
                    effective_placeholder_path, downscaled = _copy_or_downscale_comic_placeholder(
                        cover_path,
                        placeholder_path,
                        max_decode_bytes=max_image_decode_bytes,
                    )
                    thumbnail_path = effective_placeholder_path.resolve(strict=False).as_uri()
                    result.comic_placeholder_copied_count += 1
                    if downscaled:
                        result.comic_large_image_downscaled_count += 1
                except OSError as exc:
                    result.comic_errors.append(f"Comic placeholder copy failed for {normalized_cover}: {exc}")
                    thumbnail_path = existing_thumb or None

            if need_regenerate:
                result.comic_thumbnail_enqueued_count += 1

            if snapshot_unchanged and isinstance(existing, dict):
                info_text = str(existing.get("info_text") or "") or None
            else:
                info_text = _collect_comic_info_text(folder_path, preference=encoding_preference)
            payload = {
                "path": normalized_folder,
                "title": folder_path.name,
                "comic_root": normalized_root,
                "cover_image_path": normalized_cover,
                "thumbnail_path": thumbnail_path,
                "cover_fingerprint": current_fingerprint,
                "folder_size_mtime": folder_snapshot,
                "folder_mtime": folder_mtime,
                "folder_modified_at": folder_modified_at,
                "image_count": image_count,
                "info_text": info_text,
            }
            conflict = repository.find_comic_title_conflict(
                normalized_root,
                folder_path.name,
                normalized_folder,
            )
            if conflict:
                conflict_item = ScanConflict(
                    file_name=folder_path.name,
                    incoming_path=normalized_folder,
                    existing_path=str(conflict.get("path") or ""),
                    existing_title=str(conflict.get("title") or folder_path.name),
                )
                result.name_conflicts.append(conflict_item)
                if title_conflict_policy == COMIC_TITLE_CONFLICT_SKIP_INCOMING:
                    result.comic_errors.append(
                        f"Comic title conflict skipped (incoming): {normalized_folder} vs {conflict_item.existing_path}"
                    )
                    _emit_scan_progress(progress_cb, index, total, normalized_folder, result)
                    continue
                if title_conflict_policy == COMIC_TITLE_CONFLICT_PREFER_NEWER:
                    existing_mtime = max(
                        int(conflict.get("folder_modified_at") or 0),
                        int(conflict.get("folder_mtime") or 0),
                    )
                    incoming_mtime = max(int(folder_modified_at or 0), int(folder_mtime or 0))
                    if incoming_mtime <= existing_mtime:
                        result.comic_errors.append(
                            f"Comic title conflict kept existing (newer/equal): {conflict_item.existing_path}"
                        )
                        _emit_scan_progress(progress_cb, index, total, normalized_folder, result)
                        continue
                    old_id = int(conflict.get("id") or 0)
                    old_path = str(conflict.get("path") or "")
                    if old_id > 0:
                        repository.delete_comics_by_ids([old_id])
                    if old_path:
                        existing_by_path.pop(old_path, None)
                # keep_both: log conflict above, then upsert incoming as usual
            inserted = repository.upsert_comic(payload)
            if inserted:
                result.comic_added_count += 1
            else:
                result.comic_updated_count += 1
            existing_by_path[normalized_folder] = {
                "path": normalized_folder,
                "thumbnail_path": thumbnail_path,
                "cover_fingerprint": current_fingerprint,
                "folder_size_mtime": folder_snapshot,
                "folder_mtime": folder_mtime,
                "folder_modified_at": folder_modified_at,
                "info_text": info_text,
            }
            _emit_scan_progress(progress_cb, index, total, normalized_folder, result)

    if result.comic_large_image_downscaled_count > 0:
        result.warnings.append(
            {
                "code": "comic_large_image_downscaled",
                "count": result.comic_large_image_downscaled_count,
                "reason": "Some placeholder covers were downscaled to avoid Qt image allocation limits.",
            }
        )

    return result


def scan_text_roots(
    repository: LibraryRepository,
    request: TextScanRequest,
    progress_cb: ScanProgressCallback | None = None,
) -> ScanResult:
    result = ScanResult()
    preview_chars = max(100, int(request.preview_chars or 1200))
    hash_strategy: HashStrategy = request.hash_strategy
    encoding_preference = normalize_encoding_preference(request.encoding_preference)
    scanned_roots = [repository.normalize_path(item.path) for item in request.roots if str(item.path).strip()]
    total_files = _count_text_scan_files(request.roots)
    removed_missing = _remove_missing_books_in_scope(repository, scanned_roots, resource_type="text_novel")
    if removed_missing > 0:
        result.removed_missing_count += removed_missing
        result.removed_missing_book_count += removed_missing
    existing_by_path = repository.map_text_novels_for_scan(scanned_roots)

    for root in request.roots:
        normalized_root = repository.normalize_path(root.path)
        root_path = Path(normalized_root)
        if not root_path.exists() or not root_path.is_dir():
            result.text_errors.append(f"Text root unavailable: {normalized_root}")
            continue

        rule_map = _parse_rule_map(root.rules_json or "{}", result.text_errors, normalized_root)
        if "title" not in rule_map:
            rule_map["title"] = default_text_title_rule_chain()

        for dir_path, _dir_names, file_names in os.walk(root_path):
            current_dir = Path(dir_path)
            for name in sorted(file_names):
                file_path = current_dir / name
                if file_path.suffix.lower() != TEXT_FILE_EXTENSION:
                    continue

                result.text_scanned_files += 1
                normalized_path = repository.normalize_path(file_path)

                try:
                    fingerprints = compute_fingerprints(file_path, strategy=hash_strategy)
                except OSError as exc:
                    result.text_errors.append(f"Text fingerprint failed for {normalized_path}: {exc}")
                    _emit_scan_progress(progress_cb, result.text_scanned_files, total_files, normalized_path, result)
                    continue

                existing = existing_by_path.get(normalized_path)
                current_fp = fingerprints.value_for(hash_strategy)
                existing_fp = ""
                if isinstance(existing, dict):
                    if hash_strategy == "sha256":
                        existing_fp = str(existing.get("fingerprint_sha256") or "")
                    elif hash_strategy == "quick":
                        existing_fp = str(existing.get("fingerprint_quick") or "")
                    else:
                        existing_fp = str(existing.get("fingerprint_size_mtime") or "")
                if isinstance(existing, dict) and current_fp and existing_fp and current_fp == existing_fp:
                    result.skipped_unchanged_count += 1
                    _emit_scan_progress(progress_cb, result.text_scanned_files, total_files, normalized_path, result)
                    continue

                txt_first_line = _read_txt_first_line(file_path, preference=encoding_preference)
                txt_head_text = _read_txt_head_text(file_path, preview_chars, preference=encoding_preference)
                context = RuleContext(
                    file_path=normalized_path,
                    txt_first_line=txt_first_line,
                    txt_head_text=txt_head_text,
                )

                extracted = _extract_text_fields(rule_map=rule_map, context=context)
                title = extracted.get("title") or file_path.stem
                author = _clean_text_rule_author(extracted.get("author"))
                tags: list[str] = []
                if extracted.get("series"):
                    tags.append(f"series:{extracted['series']}")
                if extracted.get("tag"):
                    tags.extend(_split_text_rule_tags(extracted["tag"]))

                payload: dict[str, Any] = {
                    "path": normalized_path,
                    "file_name": file_name(file_path),
                    "extension": TEXT_FILE_EXTENSION,
                    "title": title,
                    "author": author,
                    "publisher": None,
                    "language": None,
                    "tags_json": json.dumps(tags, ensure_ascii=False),
                    "status": "UNREAD",
                    "resource_type": "text_novel",
                    "thumbnail_path": None,
                    "info_text": txt_head_text,
                    "fingerprint_sha256": fingerprints.sha256,
                    "fingerprint_size_mtime": fingerprints.size_mtime,
                    "fingerprint_quick": fingerprints.quick,
                }

                duplicate = repository.find_duplicate_name(payload["file_name"], TEXT_FILE_EXTENSION, normalized_path)
                if _cleanup_stale_duplicate_if_needed(repository, duplicate):
                    duplicate = None
                if duplicate:
                    result.name_conflicts.append(
                        ScanConflict(
                            file_name=payload["file_name"],
                            incoming_path=normalized_path,
                            existing_path=str(duplicate["path"]),
                            existing_title=(duplicate.get("title") or duplicate.get("file_name")),
                        )
                    )
                    _emit_scan_progress(progress_cb, result.text_scanned_files, total_files, normalized_path, result)
                    continue

                inserted = repository.upsert_book(payload)
                if inserted:
                    result.text_added_count += 1
                else:
                    result.text_updated_count += 1
                existing_by_path[normalized_path] = {
                    "path": normalized_path,
                    "fingerprint_sha256": fingerprints.sha256 or "",
                    "fingerprint_size_mtime": fingerprints.size_mtime or "",
                    "fingerprint_quick": fingerprints.quick or "",
                }
                _emit_scan_progress(progress_cb, result.text_scanned_files, total_files, normalized_path, result)
    return result


def scan_roots(
    repository: LibraryRepository,
    request: ScanRequest,
    progress_cb: ScanProgressCallback | None = None,
) -> ScanResult:
    result = ScanResult()
    scan_depth = min(3, max(1, request.scan_depth))
    hash_strategy: HashStrategy = request.hash_strategy
    scanned_roots = [repository.normalize_path(path) for path in request.roots]
    removed_missing = _remove_missing_books_in_scope(
        repository,
        scanned_roots,
        resource_type=None,
        exclude_text_novel=True,
    )
    if removed_missing > 0:
        result.removed_missing_count += removed_missing
        result.removed_missing_book_count += removed_missing
    pdf_backend_ok, pdf_backend_reason = _probe_pdf_backend()
    skipped_pdf_backend_count = 0
    total_files = _count_library_scan_files(scanned_roots, scan_depth)
    existing_by_path = repository.map_library_books_for_scan(scanned_roots)

    for raw_root in scanned_roots:
        root = Path(raw_root)
        if not root.exists() or not root.is_dir():
            result.errors.append(f"Scan root unavailable: {raw_root}")
            continue

        for file_path in _iter_files_with_depth(root, scan_depth):
            result.scanned_files += 1
            extension = extension_lower(file_path)
            if extension not in SUPPORTED_EXTENSIONS:
                result.ignored_unsupported += 1
                result.unsupported_files.append(str(file_path.resolve(strict=False)))
                _emit_scan_progress(progress_cb, result.scanned_files, total_files, str(file_path), result)
                continue

            normalized_path = repository.normalize_path(file_path)
            try:
                fingerprints = compute_fingerprints(file_path, strategy=hash_strategy)
            except OSError as exc:
                result.errors.append(f"Fingerprint failed for {normalized_path}: {exc}")
                _emit_scan_progress(progress_cb, result.scanned_files, total_files, normalized_path, result)
                continue

            existing = existing_by_path.get(normalized_path)
            current_fp = fingerprints.value_for(hash_strategy)
            existing_fp = ""
            if isinstance(existing, dict):
                if hash_strategy == "sha256":
                    existing_fp = str(existing.get("fingerprint_sha256") or "")
                elif hash_strategy == "quick":
                    existing_fp = str(existing.get("fingerprint_quick") or "")
                else:
                    existing_fp = str(existing.get("fingerprint_size_mtime") or "")
            existing_thumb = str(existing.get("thumbnail_path") or "") if isinstance(existing, dict) else ""
            thumb_file = uri_to_path(existing_thumb)
            has_valid_thumb = bool(thumb_file and thumb_file.exists() and thumb_file.is_file())
            if (
                isinstance(existing, dict)
                and current_fp
                and existing_fp
                and current_fp == existing_fp
                and has_valid_thumb
            ):
                result.skipped_unchanged_count += 1
                _emit_scan_progress(progress_cb, result.scanned_files, total_files, normalized_path, result)
                continue

            metadata = None
            should_skip_pdf_backend = extension == ".pdf" and not pdf_backend_ok
            if should_skip_pdf_backend:
                skipped_pdf_backend_count += 1
            else:
                try:
                    metadata = _extract_metadata_by_extension(file_path, extension)
                except Exception as exc:  # noqa: BLE001
                    result.errors.append(f"Metadata failed for {normalized_path}: {exc}")
                    metadata = None

            title = metadata.title if metadata and metadata.title else file_path.stem
            author = metadata.author if metadata else None
            publisher = metadata.publisher if metadata else None
            language = metadata.language if metadata else None
            tags = build_metadata_tags(metadata) if metadata else []

            thumb_out = _thumbnail_path_for(repository, normalized_path)
            thumbnail_path: str | None = None
            if not should_skip_pdf_backend:
                try:
                    thumbnail_path = _build_thumbnail_by_extension(
                        file_path=file_path,
                        extension=extension,
                        output_path=thumb_out,
                        title_fallback=title,
                    )
                except Exception as exc:  # noqa: BLE001
                    result.errors.append(f"Thumbnail failed for {normalized_path}: {exc}")

            payload = _build_payload(
                normalized_path=normalized_path,
                file_path=file_path,
                extension=extension,
                title=title,
                author=author,
                publisher=publisher,
                language=language,
                tags=tags,
                thumbnail_path=thumbnail_path,
                fingerprints=fingerprints,
            )

            duplicate = repository.find_duplicate_name(payload["file_name"] or "", extension, normalized_path)
            if _cleanup_stale_duplicate_if_needed(repository, duplicate):
                duplicate = None
            if duplicate:
                result.name_conflicts.append(
                    ScanConflict(
                        file_name=payload["file_name"] or file_name(file_path),
                        incoming_path=normalized_path,
                        existing_path=str(duplicate["path"]),
                        existing_title=(duplicate.get("title") or duplicate.get("file_name")),
                    )
                )
                _emit_scan_progress(progress_cb, result.scanned_files, total_files, normalized_path, result)
                continue

            inserted = repository.upsert_book(payload)
            if inserted:
                result.added_count += 1
            else:
                result.updated_count += 1
            prior = existing if isinstance(existing, dict) else {}
            existing_by_path[normalized_path] = {
                "path": normalized_path,
                "thumbnail_path": thumbnail_path,
                "fingerprint_sha256": fingerprints.sha256 or str(prior.get("fingerprint_sha256") or ""),
                "fingerprint_size_mtime": fingerprints.size_mtime or str(prior.get("fingerprint_size_mtime") or ""),
                "fingerprint_quick": fingerprints.quick or str(prior.get("fingerprint_quick") or ""),
            }
            _emit_scan_progress(progress_cb, result.scanned_files, total_files, normalized_path, result)

    if skipped_pdf_backend_count > 0:
        result.warnings.append(
            {
                "code": "pdf_backend_unavailable",
                "count": skipped_pdf_backend_count,
                "reason": pdf_backend_reason or "Unknown fitz import error.",
            }
        )

    return result
