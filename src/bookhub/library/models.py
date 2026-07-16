from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

HASH_STRATEGY_SHA256 = "sha256"
HASH_STRATEGY_SIZE_MTIME = "size_mtime"
HASH_STRATEGY_QUICK = "quick"
HASH_STRATEGIES = {
    HASH_STRATEGY_SHA256,
    HASH_STRATEGY_SIZE_MTIME,
    HASH_STRATEGY_QUICK,
}
HashStrategy = Literal["sha256", "size_mtime", "quick"]
ThumbnailTaskKind = Literal["cleanup", "regenerate", "regenerate_missing"]
ScanScope = Literal["library", "comic", "text", "all"]
ThumbnailScope = Literal["library", "comic"]

SUPPORTED_EXTENSIONS = (".pdf", ".epub")
COMIC_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
TEXT_FILE_EXTENSION = ".txt"
DEFAULT_TEXT_PREVIEW_CHARS = 1200
TEXT_PREVIEW_CHAR_OPTIONS = (600, 1200, 2000, 4000)


@dataclass(slots=True)
class ParsedMetadata:
    title: str | None = None
    author: str | None = None
    publisher: str | None = None
    language: str | None = None


@dataclass(slots=True)
class FingerprintBundle:
    sha256: str
    size_mtime: str
    quick: str

    def value_for(self, strategy: HashStrategy) -> str:
        if strategy == HASH_STRATEGY_SHA256:
            return self.sha256
        if strategy == HASH_STRATEGY_QUICK:
            return self.quick
        return self.size_mtime


@dataclass(slots=True)
class ScanConflict:
    file_name: str
    incoming_path: str
    existing_path: str
    existing_title: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "file_name": self.file_name,
            "incoming_path": self.incoming_path,
            "existing_path": self.existing_path,
            "existing_title": self.existing_title,
        }


@dataclass(slots=True)
class ScanRequest:
    roots: list[str]
    scan_depth: int
    hash_strategy: HashStrategy
    trigger: str = "manual"


@dataclass(slots=True)
class ComicScanRequest:
    roots: list[str]
    max_depth: int = 5
    placeholder_copy_enabled: bool = True
    max_image_decode_bytes: int = 256 * 1024 * 1024


@dataclass(slots=True)
class TextScanRoot:
    path: str
    rules_json: str | None = None


@dataclass(slots=True)
class TextScanRequest:
    roots: list[TextScanRoot]
    preview_chars: int = DEFAULT_TEXT_PREVIEW_CHARS


@dataclass(slots=True)
class ScanResult:
    added_count: int = 0
    updated_count: int = 0
    ignored_unsupported: int = 0
    skipped_unchanged_count: int = 0
    removed_missing_count: int = 0
    removed_missing_book_count: int = 0
    removed_missing_comic_count: int = 0
    scanned_files: int = 0
    unsupported_files: list[str] = field(default_factory=list)
    name_conflicts: list[ScanConflict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[dict[str, object]] = field(default_factory=list)
    comic_added_count: int = 0
    comic_updated_count: int = 0
    comic_scanned_dirs: int = 0
    comic_detected_folders: int = 0
    comic_errors: list[str] = field(default_factory=list)
    comic_placeholder_copied_count: int = 0
    comic_thumbnail_enqueued_count: int = 0
    comic_thumbnail_workers_used: int = 0
    comic_large_image_downscaled_count: int = 0
    text_added_count: int = 0
    text_updated_count: int = 0
    text_scanned_files: int = 0
    text_errors: list[str] = field(default_factory=list)

    def to_summary(self) -> dict[str, object]:
        return {
            "added_count": self.added_count,
            "updated_count": self.updated_count,
            "ignored_unsupported": self.ignored_unsupported,
            "skipped_unchanged_count": self.skipped_unchanged_count,
            "name_conflicts": [item.as_dict() for item in self.name_conflicts],
            "removed_missing_count": self.removed_missing_count,
            "removed_missing_book_count": self.removed_missing_book_count,
            "removed_missing_comic_count": self.removed_missing_comic_count,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "unsupported_files": list(self.unsupported_files),
            "scanned_files": self.scanned_files,
            "comic_added_count": self.comic_added_count,
            "comic_updated_count": self.comic_updated_count,
            "comic_scanned_dirs": self.comic_scanned_dirs,
            "comic_detected_folders": self.comic_detected_folders,
            "comic_errors": list(self.comic_errors),
            "comic_placeholder_copied_count": self.comic_placeholder_copied_count,
            "comic_thumbnail_enqueued_count": self.comic_thumbnail_enqueued_count,
            "comic_thumbnail_workers_used": self.comic_thumbnail_workers_used,
            "comic_large_image_downscaled_count": self.comic_large_image_downscaled_count,
            "text_added_count": self.text_added_count,
            "text_updated_count": self.text_updated_count,
            "text_scanned_files": self.text_scanned_files,
            "text_errors": list(self.text_errors),
        }


@dataclass(slots=True)
class ThumbnailTaskResult:
    task_kind: ThumbnailTaskKind
    task_scope: ThumbnailScope = "library"
    total: int = 0
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def to_summary(self) -> dict[str, object]:
        return {
            "task_kind": self.task_kind,
            "task_scope": self.task_scope,
            "total": self.total,
            "succeeded": self.succeeded,
            "skipped": self.skipped,
            "failed": self.failed,
            "errors": list(self.errors),
        }
