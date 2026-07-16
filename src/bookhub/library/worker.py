from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from bookhub.library.models import (
    HASH_STRATEGY_SIZE_MTIME,
    ComicScanRequest,
    ScanRequest,
    TextScanRequest,
    TextScanRoot,
)
from bookhub.library.repository import LibraryRepository
from bookhub.library.scanner import scan_comic_roots, scan_roots, scan_text_roots


class ScanWorker(QThread):
    scan_completed = Signal(object)
    scan_failed = Signal(str)
    progress = Signal(int, int, str, object)

    def __init__(
        self,
        db_path: str | Path,
        scan_report_path: str | Path,
        roots: list[str],
        comic_roots: list[str],
        text_roots: list[dict[str, str]],
        text_preview_chars: int,
        scan_depth: int,
        hash_strategy: str,
        comic_placeholder_copy_enabled: bool,
        comic_thumbnail_workers_used: int,
        trigger: str,
        scope: str = "all",
    ) -> None:
        super().__init__()
        self._db_path = Path(db_path)
        self._scan_report_path = Path(scan_report_path)
        self._roots = list(roots)
        self._comic_roots = list(comic_roots)
        self._text_roots = list(text_roots)
        self._text_preview_chars = int(text_preview_chars)
        self._scan_depth = scan_depth
        self._hash_strategy = (
            hash_strategy
            if hash_strategy in {"sha256", "size_mtime", "quick"}
            else HASH_STRATEGY_SIZE_MTIME
        )
        self._comic_placeholder_copy_enabled = bool(comic_placeholder_copy_enabled)
        self._comic_thumbnail_workers_used = max(1, int(comic_thumbnail_workers_used))
        self._trigger = trigger
        self._scope = str(scope or "all").strip().lower()

    def run(self) -> None:
        try:
            repository = LibraryRepository(self._db_path, self._scan_report_path)
            progress_cb = lambda current, total, label, snapshot: self.progress.emit(
                int(current),
                int(total),
                str(label),
                dict(snapshot),
            )
            request = ScanRequest(
                roots=self._roots,
                scan_depth=self._scan_depth,
                hash_strategy=self._hash_strategy,  # type: ignore[arg-type]
                trigger=self._trigger,
            )
            if self._scope in {"all", "library"}:
                result = scan_roots(repository, request, progress_cb=progress_cb)
            else:
                from bookhub.library.models import ScanResult

                result = ScanResult()

            if self._scope in {"all", "comic"}:
                comic_request = ComicScanRequest(
                    roots=self._comic_roots,
                    max_depth=5,
                    placeholder_copy_enabled=self._comic_placeholder_copy_enabled,
                )
                comic_result = scan_comic_roots(repository, comic_request, progress_cb=progress_cb)
            else:
                from bookhub.library.models import ScanResult

                comic_result = ScanResult()

            if self._scope in {"all", "text"}:
                text_request = TextScanRequest(
                    roots=[
                        TextScanRoot(path=str(item.get("path") or ""), rules_json=str(item.get("rules_json") or "{}"))
                        for item in self._text_roots
                        if str(item.get("path") or "").strip()
                    ],
                    preview_chars=self._text_preview_chars,
                )
                text_result = scan_text_roots(repository, text_request, progress_cb=progress_cb)
            else:
                from bookhub.library.models import ScanResult

                text_result = ScanResult()
            summary = result.to_summary()
            comic_summary = comic_result.to_summary()
            text_summary = text_result.to_summary()
            summary["comic_added_count"] = int(comic_summary.get("comic_added_count", 0) or 0)
            summary["comic_updated_count"] = int(comic_summary.get("comic_updated_count", 0) or 0)
            summary["comic_scanned_dirs"] = int(comic_summary.get("comic_scanned_dirs", 0) or 0)
            summary["comic_detected_folders"] = int(comic_summary.get("comic_detected_folders", 0) or 0)
            summary["comic_errors"] = list(comic_summary.get("comic_errors", []))
            summary["comic_placeholder_copied_count"] = int(comic_summary.get("comic_placeholder_copied_count", 0) or 0)
            summary["comic_thumbnail_enqueued_count"] = int(comic_summary.get("comic_thumbnail_enqueued_count", 0) or 0)
            summary["comic_thumbnail_workers_used"] = self._comic_thumbnail_workers_used
            summary["comic_large_image_downscaled_count"] = int(
                comic_summary.get("comic_large_image_downscaled_count", 0) or 0
            )
            summary["comic_thumbnail_downscaled_count"] = summary["comic_large_image_downscaled_count"]
            merged_conflicts = list(summary.get("name_conflicts", []))
            merged_conflicts.extend(list(text_summary.get("name_conflicts", [])))
            summary["name_conflicts"] = merged_conflicts
            summary["text_added_count"] = int(text_summary.get("text_added_count", 0) or 0)
            summary["text_updated_count"] = int(text_summary.get("text_updated_count", 0) or 0)
            summary["text_scanned_files"] = int(text_summary.get("text_scanned_files", 0) or 0)
            summary["text_scanned_count"] = summary["text_scanned_files"]
            summary["text_errors"] = list(text_summary.get("text_errors", []))
            summary["ignored_unsupported_count"] = int(summary.get("ignored_unsupported", 0) or 0)
            merged_warnings = list(summary.get("warnings", []))
            merged_warnings.extend(list(comic_summary.get("warnings", [])))
            merged_warnings.extend(list(text_summary.get("warnings", [])))
            summary["warnings"] = merged_warnings
            summary["removed_missing_count"] = int(summary.get("removed_missing_count", 0) or 0) + int(
                comic_summary.get("removed_missing_count", 0) or 0
            ) + int(text_summary.get("removed_missing_count", 0) or 0)
            summary["removed_missing_book_count"] = int(summary.get("removed_missing_book_count", 0) or 0) + int(
                text_summary.get("removed_missing_book_count", 0) or 0
            )
            summary["removed_missing_comic_count"] = int(comic_summary.get("removed_missing_comic_count", 0) or 0)
            summary["trigger"] = self._trigger
            summary["scope"] = self._scope
            repository.write_scan_report(summary)
            repository.record_scan_event(self._trigger, summary)
            self.scan_completed.emit(summary)
        except Exception as exc:  # noqa: BLE001
            self.scan_failed.emit(str(exc))
