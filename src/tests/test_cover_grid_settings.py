from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.repository import LibraryRepository
from bookhub.ui.resources.layout_config import (
    DEFAULT_COVER_SELECTED_BORDER_COLOR,
    DEFAULT_COVER_SELECTED_BORDER_WIDTH,
    normalize_cover_selected_border_color,
    normalize_cover_selected_border_width,
)

try:
    from PySide6.QtWidgets import QApplication

    from bookhub.ui.models.resource import ResourceItem
    from bookhub.ui.pages.library_page import LibraryPage
    from bookhub.ui.viewmodels.library_viewmodel import LibraryViewModel
    from bookhub.ui.widgets.book_card import BookCardWidget

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - optional UI dependency
    QApplication = None  # type: ignore[assignment]
    BookCardWidget = None  # type: ignore[assignment]
    LibraryPage = None  # type: ignore[assignment]
    LibraryViewModel = None  # type: ignore[assignment]
    ResourceItem = None  # type: ignore[assignment]
    QT_AVAILABLE = False


class CoverGridSettingsTests(unittest.TestCase):
    def test_cover_border_normalizers(self) -> None:
        self.assertEqual(normalize_cover_selected_border_width(None), DEFAULT_COVER_SELECTED_BORDER_WIDTH)
        self.assertEqual(normalize_cover_selected_border_width(-1), 1)
        self.assertEqual(normalize_cover_selected_border_width(100), 6)
        self.assertEqual(normalize_cover_selected_border_width("3"), 3)

        self.assertEqual(
            normalize_cover_selected_border_color(None),
            DEFAULT_COVER_SELECTED_BORDER_COLOR,
        )
        self.assertEqual(
            normalize_cover_selected_border_color("#zzzzzz"),
            DEFAULT_COVER_SELECTED_BORDER_COLOR,
        )
        self.assertEqual(normalize_cover_selected_border_color("00ff7a"), "#00FF7A")

    def test_repository_cover_border_settings_persist_and_normalize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = LibraryRepository(
                db_path=root / "library.db",
                scan_report_path=root / "scan_report.json",
            )
            self.assertEqual(repo.get_cover_selected_border_width(), DEFAULT_COVER_SELECTED_BORDER_WIDTH)
            self.assertEqual(repo.get_cover_selected_border_color(), DEFAULT_COVER_SELECTED_BORDER_COLOR)

            repo.set_cover_selected_border_width(999)
            repo.set_cover_selected_border_color("invalid")
            self.assertEqual(repo.get_cover_selected_border_width(), 6)
            self.assertEqual(repo.get_cover_selected_border_color(), DEFAULT_COVER_SELECTED_BORDER_COLOR)

            repo.set_cover_selected_border_width(4)
            repo.set_cover_selected_border_color("#11aaee")

            repo_reload = LibraryRepository(
                db_path=root / "library.db",
                scan_report_path=root / "scan_report.json",
            )
            self.assertEqual(repo_reload.get_cover_selected_border_width(), 4)
            self.assertEqual(repo_reload.get_cover_selected_border_color(), "#11AAEE")


@unittest.skipUnless(QT_AVAILABLE, "PySide6 is required for cover grid UI tests")
class CoverGridUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_book_card_selected_toggle_does_not_crash(self) -> None:
        item = ResourceItem(
            resource_id="book-1",
            title="Title",
            author="Author",
            status="UNREAD",
            tags=[],
            resource_type="book",
            path="/tmp/book.pdf",
            thumbnail_path=None,
        )
        card = BookCardWidget(item, cover_only=True)
        try:
            card.set_selected(True)
            card.set_selected(False)
            self.assertTrue(True)
        finally:
            card.deleteLater()

    def test_library_grid_no_longer_renders_add_card_tile(self) -> None:
        view_model = LibraryViewModel()
        view_model.set_resources(
            [
                ResourceItem(
                    resource_id="book-1",
                    title="Title",
                    author="Author",
                    status="UNREAD",
                    tags=[],
                    resource_type="book",
                    path="/tmp/book.pdf",
                    thumbnail_path=None,
                )
            ]
        )
        page = LibraryPage(view_model, repository=None)
        try:
            page.set_view_mode("waterfall")
            add_card_count = 0
            for idx in range(page.grid_layout.count()):
                item = page.grid_layout.itemAt(idx)
                widget = item.widget() if item is not None else None
                if widget is not None and widget.objectName() == "AddCard":
                    add_card_count += 1
            self.assertEqual(add_card_count, 0)
        finally:
            page.deleteLater()


if __name__ == "__main__":
    unittest.main()
