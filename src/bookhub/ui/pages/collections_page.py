# -*- coding: utf-8 -*-
"""
Collections page - shows all user-defined book lists (custom shelves).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QInputDialog,
    QMessageBox, QMenu, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem,
    QSizePolicy,
)
from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QAction, QFont, QIcon, QPixmap

import hashlib

from bookhub.i18n import tr
from bookhub.ui.models.resource import ResourceItem
from bookhub.ui.pages.library_page import BookDetailPanel
from bookhub.ui.resources.assets import load_icon
from bookhub.ui.resources.layout_config import UI_LAYOUT
from bookhub.ui.widgets.book_card import BookCardWidget
from bookhub.ui.widgets.book_card import format_author_publisher_meta

COLLECTIONS_DETAIL_VIEW_MODE_KEY = "collections_detail_view_mode"
VIEW_MODE_WATERFALL = "waterfall"
VIEW_MODE_LIST = "list"


def _normalize_view_mode(value: object) -> str:
    text = str(value or "").strip().lower()
    return VIEW_MODE_LIST if text == VIEW_MODE_LIST else VIEW_MODE_WATERFALL


class CollectionCard(QFrame):
    """Card widget representing a single collection (book list)."""
    clicked = Signal(int, str)          # (collection_id, collection_name)
    delete_requested = Signal(int)      # collection_id
    rename_requested = Signal(int)      # collection_id

    def __init__(self, collection: dict, repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._col = collection
        self._repo = repository
        self._col_id: int = collection.get("id", -1)
        self._col_name: str = collection.get("name", "Unnamed")
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("CollectionCard")
        self.setFixedSize(180, 230)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Cover area
        self._cover_label = QLabel()
        self._cover_label.setFixedSize(180, 160)
        self._cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover_label.setObjectName("collectionCover")
        self._render_cover()
        layout.addWidget(self._cover_label)

        # Info area
        info_widget = QWidget()
        info_widget.setObjectName("collectionInfo")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(2)

        name_label = QLabel(self._col_name)
        name_label.setObjectName("collectionName")
        name_label.setWordWrap(False)
        name_label.setMaximumWidth(160)
        name_font = QFont()
        name_font.setPointSize(11)
        name_font.setBold(True)
        name_label.setFont(name_font)
        info_layout.addWidget(name_label)

        try:
            count = self._repo.get_collection_book_count(self._col_id)
        except Exception:
            count = 0
        count_label = QLabel(f"{count} book{'s' if count != 1 else ''}")
        count_label.setObjectName("collectionCount")
        info_layout.addWidget(count_label)

        layout.addWidget(info_widget)
        self._apply_styles()

    def _render_cover(self) -> None:
        # Try to show the first book's thumbnail (JS: booklist.coverUrl = firstBookWithCover?.coverUrl || defaultCover)
        cover_shown = False
        try:
            books = self._repo.get_books_in_collection(self._col_id)
        except Exception:
            books = []

        for book in books:
            thumbnail_path = book.get("thumbnail_path")
            if not thumbnail_path:
                continue
            from pathlib import Path as _Path
            from PySide6.QtGui import QPixmap
            from urllib.parse import urlparse
            from urllib.request import url2pathname
            if thumbnail_path.startswith("file://"):
                parsed = urlparse(thumbnail_path)
                tp = _Path(url2pathname(parsed.path))
            else:
                tp = _Path(thumbnail_path)
            if not tp.exists():
                continue
            pixmap = QPixmap(str(tp))
            if pixmap.isNull():
                continue
            scaled = pixmap.scaled(
                180, 160,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._cover_label.setPixmap(scaled)
            self._cover_label.setStyleSheet(
                "QLabel#collectionCover { border-radius: 6px 6px 0px 0px; }"
            )
            cover_shown = True
            break

        if not cover_shown:
            # defaultCover: colored initials
            colors = ["#1565C0", "#2E7D32", "#B71C1C", "#E65100", "#4A148C", "#006064", "#37474F", "#558B2F"]
            idx = int(hashlib.md5(self._col_name.encode("utf-8", errors="replace")).hexdigest(), 16) % len(colors)
            color = colors[idx]
            words = self._col_name.strip().split()
            initials = "".join(w[0].upper() for w in words[:2]) if words else "?"
            self._cover_label.setText(initials)
            self._cover_label.setStyleSheet(f"""
                QLabel#collectionCover {{
                    background-color: {color};
                    color: white;
                    border-radius: 6px 6px 0px 0px;
                    font-size: 36pt;
                    font-weight: bold;
                }}
            """)

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QFrame#CollectionCard {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            QFrame#CollectionCard:hover {
                border: 1px solid #BDBDBD;
                background-color: #FAFAFA;
            }
            QWidget#collectionInfo {
                background-color: white;
                border-radius: 0px 0px 8px 8px;
            }
            QLabel#collectionName {
                color: #212121;
            }
            QLabel#collectionCount {
                color: #9E9E9E;
                font-size: 11px;
            }
        """)

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        open_act = QAction("Open", self)
        open_act.triggered.connect(lambda: self.clicked.emit(self._col_id, self._col_name))
        menu.addAction(open_act)
        menu.addSeparator()
        rename_act = QAction("Rename", self)
        rename_act.triggered.connect(lambda: self.rename_requested.emit(self._col_id))
        menu.addAction(rename_act)
        delete_act = QAction("Delete", self)
        delete_act.triggered.connect(lambda: self.delete_requested.emit(self._col_id))
        menu.addAction(delete_act)
        menu.exec(self.mapToGlobal(pos))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._col_id, self._col_name)
        super().mousePressEvent(event)


