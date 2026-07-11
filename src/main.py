from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication

from bookhub.ui.resources.assets import load_asset_icon
from bookhub.ui.web_scheme import register_app_scheme


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

    # WebEngine requires shared OpenGL contexts and the custom scheme to be
    # registered before the QApplication is instantiated.
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    register_app_scheme()

    app = QApplication(sys.argv)
    app.setWindowIcon(load_asset_icon("app_icon_bookcase.ico"))

    from bookhub.ui.web_window import WebAppWindow

    window = WebAppWindow()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
