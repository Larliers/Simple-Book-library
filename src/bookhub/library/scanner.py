from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

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
from bookhub.library.models import (
    SUPPORTED_EXTENSIONS,
    HashStrategy,
    ScanConflict,
    ScanRequest,
    ScanResult,
)
from bookhub.library.repository import LibraryRepository


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
    token = hashlib.sha1(normalized_path.encode("utf-8")).hexdigest()  # noqa: S324
    return repo.preview_dir / f"{token}.png"


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


def scan_roots(repository: LibraryRepository, request: ScanRequest) -> ScanResult:
    result = ScanResult()
    scan_depth = min(3, max(1, request.scan_depth))
    hash_strategy: HashStrategy = request.hash_strategy
    scanned_roots = [repository.normalize_path(path) for path in request.roots]

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
                continue

            normalized_path = repository.normalize_path(file_path)
            try:
                fingerprints = compute_fingerprints(file_path)
            except OSError as exc:
                result.errors.append(f"Fingerprint failed for {normalized_path}: {exc}")
                continue

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

            thumb_file = _thumbnail_path_for(repository, normalized_path)
            thumbnail_path: str | None = None
            try:
                thumbnail_path = _build_thumbnail_by_extension(
                    file_path=file_path,
                    extension=extension,
                    output_path=thumb_file,
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

            fingerprint_value = fingerprints.value_for(hash_strategy)
            missed_match = repository.find_missing_by_fingerprint(hash_strategy, fingerprint_value)
            if missed_match:
                repository.restore_missing_book(int(missed_match["id"]), payload)
                result.restored_from_missed += 1
                continue

            duplicate = repository.find_duplicate_name(payload["file_name"] or "", extension, normalized_path)
            if duplicate:
                result.name_conflicts.append(
                    ScanConflict(
                        file_name=payload["file_name"] or file_name(file_path),
                        incoming_path=normalized_path,
                        existing_path=str(duplicate["path"]),
                        existing_title=(duplicate.get("title") or duplicate.get("file_name")),
                    )
                )
                continue

            inserted = repository.upsert_book(payload)
            if inserted:
                result.added_count += 1
            else:
                result.updated_count += 1

    return result
