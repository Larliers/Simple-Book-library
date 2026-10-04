"""Exercise tag highlights in a real offscreen Qt WebEngine view and temporary library."""
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


def truth(view: QWebEngineView, expression: str) -> bool:
    return bool(evaluate(view, f"({expression}) ? 1 : 0"))


def wait_for(app: QApplication, view: QWebEngineView, expression: str) -> None:
    deadline = time.monotonic() + 30
    while not truth(view, expression):
        if time.monotonic() > deadline:
            state = evaluate(view, "JSON.stringify({ready:document.readyState, pages:typeof State === 'undefined' ? -1 : Object.keys(State.pages).length, bridge:typeof qt, config:State.settings.tagHighlights, saving:State.tagHighlightSaving, text:document.body.innerText.slice(0,200)})")
            raise TimeoutError(f"{expression}: {state}")
        app.processEvents()
        time.sleep(0.02)


def assert_geometry(view: QWebEngineView, width: int, label: str) -> None:
    values = json.loads(evaluate(view, """JSON.stringify((() => {
      const row = [...document.querySelectorAll('.tag-link')].find(b => b.dataset.tagName.startsWith('A very long'));
      const name = row.querySelector('.tag-name').getBoundingClientRect();
      const count = row.querySelector('.tag-resource-count').getBoundingClientRect();
      const menu = document.getElementById('contextMenu').getBoundingClientRect();
      const highlighted = row.querySelector('.tag-highlighted');
      return { nameRight: name.right, countLeft: count.left, menuLeft: menu.left,
        menuRight: menu.right, menuTop: menu.top, menuBottom: menu.bottom,
        viewportWidth: innerWidth, viewportHeight: innerHeight,
        scrollWidth: document.documentElement.scrollWidth,
        highlightOnlyName: !!highlighted && !row.querySelector('.tag-bullet.tag-highlighted, .tag-resource-count.tag-highlighted'),
        nameInk: getComputedStyle(highlighted).color, rowInk: getComputedStyle(row).color,
        cardFill: getComputedStyle(highlighted).backgroundColor,
        cardRadius: getComputedStyle(highlighted).borderRadius,
        cardBorder: getComputedStyle(highlighted).borderTopWidth,
        cardShadow: getComputedStyle(highlighted).boxShadow };
    })())"""))
    if not values["highlightOnlyName"] or values["nameRight"] > values["countLeft"] + 1:
        raise AssertionError(f"{label} name/count overlap: {values}")
    if values["nameInk"] != values["rowInk"] or values["cardFill"] == "rgba(0, 0, 0, 0)" or values["cardRadius"] == "0px":
        raise AssertionError(f"{label} highlight card or text color: {values}")
    if values["cardBorder"] != "0px" or values["cardShadow"] != "none":
        raise AssertionError(f"{label} highlight card has an outline: {values}")
    if (values["menuLeft"] < 0 or values["menuRight"] > values["viewportWidth"] + 1
            or values["menuTop"] < 0 or values["menuBottom"] > values["viewportHeight"] + 1):
        raise AssertionError(f"{label} menu overflow: {values}")
    if values["scrollWidth"] > values["viewportWidth"] + 1:
        raise AssertionError(f"{label} page horizontal overflow: {values}")
    if abs(values["viewportWidth"] - width) > 1:
        raise AssertionError(f"{label} viewport did not resize: {values}")


