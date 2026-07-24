from __future__ import annotations

import json

from PySide6.QtCore import QThread, Signal

from bookhub.library.update_checker import check_for_update
from bookhub.version import APP_VERSION


class UpdateCheckWorker(QThread):
    finished = Signal(str)

    def __init__(self, current_version: str = APP_VERSION, parent=None) -> None:
        super().__init__(parent)
        self._current_version = current_version

    def run(self) -> None:
        result = check_for_update(self._current_version)
        self.finished.emit(json.dumps(result, ensure_ascii=False))
