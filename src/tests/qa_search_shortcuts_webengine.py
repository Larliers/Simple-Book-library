"""Offscreen Qt WebEngine check for current-page search and navigation shortcuts."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

from PySide6.QtCore import QEventLoop, QTimer, QUrl, Qt
from PySide6.QtTest import QTest
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bookhub.i18n import language_manager
from bookhub.library.repository import LibraryRepository
from bookhub.ui.web_bridge import UiBridge
from bookhub.ui.web_scheme import AppSchemeHandler, register_app_scheme


def evaluate(view: QWebEngineView, script: str):
    loop = QEventLoop()
    result = []
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(10000)
    view.page().runJavaScript(script, 0, lambda value: (result.append(value), loop.quit()))
    loop.exec()
    if not result:
        raise TimeoutError(f"JavaScript timed out: {script[:100]}")
    return result[0]


def wait_for(app: QApplication, view: QWebEngineView, expression: str) -> None:
    deadline = time.monotonic() + 15
    while not evaluate(view, f"({expression}) ? 1 : 0"):
        if time.monotonic() > deadline:
            raise TimeoutError(f"{expression}: {evaluate(view, 'JSON.stringify({page: State.currentPage, query: State.searchQuery, focus: document.activeElement?.id})')}")
        app.processEvents()
        time.sleep(0.02)


def press(view: QWebEngineView, key: Qt.Key, modifiers: Qt.KeyboardModifier) -> None:
    view.activateWindow()
    view.setFocus()
    QTest.qWait(80)
    QTest.keyClick(view.focusProxy() or view, key, modifiers)


def main() -> None:
    register_app_scheme()
    app = QApplication([])
    language_manager.set_language("zh-cn")
    with tempfile.TemporaryDirectory(prefix="search_shortcuts_webengine_") as directory:
        root = Path(directory)
        book_path = root / "Demo.epub"
        book_path.write_bytes(b"demo")
        repo = LibraryRepository(root / "library.db", root / "scan_report.json")
        repo.upsert_book({
            "path": str(book_path), "file_name": book_path.name,
            "extension": ".epub", "title": "Demo Book",
            "resource_type": "book", "tags_json": "[]",
        })
        view = QWebEngineView()
        view.resize(1100, 760)
        allowed: set[str] = set()
        handler = AppSchemeHandler(allowed, view)
        view.page().profile().installUrlSchemeHandler(b"app", handler)
        channel = QWebChannel(view)
        bridge = UiBridge(repo, allowed, view)
        channel.registerObject("bridge", bridge)
        view.page().setWebChannel(channel)
        loaded = []
        view.loadFinished.connect(lambda ok: loaded.append(ok))
        view.show()
        view.load(QUrl("app://app/index.html"))
        deadline = time.monotonic() + 15
        while not loaded:
            if time.monotonic() > deadline:
                raise TimeoutError("Page load timed out")
            app.processEvents()
            time.sleep(0.02)
        if not loaded[0]:
            raise RuntimeError("Page load failed")
        wait_for(app, view, "Object.keys(State.pages).length > 0 && State.currentPage === 'library'")

        for skin in ("glass", "vaporwave"):
            evaluate(view, f"applyUiSkin({json.dumps(skin)}); true")
            wait_for(app, view, f"State.uiSkin === {json.dumps(skin)} && !State.uiSkinPending")
            evaluate(view, "selectPage('text_novel'); selectPage('library'); true")
            wait_for(app, view, "State.currentPage === 'library' && !State.renderTimer")
            evaluate(view, """(() => {
                const input = document.getElementById('searchInput');
                input.value = 'Demo';
                input.dispatchEvent(new Event('input', { bubbles: true }));
                document.getElementById('scanBtn').focus();
                return true;
            })()""")
            wait_for(app, view, "State.searchQuery === 'Demo' && State.pages.library.items.length === 1")

            press(view, Qt.Key_F, Qt.ControlModifier)
            wait_for(app, view, "document.activeElement?.id === 'searchInput' && document.getElementById('searchInput').selectionStart === 0 && document.getElementById('searchInput').selectionEnd === 4")
            for digit, page in ((Qt.Key_2, "text_novel"), (Qt.Key_3, "comic"), (Qt.Key_1, "library")):
                evaluate(view, "document.getElementById('scanBtn').focus(); true")
                press(view, digit, Qt.AltModifier)
                wait_for(app, view, f"State.currentPage === {json.dumps(page)}")
            wait_for(app, view, "document.getElementById('searchInput').value === 'Demo' && State.searchQuery === 'Demo'")
            press(view, Qt.Key_F, Qt.ControlModifier)
            wait_for(app, view, "document.activeElement?.id === 'searchInput'")
            press(view, Qt.Key_F, Qt.ControlModifier | Qt.ShiftModifier)
            wait_for(app, view, "State.searchQuery === '' && document.getElementById('searchInput').value === '' && State.pages.library.items.length === 1 && !State.renderTimer")

            evaluate(view, "selectPage('settings'); document.getElementById('scanBtn').focus(); true")
            wait_for(app, view, "State.currentPage === 'settings'")
            press(view, Qt.Key_F, Qt.ControlModifier)
            if not evaluate(view, "State.currentPage === 'settings' && document.activeElement?.id !== 'searchInput' ? 1 : 0"):
                raise AssertionError(f"{skin}: search shortcut changed an unavailable page")
            print(f"{skin}: search focus/select, clear, navigation and unavailable page OK")

        view.close()
        print("SEARCH_SHORTCUTS_WEBENGINE_QA_OK")


if __name__ == "__main__":
    main()
