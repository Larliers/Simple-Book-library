from __future__ import annotations

import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    from PySide6.QtWidgets import QApplication
    from bookhub.ui.pages.comic_page import ComicPage
    QT_AVAILABLE = True
except Exception:  # pragma: no cover - optional UI dependency
    QApplication = None  # type: ignore[assignment]
    ComicPage = None  # type: ignore[assignment]
    QT_AVAILABLE = False


class FakeComicRepository:
    def __init__(self) -> None:
        self._settings: dict[str, object] = {}
        self._comic_rows: list[dict[str, object]] = [
            {
                "id": 101,
                "resource_id": "comic-101",
                "title": "Alpha",
                "path": "/comic/alpha",
                "cover_image_path": "/comic/alpha/001.png",
                "thumbnail_path": "file:///tmp/alpha.webp",
                "image_count": 5,
                "info_text": "",
                "is_missing": 0,
            }
        ]
        self._favorite_ids: set[int] = set()
        self.list_comics_calls = 0
        self.favorite_comics_calls = 0

    def get_comic_sort_order_main(self) -> str:
        return str(self._settings.get("comic_sort_order_main", "folder_mtime_desc"))

    def get_comic_sort_order_fav(self) -> str:
        return str(self._settings.get("comic_sort_order_fav", "folder_mtime_desc"))

    def set_comic_sort_order_main(self, value: str) -> None:
        self._settings["comic_sort_order_main"] = value

    def set_comic_sort_order_fav(self, value: str) -> None:
        self._settings["comic_sort_order_fav"] = value

    def get_comic_view_mode(self) -> str:
        return str(self._settings.get("comic_view_mode", "pagination"))

    def set_comic_view_mode(self, value: str) -> None:
        self._settings["comic_view_mode"] = value

    def get_comic_page_size(self) -> int:
        return int(self._settings.get("comic_page_size", 24))

    def set_comic_page_size(self, value: int) -> None:
        self._settings["comic_page_size"] = int(value)

    def get_setting(self, key: str, default: object = None) -> object:
        return self._settings.get(key, default)

    def set_setting(self, key: str, value: object) -> None:
        self._settings[key] = value

    def list_comics(self, include_missing: bool | None = None, order_by: str = "folder_mtime_desc") -> list[dict[str, object]]:
        _ = (include_missing, order_by)
        self.list_comics_calls += 1
        return [deepcopy(item) for item in self._comic_rows]

    def get_favorite_comics(self, order: str = "desc", order_by: str | None = None) -> list[dict[str, object]]:
        _ = (order, order_by)
        self.favorite_comics_calls += 1
        return [deepcopy(item) for item in self._comic_rows if int(item["id"]) in self._favorite_ids]

    def get_comic_int_id(self, resource_id: str) -> int | None:
        for row in self._comic_rows:
            if str(row.get("resource_id") or "") == resource_id:
                return int(row["id"])
        return None

    def add_comic_to_favorites(self, comic_id: int) -> None:
        self._favorite_ids.add(int(comic_id))

    def remove_comic_from_favorites(self, comic_id: int) -> None:
        self._favorite_ids.discard(int(comic_id))

    def is_favorite_comic(self, comic_id: int) -> bool:
        return int(comic_id) in self._favorite_ids

    def update_first_thumbnail(self, thumbnail_path: str) -> None:
        if not self._comic_rows:
            return
        self._comic_rows[0]["thumbnail_path"] = thumbnail_path


@unittest.skipUnless(QT_AVAILABLE, "PySide6 is required for comic page UI cache tests")
class ComicPageCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.repo = FakeComicRepository()

    def tearDown(self) -> None:
        QApplication.processEvents()

    def test_data_cache_skips_repository_until_invalidated(self) -> None:
        page = ComicPage(self.repo, favorite_only=False)
        try:
            self.assertEqual(self.repo.list_comics_calls, 1)
            page.refresh()
            self.assertEqual(self.repo.list_comics_calls, 1)

            page.invalidate_cache()
            page.refresh()
            self.assertEqual(self.repo.list_comics_calls, 2)
        finally:
            page.deleteLater()

    def test_render_cache_reuses_card_and_rebuilds_on_signature_change(self) -> None:
        page = ComicPage(self.repo, favorite_only=False)
        try:
            resource_id = page._resources[0].resource_id
            card_first = page._card_by_resource_id[resource_id]

            page.refresh()
            card_second = page._card_by_resource_id[resource_id]
            self.assertIs(card_first, card_second)

            self.repo.update_first_thumbnail("file:///tmp/alpha-v2.webp")
            page.invalidate_cache()
            page.refresh()
            card_third = page._card_by_resource_id[resource_id]
            self.assertIsNot(card_first, card_third)
        finally:
            page.deleteLater()

    def test_favorite_chain_updates_favorite_page_after_invalidation(self) -> None:
        main_page = ComicPage(self.repo, favorite_only=False)
        favorite_page = ComicPage(self.repo, favorite_only=True)
        try:
            main_page.favorites_changed.connect(favorite_page.invalidate_cache)
            self.assertEqual(len(favorite_page._resources), 0)

            main_page._toggle_favorite(main_page._resources[0])
            favorite_page.refresh()
            self.assertEqual(len(favorite_page._resources), 1)

            main_page._toggle_favorite(main_page._resources[0])
            favorite_page.refresh()
            self.assertEqual(len(favorite_page._resources), 0)
        finally:
            main_page.deleteLater()
            favorite_page.deleteLater()


if __name__ == "__main__":
    unittest.main()
