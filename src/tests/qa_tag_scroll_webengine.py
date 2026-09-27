"""Offscreen Qt WebEngine check for Tag Manager directory scroll restoration."""
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

from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

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
        raise TimeoutError("JavaScript result timed out")
    return result[0]


def wait_for(app: QApplication, view: QWebEngineView, expression: str) -> None:
    deadline = time.monotonic() + 15
    while not evaluate(view, f"({expression}) ? 1 : 0"):
        if time.monotonic() > deadline:
            state = evaluate(view, "JSON.stringify({ready:document.readyState, pages:typeof State === 'undefined' ? -1 : Object.keys(State.pages).length, bridge:typeof qt})")
            raise TimeoutError(f"{expression}: {state}")
        app.processEvents()
        time.sleep(0.02)


def catalog_position(view: QWebEngineView) -> int:
    return int(evaluate(view, "document.getElementById('contentArea').scrollTop"))


def assert_position(view: QWebEngineView, expected: int, label: str) -> None:
    actual = catalog_position(view)
    if abs(actual - expected) > 1:
        raise AssertionError(f"{label}: expected {expected}px, got {actual}px")


def wait_for_catalog(app: QApplication, view: QWebEngineView, count: int) -> None:
    wait_for(app, view, f"State.currentPage === 'tag_manager' && !State.tagDetail && !State.tagLoading && !State.renderTimer && document.querySelectorAll('.tag-link').length === {count}")


def open_first_tag(app: QApplication, view: QWebEngineView) -> None:
    evaluate(view, "document.querySelector('.tag-link').click(); true")
    wait_for(app, view, "State.tagDetail && !State.tagLoading && document.body.dataset.pageMode === 'tag_detail' && !State.renderTimer")


def main() -> None:
    register_app_scheme()
    app = QApplication([])
    language_manager.set_language("zh-cn")
    with tempfile.TemporaryDirectory(prefix="tag_scroll_webengine_") as directory:
        root = Path(directory)
        repo = LibraryRepository(root / "library.db", root / "scan_report.json")
        for number in range(240):
            repo.upsert_book({
                "path": f"C:/demo/{number:03d}.epub", "file_name": f"{number:03d}.epub",
                "extension": ".epub", "title": f"Demo {number:03d}",
                "resource_type": "book", "tags_json": json.dumps([f"Tag {number:03d}"]),
            })
        view = QWebEngineView()
        view.resize(1100, 850)
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
        wait_for(app, view, "Object.keys(State.pages).length > 0")

        for skin in ("glass", "vaporwave"):
            evaluate(view, f"applyUiSkin({json.dumps(skin)}); true")
            wait_for(app, view, f"State.uiSkin === {json.dumps(skin)} && !State.uiSkinPending")
            evaluate(view, "selectPage('tag_manager'); true")
            wait_for_catalog(app, view, 240)
            position = int(evaluate(view, "document.getElementById('contentArea').scrollTop = 600; document.getElementById('contentArea').scrollTop"))
            if position < 500:
                raise AssertionError(f"Directory is too short to test scrolling: {position}px")

            open_first_tag(app, view)
            evaluate(view, "document.querySelector('#pageHeadTools button').click(); true")
            wait_for_catalog(app, view, 240)
            assert_position(view, position, f"{skin} Back button")

            evaluate(view, "selectPage('library'); true")
            wait_for(app, view, "State.currentPage === 'library' && !State.renderTimer")
            evaluate(view, "selectPage('tag_manager'); true")
            wait_for_catalog(app, view, 240)
            assert_position(view, position, f"{skin} sidebar return")

            open_first_tag(app, view)
            evaluate(view, "State.settings.shortcutBindings.exit_collection = 'MouseBack'; dispatchShortcutInput('MouseBack')")
            wait_for_catalog(app, view, 240)
            assert_position(view, position, f"{skin} shortcut Back")

            evaluate(view, "document.getElementById('contentArea').scrollTop = 450; setTagOrder('desc'); true")
            wait_for_catalog(app, view, 240)
            assert_position(view, 0, f"{skin} sorting")

            evaluate(view, "document.getElementById('contentArea').scrollTop = 450; setTagManagerScope('library', false); true")
            wait_for_catalog(app, view, 0)
            assert_position(view, 0, f"{skin} shorter directory")
            print(f"{skin}: Back, shortcut, sidebar, sort and shorter directory OK")
            evaluate(view, "setTagManagerScope('library', true); setTagOrder('asc'); true")
            wait_for_catalog(app, view, 240)

        view.close()
        print("TAG_SCROLL_WEBENGINE_QA_OK")


if __name__ == "__main__":
    main()
