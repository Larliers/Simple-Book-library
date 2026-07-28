from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.ui.models.resource import ResourceItem
from bookhub.ui.viewmodels.library_viewmodel import LibraryViewModel

try:
    from bookhub.ui.web_bridge import PAGE_COMIC, PAGE_COMIC_FAV, UiBridge

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - optional UI dependency
    PAGE_COMIC = "comic"
    PAGE_COMIC_FAV = "comic_fav"
    UiBridge = None  # type: ignore[assignment,misc]
    QT_AVAILABLE = False


def _comic_item(
    resource_id: str,
    title: str,
    path: str,
    info_text: str | None = None,
) -> ResourceItem:
    return ResourceItem(
        resource_id=resource_id,
        title=title,
        path=path,
        resource_type="comic_folder",
        info_text=info_text,
    )


class ComicSearchViewModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.view_model = LibraryViewModel()
        self.view_model.set_resources(
            [
                _comic_item("comic-1", "进击的巨人", "D:/comics/shingeki"),
                _comic_item("comic-2", "海贼王", "D:/comics/one-piece", info_text="长篇连载"),
                _comic_item("comic-3", "Death Note", "D:/comics/death-note"),
            ]
        )

    def test_title_search_matches_comic_title(self) -> None:
        self.view_model.set_query("进击")
        self.assertEqual([item.resource_id for item in self.view_model.filtered_resources()], ["comic-1"])

    def test_path_search_matches_comic_path(self) -> None:
        self.view_model.set_query("one-piece")
        self.assertEqual([item.resource_id for item in self.view_model.filtered_resources()], ["comic-2"])

    def test_info_text_search_matches_comic_notes(self) -> None:
        self.view_model.set_query("长篇")
        self.assertEqual([item.resource_id for item in self.view_model.filtered_resources()], ["comic-2"])

    def test_empty_query_returns_all_comics(self) -> None:
        self.view_model.set_query("")
        self.assertEqual(
            {item.resource_id for item in self.view_model.filtered_resources()},
            {"comic-1", "comic-2", "comic-3"},
        )

    def test_title_prefix_search(self) -> None:
        self.view_model.set_query("title:death")
        self.assertEqual([item.resource_id for item in self.view_model.filtered_resources()], ["comic-3"])


@unittest.skipUnless(QT_AVAILABLE, "PySide6 is not available")
class UiBridgeComicSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = MagicMock()
        self.repo.list_books.return_value = []
        self.repo.get_comic_sort_order_main.return_value = "folder_name_asc"
        self.repo.get_comic_sort_order_fav.return_value = "folder_name_asc"
        self.repo.get_comic_view_mode.return_value = "waterfall"
        self.repo.get_comic_page_size.return_value = 48
        self.repo.list_comics.return_value = [
            {
                "resource_id": "comic-1",
                "title": "Alpha Comic",
                "path": "D:/comics/alpha",
                "cover_image_path": "",
                "thumbnail_path": None,
                "image_count": 10,
                "info_text": "",
                "is_missing": False,
            },
            {
                "resource_id": "comic-2",
                "title": "Beta Comic",
                "path": "D:/comics/beta",
                "cover_image_path": "",
                "thumbnail_path": None,
                "image_count": 5,
                "info_text": "",
                "is_missing": False,
            },
        ]
        self.repo.get_favorite_comics.return_value = [
            {
                "resource_id": "comic-2",
                "title": "Beta Comic",
                "path": "D:/comics/beta",
                "cover_image_path": "",
                "thumbnail_path": None,
                "image_count": 5,
                "info_text": "",
                "is_missing": False,
            }
        ]
        self.bridge = UiBridge(self.repo, allowed_images=set())

    def test_search_filters_comic_page(self) -> None:
        payload = self.bridge.search(PAGE_COMIC, "alpha")
        import json

        data = json.loads(payload)
        self.assertEqual([item["id"] for item in data["items"]], ["comic-1"])

    def test_search_filters_comic_fav_page_independently(self) -> None:
        import json

        self.bridge.search(PAGE_COMIC, "alpha")
        payload = self.bridge.search(PAGE_COMIC_FAV, "beta")
        data = json.loads(payload)
        self.assertEqual([item["id"] for item in data["items"]], ["comic-2"])

        comic_payload = json.loads(self.bridge.search(PAGE_COMIC, ""))
        self.assertEqual({item["id"] for item in comic_payload["items"]}, {"comic-1", "comic-2"})


if __name__ == "__main__":
    unittest.main()
