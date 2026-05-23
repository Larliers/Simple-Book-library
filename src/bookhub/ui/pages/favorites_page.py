from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr
from bookhub.ui.models.resource import ResourceItem
from bookhub.ui.pages.library_page import BookDetailPanel
from bookhub.ui.resources.assets import load_icon
from bookhub.ui.resources.layout_config import UI_LAYOUT
from bookhub.ui.widgets.book_card import BookCardWidget
from bookhub.ui.widgets.book_card import format_author_publisher_meta

SORT_ORDER_SETTING_KEY = "favorites_sort_order"
SORT_ORDER_DESC = "desc"
SORT_ORDER_ASC = "asc"
VIEW_MODE_SETTING_KEY = "favorites_view_mode"
VIEW_MODE_WATERFALL = "waterfall"
VIEW_MODE_LIST = "list"


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


def _normalize_view_mode(value: object) -> str:
    text = str(value or "").strip().lower()
    return VIEW_MODE_LIST if text == VIEW_MODE_LIST else VIEW_MODE_WATERFALL


class FavoritesPage(QWidget):
    """Favorites page as a flat list of favorited books (not reading lists)."""

    def __init__(self, repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repository
        self._sort_order = self._load_sort_order()
        self._view_mode = self._load_view_mode()
        self._book_id_by_resource_id: dict[str, int] = {}
        self._resources: list[ResourceItem] = []
        self._resource_by_id: dict[str, ResourceItem] = {}
        self._selected_resource_id: str | None = None
        self._card_by_resource_id: dict[str, BookCardWidget] = {}
        self._card_signature_by_resource_id: dict[str, tuple[str, str, str]] = {}
        self._last_columns = 0
        self._setup_ui()
        self.refresh(force=True)

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

        self._view_toggle_panel = QFrame()
        self._view_toggle_panel.setObjectName("ViewTogglePanel")
        view_toggle_layout = QHBoxLayout(self._view_toggle_panel)
        view_toggle_layout.setContentsMargins(0, 0, 0, 0)
        view_toggle_layout.setSpacing(2)

        self._grid_btn = QPushButton()
        self._grid_btn.setObjectName("ViewToggleButton")
        self._grid_btn.setCheckable(True)
        self._grid_btn.setIcon(load_icon("view_grid.svg"))
        self._grid_btn.setIconSize(QSize(14, 14))
        self._grid_btn.clicked.connect(lambda: self._set_view_mode(VIEW_MODE_WATERFALL))
        view_toggle_layout.addWidget(self._grid_btn)

        self._list_btn = QPushButton()
        self._list_btn.setObjectName("ViewToggleButton")
        self._list_btn.setCheckable(True)
        self._list_btn.setIcon(load_icon("view_list.svg"))
        self._list_btn.setIconSize(QSize(14, 14))
        self._list_btn.clicked.connect(lambda: self._set_view_mode(VIEW_MODE_LIST))
        view_toggle_layout.addWidget(self._list_btn)
        header_row.addWidget(self._view_toggle_panel, 0, Qt.AlignRight | Qt.AlignVCenter)

        self._sort_label = QLabel()
        self._sort_label.setObjectName("PageSubtitle")
        self._sort_combo = QComboBox()
        self._sort_combo.setMinimumWidth(190)
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        header_row.addWidget(self._sort_label, 0, Qt.AlignRight | Qt.AlignVCenter)
        header_row.addWidget(self._sort_combo, 0, Qt.AlignRight | Qt.AlignVCenter)
        root.addLayout(header_row)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setObjectName("LibraryContentSplitter")
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.splitterMoved.connect(self._on_main_splitter_moved)

        self.main_pane = QWidget()
        self.main_pane.setObjectName("LibraryMainPane")
        pane_layout = QVBoxLayout(self.main_pane)
        pane_layout.setContentsMargins(0, 0, 0, 0)
        pane_layout.setSpacing(0)

        self._view_stack = QStackedWidget()

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setVerticalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setContentsMargins(UI_LAYOUT.grid_left_inset, 0, 0, 0)
        self._grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._scroll.setWidget(self._container)
        self._view_stack.addWidget(self._scroll)

        self._list_table = QTableWidget(0, 4)
        self._list_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._list_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._list_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list_table.customContextMenuRequested.connect(self._show_list_menu)
        self._list_table.horizontalHeader().setStretchLastSection(True)
        self._list_table.verticalHeader().setVisible(False)
        self._list_table.cellClicked.connect(self._on_list_row_clicked)
        self._list_table.cellDoubleClicked.connect(self._on_list_row_double_clicked)
        self._view_stack.addWidget(self._list_table)
        pane_layout.addWidget(self._view_stack, 1)

        self._empty_label = QLabel()
        self._empty_label.setObjectName("PageSubtitle")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.hide()
        pane_layout.addWidget(self._empty_label, 1)

        self.detail_panel = BookDetailPanel(repository=self._repo)
        self.detail_panel.setMinimumWidth(240)

        self.main_splitter.addWidget(self.main_pane)
        self.main_splitter.addWidget(self.detail_panel)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        self.main_splitter.setSizes([1020, 320])
        root.addWidget(self.main_splitter, 1)

        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self._title.setText(tr("favorites.page.title", "Favorites"))
        self._empty_label.setText(tr("favorites.page.empty", "No favorite books yet."))
        self._grid_btn.setToolTip(tr("library.grid", "Grid"))
        self._list_btn.setToolTip(tr("library.list", "List"))
        self._sort_label.setText(tr("favorites.sort.label", "Sort"))
        self._sort_combo.blockSignals(True)
        self._sort_combo.clear()
        self._sort_combo.addItem(tr("favorites.sort.added_desc", "Added Time: Newest First"), SORT_ORDER_DESC)
        self._sort_combo.addItem(tr("favorites.sort.added_asc", "Added Time: Oldest First"), SORT_ORDER_ASC)
        selected_index = self._sort_combo.findData(self._sort_order)
        self._sort_combo.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self._sort_combo.blockSignals(False)
        self._list_table.setHorizontalHeaderLabels(
            [
                tr("library.table.cover", "Cover"),
                tr("library.table.title", "Title"),
                tr("library.table.author", "Author"),
                tr("library.table.tags", "Tags"),
            ]
        )
        self._apply_view_mode()

    def refresh(self, force: bool = False) -> None:
        _ = force
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
        self._resource_by_id = {item.resource_id: item for item in self._resources}

        count = len(self._resources)
        self._subtitle.setText(
            tr("favorites.page.subtitle.count", "{count} books in favorites").format(count=count)
        )

        if self._selected_resource_id and self._selected_resource_id not in self._resource_by_id:
            self._selected_resource_id = None

        if not self._resources:
            while self._grid.count():
                item = self._grid.takeAt(0)
                if item and item.widget():
                    item.widget().setParent(None)
            self._prune_grid_card_cache(set())
            self._list_table.setRowCount(0)
            self._view_stack.hide()
            self._empty_label.show()
            self.detail_panel.clear_selection()
            return

        self._empty_label.hide()
        self._view_stack.show()
        self._render_grid()
        self._render_list()
        self._apply_view_mode()
        self._sync_list_selection()
        if self._selected_resource_id:
            self._update_detail_panel(self._selected_resource_id)
        else:
            self.detail_panel.clear_selection()

    def _render_grid(self) -> None:
        self._grid.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setVerticalSpacing(UI_LAYOUT.card_spacing)
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)

        columns = self._calculate_columns()
        self._last_columns = columns
        for idx, resource in enumerate(self._resources):
            row = idx // columns
            col = idx % columns
            card = self._get_or_create_grid_card(resource)
            card.set_selected(resource.resource_id == self._selected_resource_id)
            self._grid.addWidget(card, row, col, alignment=Qt.AlignLeft | Qt.AlignTop)
        self._prune_grid_card_cache({item.resource_id for item in self._resources})

    def _render_list(self) -> None:
        self._list_table.setRowCount(len(self._resources))
        for row, resource in enumerate(self._resources):
            cover_item = QTableWidgetItem("  ")
            cover_item.setData(Qt.UserRole, resource.resource_id)
            cover_item.setIcon(self._build_thumbnail_icon(resource))
            self._list_table.setItem(row, 0, cover_item)
            self._list_table.setItem(row, 1, QTableWidgetItem(resource.title))
            self._list_table.setItem(
                row,
                2,
                QTableWidgetItem(format_author_publisher_meta(resource.author, resource.publisher)),
            )
            self._list_table.setItem(row, 3, QTableWidgetItem(", ".join(resource.tags)))

        self._list_table.resizeColumnsToContents()
        self._list_table.setColumnWidth(1, 260)

    def _build_thumbnail_icon(self, item: ResourceItem) -> QIcon:
        if item.thumbnail_path:
            thumb = item.thumbnail_path
            if thumb.startswith("file://"):
                from urllib.parse import urlparse
                from urllib.request import url2pathname

                parsed = urlparse(thumb)
                file_path = Path(url2pathname(parsed.path))
            else:
                file_path = Path(thumb)
            if file_path.exists():
                pixmap = QPixmap(str(file_path))
                if not pixmap.isNull():
                    return QIcon(
                        pixmap.scaled(26, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
        fallback = QPixmap(26, 38)
        fallback.fill(Qt.lightGray)
        return QIcon(fallback)

    def _show_card_menu(self, resource: ResourceItem, global_pos) -> None:
        menu = QMenu(self)
        open_action = menu.addAction(tr("favorites.menu.open_external", "Open External"))
        remove_action = menu.addAction(tr("favorites.menu.remove_favorite", "Remove from Favorites"))
        chosen = menu.exec(global_pos)
        if chosen == open_action:
            self._open_external(resource.path)
        elif chosen == remove_action:
            self._remove_favorite(resource.resource_id)

    def _show_list_menu(self, pos) -> None:
        row = self._list_table.rowAt(pos.y())
        if row < 0:
            return
        item = self._list_table.item(row, 0)
        if item is None:
            return
        resource_id = str(item.data(Qt.UserRole) or "")
        resource = self._resource_by_id.get(resource_id)
        if resource is None:
            return
        global_pos = self._list_table.viewport().mapToGlobal(pos)
        self._show_card_menu(resource, global_pos)

    def _on_list_row_clicked(self, row: int, _column: int) -> None:
        item = self._list_table.item(row, 0)
        if item is None:
            return
        self._select_resource(str(item.data(Qt.UserRole) or ""))

    def _on_list_row_double_clicked(self, row: int, _column: int) -> None:
        item = self._list_table.item(row, 0)
        if item is None:
            return
        resource_id = str(item.data(Qt.UserRole) or "")
        resource = self._resource_by_id.get(resource_id)
        if resource is not None:
            self._open_external(resource.path)

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

    def _select_resource(self, resource_id: str) -> None:
        if resource_id not in self._resource_by_id:
            return
        self._selected_resource_id = resource_id
        self._sync_card_selection()
        self._sync_list_selection()
        self._update_detail_panel(resource_id)

    def _sync_card_selection(self) -> None:
        for resource_id, card in self._card_by_resource_id.items():
            card.set_selected(resource_id == self._selected_resource_id)

    def _sync_list_selection(self) -> None:
        if not self._selected_resource_id:
            self._list_table.clearSelection()
            return
        for row in range(self._list_table.rowCount()):
            item = self._list_table.item(row, 0)
            if item is None:
                continue
            if str(item.data(Qt.UserRole) or "") == self._selected_resource_id:
                self._list_table.selectRow(row)
                return

    def _update_detail_panel(self, resource_id: str) -> None:
        resource = self._resource_by_id.get(resource_id)
        if resource is None:
            self.detail_panel.clear_selection()
            return
        collection_names: list[str] = []
        if self._repo is not None:
            try:
                book_id = self._repo.get_book_int_id(resource.resource_id)
                if isinstance(book_id, int):
                    collections = self._repo.get_collections_for_book(book_id)
                    collection_names = [
                        str(item.get("name") or "").strip()
                        for item in collections
                        if str(item.get("name") or "").strip()
                    ]
            except Exception as e:
                print(f"[FavoritesPage] load collections for detail error: {e}")
        self.detail_panel.set_resource(resource, collection_names)

    @staticmethod
    def _card_signature(item: ResourceItem) -> tuple[str, str, str]:
        return (
            str(item.title or ""),
            str(item.path or ""),
            str(item.thumbnail_path or ""),
        )

    def _get_or_create_grid_card(self, item: ResourceItem) -> BookCardWidget:
        resource_id = item.resource_id
        signature = self._card_signature(item)
        card = self._card_by_resource_id.get(resource_id)
        cached_signature = self._card_signature_by_resource_id.get(resource_id)
        if card is not None and cached_signature == signature:
            return card
        if card is not None:
            card.deleteLater()
        card = BookCardWidget(item, cover_only=True)
        self._card_by_resource_id[resource_id] = card
        self._card_signature_by_resource_id[resource_id] = signature
        card.clicked.connect(lambda res_id=resource_id: self._select_resource(res_id))
        card.open_requested.connect(lambda _pos, res_id=resource_id: self._open_resource_by_id(res_id))
        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, res_id=resource_id, widget=card: self._show_card_menu_by_id(res_id, widget.mapToGlobal(pos))
        )
        return card

    def _prune_grid_card_cache(self, valid_resource_ids: set[str]) -> None:
        for resource_id in list(self._card_by_resource_id.keys()):
            if resource_id in valid_resource_ids:
                continue
            card = self._card_by_resource_id.pop(resource_id, None)
            self._card_signature_by_resource_id.pop(resource_id, None)
            if card is not None:
                card.deleteLater()

    def _open_resource_by_id(self, resource_id: str) -> None:
        resource = self._resource_by_id.get(resource_id)
        if resource is None:
            return
        self._open_external(resource.path)

    def _show_card_menu_by_id(self, resource_id: str, global_pos) -> None:
        resource = self._resource_by_id.get(resource_id)
        if resource is None:
            return
        self._show_card_menu(resource, global_pos)

    def _set_view_mode(self, mode: str) -> None:
        normalized = _normalize_view_mode(mode)
        if normalized == self._view_mode:
            return
        self._view_mode = normalized
        self._save_view_mode(normalized)
        self._apply_view_mode()

    def _apply_view_mode(self) -> None:
        is_list = self._view_mode == VIEW_MODE_LIST
        self._view_stack.setCurrentIndex(1 if is_list else 0)
        self._grid_btn.setChecked(not is_list)
        self._list_btn.setChecked(is_list)

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

    def _load_view_mode(self) -> str:
        if self._repo is None:
            return VIEW_MODE_WATERFALL
        raw_value = self._repo.get_setting(VIEW_MODE_SETTING_KEY, VIEW_MODE_WATERFALL)
        return _normalize_view_mode(raw_value)

    def _save_view_mode(self, mode: str) -> None:
        if self._repo is None:
            return
        self._repo.set_setting(VIEW_MODE_SETTING_KEY, _normalize_view_mode(mode))

    def _on_sort_changed(self, _index: int) -> None:
        selected = _normalize_sort_order(self._sort_combo.currentData())
        if selected == self._sort_order:
            return
        self._sort_order = selected
        self._save_sort_order(selected)
        self.refresh()

    def invalidate_cache(self) -> None:
        self._prune_grid_card_cache(set())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._view_mode != VIEW_MODE_WATERFALL:
            return
        columns = self._calculate_columns()
        if columns != self._last_columns and self._resources:
            self._render_grid()

    def _on_main_splitter_moved(self, _pos: int, _index: int) -> None:
        if self._view_mode != VIEW_MODE_WATERFALL:
            return
        columns = self._calculate_columns()
        if columns != self._last_columns and self._resources:
            self._render_grid()
