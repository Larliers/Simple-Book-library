from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime
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
    from bookhub.library.repository import COLLECTION_KIND_TEXT_NOVEL
    from bookhub.library.scanner import scan_comic_roots
    from bookhub.ui.web_bridge import (
        PAGE_COMIC,
        PAGE_COMIC_COLLECTIONS,
        PAGE_COLLECTIONS,
        PAGE_LIBRARY,
        PAGE_NOVEL_COLLECTIONS,
        PAGE_RANDOM_RECOMMENDATIONS,
        PAGE_TAG_MANAGER,
        PAGE_TEXT,
        UiBridge,
        NAV_ITEMS,
    )
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

    def _assert_open_external_event(self, events: list[dict[str, object]], resource_id: str) -> None:
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "open_external")
        self.assertEqual(events[0]["resource_id"], resource_id)
        parsed = datetime.fromisoformat(str(events[0]["timestamp"]))
        self.assertIsNotNone(parsed.tzinfo)

    def test_bootstrap_has_all_pages(self) -> None:
        bridge = self._make_bridge()
        payload = json.loads(bridge.getBootstrap())
        self.assertIn("strings", payload)
        self.assertIn("settings", payload)
        self.assertIn("theme", payload["settings"])
        self.assertEqual(payload["settings"]["recommendationItemsPerCategory"], 6)
        self.assertEqual(payload["settings"]["recommendationColumnsPerCategory"], 2)
        self.assertEqual(payload["settings"]["textNovelViewMode"], "grid")
        self.assertEqual(
            payload["settings"]["tagManagerScopes"],
            {"library": True, "text_novel": True, "comic": True},
        )
        self.assertEqual(
            payload["settings"]["shortcutBindings"],
            {
                "exit_collection": "",
                "reopen_recent_collection": "",
                "open_resource": "",
                "open_folder": "",
                "quick_add": "",
                "edit_cover": "",
                "remove_from_collection": "",
                "remove_from_library": "",
            },
        )
        page_keys = {page for page, _, _ in NAV_ITEMS}
        self.assertEqual(set(payload["pages"].keys()), page_keys)
        pages = [page for page, _, _ in NAV_ITEMS]
        self.assertEqual(pages[-2:], [PAGE_RANDOM_RECOMMENDATIONS, PAGE_TAG_MANAGER])

    def test_tag_manager_bridge_catalog_detail_and_scope_contract(self) -> None:
        bridge = self._make_bridge()
        bridge._repo.upsert_book(
            {
                "resource_id": "book-tagged",
                "path": r"C:\library\book-tagged.pdf",
                "title": "Tagged Book",
                "file_name": "book-tagged.pdf",
                "extension": ".pdf",
                "resource_type": "book",
                "tags_json": "[]",
            }
        )
        bridge.reload_data()
        self.assertTrue(bridge.addResourceTag(PAGE_LIBRARY, "book-tagged", "白色"))

        catalog = json.loads(bridge.getTagCatalog("asc"))
        detail = json.loads(bridge.getTagResources("白色"))
        saved = json.loads(
            bridge.setTagManagerScopes(
                json.dumps({"library": True, "text_novel": False, "comic": False})
            )
        )
        rejected = json.loads(
            bridge.setTagManagerScopes(
                json.dumps({"library": False, "text_novel": False, "comic": False})
            )
        )

        self.assertEqual(catalog["groups"][0]["letter"], "B")
        self.assertEqual(detail["mode"], "tag_detail")
        self.assertEqual(detail["tag"], "白色")
        self.assertEqual(detail["items"][0]["sourcePage"], PAGE_LIBRARY)
        self.assertTrue(saved["ok"])
        self.assertEqual(saved["scopes"], {"library": True, "text_novel": False, "comic": False})
        self.assertEqual(rejected["error"], "empty_scope")

    def test_open_tag_emits_interaction_event_only_for_user_open(self) -> None:
        bridge = self._make_bridge()
        events: list[dict[str, object]] = []
        bridge.interactionEvent.connect(lambda raw: events.append(json.loads(raw)))

        json.loads(bridge.getTagResources("白色"))
        self.assertEqual(events, [])

        bridge.openTag("")
        bridge.openTag("   ")
        self.assertEqual(events, [])

        bridge.openTag("白色")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "open_tag")
        self.assertEqual(events[0]["resource_id"], "白色")
        parsed = datetime.fromisoformat(str(events[0]["timestamp"]))
        self.assertIsNotNone(parsed.tzinfo)

    def test_comic_tags_use_page_aware_bridge_and_invalidate_catalog(self) -> None:
        bridge = self._make_bridge()
        bridge._repo.upsert_comic(
            {
                "resource_id": "comic-tagged",
                "path": r"C:\comics\comic-tagged",
                "title": "Tagged Comic",
                "image_count": 3,
            }
        )
        bridge.reload_data()
        resource_payloads: list[dict[str, object]] = []
        bridge.resourcesChanged.connect(lambda raw: resource_payloads.append(json.loads(raw)))

        self.assertTrue(bridge.addResourceTag(PAGE_COMIC, "comic-tagged", "漫画标签"))
        self.assertEqual(json.loads(bridge.getDetail(PAGE_COMIC, "comic-tagged"))["tags"], ["漫画标签"])
        self.assertTrue(resource_payloads[-1]["tagCatalogInvalidated"])

        self.assertTrue(bridge.removeResourceTag(PAGE_COMIC, "comic-tagged", "漫画标签"))
        self.assertEqual(json.loads(bridge.getDetail(PAGE_COMIC, "comic-tagged"))["tags"], [])
        self.assertTrue(resource_payloads[-1]["tagCatalogInvalidated"])

    def test_shortcut_binding_bridge_returns_conflicts_and_emits_native_input(self) -> None:
        bridge = self._make_bridge()
        settings_payloads: list[dict[str, object]] = []
        native_inputs: list[str] = []
        bridge.settingsChanged.connect(lambda raw: settings_payloads.append(json.loads(raw)))
        bridge.nativeShortcutInput.connect(native_inputs.append)

        saved = json.loads(bridge.setShortcutBinding("open_resource", "MouseForward"))
        duplicate = json.loads(bridge.setShortcutBinding("quick_add", "MouseForward"))
        bridge.nativeShortcutInput.emit("MouseBack")

        self.assertTrue(saved["ok"])
        self.assertEqual(saved["bindings"]["open_resource"], "MouseForward")
        self.assertEqual(duplicate["error"], "duplicate")
        self.assertEqual(duplicate["conflictAction"], "open_resource")
        self.assertEqual(settings_payloads[-1]["shortcutBindings"]["open_resource"], "MouseForward")
        self.assertEqual(native_inputs, ["MouseBack"])

    def test_resource_push_marks_only_explicit_recommendation_invalidation(self) -> None:
        bridge = self._make_bridge()
        payloads: list[dict[str, object]] = []
        bridge.resourcesChanged.connect(lambda raw: payloads.append(json.loads(raw)))

        bridge.push_resources()
        bridge.push_resources(recommendations_invalidated=True)
        bridge.push_resources(tag_catalog_invalidated=True)

        self.assertFalse(payloads[0]["recommendationsInvalidated"])
        self.assertFalse(payloads[0]["tagCatalogInvalidated"])
        self.assertTrue(payloads[1]["recommendationsInvalidated"])
        self.assertTrue(payloads[2]["tagCatalogInvalidated"])

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

    def test_random_recommendations_empty_sources_keep_three_columns(self) -> None:
        bridge = self._make_bridge()

        payload = json.loads(bridge.getRandomRecommendations())

        self.assertEqual(payload["mode"], "recommendations")
        self.assertEqual(
            [(column["key"], column["sourcePage"]) for column in payload["columns"]],
            [("books", "library"), ("novels", "text_novel"), ("comics", "comic")],
        )
        self.assertEqual([column["items"] for column in payload["columns"]], [[], [], []])

    def test_random_recommendations_isolate_sources_and_limit_each_column(self) -> None:
        bridge = self._make_bridge()
        for index in range(5):
            bridge._repo.upsert_book(
                {
                    "path": f"C:/library/book-{index}.pdf",
                    "file_name": f"book-{index}.pdf",
                    "extension": ".pdf",
                    "title": f"Book {index}",
                    "resource_type": "pdf",
                    "tags_json": "[]",
                }
            )
        for index in range(2):
            bridge._repo.upsert_book(
                {
                    "path": f"C:/novels/novel-{index}.txt",
                    "file_name": f"novel-{index}.txt",
                    "extension": ".txt",
                    "title": f"Novel {index}",
                    "resource_type": "text_novel",
                    "tags_json": "[]",
                }
            )
        for index in range(4):
            bridge._repo.upsert_comic(
                {
                    "path": f"C:/comics/comic-{index}",
                    "title": f"Comic {index}",
                    "image_count": index + 1,
                }
            )
        bridge.reload_data()

        columns = {
            column["key"]: column for column in json.loads(bridge.getRandomRecommendations())["columns"]
        }

        self.assertEqual(len(columns["books"]["items"]), 5)
        self.assertEqual(len(columns["novels"]["items"]), 2)
        self.assertEqual(len(columns["comics"]["items"]), 4)
        self.assertTrue(all(item["type"] != "text_novel" for item in columns["books"]["items"]))
        self.assertTrue(all(item["type"] == "text_novel" for item in columns["novels"]["items"]))
        self.assertTrue(all(item["type"] == "comic_folder" for item in columns["comics"]["items"]))
        for column in columns.values():
            ids = [item["id"] for item in column["items"]]
            self.assertEqual(len(ids), len(set(ids)))

    def test_random_recommendations_honor_configured_item_count(self) -> None:
        bridge = self._make_bridge()
        for index in range(12):
            bridge._repo.upsert_book(
                {
                    "path": f"C:/library/configured-book-{index}.pdf",
                    "file_name": f"configured-book-{index}.pdf",
                    "extension": ".pdf",
                    "title": f"Configured Book {index}",
                    "resource_type": "pdf",
                    "tags_json": "[]",
                }
            )
            bridge._repo.upsert_book(
                {
                    "path": f"C:/novels/configured-novel-{index}.txt",
                    "file_name": f"configured-novel-{index}.txt",
                    "extension": ".txt",
                    "title": f"Configured Novel {index}",
                    "resource_type": "text_novel",
                    "tags_json": "[]",
                }
            )
            bridge._repo.upsert_comic(
                {
                    "path": f"C:/comics/configured-comic-{index}",
                    "title": f"Configured Comic {index}",
                    "image_count": index + 1,
                }
            )
        bridge.reload_data()

        for expected in (3, 6, 9, 12):
            bridge._repo.set_recommendation_items_per_category(expected)
            columns = json.loads(bridge.getRandomRecommendations())["columns"]
            self.assertEqual([len(column["items"]) for column in columns], [expected] * 3)
            for column in columns:
                ids = [item["id"] for item in column["items"]]
                self.assertEqual(len(ids), len(set(ids)))

    def test_random_recommendations_exclude_missing_records(self) -> None:
        bridge = self._make_bridge()
        bridge._repo.upsert_book(
            {
                "path": "C:/library/missing-book.pdf",
                "file_name": "missing-book.pdf",
                "extension": ".pdf",
                "title": "Missing Book",
                "resource_type": "pdf",
                "tags_json": "[]",
            }
        )
        bridge._repo.upsert_book(
            {
                "path": "C:/novels/missing-novel.txt",
                "file_name": "missing-novel.txt",
                "extension": ".txt",
                "title": "Missing Novel",
                "resource_type": "text_novel",
                "tags_json": "[]",
            }
        )
        bridge._repo.upsert_comic(
            {"path": "C:/comics/missing-comic", "title": "Missing Comic", "image_count": 1}
        )
        with bridge._repo._connection() as conn:
            conn.execute("UPDATE books SET is_missing = 1")
            conn.execute("UPDATE comics SET is_missing = 1")
        bridge.reload_data()

        payload = json.loads(bridge.getRandomRecommendations())

        self.assertEqual([column["items"] for column in payload["columns"]], [[], [], []])

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

    def test_vaporwave_font_urls_resolve_to_existing_assets(self) -> None:
        stylesheet = WEB_ROOT / "css" / "skins" / "vaporwave" / "fonts.css"
        font_urls = re.findall(r"url\([\"']?([^\"')]+)", stylesheet.read_text(encoding="utf-8"))

        self.assertEqual(len(font_urls), 5)
        for font_url in font_urls:
            with self.subTest(font_url=font_url):
                self.assertTrue(
                    (stylesheet.parent / font_url).resolve().is_file(),
                    f"font URL does not resolve to an asset: {font_url}",
                )

    def test_collection_rename_delete_roundtrip(self) -> None:
        bridge = self._make_bridge()
        cid = bridge.createCollection("collections", "Temp List")
        self.assertGreater(cid, 0)
        self.assertTrue(bridge.renameCollection(cid, "Renamed List"))
        collections = json.loads(bridge.getCollections("collections"))
        self.assertTrue(any(c["id"] == cid and c["name"] == "Renamed List" for c in collections))
        self.assertTrue(bridge.deleteCollection(cid))
        collections = json.loads(bridge.getCollections("collections"))
        self.assertFalse(any(c["id"] == cid for c in collections))

    def test_collection_membership_change_does_not_broadcast_full_page_refresh(self) -> None:
        bridge = self._make_bridge()
        bridge._repo.upsert_book(
            {
                "resource_id": "scroll-book",
                "path": r"C:\library\scroll-book.pdf",
                "title": "Scroll Book",
                "file_name": "scroll-book.pdf",
                "extension": ".pdf",
                "resource_type": "book",
                "tags_json": "[]",
            }
        )
        bridge.reload_data()
        cid = bridge.createCollection(PAGE_LIBRARY, "Scroll Test")
        emitted: list[dict[str, object]] = []
        bridge.resourcesChanged.connect(lambda payload: emitted.append(json.loads(payload)))

        bridge.setCollectionMembership("scroll-book", cid, True)

        detail = json.loads(bridge.getDetail(PAGE_LIBRARY, "scroll-book"))
        self.assertEqual([collection["id"] for collection in detail["bookCollections"]], [cid])
        self.assertEqual(emitted, [])

    def test_apply_collection_quick_add_returns_targeted_state_without_refresh(self) -> None:
        bridge = self._make_bridge()
        bridge._repo.upsert_book(
            {
                "resource_id": "quick-book",
                "path": r"C:\library\quick-book.pdf",
                "title": "Quick Book",
                "file_name": "quick-book.pdf",
                "extension": ".pdf",
                "resource_type": "book",
                "tags_json": "[]",
            }
        )
        bridge.reload_data()
        emitted: list[dict[str, object]] = []
        bridge.resourcesChanged.connect(lambda payload: emitted.append(json.loads(payload)))

        result = json.loads(
            bridge.applyCollectionQuickAdd(
                PAGE_LIBRARY,
                "quick-book",
                json.dumps({"addIds": [], "removeIds": [], "createName": "Quick Shelf"}),
            )
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["collectionPage"], PAGE_COLLECTIONS)
        self.assertEqual(result["createdCollection"]["name"], "Quick Shelf")
        self.assertEqual(result["memberIds"], [result["createdCollection"]["id"]])
        self.assertEqual(result["collectionPageData"]["items"][0]["meta"], "1 books")
        self.assertEqual(result["detail"]["bookCollections"], [result["createdCollection"]])
        self.assertEqual(emitted, [])

    def test_apply_collection_quick_add_supports_text_and_comic_kinds(self) -> None:
        bridge = self._make_bridge()
        bridge._repo.upsert_book(
            {
                "resource_id": "quick-novel",
                "path": r"C:\library\quick-novel.txt",
                "title": "Quick Novel",
                "file_name": "quick-novel.txt",
                "extension": ".txt",
                "resource_type": "text_novel",
                "tags_json": "[]",
            }
        )
        bridge._repo.upsert_comic(
            {
                "resource_id": "quick-comic",
                "path": r"C:\comics\quick-comic",
                "title": "Quick Comic",
                "image_count": 3,
            }
        )
        bridge.reload_data()

        novel_result = json.loads(
            bridge.applyCollectionQuickAdd(
                PAGE_TEXT,
                "quick-novel",
                json.dumps({"addIds": [], "removeIds": [], "createName": "Novel Shelf"}),
            )
        )
        comic_result = json.loads(
            bridge.applyCollectionQuickAdd(
                PAGE_COMIC,
                "quick-comic",
                json.dumps({"addIds": [], "removeIds": [], "createName": "Comic Shelf"}),
            )
        )

        self.assertTrue(novel_result["ok"])
        self.assertEqual(novel_result["collectionPage"], PAGE_NOVEL_COLLECTIONS)
        self.assertEqual(novel_result["detail"]["bookCollections"], [novel_result["createdCollection"]])
        self.assertTrue(comic_result["ok"])
        self.assertEqual(comic_result["collectionPage"], PAGE_COMIC_COLLECTIONS)
        self.assertEqual(comic_result["detail"]["comicCollections"], [comic_result["createdCollection"]])

    def test_apply_collection_quick_add_rejects_invalid_payload_without_writing(self) -> None:
        bridge = self._make_bridge()
        bridge._repo.upsert_book(
            {
                "resource_id": "quick-invalid",
                "path": r"C:\library\quick-invalid.pdf",
                "title": "Quick Invalid",
                "file_name": "quick-invalid.pdf",
                "extension": ".pdf",
                "resource_type": "book",
                "tags_json": "[]",
            }
        )
        bridge.reload_data()

        result = json.loads(
            bridge.applyCollectionQuickAdd(
                PAGE_LIBRARY,
                "quick-invalid",
                json.dumps({"addIds": [999999], "removeIds": [], "createName": "No Partial"}),
            )
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "invalid_collection")
        self.assertEqual(bridge._repo.get_all_collections(), [])

    def test_collection_name_key_uses_backend_unicode_casefold(self) -> None:
        bridge = self._make_bridge()
        self.assertEqual(bridge.getCollectionNameKey("  Straße  "), "strasse")

    def test_apply_collection_quick_add_returns_storage_error_and_rolls_back(self) -> None:
        bridge = self._make_bridge()
        bridge._repo.upsert_book(
            {
                "resource_id": "quick-storage-error",
                "path": r"C:\library\quick-storage-error.pdf",
                "title": "Quick Storage Error",
                "file_name": "quick-storage-error.pdf",
                "extension": ".pdf",
                "resource_type": "book",
                "tags_json": "[]",
            }
        )
        bridge.reload_data()
        with bridge._repo._connection() as conn:
            conn.execute(
                """
                CREATE TRIGGER fail_bridge_quick_add_insert
                BEFORE INSERT ON collection_books
                BEGIN
                    SELECT RAISE(ABORT, 'forced bridge quick add failure');
                END
                """
            )

        result = json.loads(
            bridge.applyCollectionQuickAdd(
                PAGE_LIBRARY,
                "quick-storage-error",
                json.dumps({"addIds": [], "removeIds": [], "createName": "Rolled Back"}),
            )
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "storage_error")
        self.assertEqual(bridge._repo.get_all_collections(), [])

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
            "text_novel.sort.file_mtime_desc",
            "text_novel.sort.title_asc",
            "text_novel.sort.author_asc",
            "text_novel.sort.tags_desc",
            "text_novel.sort.path_asc",
            "settings.comic.placeholder_copy",
            "settings.delete_confirm_title",
            "settings.scan_summary_title",
            "settings.hash.hint",
            "settings.nav.paths",
            "settings.per_root_strategy",
            "settings.comic_scan_strategy",
            "settings.roots.scan_strategy",
            "settings.scan_strategy.inherit",
            "sidebar.random_recommendations",
            "recommendations.refresh",
            "recommendations.empty_column",
            "settings.recommendation_items_per_category",
            "settings.recommendation_columns_per_category",
        ):
            self.assertIn(key, strings)
        self.assertIn("Fast", strings["settings.hash.hint"])
        self.assertIn("Paths", strings["settings.nav.paths"])

    def test_text_novel_page_sort_updates_main_and_collection_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bookhub_text_sort_") as tmp:
            repo = LibraryRepository(db_path=str(Path(tmp) / "library.db"))
            for payload in (
                {
                    "path": "Z:/novels/alpha.txt",
                    "file_name": "alpha.txt",
                    "extension": ".txt",
                    "title": "Alpha",
                    "author": "Zulu",
                    "tags_json": '["Alpha"]',
                    "resource_type": "text_novel",
                },
                {
                    "path": "A:/novels/beta.txt",
                    "file_name": "beta.txt",
                    "extension": ".txt",
                    "title": "Beta",
                    "author": "Alpha",
                    "tags_json": '["Zulu"]',
                    "resource_type": "text_novel",
                },
            ):
                repo.upsert_book(payload)

            collection_id = repo.create_collection("Novels", kind=COLLECTION_KIND_TEXT_NOVEL)
            for row in repo.list_books(include_missing=False, resource_type="text_novel"):
                book_id = repo.get_book_int_id(str(row["resource_id"]))
                self.assertIsNotNone(book_id)
                repo.add_book_to_collection(int(book_id), collection_id)

            bridge = UiBridge(repo, set())
            interaction_events: list[dict[str, object]] = []
            bridge.interactionEvent.connect(lambda raw: interaction_events.append(json.loads(raw)))
            main_payload = json.loads(bridge.setPageSort(PAGE_TEXT, "author_asc"))
            self.assertEqual(main_payload["sort"], "author_asc")
            self.assertEqual([item["title"] for item in main_payload["items"]], ["Beta", "Alpha"])

            bridge.openCollection(PAGE_NOVEL_COLLECTIONS, collection_id)
            collection_payload = json.loads(bridge.setPageSort(PAGE_NOVEL_COLLECTIONS, "tags_desc"))
            self.assertEqual(collection_payload["sort"], "tags_desc")
            self.assertEqual([item["title"] for item in collection_payload["items"]], ["Beta", "Alpha"])
            self.assertEqual(repo.get_text_novel_sort_order_main(), "author_asc")
            self.assertEqual(repo.get_text_novel_sort_order_fav(), "tags_desc")
            self.assertEqual([event["event"] for event in interaction_events], ["sort", "sort"])
            self.assertTrue(all(event["resource_id"] is None for event in interaction_events))

            bridge.setPageSort(PAGE_COMIC, "folder_mtime_desc")
            self.assertEqual(len(interaction_events), 2)

    def test_library_page_sort_updates_main_and_collection_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bookhub_library_sort_") as tmp:
            repo = LibraryRepository(db_path=str(Path(tmp) / "library.db"))
            for payload in (
                {
                    "resource_id": "book-alpha",
                    "path": "Z:/books/alpha.pdf",
                    "file_name": "alpha.pdf",
                    "extension": ".pdf",
                    "title": "Alpha",
                    "author": "Zulu",
                    "tags_json": '["Alpha"]',
                    "resource_type": "book",
                },
                {
                    "resource_id": "book-beta",
                    "path": "A:/books/beta.pdf",
                    "file_name": "beta.pdf",
                    "extension": ".pdf",
                    "title": "Beta",
                    "author": "Alpha",
                    "tags_json": '["Zulu"]',
                    "resource_type": "book",
                },
            ):
                repo.upsert_book(payload)

            collection_id = repo.create_collection("Books")
            for resource_id in ("book-alpha", "book-beta"):
                book_id = repo.get_book_int_id(resource_id)
                self.assertIsNotNone(book_id)
                repo.add_book_to_collection(int(book_id), collection_id)

            bridge = UiBridge(repo, set())
            interaction_events: list[dict[str, object]] = []
            bridge.interactionEvent.connect(lambda raw: interaction_events.append(json.loads(raw)))
            initial_payload = json.loads(bridge.getBootstrap())["pages"][PAGE_LIBRARY]
            self.assertEqual(initial_payload["sort"], "title_asc")
            self.assertEqual([item["title"] for item in initial_payload["items"]], ["Alpha", "Beta"])

            main_payload = json.loads(bridge.setPageSort(PAGE_LIBRARY, "author_asc"))
            self.assertEqual(main_payload["sort"], "author_asc")
            self.assertEqual([item["title"] for item in main_payload["items"]], ["Beta", "Alpha"])
            search_payload = json.loads(bridge.search(PAGE_LIBRARY, "books"))
            self.assertEqual([item["title"] for item in search_payload["items"]], ["Beta", "Alpha"])

            bridge.openCollection(PAGE_COLLECTIONS, collection_id)
            collection_payload = json.loads(bridge.setPageSort(PAGE_COLLECTIONS, "title_desc"))
            self.assertEqual(collection_payload["sort"], "title_desc")
            self.assertEqual([item["title"] for item in collection_payload["items"]], ["Beta", "Alpha"])
            self.assertEqual(repo.get_library_sort_order_main(), "author_asc")
            self.assertEqual(repo.get_library_sort_order_fav(), "title_desc")
            self.assertEqual([event["event"] for event in interaction_events], ["sort", "sort"])
            self.assertTrue(all(event["resource_id"] is None for event in interaction_events))

            reopened = UiBridge(LibraryRepository(db_path=str(Path(tmp) / "library.db")), set())
            reopened_main = json.loads(reopened.getBootstrap())["pages"][PAGE_LIBRARY]
            reopened_collection = json.loads(reopened.openCollection(PAGE_COLLECTIONS, collection_id))
            self.assertEqual(reopened_main["sort"], "author_asc")
            self.assertEqual([item["title"] for item in reopened_main["items"]], ["Beta", "Alpha"])
            self.assertEqual(reopened_collection["sort"], "title_desc")
            self.assertEqual([item["title"] for item in reopened_collection["items"]], ["Beta", "Alpha"])

    def test_nav_items_typed_collections_order(self) -> None:
        pages = [page for page, _, _ in NAV_ITEMS]
        self.assertEqual(
            pages,
            [
                "library",
                "collections",
                "text_novel",
                "novel_collections",
                "comic",
                "comic_collections",
                "random_recommendations",
                "tag_manager",
            ],
        )
        self.assertEqual(PAGE_RANDOM_RECOMMENDATIONS, "random_recommendations")
        self.assertNotIn("favorites", pages)
        self.assertNotIn("comic_fav", pages)

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
            resource_id = str(comics[0]["resource_id"])
            bridge = UiBridge(repo, set())
            opened: list[str] = []
            events: list[dict[str, object]] = []
            bridge.interactionEvent.connect(lambda raw: events.append(json.loads(raw)))

            def capture_open(path: str) -> None:
                opened.append(path)

            with patch.object(bridge, "_open_external", side_effect=capture_open):
                bridge.openResource(PAGE_COMIC, resource_id)

            self.assertEqual(len(opened), 1)
            self._assert_open_external_event(events, resource_id)
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
            resource_id = str(comics[0]["resource_id"])
            bridge = UiBridge(repo, set())
            opened: list[str] = []
            events: list[dict[str, object]] = []
            bridge.interactionEvent.connect(lambda raw: events.append(json.loads(raw)))

            def capture_open(path: str) -> None:
                opened.append(path)

            with patch.object(bridge, "_open_external", side_effect=capture_open):
                bridge.openResource(PAGE_COMIC, resource_id)

            self.assertEqual(opened, [str(cover)])
            self._assert_open_external_event(events, resource_id)

    def test_open_resource_missing_target_does_not_emit_interaction_event(self) -> None:
        bridge = self._make_bridge()
        events: list[dict[str, object]] = []
        bridge.interactionEvent.connect(lambda raw: events.append(json.loads(raw)))

        with patch.object(bridge, "_open_external") as mocked_open:
            bridge.openResource(PAGE_LIBRARY, "missing-resource")
            mocked_open.assert_not_called()
        self.assertEqual(events, [])

        bridge._repo.upsert_book(
            {
                "path": "C:/missing/does-not-exist.epub",
                "title": "Ghost EPUB",
                "file_name": "does-not-exist.epub",
                "extension": ".epub",
                "resource_type": "epub",
                "tags_json": "[]",
            }
        )
        bridge.reload_data()
        items = json.loads(bridge.getBootstrap())["pages"]["library"]["items"]
        book = next(item for item in items if item.get("title") == "Ghost EPUB")

        with patch.object(bridge, "_open_external") as mocked_open:
            bridge.openResource(PAGE_LIBRARY, str(book["id"]))
            mocked_open.assert_called_once()
        self.assertEqual(events, [])


