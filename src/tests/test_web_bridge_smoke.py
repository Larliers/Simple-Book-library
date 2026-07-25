from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    from PySide6.QtWidgets import QApplication

    from bookhub.library import LibraryRepository
    from bookhub.library.models import ComicScanRequest, ComicScanRoot
    from bookhub.library.scanner import scan_comic_roots
    from bookhub.ui.web_bridge import PAGE_COMIC, UiBridge, NAV_ITEMS
    from bookhub.ui.web_scheme import WEB_ROOT, to_local_path

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - optional UI dependency
    QApplication = None  # type: ignore[assignment]
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, "PySide6/WebEngine is not available")
class WebBridgeSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def _make_bridge(self) -> UiBridge:
        tmp = tempfile.mkdtemp(prefix="bookhub_web_")
        repo = LibraryRepository(db_path=str(Path(tmp) / "library.db"))
        return UiBridge(repo, set())

    def test_bootstrap_has_all_pages(self) -> None:
        bridge = self._make_bridge()
        payload = json.loads(bridge.getBootstrap())
        self.assertIn("strings", payload)
        self.assertIn("settings", payload)
        self.assertIn("theme", payload["settings"])
        page_keys = {page for page, _, _ in NAV_ITEMS}
        self.assertEqual(set(payload["pages"].keys()), page_keys)

    def test_library_payload_includes_extension(self) -> None:
        bridge = self._make_bridge()
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "sample.epub"
            sample.write_bytes(b"")
            bridge._repo.upsert_book(
                {
                    "path": str(sample),
                    "title": "Sample EPUB",
                    "file_name": "sample.epub",
                    "extension": ".epub",
                    "resource_type": "epub",
                    "tags_json": "[]",
                }
            )
            bridge.reload_data()
            items = json.loads(bridge.getBootstrap())["pages"]["library"]["items"]
            book = next(item for item in items if item.get("title") == "Sample EPUB")
            self.assertEqual(book.get("extension"), ".epub")

    def test_search_returns_json_payload(self) -> None:
        bridge = self._make_bridge()
        result = json.loads(bridge.search("library", "nonexistent-query-xyz"))
        self.assertIn("items", result)
        self.assertIsInstance(result["items"], list)

    def test_theme_settings_persist(self) -> None:
        bridge = self._make_bridge()
        bridge.setThemeSettings(json.dumps({"mode": "night", "nightStart": "21:30"}))
        theme = json.loads(bridge.getBootstrap())["settings"]["theme"]
        self.assertEqual(theme["mode"], "night")
        self.assertEqual(theme["nightStart"], "21:30")

    def test_ui_skin_persist(self) -> None:
        bridge = self._make_bridge()
        self.assertEqual(json.loads(bridge.getBootstrap())["settings"]["uiSkin"], "glass")
        bridge.setUiSkin("vaporwave")
        self.assertEqual(json.loads(bridge.getBootstrap())["settings"]["uiSkin"], "vaporwave")
        bridge.setUiSkin("invalid")
        self.assertEqual(json.loads(bridge.getBootstrap())["settings"]["uiSkin"], "vaporwave")

    def test_web_assets_present(self) -> None:
        for rel in (
            "index.html",
            "css/app.css",
            "css/base.css",
            "css/skins/glass/tokens.css",
            "css/skins/glass/components.css",
            "css/skins/vaporwave/fonts.css",
            "css/skins/vaporwave/tokens.css",
            "css/skins/vaporwave/background.css",
            "css/skins/vaporwave/layout.css",
            "css/skins/vaporwave/components.css",
            "js/app.js",
            "js/qwebchannel.js",
            "fonts/Sora-Regular.woff2",
            "fonts/SpaceMono-Regular.woff2",
        ):
            self.assertTrue((WEB_ROOT / rel).is_file(), f"missing web asset: {rel}")

    def test_collection_rename_delete_roundtrip(self) -> None:
        bridge = self._make_bridge()
        cid = bridge.createCollection("Temp List")
        self.assertGreater(cid, 0)
        self.assertTrue(bridge.renameCollection(cid, "Renamed List"))
        collections = json.loads(bridge.getCollections())
        self.assertTrue(any(c["id"] == cid and c["name"] == "Renamed List" for c in collections))
        self.assertTrue(bridge.deleteCollection(cid))
        collections = json.loads(bridge.getCollections())
        self.assertFalse(any(c["id"] == cid for c in collections))

    def test_bootstrap_includes_menu_i18n_keys(self) -> None:
        bridge = self._make_bridge()
        strings = json.loads(bridge.getBootstrap())["strings"]
        for key in (
            "page.count",
            "menu.open_folder",
            "menu.collection_rename",
            "menu.favorite_remove",
            "menu.edit_cover",
            "detail.edit_cover",
            "quick_add.add",
            "quick_add.added",
            "quick_add.confirm",
            "quick_add.recent_tags",
            "favorites.sort.added_desc",
            "settings.comic.placeholder_copy",
            "settings.delete_confirm_title",
            "settings.scan_summary_title",
            "settings.hash.hint",
            "settings.nav.paths",
            "settings.per_root_strategy",
            "settings.comic_scan_strategy",
            "settings.roots.scan_strategy",
            "settings.scan_strategy.inherit",
        ):
            self.assertIn(key, strings)
        self.assertIn("Fast", strings["settings.hash.hint"])
        self.assertIn("Paths", strings["settings.nav.paths"])

    def test_set_page_sort_favorites(self) -> None:
        bridge = self._make_bridge()
        payload = json.loads(bridge.setPageSort("favorites", "asc"))
        self.assertEqual(payload.get("sort"), "asc")
        self.assertEqual(bridge._repo.get_setting("favorites_sort_order", "desc"), "asc")

    def test_settings_payload_includes_comic_perf(self) -> None:
        bridge = self._make_bridge()
        settings = json.loads(bridge.getBootstrap())["settings"]
        self.assertIn("comicPlaceholderCopy", settings)
        self.assertIn("autoGenerateComicThumbs", settings)
        self.assertIn("comicThumbnailWorkers", settings)
        self.assertIn("scanReport", settings)
        self.assertIn("perRootScanStrategyEnabled", settings)
        self.assertIn("comicScanStrategy", settings)
        self.assertEqual(settings.get("hashStrategy"), "quick")
        self.assertFalse(settings["perRootScanStrategyEnabled"])
        self.assertEqual(settings["comicScanStrategy"], "snapshot")

    def test_settings_payload_includes_app_version(self) -> None:
        bridge = self._make_bridge()
        settings = json.loads(bridge.getBootstrap())["settings"]
        self.assertIn("appVersion", settings)
        self.assertTrue(str(settings["appVersion"]).strip())

    def test_update_check_slots_exist(self) -> None:
        bridge = self._make_bridge()
        self.assertTrue(callable(getattr(bridge, "checkForUpdates", None)))
        self.assertTrue(callable(getattr(bridge, "openExternalUrl", None)))

    def test_edit_cover_slot_exists(self) -> None:
        bridge = self._make_bridge()
        self.assertTrue(callable(getattr(bridge, "editCover", None)))

    def test_remove_from_library_slot_exists(self) -> None:
        bridge = self._make_bridge()
        self.assertTrue(callable(getattr(bridge, "removeFromLibrary", None)))

    def test_set_root_scan_strategy_slot_exists(self) -> None:
        bridge = self._make_bridge()
        self.assertTrue(callable(getattr(bridge, "setRootScanStrategy", None)))

    def test_comic_view_default_is_pagination(self) -> None:
        bridge = self._make_bridge()
        self.assertEqual(bridge._repo.get_comic_view_mode(), "pagination")

    def test_viewport_buffer_screens_default_and_clamp(self) -> None:
        bridge = self._make_bridge()
        self.assertEqual(bridge._repo.get_viewport_buffer_screens(), 3)
        bridge._repo.set_viewport_buffer_screens(5)
        self.assertEqual(bridge._repo.get_viewport_buffer_screens(), 5)
        bridge._repo.set_viewport_buffer_screens(99)
        self.assertEqual(bridge._repo.get_viewport_buffer_screens(), 3)
        payload = bridge._settings_payload()
        self.assertEqual(payload.get("viewportBufferScreens"), 3)

    def test_grid_columns_default_and_clamp(self) -> None:
        bridge = self._make_bridge()
        self.assertEqual(bridge._repo.get_grid_columns(), 6)
        bridge._repo.set_grid_columns(8)
        self.assertEqual(bridge._repo.get_grid_columns(), 8)
        bridge._repo.set_grid_columns(99)
        self.assertEqual(bridge._repo.get_grid_columns(), 6)
        self.assertEqual(bridge._settings_payload().get("gridColumns"), 6)

    def test_text_rules_get_save_preview_roundtrip(self) -> None:
        bridge = self._make_bridge()
        tmp = tempfile.mkdtemp(prefix="bookhub_text_root_")
        root = Path(tmp)
        sample = root / "demo.txt"
        sample.write_text("T书名\n作者：测试\n", encoding="utf-8")
        bridge._repo.add_text_root(str(root))

        opened = json.loads(bridge.getTextRules(str(root)))
        self.assertTrue(opened.get("ok"), opened)
        self.assertIn("catalog", opened)
        self.assertTrue(opened["catalog"].get("steps"))
        self.assertTrue(any(s["name"] == "demo.txt" for s in opened.get("samples") or []))

        rules = {
            "title": [
                {
                    "field": "title",
                    "source": "txt_first_line",
                    "steps": [{"type": "take_after_text", "value": "T"}, {"type": "trim"}],
                }
            ]
        }
        saved = json.loads(bridge.saveTextRules(str(root), json.dumps(rules, ensure_ascii=False)))
        self.assertTrue(saved.get("ok"), saved)
        stored = json.loads(bridge._repo.get_text_root_rules_json(str(root)))
        self.assertEqual(stored["title"][0]["source"], "txt_first_line")

        preview = json.loads(
            bridge.previewTextRule(
                str(root),
                json.dumps(rules["title"], ensure_ascii=False),
                str(sample),
            )
        )
        self.assertTrue(preview.get("ok"), preview)
        self.assertTrue(preview.get("success"), preview)
        self.assertEqual(preview.get("value"), "书名")

        multi = json.loads(bridge.previewTextRulesMulti(str(root), json.dumps(rules["title"], ensure_ascii=False)))
        self.assertTrue(multi.get("ok"), multi)
        self.assertGreaterEqual(len(multi.get("items") or []), 1)

        outside = json.loads(bridge.previewTextRule(str(root), json.dumps(rules["title"]), r"C:\Windows\win.ini"))
        self.assertFalse(outside.get("ok"))

    def test_text_rules_js_asset_present(self) -> None:
        self.assertTrue((WEB_ROOT / "js" / "text_rules.js").is_file())

    def test_to_local_path_handles_file_url(self) -> None:
        self.assertIsNone(to_local_path(""))
        converted = to_local_path("file:///C:/tmp/cover.webp")
        self.assertIsNotNone(converted)
        self.assertTrue(converted.lower().endswith("cover.webp"))

    def test_open_resource_cbz_resolves_materialized_cover_path(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "comics"
            root.mkdir()
            page = base / "001.png"
            Image.new("RGB", (80, 120), color=(200, 80, 80)).save(page, format="PNG")
            cbz = root / "MyComic.cbz"
            with zipfile.ZipFile(cbz, "w") as zf:
                zf.write(page, "001.png")
            preview = base / "preview"
            repo = LibraryRepository(db_path=str(base / "library.db"), preview_dir=preview)
            repo.add_comic_root(root)
            scan_comic_roots(
                repo,
                ComicScanRequest(roots=[ComicScanRoot(path=str(root))], max_depth=3, placeholder_copy_enabled=True),
            )
            comics = repo.list_comics(include_missing=False)
            self.assertEqual(len(comics), 1)
            bridge = UiBridge(repo, set())
            opened: list[str] = []

            def capture_open(path: str) -> None:
                opened.append(path)

            with patch.object(bridge, "_open_external", side_effect=capture_open):
                bridge.openResource(PAGE_COMIC, str(comics[0]["resource_id"]))

            self.assertEqual(len(opened), 1)
            opened_path = Path(opened[0])
            self.assertTrue(opened_path.exists())
            self.assertTrue(opened_path.is_file())
            self.assertNotIn("::", opened[0])
            self.assertEqual(opened_path.name, "001.png")
            normalized = opened[0].replace("\\", "/").lower()
            self.assertIn("/comic/read/", normalized)
            self.assertTrue((opened_path.parent / "001.png").is_file())

    def test_open_resource_folder_comic_uses_source_image(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            comic_dir = base / "MyFolderComic"
            comic_dir.mkdir()
            cover = comic_dir / "001.png"
            Image.new("RGB", (80, 120), color=(120, 160, 200)).save(cover, format="PNG")
            preview = base / "preview"
            repo = LibraryRepository(db_path=str(base / "library.db"), preview_dir=preview)
            normalized = repo.normalize_path(comic_dir)
            repo.upsert_comic(
                {
                    "path": normalized,
                    "title": "MyFolderComic",
                    "cover_image_path": str(cover),
                    "image_count": 1,
                }
            )
            comics = repo.list_comics(include_missing=False)
            self.assertEqual(len(comics), 1)
            bridge = UiBridge(repo, set())
            opened: list[str] = []

            def capture_open(path: str) -> None:
                opened.append(path)

            with patch.object(bridge, "_open_external", side_effect=capture_open):
                bridge.openResource(PAGE_COMIC, str(comics[0]["resource_id"]))

            self.assertEqual(opened, [str(cover)])


class SettingsUiStructureTests(unittest.TestCase):
    def test_app_js_merges_paths_and_tasks(self) -> None:
        app_js = (PROJECT_ROOT / "src" / "bookhub" / "ui" / "web" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn('["paths", "settings.nav.paths"]', app_js)
        self.assertNotIn('["tasks", "settings.nav.tasks"]', app_js)
        self.assertIn("renderSettingsPaths(panel)", app_js)
        self.assertIn("renderSettingsTasks(panel)", app_js)
        self.assertIn('State._settingsSection === "tasks"', app_js)
        self.assertIn("settings.hash.hint", app_js)
        self.assertIn("scanProgressBar", app_js)
        self.assertIn("scanProgressLabel", app_js)
        self.assertIn("scanSummaryBox", app_js)
        self.assertIn("formatBadgeLabel", app_js)
        self.assertIn("buildCoverSlot", app_js)
        self.assertIn('page === "library"', app_js)

    def test_set_ui_skin_updates_active_segment(self) -> None:
        app_js = (PROJECT_ROOT / "src" / "bookhub" / "ui" / "web" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("State.uiSkin = normalized;", app_js)
        self.assertIn("if (State.currentPage === \"settings\") renderSettings();", app_js)


if __name__ == "__main__":
    unittest.main()