def main() -> None:
    register_app_scheme()
    app = QApplication([])
    language_manager.set_language("zh-cn")
    with tempfile.TemporaryDirectory(prefix="tag_highlight_webengine_") as directory:
        root = Path(directory)
        repo = LibraryRepository(root / "library.db", root / "scan_report.json")
        long_tag = "A very long tag title used to check that the book count is not covered in narrow windows"
        for number, tag in enumerate((long_tag, "Architecture", "LOL")):
            repo.upsert_book({
                "path": f"C:/demo/{number}.epub", "file_name": f"{number}.epub",
                "extension": ".epub", "title": f"Demo {number}",
                "resource_type": "book", "tags_json": json.dumps([tag]),
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
        wait_for(app, view, "Object.keys(State.pages).length > 0")
        evaluate(view, "selectPage('tag_manager'); true")
        wait_for(app, view, "State.currentPage === 'tag_manager' && document.querySelectorAll('.tag-link').length === 3")

        # Keyboard opening, native picker input preview, committed custom color and reuse.
        evaluate(view, """(() => {
          const row = document.querySelector('.tag-link'); row.focus();
          row.dispatchEvent(new KeyboardEvent('keydown', {key:'F10', shiftKey:true, bubbles:true}));
          document.querySelector('#contextMenu > button').click(); return true;
        })()""")
        assert truth(view, "!!State.tagHighlightMenu && !State.tagHighlightMenu.customGrid.closest('.hidden')")
        evaluate(view, """(() => {
          const input = document.querySelector('.tag-color-input');
          input.value = '#38ad65'; input.dispatchEvent(new Event('input', {bubbles:true})); return true;
        })()""")
        assert truth(view, "!!document.querySelector('.tag-custom-colors .tag-color-swatch[data-color=\"#38ad65\"]')")
        assert repo.get_tag_highlights()["byTag"] == {}
        evaluate(view, "document.querySelector('.tag-color-input').dispatchEvent(new Event('change', {bubbles:true})); true")
        wait_for(app, view, "!State.tagHighlightSaving && !!document.querySelector('.tag-link .tag-highlighted')")
        assert truth(view, "!!State.tagHighlightMenu && !document.getElementById('contextMenu').classList.contains('hidden')")
        assert repo.get_tag_highlights()["customColors"] == ["#38ad65"]
        evaluate(view, "document.querySelector('.tag-color-delete').click(); true")
        wait_for(app, view, "!State.tagHighlightSaving && State.settings.tagHighlights.customColors.length === 0")
        assert repo.get_tag_highlights()["byTag"][long_tag] == "#38ad65"
        assert truth(view, "!!State.tagHighlightMenu && !document.getElementById('contextMenu').classList.contains('hidden')")
        evaluate(view, "document.querySelector('.tag-color-swatch[data-color=\"#ffe58a\"]').click(); true")
        wait_for(app, view, "!State.tagHighlightSaving && State.settings.tagHighlights.byTag[document.querySelector('.tag-link').dataset.tagName] === '#ffe58a'")
        assert truth(view, "document.getElementById('contextMenu').classList.contains('hidden')")

        # A failed save must restore the previous color on the existing row.
        evaluate(view, """(() => {
          const row = document.querySelector('.tag-link');
          window.highlightRowBeforeFailure = row;
          window.originalHighlightBridge = State.bridge.updateTagHighlight;
          State.bridge.updateTagHighlight = (_, callback) => callback('{"ok":false,"error":"save_failed"}');
          row.dispatchEvent(new MouseEvent('contextmenu', {bubbles:true, cancelable:true,
            clientX:80, clientY:80}));
          document.querySelector('#contextMenu > button').click();
          document.querySelector('.tag-color-swatch[data-color="#c8e2fa"]').click();
          State.bridge.updateTagHighlight = window.originalHighlightBridge;
          return true;
        })()""")
        assert truth(view, "State.settings.tagHighlights.byTag[window.highlightRowBeforeFailure.dataset.tagName] === '#ffe58a' && window.highlightRowBeforeFailure.isConnected")
        assert repo.get_tag_highlights()["byTag"][long_tag] == "#ffe58a"

        # A fresh custom color remains available in all skins and after route changes.
        repo.update_tag_highlight({"action": "create_color", "tag": long_tag, "color": "#38ad65"})
        bridge.push_settings()
        wait_for(app, view, "State.settings.tagHighlights.customColors.length === 1")
        for skin in ("glass", "vaporwave"):
            evaluate(view, f"applyUiSkin({json.dumps(skin)}); true")
            wait_for(app, view, f"State.uiSkin === {json.dumps(skin)} && !State.uiSkinPending")
            for width in (1100, 740, 600):
                view.setFixedSize(width, 760)
                app.processEvents()
                wait_for(app, view, f"innerWidth === {width}")
                evaluate(view, """(() => {
                  const row = document.querySelector('.tag-link'); const rect = row.getBoundingClientRect();
                  row.dispatchEvent(new MouseEvent('contextmenu', {bubbles:true, cancelable:true,
                    clientX:innerWidth - 2, clientY:innerHeight - 2}));
                  document.querySelector('#contextMenu > button').click(); return true;
                })()""")
                assert_geometry(view, width, f"{skin}/{width}")
                assert truth(view, "!!document.querySelector('.tag-color-delete')")
                evaluate(view, "document.querySelector('.tag-color-delete').focus(); document.getElementById('contextMenu').dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true})); true")
                assert truth(view, "document.activeElement.classList.contains('tag-link') && document.getElementById('contextMenu').classList.contains('hidden')")
            evaluate(view, "selectPage('library'); selectPage('tag_manager'); true")
            wait_for(app, view, "State.currentPage === 'tag_manager' && document.querySelectorAll('.tag-link').length === 3")
            assert truth(view, "!!document.querySelector('.tag-link .tag-highlighted')")
        evaluate(view, """(() => {
          const row = document.querySelector('.tag-link');
          row.dispatchEvent(new MouseEvent('contextmenu', {bubbles:true, cancelable:true, clientX:60, clientY:60}));
          document.querySelector('#contextMenu > button').click();
          document.querySelector('.tag-color-swatch[data-color="#38ad65"]').click();
          return true;
        })()""")
        wait_for(app, view, "!State.tagHighlightSaving && State.settings.tagHighlights.byTag[document.querySelector('.tag-link').dataset.tagName] === '#38ad65'")
        evaluate(view, """(() => {
          const row = document.querySelector('.tag-link');
          row.dispatchEvent(new MouseEvent('contextmenu', {bubbles:true, cancelable:true, clientX:60, clientY:60}));
          State.tagHighlightMenu.removeButton.click(); return true;
        })()""")
        wait_for(app, view, "!State.tagHighlightSaving && !State.settings.tagHighlights.byTag[document.querySelector('.tag-link').dataset.tagName]")
        assert repo.get_tag_highlights()["customColors"] == ["#38ad65"]
        repo.update_tag_highlight({"action": "set", "tag": long_tag, "color": "#38ad65"})
        assert LibraryRepository(root / "library.db").get_tag_highlights()["byTag"][long_tag] == "#38ad65"
        loaded.clear()
        view.reload()
        deadline = time.monotonic() + 15
        while not loaded:
            if time.monotonic() > deadline:
                raise TimeoutError("Page refresh timed out")
            app.processEvents()
            time.sleep(0.02)
        if not loaded[0]:
            raise RuntimeError("Page refresh failed")
        wait_for(app, view, "Object.keys(State.pages).length > 0")
        evaluate(view, "selectPage('tag_manager'); true")
        wait_for(app, view, "State.currentPage === 'tag_manager' && document.querySelectorAll('.tag-link').length === 3")
        assert truth(view, "!!document.querySelector('.tag-link .tag-highlighted') && State.settings.tagHighlights.customColors.includes('#38ad65')")
        view.close()
        print("TAG_HIGHLIGHT_WEBENGINE_QA_OK")


if __name__ == "__main__":
    main()
