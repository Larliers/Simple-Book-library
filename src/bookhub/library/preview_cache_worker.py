from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from bookhub.library.preview_cache_migrate import apply_preview_cache_change
from bookhub.library.repository import LibraryRepository


class PreviewCacheMigrateWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        db_path: str | Path,
        scan_report_path: str | Path,
        preview_dir: str | Path,
        new_path: str,
        mode: str,
    ) -> None:
        super().__init__()
        self._db_path = Path(db_path)
        self._scan_report_path = Path(scan_report_path)
        self._preview_dir = Path(preview_dir)
        self._new_path = str(new_path or "")
        self._mode = str(mode or "migrate")

    def run(self) -> None:
        try:
            repository = LibraryRepository(
                self._db_path,
                self._scan_report_path,
                preview_dir=self._preview_dir,
            )
            result = apply_preview_cache_change(repository, self._new_path, self._mode)
            self.completed.emit(result.to_summary())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
