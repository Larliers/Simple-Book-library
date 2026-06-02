from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from bookhub.ui.app_window import AppWindow
from bookhub.ui.resources.assets import load_asset_icon


def _check_pymupdf() -> int:
    try:
        import fitz  # type: ignore[import-not-found]

        doc = fitz.open()
        page = doc.new_page()
        pixmap = page.get_pixmap()
        return 0 if pixmap.width > 0 and pixmap.height > 0 else 1
    except Exception:
        return 1


def main() -> int:
    if "--check-pymupdf" in sys.argv:
        return _check_pymupdf()

    app = QApplication(sys.argv)
    app.setWindowIcon(load_asset_icon("app_icon_bookcase.ico"))
    window = AppWindow()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

