from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr
from bookhub.ui.models.resource import ResourceItem
from bookhub.ui.resources.layout_config import UI_LAYOUT
from bookhub.ui.widgets.book_card import BookCardWidget

SORT_ORDER_SETTING_KEY = "favorites_sort_order"
SORT_ORDER_DESC = "desc"
SORT_ORDER_ASC = "asc"


def _parse_tags(raw_value: object) -> list[str]:
    if isinstance(raw_value, list):
        return [str(item) for item in raw_value if str(item).strip()]
    if isinstance(raw_value, str):
        try:
            loaded = json.loads(raw_value)
        except json.JSONDecodeError:
            return []
        if isinstance(loaded, list):
            return [str(item) for item in loaded if str(item).strip()]
    return []


def _normalize_sort_order(value: object) -> str:
    text = str(value or "").strip().lower()
    return SORT_ORDER_ASC if text == SORT_ORDER_ASC else SORT_ORDER_DESC


class FavoritesPage(QWidget):
    """Favorites page as a flat list of favorited books (not reading lists)."""

    def __init__(self, repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repository
        self._sort_order = self._load_sort_order()
        self._book_id_by_resource_id: dict[str, int] = {}
        self._resources: list[ResourceItem] = []
        self._last_columns = 0
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self._title = QLabel()
        self._title.setObjectName("PageTitle")
        self._subtitle = QLabel()
        self._subtitle.setObjectName("PageSubtitle")

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(self._title)
        title_col.addWidget(self._subtitle)
        header_row.addLayout(title_col, 1)

        self._sort_label = QLabel()
        self._sort_label.setObjectName("PageSubtitle")
        self._sort_combo = QComboBox()
        self._sort_combo.setMinimumWidth(190)
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        header_row.addWidget(self._sort_label, 0, Qt.AlignRight | Qt.AlignVCenter)
        header_row.addWidget(self._sort_combo, 0, Qt.AlignRight | Qt.AlignVCenter)
        root.addLayout(header_row)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setVerticalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._scroll.setWidget(self._container)
        root.addWidget(self._scroll, 1)

        self._empty_label = QLabel()
        self._empty_label.setObjectName("PageSubtitle")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.hide()
        root.addWidget(self._empty_label, 1)

        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self._title.setText(tr("favorites.page.title", "Favorites"))
        self._empty_label.setText(tr("favorites.page.empty", "No favorite books yet."))
        self._sort_label.setText(tr("favorites.sort.label", "Sort"))
        self._sort_combo.blockSignals(True)
        self._sort_combo.clear()
        self._sort_combo.addItem(tr("favorites.sort.added_desc", "Added Time: Newest First"), SORT_ORDER_DESC)
        self._sort_combo.addItem(tr("favorites.sort.added_asc", "Added Time: Oldest First"), SORT_ORDER_ASC)
        selected_index = self._sort_combo.findData(self._sort_order)
        self._sort_combo.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self._sort_combo.blockSignals(False)

    def refresh(self) -> None:
        records = (
            self._repo.get_favorite_books(order=self._sort_order) if self._repo is not None else []
        )
        self._book_id_by_resource_id.clear()

        resources: list[ResourceItem] = []
        for record in records:
            resource_id = str(record.get("resource_id") or "").strip()
            if not resource_id:
                continue

            book_id_value = record.get("id")
            if isinstance(book_id_value, int):
                self._book_id_by_resource_id[resource_id] = book_id_value

            title = str(record.get("title") or "").strip() or Path(
                str(record.get("file_name") or "")
            ).stem or "Unknown"
            resources.append(
                ResourceItem(
                    resource_id=resource_id,
                    title=title,
                    author=str(record.get("author") or ""),
                    status=str(record.get("status") or "UNREAD"),
                    tags=_parse_tags(record.get("tags_json")),
                    resource_type=str(record.get("resource_type") or "book"),
                    path=str(record.get("path") or ""),
                    thumbnail_path=record.get("thumbnail_path"),
                    publisher=record.get("publisher"),
                    language=record.get("language"),
                    is_missing=bool(record.get("is_missing")),
                    file_name=str(record.get("file_name") or ""),
                    extension=str(record.get("extension") or ""),
                )
            )
        self._resources = resources

        count = len(self._resources)
        self._subtitle.setText(
            tr("favorites.page.subtitle.count", "{count} books in favorites").format(count=count)
        )

        if not self._resources:
            while self._grid.count():
                item = self._grid.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
            self._scroll.hide()
            self._empty_label.show()
            return

        self._empty_label.hide()
        self._scroll.show()
        self._render_grid()

    def _render_grid(self) -> None:
        self._grid.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setVerticalSpacing(UI_LAYOUT.card_spacing)
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        columns = self._calculate_columns()
        self._last_columns = columns
        for idx, resource in enumerate(self._resources):
            row = idx // columns
            col = idx % columns
            card = BookCardWidget(resource)
            card.open_requested.connect(lambda _pos, res=resource: self._open_external(res.path))
            card.setContextMenuPolicy(Qt.CustomContextMenu)
            card.customContextMenuRequested.connect(
                lambda pos, res=resource, widget=card: self._show_card_menu(res, widget.mapToGlobal(pos))
            )
            self._grid.addWidget(card, row, col, alignment=Qt.AlignLeft | Qt.AlignTop)

    def _show_card_menu(self, resource: ResourceItem, global_pos) -> None:
        menu = QMenu(self)
        open_action = menu.addAction(tr("favorites.menu.open_external", "Open External"))
        remove_action = menu.addAction(tr("favorites.menu.remove_favorite", "Remove from Favorites"))
        chosen = menu.exec(global_pos)
        if chosen == open_action:
            self._open_external(resource.path)
        elif chosen == remove_action:
            self._remove_favorite(resource.resource_id)

    def _remove_favorite(self, resource_id: str) -> None:
        if self._repo is None:
            return
        book_id = self._book_id_by_resource_id.get(resource_id)
        if book_id is None:
            return
        try:
            self._repo.remove_from_favorites(book_id)
            self.refresh()
        except Exception as e:
            print(f"[FavoritesPage] remove favorite error: {e}")

    def _open_external(self, path: str) -> None:
        file_path = Path(path).expanduser()
        if not str(file_path).strip() or not file_path.exists():
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(file_path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(file_path)])
            else:
                subprocess.Popen(["xdg-open", str(file_path)])
        except Exception as e:
            print(f"[FavoritesPage] open external error: {e}")

    def _calculate_columns(self) -> int:
        available_width = max(1, self._scroll.viewport().width())
        cell_width = UI_LAYOUT.card_width + UI_LAYOUT.card_spacing
        return max(1, available_width // max(1, cell_width))

    def apply_card_spacing(self, _spacing: int) -> None:
        self._grid.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setVerticalSpacing(UI_LAYOUT.card_spacing)
        if self._resources:
            self._render_grid()

    def _load_sort_order(self) -> str:
        if self._repo is None:
            return SORT_ORDER_DESC
        raw_value = self._repo.get_setting(SORT_ORDER_SETTING_KEY, SORT_ORDER_DESC)
        return _normalize_sort_order(raw_value)

    def _save_sort_order(self, order: str) -> None:
        if self._repo is None:
            return
        self._repo.set_setting(SORT_ORDER_SETTING_KEY, _normalize_sort_order(order))

    def _on_sort_changed(self, _index: int) -> None:
        selected = _normalize_sort_order(self._sort_combo.currentData())
        if selected == self._sort_order:
            return
        self._sort_order = selected
        self._save_sort_order(selected)
        self.refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        columns = self._calculate_columns()
        if columns != self._last_columns and self._resources:
            self._render_grid()