class SettingsUiStructureTests(unittest.TestCase):
    def test_shortcut_settings_ui_and_both_skins_are_wired(self) -> None:
        app_js = (PROJECT_ROOT / "src" / "bookhub" / "ui" / "web" / "js" / "app.js").read_text(encoding="utf-8")
        strings = (PROJECT_ROOT / "src" / "bookhub" / "ui" / "web_bridge.py").read_text(encoding="utf-8")
        locale = (PROJECT_ROOT / "src" / "bookhub" / "i18n" / "locales" / "zh-cn.json").read_text(encoding="utf-8")
        self.assertIn('["shortcuts", "settings.nav.shortcuts"]', app_js)
        self.assertIn("function renderSettingsShortcuts(panel)", app_js)
        self.assertIn('"reopen_recent_collection"', app_js)
        self.assertIn('"exit_collection"', app_js)
        self.assertNotIn("toggle_recent_collection", app_js)
        self.assertIn("function executeAction(actionId, context)", app_js)
        self.assertIn("function handleShortcutSideButton(event)", app_js)
        self.assertIn("function handleShortcutMouseDown(event)", app_js)
        self.assertIn('code === "BrowserBack"', app_js)
        self.assertIn("buttons & 8", app_js)
        self.assertIn("keyCode === 166", app_js)
        self.assertIn("nativeShortcutInput.connect(handleNativeShortcutInput)", app_js)
        self.assertIn('("settings.nav.shortcuts", "Shortcuts")', strings)
        self.assertIn('"settings.nav.shortcuts": "快捷键"', locale)
        css_root = PROJECT_ROOT / "src" / "bookhub" / "ui" / "web" / "css" / "skins"
        for skin in ("glass", "vaporwave"):
            css = (css_root / skin / "components.css").read_text(encoding="utf-8")
            self.assertIn(".shortcut-row", css)
            self.assertIn(".shortcut-keycap", css)
            self.assertIn("grid-template-columns: minmax(0, 1fr)", css)

    @unittest.skipUnless(QT_AVAILABLE, "PySide6/WebEngine is not available")
    def test_win_side_button_messages_map_to_tokens(self) -> None:
        from bookhub.ui.web_window import (
            APPCOMMAND_BROWSER_BACKWARD,
            APPCOMMAND_BROWSER_FORWARD,
            WM_APPCOMMAND,
            WM_XBUTTONDOWN,
            token_from_win_mouse_message,
        )

        self.assertEqual(token_from_win_mouse_message(WM_XBUTTONDOWN, 1 << 16), "MouseBack")
        self.assertEqual(token_from_win_mouse_message(WM_XBUTTONDOWN, 2 << 16), "MouseForward")
        self.assertEqual(
            token_from_win_mouse_message(WM_APPCOMMAND, 0, APPCOMMAND_BROWSER_BACKWARD << 16),
            "MouseBack",
        )
        self.assertEqual(
            token_from_win_mouse_message(WM_APPCOMMAND, 0, APPCOMMAND_BROWSER_FORWARD << 16),
            "MouseForward",
        )
        self.assertIsNone(token_from_win_mouse_message(0x0201, 0, 0))

    @unittest.skipUnless(QT_AVAILABLE, "PySide6/WebEngine is not available")
    def test_native_web_view_captures_mouse_side_buttons(self) -> None:
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent

        from bookhub.ui.web_window import ShortcutWebView

        app = QApplication.instance() or QApplication([])
        view = ShortcutWebView()
        inputs: list[str] = []
        view.nativeShortcutInput.connect(inputs.append)

        for button in (Qt.BackButton, Qt.ForwardButton):
            press_event = QMouseEvent(
                QEvent.MouseButtonPress,
                QPointF(5, 5),
                QPointF(5, 5),
                button,
                button,
                Qt.NoModifier,
            )
            release_event = QMouseEvent(
                QEvent.MouseButtonRelease,
                QPointF(5, 5),
                QPointF(5, 5),
                button,
                Qt.NoButton,
                Qt.NoModifier,
            )
            app.sendEvent(view, press_event)
            app.sendEvent(view, release_event)
            self.assertTrue(press_event.isAccepted())
            self.assertTrue(release_event.isAccepted())

        self.assertEqual(inputs, ["MouseBack", "MouseForward"])
        view.deleteLater()

    @unittest.skipUnless(QT_AVAILABLE, "PySide6/WebEngine is not available")
    def test_native_web_view_captures_side_buttons_on_child_widget(self) -> None:
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtWidgets import QWidget

        from bookhub.ui.web_window import ShortcutWebView

        app = QApplication.instance() or QApplication([])
        view = ShortcutWebView()

        class _EatingChild(QWidget):
            def mousePressEvent(self, event) -> None:  # type: ignore[override]
                event.accept()

        child = _EatingChild(view)
        child.resize(40, 40)
        inputs: list[str] = []
        view.nativeShortcutInput.connect(inputs.append)

        press_event = QMouseEvent(
            QEvent.MouseButtonPress,
            QPointF(5, 5),
            QPointF(5, 5),
            Qt.BackButton,
            Qt.BackButton,
            Qt.NoModifier,
        )
        app.sendEvent(child, press_event)
        self.assertTrue(press_event.isAccepted())
        self.assertEqual(inputs, ["MouseBack"])
        view.deleteLater()

    def test_random_recommendation_density_settings_are_exposed(self) -> None:
        app_js = (PROJECT_ROOT / "src" / "bookhub" / "ui" / "web" / "js" / "app.js").read_text(encoding="utf-8")
        web_window = (PROJECT_ROOT / "src" / "bookhub" / "ui" / "web_window.py").read_text(encoding="utf-8")
        self.assertIn('"settings.recommendation_items_per_category", "recommendationItemsPerCategory"', app_js)
        self.assertIn('"settings.recommendation_columns_per_category", "recommendationColumnsPerCategory"', app_js)
        self.assertIn('key == "recommendationItemsPerCategory"', web_window)
        self.assertIn('key == "recommendationColumnsPerCategory"', web_window)

    def test_random_recommendation_cards_do_not_use_fixed_148px_tracks(self) -> None:
        css_root = PROJECT_ROOT / "src" / "bookhub" / "ui" / "web" / "css" / "skins"
        for skin in ("glass", "vaporwave"):
            css = (css_root / skin / "components.css").read_text(encoding="utf-8")
            self.assertNotIn("grid-template-columns: minmax(0, 148px)", css)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not available")
    def test_random_recommendations_frontend_behavior(self) -> None:
        script = PROJECT_ROOT / "src" / "tests" / "js" / "test_random_recommendations.js"
        app_js = PROJECT_ROOT / "src" / "bookhub" / "ui" / "web" / "js" / "app.js"
        completed = subprocess.run(
            [shutil.which("node") or "node", str(script), str(app_js)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("RANDOM_RECOMMENDATIONS_BEHAVIOR_OK", completed.stdout)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not available")
    def test_tag_management_frontend_behavior(self) -> None:
        script = PROJECT_ROOT / "src" / "tests" / "js" / "test_tag_management.js"
        app_js = PROJECT_ROOT / "src" / "bookhub" / "ui" / "web" / "js" / "app.js"
        completed = subprocess.run(
            [shutil.which("node") or "node", str(script), str(app_js)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("TAG_MANAGEMENT_BEHAVIOR_OK", completed.stdout)

    def test_text_novel_thumbnail_tasks_are_exposed_in_settings_and_worker(self) -> None:
        app_js = (PROJECT_ROOT / "src" / "bookhub" / "ui" / "web" / "js" / "app.js").read_text(encoding="utf-8")
        worker_py = (PROJECT_ROOT / "src" / "bookhub" / "library" / "thumbnail_worker.py").read_text(encoding="utf-8")
        base_css = (PROJECT_ROOT / "src" / "bookhub" / "ui" / "web" / "css" / "base.css").read_text(encoding="utf-8")

        self.assertIn('["cleanup","text_novel","settings.tasks.cleanup_text"]', app_js)
        self.assertIn('["regenerate","text_novel","settings.tasks.regen_text"]', app_js)
        self.assertIn('self._task_scope == "text_novel"', worker_py)
        self.assertIn('body:is([data-page="text_novel"], [data-page="settings"])', base_css)
        self.assertIn('body[data-page="settings"] [data-library-task-btn="thumb"]', base_css)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not available")
    def test_shortcuts_frontend_behavior(self) -> None:
        script = PROJECT_ROOT / "src" / "tests" / "js" / "test_shortcuts.js"
        app_js = PROJECT_ROOT / "src" / "bookhub" / "ui" / "web" / "js" / "app.js"
        completed = subprocess.run(
            [shutil.which("node") or "node", str(script), str(app_js)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("SHORTCUTS_BEHAVIOR_OK", completed.stdout)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not available")
    def test_quick_add_frontend_behavior(self) -> None:
        script = PROJECT_ROOT / "src" / "tests" / "js" / "test_quick_add.js"
        app_js = PROJECT_ROOT / "src" / "bookhub" / "ui" / "web" / "js" / "app.js"
        completed = subprocess.run(
            [shutil.which("node") or "node", str(script), str(app_js)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("QUICK_ADD_BEHAVIOR_OK", completed.stdout)

    def test_random_recommendations_keep_source_page_for_actions(self) -> None:
        app_js = (PROJECT_ROOT / "src" / "bookhub" / "ui" / "web" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("selectRecommendedResource(column.sourcePage", app_js)
        self.assertIn("State.bridge.openResource(column.sourcePage", app_js)
        self.assertIn("openContextMenu(event, column.sourcePage", app_js)
        self.assertIn("function renderDetail(d, sourcePage)", app_js)
        self.assertIn("function openQuickAddModal(item, sourcePage)", app_js)

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
