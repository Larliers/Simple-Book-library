from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from bookhub.library.repository import LibraryRepository
from bookhub.library.thumbnail_tasks import (
    cleanup_comic_thumbnails,
    cleanup_library_thumbnails,
    regenerate_comic_thumbnails,
    regenerate_library_thumbnails,
)


class ThumbnailTaskWorker(QThread):
    progress = Signal(int, int, str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        db_path: str | Path,
        scan_report_path: str | Path,
        task_kind: str,
        task_scope: str,
    ) -> None:
        super().__init__()
        self._db_path = Path(db_path)
        self._scan_report_path = Path(scan_report_path)
        self._task_kind = task_kind
        self._task_scope = task_scope

    def run(self) -> None:
        try:
            repository = LibraryRepository(self._db_path, self._scan_report_path)
            progress_cb = lambda current, total, label: self.progress.emit(current, total, label)
            if self._task_scope == "library":
                if self._task_kind == "cleanup":
                    result = cleanup_library_thumbnails(repository, progress_cb=progress_cb)
                elif self._task_kind == "regenerate":
                    result = regenerate_library_thumbnails(repository=repository, progress_cb=progress_cb)
                else:
                    raise RuntimeError(f"Unsupported thumbnail task: {self._task_kind}")
            elif self._task_scope == "comic":
                if self._task_kind == "cleanup":
                    result = cleanup_comic_thumbnails(repository, progress_cb=progress_cb)
                elif self._task_kind == "regenerate":
                    result = regenerate_comic_thumbnails(repository=repository, progress_cb=progress_cb)
                else:
                    raise RuntimeError(f"Unsupported thumbnail task: {self._task_kind}")
            else:
                raise RuntimeError(f"Unsupported thumbnail scope: {self._task_scope}")
            self.completed.emit(result.to_summary())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
