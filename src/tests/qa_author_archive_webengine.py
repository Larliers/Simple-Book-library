"""Manual offscreen Qt WebEngine check for the Auto Archive settings page."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

from PySide6.QtCore import QEventLoop, QTimer, QUrl, Qt
from PySide6.QtTest import QTest
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


def pump(app: QApplication, predicate, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise TimeoutError("WebEngine did not reach the expected state")
        app.processEvents()
        time.sleep(0.02)


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


def main() -> None:
    register_app_scheme()
    app = QApplication([])
    language_manager.set_language("zh-cn")
    with tempfile.TemporaryDirectory(prefix="author_archive_webengine_") as directory:
        root = Path(directory)
        repo = LibraryRepository(root / "library.db", root / "scan_report.json")
        for number in range(23):
            author = "Alice" if number < 21 else f"Author {number}"
            repo.upsert_book({"path": f"C:/novels/{number}.txt", "file_name": f"{number}.txt",
                              "extension": ".txt", "title": f"Novel {number}",
                              "resource_type": "text_novel", "author": author, "tags_json": "[]"})
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
        pump(app, lambda: bool(loaded))
        if not loaded[0]:
            raise RuntimeError("Page load failed")
        pump(app, lambda: evaluate(view, "Object.keys(State.pages).length"))
        evaluate(view, "selectPage('novel_collections'); true")
        pump(app, lambda: evaluate(view, "document.querySelector('#pageHeadTools button')?.textContent === '自动归档' ? 1 : 0"))
        evaluate(view, "document.querySelector('#pageHeadTools button').click(); true")
        pump(app, lambda: evaluate(view, "State.archivePreset.loaded && document.querySelector('.archive-settings-card') ? 1 : 0"))
        if not evaluate(view, "State.archivePreset.origin === 'novel_collections' && document.querySelector('.archive-settings-card button')?.textContent === '返回小说合集' ? 1 : 0"):
            raise AssertionError("Novel collection entry did not open the shared settings page")
        evaluate(view, "document.querySelector('.archive-settings-card button').click(); selectPage('settings'); [...document.querySelectorAll('.settings-nav button')].find(x => x.textContent === '自动归档').click(); true")
        for _ in range(30):
            app.processEvents()
            time.sleep(0.02)
        for skin in ("glass", "vaporwave"):
            evaluate(view, f"applyUiSkin({json.dumps(skin)}); true")
            pump(app, lambda: evaluate(view, f"State.uiSkin === {json.dumps(skin)} && !State.uiSkinPending ? 1 : 0"))
            for width in (1100, 740, 600):
                view.resize(width, 850)
                pump(app, lambda: evaluate(view, "innerWidth") == width)
                for _ in range(12):
                    app.processEvents()
                    time.sleep(0.02)
                result = json.loads(evaluate(view, """JSON.stringify((() => ({
                    width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
                    button: Boolean(document.querySelector('.archive-controls button')),
                    heading: document.querySelector('.archive-status strong')?.textContent,
                    tabs: [...document.querySelectorAll('.settings-nav button')].map(x => x.textContent),
                    focusable: [...document.querySelectorAll('.archive-settings-card button, .archive-settings-card input')].every(x => x.tabIndex >= 0),
                    innerOverflow: ['#contentArea', '.settings-grid', '.archive-settings-card'].map(s => {
                        const e = document.querySelector(s); return e ? e.scrollWidth - e.clientWidth : -1;
                    })
                }))())"""))
                print(skin, width, json.dumps(result, ensure_ascii=False))
                if result["scrollWidth"] > result["width"] + 1 or not result["button"] or not result["focusable"] or max(result["innerOverflow"]) > 1:
                    raise AssertionError(f"Layout failure: {skin} {width}: {result}")
                screenshot = root / f"{skin}-{width}.png"
                view.grab().save(str(screenshot))
                output = os.environ.get("AUTHOR_ARCHIVE_QA_OUTPUT")
                if output:
                    target = Path(output)
                    target.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(screenshot, target / screenshot.name)
        view.activateWindow()
        view.setFocus()
        QTest.qWait(80)
        evaluate(view, "document.querySelector('.archive-toggle input').click(); document.querySelector('.archive-controls button').focus(); true")
        if not evaluate(view, "document.activeElement === document.querySelector('.archive-controls button') ? 1 : 0"):
            raise AssertionError("Preview button could not receive keyboard focus")
        QTest.keyClick(view.focusProxy() or view, Qt.Key_Return)
        pump(app, lambda: evaluate(view, "State.archivePreset.preview && State.archivePreset.token ? 1 : 0"))
        result = json.loads(evaluate(view, "JSON.stringify({total: State.archivePreset.preview.rows.total, confirm: Boolean(document.querySelector('.archive-preview > button'))})"))
        if result["total"] != 3 or not result["confirm"]:
            raise AssertionError(result)
        for skin in ("glass", "vaporwave"):
            evaluate(view, f"applyUiSkin({json.dumps(skin)}); true")
            pump(app, lambda: evaluate(view, f"State.uiSkin === {json.dumps(skin)} && !State.uiSkinPending ? 1 : 0"))
            for width in (1100, 740, 600):
                view.resize(width, 850)
                pump(app, lambda: evaluate(view, "innerWidth") == width)
                for _ in range(12):
                    app.processEvents()
                    time.sleep(0.02)
                layout = json.loads(evaluate(view, "JSON.stringify({outer:document.documentElement.scrollWidth-innerWidth, inner:document.querySelector('.archive-settings-card').scrollWidth-document.querySelector('.archive-settings-card').clientWidth, rows:document.querySelectorAll('.archive-preview-row').length})"))
                print("preview", skin, width, json.dumps(layout))
                if layout["outer"] > 1 or layout["inner"] > 1 or layout["rows"] != 3:
                    raise AssertionError(layout)
                output = os.environ.get("AUTHOR_ARCHIVE_QA_OUTPUT")
                if output:
                    view.grab().save(str(Path(output) / f"{skin}-{width}-preview.png"))
        evaluate(view, "document.querySelector('.archive-preview > button').click(); true")
        pump(app, lambda: evaluate(view, "State.archivePreset.enabled && !State.archivePreset.loading ? 1 : 0"))
        if not repo.get_setting("text_novel_author_archive_enabled", False):
            raise AssertionError("Enable did not persist")
        evaluate(view, "document.querySelector('.archive-toggle input').click(); "
                 "const mode = document.querySelector('.archive-mode select'); mode.value = 'convert'; "
                 "mode.dispatchEvent(new Event('change', {bubbles:true})); "
                 "document.querySelector('.archive-controls button').click(); true")
        pump(app, lambda: evaluate(view, "State.archivePreset.preview && State.archivePreset.preview.disableMode === 'convert' ? 1 : 0"))
        evaluate(view, "document.querySelector('.archive-preview > button').click(); true")
        pump(app, lambda: evaluate(view, "!State.archivePreset.enabled && !State.archivePreset.loading ? 1 : 0"))
        if repo.get_setting("text_novel_author_archive_enabled", False):
            raise AssertionError("Disable did not persist")
        with repo._connection() as conn:
            converted = conn.execute("SELECT COUNT(*) FROM collection_books cb JOIN collections c ON c.id = cb.collection_id "
                                     "WHERE c.archive_preset = 'text_novel_author' AND cb.manual_source = 1 AND cb.rule_source = 0").fetchone()[0]
        if converted != 23:
            raise AssertionError(f"Expected 23 converted manual members, got {converted}")
        print("ARCHIVE_WEBENGINE_QA_OK")
        view.close()


if __name__ == "__main__":
    main()
