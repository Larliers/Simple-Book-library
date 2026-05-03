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
ThumbnailTaskKind = Literal["cleanup", "regenerate"]

SUPPORTED_EXTENSIONS = (".pdf", ".epub")
COMIC_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


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


@dataclass(slots=True)
class ScanResult:
    added_count: int = 0
    updated_count: int = 0
    ignored_unsupported: int = 0
    restored_from_missed: int = 0
    moved_to_missed_count: int = 0
    scanned_files: int = 0
    unsupported_files: list[str] = field(default_factory=list)
    name_conflicts: list[ScanConflict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    comic_added_count: int = 0
    comic_updated_count: int = 0
    comic_scanned_dirs: int = 0
    comic_detected_folders: int = 0
    comic_errors: list[str] = field(default_factory=list)

    def to_summary(self) -> dict[str, object]:
        return {
            "added_count": self.added_count,
            "updated_count": self.updated_count,
            "ignored_unsupported": self.ignored_unsupported,
            "name_conflicts": [item.as_dict() for item in self.name_conflicts],
            "restored_from_missed": self.restored_from_missed,
            "moved_to_missed_count": self.moved_to_missed_count,
            "errors": list(self.errors),
            "unsupported_files": list(self.unsupported_files),
            "scanned_files": self.scanned_files,
            "comic_added_count": self.comic_added_count,
            "comic_updated_count": self.comic_updated_count,
            "comic_scanned_dirs": self.comic_scanned_dirs,
            "comic_detected_folders": self.comic_detected_folders,
            "comic_errors": list(self.comic_errors),
        }


@dataclass(slots=True)
class ThumbnailTaskResult:
    task_kind: ThumbnailTaskKind
    total: int = 0
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def to_summary(self) -> dict[str, object]:
        return {
            "task_kind": self.task_kind,
            "total": self.total,
            "succeeded": self.succeeded,
            "skipped": self.skipped,
            "failed": self.failed,
            "errors": list(self.errors),
        }
