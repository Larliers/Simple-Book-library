from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from bookhub.library.models import (
    HASH_STRATEGY_SIZE_MTIME,
    ScanRequest,
)
from bookhub.library.repository import LibraryRepository
from bookhub.library.scanner import scan_roots


class ScanWorker(QThread):
    scan_completed = Signal(object)
    scan_failed = Signal(str)

    def __init__(
        self,
        db_path: str | Path,
        scan_report_path: str | Path,
        roots: list[str],
        scan_depth: int,
        hash_strategy: str,
        trigger: str,
    ) -> None:
        super().__init__()
        self._db_path = Path(db_path)
        self._scan_report_path = Path(scan_report_path)
        self._roots = list(roots)
        self._scan_depth = scan_depth
        self._hash_strategy = (
            hash_strategy
            if hash_strategy in {"sha256", "size_mtime", "quick"}
            else HASH_STRATEGY_SIZE_MTIME
        )
        self._trigger = trigger

    def run(self) -> None:
        try:
            repository = LibraryRepository(self._db_path, self._scan_report_path)
            request = ScanRequest(
                roots=self._roots,
                scan_depth=self._scan_depth,
                hash_strategy=self._hash_strategy,  # type: ignore[arg-type]
                trigger=self._trigger,
            )
            result = scan_roots(repository, request)
            summary = result.to_summary()
            summary["trigger"] = self._trigger
            repository.write_scan_report(summary)
            repository.record_scan_event(self._trigger, summary)
            self.scan_completed.emit(summary)
        except Exception as exc:  # noqa: BLE001
            self.scan_failed.emit(str(exc))