class CollectionDetailPage(QWidget):
    """Shows books inside a specific collection."""
    back_requested = Signal()
    book_removed = Signal(int, int)  # (book_id, collection_id)

    def __init__(self, collection_id: int, collection_name: str, repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._col_id = collection_id
        self._col_name = collection_name
        self._repo = repository
        self._view_mode = self._load_view_mode()
        self._book_id_by_resource_id: dict[str, int] = {}
        self._resource_by_id: dict[str, ResourceItem] = {}
        self._resources: list[ResourceItem] = []
        self._card_by_resource_id: dict[str, BookCardWidget] = {}
        self._card_signature_by_resource_id: dict[str, tuple[str, str, str]] = {}
        self._selected_resource_id: str | None = None
        self._last_columns = 0
        self._setup_ui()
        self.refresh(force=True)

    def _setup_ui(self) -> None:
        self.setObjectName("CollectionDetailPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(0)

        header = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("backBtn")
        back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(back_btn)

        title_label = QLabel(self._col_name)
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setObjectName("detailTitle")
        header.addWidget(title_label, 1)

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
        self._grid_btn.setToolTip(tr("library.grid", "Grid"))
        self._grid_btn.clicked.connect(lambda: self._set_view_mode(VIEW_MODE_WATERFALL))
        view_toggle_layout.addWidget(self._grid_btn)

        self._list_btn = QPushButton()
        self._list_btn.setObjectName("ViewToggleButton")
        self._list_btn.setCheckable(True)
        self._list_btn.setIcon(load_icon("view_list.svg"))
        self._list_btn.setIconSize(QSize(14, 14))
        self._list_btn.setToolTip(tr("library.list", "List"))
        self._list_btn.clicked.connect(lambda: self._set_view_mode(VIEW_MODE_LIST))
        view_toggle_layout.addWidget(self._list_btn)
        header.addWidget(self._view_toggle_panel, 0, Qt.AlignVCenter)
        layout.addLayout(header)
        layout.addSpacing(24)

        self._count_label = QLabel("")
        self._count_label.setObjectName("countLabel")
        self._count_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._count_label)
        layout.addSpacing(16)

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
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(UI_LAYOUT.grid_left_inset, 0, 0, 0)
        self._grid.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setVerticalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
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
        self._list_table.setHorizontalHeaderLabels(
            [
                tr("library.table.cover", "Cover"),
                tr("library.table.title", "Title"),
                tr("library.table.author", "Author"),
                tr("library.table.tags", "Tags"),
            ]
        )
        self._view_stack.addWidget(self._list_table)
        pane_layout.addWidget(self._view_stack, 1)

        self._empty_label = QLabel(
            "No books in this collection yet.\n\nAdd books by right-clicking on them in the Library."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.hide()
        pane_layout.addWidget(self._empty_label, 1)

        self.detail_panel = BookDetailPanel(repository=self._repo)
        self.detail_panel.setMinimumWidth(240)

        self.main_splitter.addWidget(self.main_pane)
        self.main_splitter.addWidget(self.detail_panel)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        self.main_splitter.setSizes([1020, 320])
        layout.addWidget(self.main_splitter, 1)

        self.setStyleSheet("""
            CollectionDetailPage { background-color: #F5F5F5; }
            QPushButton#backBtn {
                background-color: transparent; border: none;
                color: #1565C0; font-size: 13px; font-weight: bold;
                padding: 6px 12px; margin-right: 16px;
            }
            QPushButton#backBtn:hover { text-decoration: underline; }
            QLabel#detailTitle { color: #212121; }
            QLabel#countLabel { color: #757575; font-size: 13px; }
            QLabel#emptyLabel { color: #9E9E9E; font-size: 14px; padding: 40px; }
        """)
        self._apply_view_mode()

        for watched in (self, self._scroll.viewport(), self._list_table.viewport(), self._view_stack):
            watched.installEventFilter(self)

    def refresh(self, force: bool = False) -> None:
        _ = force
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._list_table.setRowCount(0)
        self._book_id_by_resource_id.clear()
        self._resource_by_id.clear()
        self._resources = []

        try:
            books = self._repo.get_books_in_collection(self._col_id)
        except Exception as e:
            print(f"[CollectionDetailPage] error: {e}")
            books = []

        count = len(books)
        self._count_label.setText(f"{count} book{'s' if count != 1 else ''}")

        if not books:
            self._empty_label.show()
            self._view_stack.hide()
            self._selected_resource_id = None
            self.detail_panel.clear_selection()
            self._prune_grid_card_cache(set())
        else:
            self._empty_label.hide()
            self._view_stack.show()
            for book_data in books:
                resource = self._record_to_resource(book_data)
                self._resources.append(resource)
                self._resource_by_id[resource.resource_id] = resource
                raw_book_id = book_data.get("id")
                if isinstance(raw_book_id, int):
                    self._book_id_by_resource_id[resource.resource_id] = raw_book_id
                else:
                    try:
                        book_id = self._repo.get_book_int_id(resource.resource_id)
                        if isinstance(book_id, int):
                            self._book_id_by_resource_id[resource.resource_id] = book_id
                    except Exception:
                        pass
            if self._selected_resource_id and self._selected_resource_id not in self._resource_by_id:
                self._selected_resource_id = None
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
            if item.widget():
                item.widget().setParent(None)
        columns = self._calculate_grid_columns()
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

    def _calculate_grid_columns(self) -> int:
        available_width = max(1, self._scroll.viewport().width())
        cell_width = UI_LAYOUT.card_width + UI_LAYOUT.card_spacing
        return max(1, available_width // max(1, cell_width))

    def apply_card_spacing(self, _spacing: int) -> None:
        self._grid.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setVerticalSpacing(UI_LAYOUT.card_spacing)
        if self._view_mode == VIEW_MODE_WATERFALL and self._resources:
            self._render_grid()

    def _show_card_menu(self, resource_id: str, global_pos) -> None:
        resource = self._resource_by_id.get(resource_id)
        if resource is None:
            return
        menu = QMenu(self)
        open_act = menu.addAction(tr("library.menu.open_external", "Open External"))
        remove_act = menu.addAction("Remove from Collection")
        act = menu.exec(global_pos)
        if act == open_act:
            self._open_external(resource.path)
        elif act == remove_act:
            self._remove_book_from_collection(resource_id)

    def _show_list_menu(self, pos) -> None:
        row = self._list_table.rowAt(pos.y())
        if row < 0:
            return
        item = self._list_table.item(row, 0)
        if item is None:
            return
        resource_id = str(item.data(Qt.UserRole) or "")
        self._show_card_menu(resource_id, self._list_table.viewport().mapToGlobal(pos))

    def _on_list_row_double_clicked(self, row: int, _column: int) -> None:
        item = self._list_table.item(row, 0)
        if item is None:
            return
        resource_id = str(item.data(Qt.UserRole) or "")
        resource = self._resource_by_id.get(resource_id)
        if resource is not None:
            self._open_external(resource.path)

    def _on_list_row_clicked(self, row: int, _column: int) -> None:
        item = self._list_table.item(row, 0)
        if item is None:
            return
        self._select_resource(str(item.data(Qt.UserRole) or ""))

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
            print(f"[CollectionDetailPage] load collections for detail error: {e}")
        self.detail_panel.set_resource(resource, collection_names)

    def _remove_book_from_collection(self, resource_id: str) -> None:
        book_id = self._book_id_by_resource_id.get(resource_id)
        if book_id is None:
            return
        try:
            self._repo.remove_book_from_collection(book_id, self._col_id)
            self.book_removed.emit(book_id, self._col_id)
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to remove: {exc}")

    @staticmethod
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

    def _record_to_resource(self, record: dict) -> ResourceItem:
        resource_id = str(record.get("resource_id") or "").strip()
        if not resource_id:
            fallback_id = str(record.get("id") or "")
            resource_id = f"collection-book-{self._col_id}-{fallback_id or 'unknown'}"

        title = str(record.get("title") or "").strip()
        if not title:
            title = Path(str(record.get("file_name") or "")).stem or "Unknown"

        return ResourceItem(
            resource_id=resource_id,
            title=title,
            author=str(record.get("author") or ""),
            status=str(record.get("status") or "UNREAD"),
            tags=self._parse_tags(record.get("tags_json")),
            resource_type=str(record.get("resource_type") or "book"),
            path=str(record.get("path") or ""),
            thumbnail_path=record.get("thumbnail_path"),
            publisher=record.get("publisher"),
            language=record.get("language"),
            is_missing=bool(record.get("is_missing")),
            file_name=str(record.get("file_name") or ""),
            extension=str(record.get("extension") or ""),
        )

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
            print(f"[CollectionDetailPage] open external error: {e}")

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

    def _load_view_mode(self) -> str:
        raw = self._repo.get_setting(COLLECTIONS_DETAIL_VIEW_MODE_KEY, VIEW_MODE_WATERFALL)
        return _normalize_view_mode(raw)

    def _save_view_mode(self, mode: str) -> None:
        self._repo.set_setting(COLLECTIONS_DETAIL_VIEW_MODE_KEY, _normalize_view_mode(mode))

    def _set_view_mode(self, mode: str) -> None:
        normalized = _normalize_view_mode(mode)
        if normalized == self._view_mode:
            return
        self._view_mode = normalized
        self._save_view_mode(normalized)
        self._apply_view_mode()

    @staticmethod
    def _card_signature(item: ResourceItem) -> tuple[str, str, str]:
        return (
            str(item.title or ""),
            str(item.path or ""),
            str(item.thumbnail_path or ""),
        )

    def _get_or_create_grid_card(self, resource: ResourceItem) -> BookCardWidget:
        resource_id = resource.resource_id
        signature = self._card_signature(resource)
        card = self._card_by_resource_id.get(resource_id)
        cached_signature = self._card_signature_by_resource_id.get(resource_id)
        if card is not None and cached_signature == signature:
            return card
        if card is not None:
            card.deleteLater()
        card = BookCardWidget(resource, cover_only=True)
        self._card_by_resource_id[resource_id] = card
        self._card_signature_by_resource_id[resource_id] = signature
        card.clicked.connect(lambda rid=resource_id: self._select_resource(rid))
        card.open_requested.connect(lambda _pos, rid=resource_id: self._open_resource_by_id(rid))
        card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, rid=resource_id, widget=card: self._show_card_menu(rid, widget.mapToGlobal(pos))
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

    def invalidate_cache(self) -> None:
        self._prune_grid_card_cache(set())

    def _apply_view_mode(self) -> None:
        is_list = self._view_mode == VIEW_MODE_LIST
        self._view_stack.setCurrentIndex(1 if is_list else 0)
        self._grid_btn.setChecked(not is_list)
        self._list_btn.setChecked(is_list)

    @staticmethod
    def _is_back_button(button: object) -> bool:
        candidates = ("BackButton", "XButton1", "XButton2")
        for name in candidates:
            value = getattr(Qt.MouseButton, name, None)
            if value is not None and button == value:
                return True
        return False

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress and self._is_back_button(event.button()):
            self.back_requested.emit()
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._view_mode != VIEW_MODE_WATERFALL:
            return
        columns = self._calculate_grid_columns()
        if columns != self._last_columns and self._resources:
            self._render_grid()

    def _on_main_splitter_moved(self, _pos: int, _index: int) -> None:
        if self._view_mode != VIEW_MODE_WATERFALL:
            return
        columns = self._calculate_grid_columns()
        if columns != self._last_columns and self._resources:
            self._render_grid()


class CollectionsPage(QWidget):
    """
    Main Collections page showing all user-created book lists.
    Clicking a collection shows its detail view inline.
    """
    def __init__(self, repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repository
        self._collection_card_by_id: dict[int, CollectionCard] = {}
        self._collection_card_signature_by_id: dict[int, tuple[str]] = {}
        self._setup_ui()
        self.refresh(force=True)

    def _setup_ui(self) -> None:
        self.setObjectName("CollectionsPage")
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # --- Grid view ---
        self._grid_view = QWidget()
        self._grid_view.setObjectName("CollectionsGridView")
        grid_layout = QVBoxLayout(self._grid_view)
        grid_layout.setContentsMargins(32, 24, 32, 24)
        grid_layout.setSpacing(0)

        header = QHBoxLayout()
        title_label = QLabel("Collections")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setObjectName("pageTitle")
        header.addWidget(title_label)
        header.addStretch()

        self._new_list_btn = QPushButton("+ NEW LIST")
        self._new_list_btn.setObjectName("newListBtn")
        self._new_list_btn.clicked.connect(self._create_new_collection)
        header.addWidget(self._new_list_btn)
        grid_layout.addLayout(header)
        grid_layout.addSpacing(24)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("collectionsScroll")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._grid_container = QWidget()
        self._grid_container.setObjectName("collectionsGrid")
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid_layout.setVerticalSpacing(UI_LAYOUT.card_spacing)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll.setWidget(self._grid_container)
        grid_layout.addWidget(self._scroll)

        self._empty_label = QLabel("No collections yet.\n\nClick '+ NEW LIST' to create your first collection.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.hide()
        grid_layout.addWidget(self._empty_label)

        self._main_layout.addWidget(self._grid_view)

        # --- Detail view (shown when a collection is clicked) ---
        self._detail_view: CollectionDetailPage | None = None

        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QWidget#CollectionsGridView { background-color: #F5F5F5; }
            QLabel#pageTitle { color: #212121; }
            QPushButton#newListBtn {
                background-color: #1565C0; color: white;
                border: none; border-radius: 6px;
                padding: 10px 20px; font-size: 13px;
                font-weight: bold; min-width: 120px;
            }
            QPushButton#newListBtn:hover { background-color: #0D47A1; }
            QScrollArea#collectionsScroll { background-color: transparent; border: none; }
            QWidget#collectionsGrid { background-color: transparent; }
            QFrame#CollectionCard {
                background-color: white; border: 1px solid #E0E0E0; border-radius: 8px;
            }
            QFrame#CollectionCard:hover {
                border: 1px solid #BDBDBD; background-color: #FAFAFA;
            }
            QLabel#emptyLabel { color: #9E9E9E; font-size: 14px; padding: 40px; }
        """)

    def refresh(self, force: bool = False) -> None:
        _ = force
        """Reload collections from database (grid view)."""
        # Remove detail view if shown
        self._hide_detail_view()

        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        try:
            collections = self._repo.get_all_collections()
        except Exception as e:
            print(f"[CollectionsPage] get_all_collections error: {e}")
            collections = []

        if not collections:
            self._empty_label.show()
            self._scroll.hide()
            self._prune_collection_card_cache(set())
        else:
            self._empty_label.hide()
            self._scroll.show()
            self._grid_layout.setHorizontalSpacing(UI_LAYOUT.card_spacing)
            self._grid_layout.setVerticalSpacing(UI_LAYOUT.card_spacing)
            cols_per_row = self._calculate_grid_columns()
            for i, col in enumerate(collections):
                card = self._get_or_create_collection_card(col)
                self._grid_layout.addWidget(card, i // cols_per_row, i % cols_per_row)
            self._prune_collection_card_cache(
                {int(item.get("id")) for item in collections if isinstance(item.get("id"), int)}
            )

    def _calculate_grid_columns(self) -> int:
        available_width = max(1, self._scroll.viewport().width())
        cell_width = 180 + UI_LAYOUT.card_spacing
        return max(1, available_width // max(1, cell_width))

    def apply_card_spacing(self, spacing: int) -> None:
        _ = spacing
        self._grid_layout.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid_layout.setVerticalSpacing(UI_LAYOUT.card_spacing)
        if self._detail_view is not None and hasattr(self._detail_view, "apply_card_spacing"):
            self._detail_view.apply_card_spacing(UI_LAYOUT.card_spacing)
            return
        self.refresh()

    @staticmethod
    def _collection_card_signature(collection: dict) -> tuple[str]:
        name = str(collection.get("name") or "")
        return (name,)

    def _get_or_create_collection_card(self, collection: dict) -> CollectionCard:
        collection_id = int(collection.get("id"))
        signature = self._collection_card_signature(collection)
        card = self._collection_card_by_id.get(collection_id)
        cached_signature = self._collection_card_signature_by_id.get(collection_id)
        if card is not None and cached_signature == signature:
            return card
        if card is not None:
            card.deleteLater()
        card = CollectionCard(collection, self._repo)
        self._collection_card_by_id[collection_id] = card
        self._collection_card_signature_by_id[collection_id] = signature
        card.clicked.connect(self._show_detail_view)
        card.delete_requested.connect(self._on_delete_collection)
        card.rename_requested.connect(self._on_rename_collection)
        return card

    def _prune_collection_card_cache(self, valid_collection_ids: set[int]) -> None:
        for collection_id in list(self._collection_card_by_id.keys()):
            if collection_id in valid_collection_ids:
                continue
            card = self._collection_card_by_id.pop(collection_id, None)
            self._collection_card_signature_by_id.pop(collection_id, None)
            if card is not None:
                card.deleteLater()

    def _show_detail_view(self, collection_id: int, collection_name: str) -> None:
        self._hide_detail_view()
        self._grid_view.hide()
        detail = CollectionDetailPage(collection_id, collection_name, self._repo)
        detail.back_requested.connect(self._on_detail_back)
        self._detail_view = detail
        self._main_layout.addWidget(detail, 1)
        detail.show()

    def _hide_detail_view(self) -> None:
        if self._detail_view is not None:
            self._main_layout.removeWidget(self._detail_view)
            self._detail_view.deleteLater()
            self._detail_view = None
        self._grid_view.show()

    def invalidate_cache(self) -> None:
        self._prune_collection_card_cache(set())
        if self._detail_view is not None and hasattr(self._detail_view, "invalidate_cache"):
            self._detail_view.invalidate_cache()

    def _on_detail_back(self) -> None:
        self._hide_detail_view()
        self.invalidate_cache()
        self.refresh()

    def _create_new_collection(self) -> None:
        name, ok = QInputDialog.getText(self, "New Collection", "Collection name:")
        if ok and name.strip():
            try:
                self._repo.create_collection(name.strip())
                self.invalidate_cache()
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create collection: {e}")

    def _on_delete_collection(self, collection_id: int) -> None:
        reply = QMessageBox.question(
            self,
            "Delete Collection",
            "Are you sure you want to delete this collection?\nBooks will not be removed from the library.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._repo.delete_collection(collection_id)
                self.invalidate_cache()
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

    def _on_rename_collection(self, collection_id: int) -> None:
        try:
            collections = self._repo.get_all_collections()
            old_name = next((c["name"] for c in collections if c["id"] == collection_id), "")
        except Exception:
            old_name = ""
        name, ok = QInputDialog.getText(self, "Rename Collection", "New name:", text=old_name)
        if ok and name.strip():
            try:
                self._repo.rename_collection(collection_id, name.strip())
                self.invalidate_cache()
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to rename: {e}")
