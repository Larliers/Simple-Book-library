# -*- coding: utf-8 -*-
"""
Collections page - shows all user-defined book lists (custom shelves).
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QSizePolicy, QInputDialog,
    QMessageBox, QMenu
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QAction

import hashlib


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
        self._setup_ui()
        self.refresh()

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
        layout.addLayout(header)
        layout.addSpacing(24)

        self._count_label = QLabel("")
        self._count_label.setObjectName("countLabel")
        layout.addWidget(self._count_label)
        layout.addSpacing(16)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(16)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

        self._empty_label = QLabel(
            "No books in this collection yet.\n\nAdd books by right-clicking on them in the Library."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

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

    def refresh(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            books = self._repo.get_books_in_collection(self._col_id)
        except Exception as e:
            print(f"[CollectionDetailPage] error: {e}")
            books = []

        count = len(books)
        self._count_label.setText(f"{count} book{'s' if count != 1 else ''}")

        if not books:
            self._empty_label.show()
            self._scroll.hide()
        else:
            self._empty_label.hide()
            self._scroll.show()
            cols_per_row = 6
            for i, book_data in enumerate(books):
                card = self._make_book_card(book_data)
                self._grid.addWidget(card, i // cols_per_row, i % cols_per_row)

    def _make_book_card(self, book_data: dict) -> QFrame:
        frame = QFrame()
        frame.setObjectName("DetailBookCard")
        frame.setFixedSize(160, 230)
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        cover = QLabel()
        cover.setFixedSize(144, 170)
        cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = str(book_data.get("title", book_data.get("file_path", "?")))
        colors = ["#1565C0", "#2E7D32", "#B71C1C", "#E65100", "#4A148C"]
        idx = int(hashlib.md5(title.encode("utf-8", errors="replace")).hexdigest(), 16) % len(colors)
        color = colors[idx]
        cover.setText(title[0].upper() if title else "?")
        cover.setStyleSheet(
            f"background-color: {color}; color: white; border-radius: 4px;"
            " font-size: 28pt; font-weight: bold;"
        )
        layout.addWidget(cover)

        display = (title[:22] + "...") if len(title) > 22 else title
        lbl = QLabel(display)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 11px; color: #333;")
        layout.addWidget(lbl)

        frame.setStyleSheet("""
            QFrame#DetailBookCard { background-color: white; border: 1px solid #E0E0E0; border-radius: 6px; }
            QFrame#DetailBookCard:hover { border: 1px solid #BDBDBD; }
        """)

        book_id = book_data.get("id")
        col_id = self._col_id
        repo = self._repo

        def show_ctx(pos) -> None:
            menu = QMenu(frame)
            rem_act = menu.addAction("Remove from Collection")
            act = menu.exec(frame.mapToGlobal(pos))
            if act == rem_act and book_id is not None:
                try:
                    repo.remove_book_from_collection(book_id, col_id)
                    self.book_removed.emit(book_id, col_id)
                    self.refresh()
                except Exception as exc:
                    QMessageBox.critical(self, "Error", f"Failed to remove: {exc}")

        frame.customContextMenuRequested.connect(show_ctx)
        return frame


class CollectionsPage(QWidget):
    """
    Main Collections page showing all user-created book lists.
    Clicking a collection shows its detail view inline.
    """
    def __init__(self, repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repository
        self._setup_ui()
        self.refresh()

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
        self._grid_layout.setSpacing(20)
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

    def refresh(self) -> None:
        """Reload collections from database (grid view)."""
        # Remove detail view if shown
        self._hide_detail_view()

        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            collections = self._repo.get_all_collections()
        except Exception as e:
            print(f"[CollectionsPage] get_all_collections error: {e}")
            collections = []

        if not collections:
            self._empty_label.show()
            self._scroll.hide()
        else:
            self._empty_label.hide()
            self._scroll.show()
            cols_per_row = 5
            for i, col in enumerate(collections):
                card = CollectionCard(col, self._repo)
                card.clicked.connect(self._show_detail_view)
                card.delete_requested.connect(self._on_delete_collection)
                card.rename_requested.connect(self._on_rename_collection)
                self._grid_layout.addWidget(card, i // cols_per_row, i % cols_per_row)

    def _show_detail_view(self, collection_id: int, collection_name: str) -> None:
        self._hide_detail_view()
        self._grid_view.hide()
        detail = CollectionDetailPage(collection_id, collection_name, self._repo)
        detail.back_requested.connect(self._on_detail_back)
        self._detail_view = detail
        self._main_layout.addWidget(detail)
        detail.show()

    def _hide_detail_view(self) -> None:
        if self._detail_view is not None:
            self._main_layout.removeWidget(self._detail_view)
            self._detail_view.deleteLater()
            self._detail_view = None
        self._grid_view.show()

    def _on_detail_back(self) -> None:
        self._hide_detail_view()
        self.refresh()

    def _create_new_collection(self) -> None:
        name, ok = QInputDialog.getText(self, "New Collection", "Collection name:")
        if ok and name.strip():
            try:
                self._repo.create_collection(name.strip())
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
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to rename: {e}")