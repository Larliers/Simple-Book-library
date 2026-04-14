# -*- coding: utf-8 -*-
"""
Favorites page - redesigned as "自定义书单" (Custom Reading Lists).
Shows user-created named reading lists backed by the collections table.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QAction
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import hashlib


# ---------------------------------------------------------------------------
# Thumbnail helper
# ---------------------------------------------------------------------------

def _load_thumbnail(thumbnail_path: str | None, w: int, h: int) -> QPixmap | None:
    """Try to load and crop-scale a thumbnail, returning None on failure.

    Supports both ``file://`` URLs (new format, stored since 2026-04-14)
    and legacy bare filesystem paths.
    """
    if not thumbnail_path:
        return None
    # Resolve file:// URL → local path (JS equivalent: booklist.coverUrl = firstBookWithCover?.coverUrl || defaultCover)
    if thumbnail_path.startswith("file://"):
        from urllib.parse import urlparse
        from urllib.request import url2pathname
        parsed = urlparse(thumbnail_path)
        tp = Path(url2pathname(parsed.path))
    else:
        tp = Path(thumbnail_path)
    if not tp.exists():
        return None
    pixmap = QPixmap(str(tp))
    if pixmap.isNull():
        return None
    scaled = pixmap.scaled(
        w, h,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    if scaled.width() > w or scaled.height() > h:
        x = max(0, (scaled.width() - w) // 2)
        y = max(0, (scaled.height() - h) // 2)
        scaled = scaled.copy(x, y, w, h)
    return scaled


def _fallback_cover(label: QLabel, title: str) -> None:
    """Set a colored initial-letter fallback on a QLabel."""
    colors = ["#1565C0", "#2E7D32", "#B71C1C", "#E65100", "#4A148C", "#006064", "#37474F"]
    idx = int(hashlib.md5(title.encode("utf-8", errors="replace")).hexdigest(), 16) % len(colors)
    color = colors[idx]
    label.setText(title[0].upper() if title else "?")
    label.setStyleSheet(f"""
        QLabel {{
            background-color: {color};
            color: white;
            border-radius: 6px;
            font-size: 32pt;
            font-weight: bold;
        }}
    """)


# ---------------------------------------------------------------------------
# ReadingListCard  (represents one named list, like CollectionCard)
# ---------------------------------------------------------------------------

class ReadingListCard(QFrame):
    """Card for a single custom reading list (book shelf)."""

    clicked = Signal(int, str)        # (list_id, list_name)
    delete_requested = Signal(int)    # list_id
    rename_requested = Signal(int)    # list_id

    def __init__(self, collection: dict, repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._col = collection
        self._repo = repository
        self._col_id: int = collection.get("id", -1)
        self._col_name: str = collection.get("name", "Unnamed")
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("ReadingListCard")
        self.setFixedSize(180, 230)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Cover
        self._cover_label = QLabel()
        self._cover_label.setFixedSize(180, 160)
        self._cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover_label.setObjectName("listCover")
        self._render_cover()
        layout.addWidget(self._cover_label)

        # Info
        info_widget = QWidget()
        info_widget.setObjectName("listInfo")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(2)

        name_label = QLabel(self._col_name)
        name_label.setObjectName("listName")
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
        count_label = QLabel(f"{count} 本书" if count != 1 else "1 本书")
        count_label.setObjectName("listCount")
        info_layout.addWidget(count_label)

        layout.addWidget(info_widget)
        self._apply_styles()

    def _render_cover(self) -> None:
        # Try to show the thumbnail of the first book in the list
        try:
            books = self._repo.get_books_in_collection(self._col_id)
        except Exception:
            books = []

        cover_shown = False
        for book in books:
            pixmap = _load_thumbnail(book.get("thumbnail_path"), 180, 160)
            if pixmap:
                self._cover_label.setPixmap(pixmap)
                self._cover_label.setStyleSheet(
                    "QLabel#listCover { border-radius: 6px 6px 0px 0px; }"
                )
                cover_shown = True
                break

        if not cover_shown:
            colors = ["#1565C0", "#2E7D32", "#B71C1C", "#E65100", "#4A148C", "#006064", "#37474F", "#558B2F"]
            idx = int(hashlib.md5(self._col_name.encode("utf-8", errors="replace")).hexdigest(), 16) % len(colors)
            color = colors[idx]
            words = self._col_name.strip().split()
            initials = "".join(w[0].upper() for w in words[:2]) if words else "?"
            self._cover_label.setText(initials)
            self._cover_label.setStyleSheet(f"""
                QLabel#listCover {{
                    background-color: {color};
                    color: white;
                    border-radius: 6px 6px 0px 0px;
                    font-size: 36pt;
                    font-weight: bold;
                }}
            """)

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QFrame#ReadingListCard {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            QFrame#ReadingListCard:hover {
                border: 1px solid #BDBDBD;
                background-color: #FAFAFA;
            }
            QWidget#listInfo {
                background-color: white;
                border-radius: 0px 0px 8px 8px;
            }
            QLabel#listName { color: #212121; }
            QLabel#listCount { color: #9E9E9E; font-size: 11px; }
        """)

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        open_act = QAction("打开书单", self)
        open_act.triggered.connect(lambda: self.clicked.emit(self._col_id, self._col_name))
        menu.addAction(open_act)
        menu.addSeparator()
        rename_act = QAction("重命名", self)
        rename_act.triggered.connect(lambda: self.rename_requested.emit(self._col_id))
        menu.addAction(rename_act)
        delete_act = QAction("删除书单", self)
        delete_act.triggered.connect(lambda: self.delete_requested.emit(self._col_id))
        menu.addAction(delete_act)
        menu.exec(self.mapToGlobal(pos))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._col_id, self._col_name)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# ReadingListDetailPage  (books inside a list)
# ---------------------------------------------------------------------------

class ReadingListDetailPage(QWidget):
    """Shows books inside a custom reading list with real thumbnails."""

    back_requested = Signal()
    book_removed = Signal(int, int)   # (book_id, list_id)

    def __init__(self, list_id: int, list_name: str, repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._list_id = list_id
        self._list_name = list_name
        self._repo = repository
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        self.setObjectName("ReadingListDetailPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(0)

        header = QHBoxLayout()
        back_btn = QPushButton("← 返回")
        back_btn.setObjectName("backBtn")
        back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(back_btn)

        title_label = QLabel(self._list_name)
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
            "这个书单还没有书。\n\n在图书馆中右键点击书本，选择「添加到自定义书单」。"
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

        self.setStyleSheet("""
            ReadingListDetailPage { background-color: #F5F5F5; }
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
            books = self._repo.get_books_in_collection(self._list_id)
        except Exception as e:
            print(f"[ReadingListDetailPage] error: {e}")
            books = []

        count = len(books)
        self._count_label.setText(f"{count} 本书")

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

        title = str(book_data.get("title") or book_data.get("file_name") or "?")

        pixmap = _load_thumbnail(book_data.get("thumbnail_path"), 144, 170)
        if pixmap:
            cover.setPixmap(pixmap)
            cover.setStyleSheet("border-radius: 4px;")
        else:
            _fallback_cover(cover, title)

        layout.addWidget(cover)

        display = (title[:22] + "…") if len(title) > 22 else title
        lbl = QLabel(display)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 11px; color: #333;")
        layout.addWidget(lbl)

        frame.setStyleSheet("""
            QFrame#DetailBookCard {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
            }
            QFrame#DetailBookCard:hover { border: 1px solid #BDBDBD; }
        """)

        book_id = book_data.get("id")
        list_id = self._list_id
        repo = self._repo

        def show_ctx(pos) -> None:
            menu = QMenu(frame)
            rem_act = menu.addAction("从书单中移除")
            act = menu.exec(frame.mapToGlobal(pos))
            if act == rem_act and book_id is not None:
                try:
                    repo.remove_book_from_collection(book_id, list_id)
                    self.book_removed.emit(book_id, list_id)
                    self.refresh()
                except Exception as exc:
                    QMessageBox.critical(self, "错误", f"移除失败: {exc}")

        frame.customContextMenuRequested.connect(show_ctx)
        return frame


# ---------------------------------------------------------------------------
# FavoritesPage  =  自定义书单 page (replaces old flat favorites list)
# ---------------------------------------------------------------------------

class FavoritesPage(QWidget):
    """
    自定义书单 page.
    Shows all user-created named reading lists (backed by the collections table).
    Each list card shows the thumbnail of its first book (or an initial-letter fallback).
    """

    def __init__(self, repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repository
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        self.setObjectName("FavoritesPage")
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # --- Grid view ---
        self._grid_view = QWidget()
        self._grid_view.setObjectName("FavoritesGridView")
        grid_layout = QVBoxLayout(self._grid_view)
        grid_layout.setContentsMargins(32, 24, 32, 24)
        grid_layout.setSpacing(0)

        # Header
        header = QHBoxLayout()
        title_label = QLabel("自定义书单")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setObjectName("pageTitle")
        header.addWidget(title_label)
        header.addStretch()

        self._new_list_btn = QPushButton("+ 新建书单")
        self._new_list_btn.setObjectName("newListBtn")
        self._new_list_btn.clicked.connect(self._create_new_list)
        header.addWidget(self._new_list_btn)
        grid_layout.addLayout(header)
        grid_layout.addSpacing(8)

        subtitle = QLabel("在这里管理您的自定义书单，右键书本可快速添加到书单")
        subtitle.setObjectName("pageSubtitle")
        grid_layout.addWidget(subtitle)
        grid_layout.addSpacing(20)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("favoritesScroll")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._grid_container = QWidget()
        self._grid_container.setObjectName("favoritesGrid")
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(20)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll.setWidget(self._grid_container)
        grid_layout.addWidget(self._scroll)

        # Empty state
        self._empty_label = QLabel(
            "还没有自定义书单。\n\n点击「+ 新建书单」创建你的第一个书单。"
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.hide()
        grid_layout.addWidget(self._empty_label)

        self._main_layout.addWidget(self._grid_view)

        # Detail view placeholder
        self._detail_view: ReadingListDetailPage | None = None

        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QWidget#FavoritesGridView { background-color: #F5F5F5; }
            QLabel#pageTitle { color: #212121; }
            QLabel#pageSubtitle { color: #757575; font-size: 13px; }
            QPushButton#newListBtn {
                background-color: #005FAC;
                color: white;
                border: none;
                border-radius: 0px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton#newListBtn:hover { background-color: #004A8C; }
            QScrollArea#favoritesScroll { background-color: transparent; border: none; }
            QWidget#favoritesGrid { background-color: transparent; }
            QLabel#emptyLabel { color: #9E9E9E; font-size: 14px; padding: 40px; }
        """)

    def refresh(self) -> None:
        """Reload reading lists from database."""
        self._hide_detail_view()

        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            collections = self._repo.get_all_collections()
        except Exception as e:
            print(f"[FavoritesPage] get_all_collections error: {e}")
            collections = []

        if not collections:
            self._empty_label.show()
            self._scroll.hide()
        else:
            self._empty_label.hide()
            self._scroll.show()
            cols_per_row = 5
            for i, col in enumerate(collections):
                card = ReadingListCard(col, self._repo)
                card.clicked.connect(self._show_detail_view)
                card.delete_requested.connect(self._on_delete_list)
                card.rename_requested.connect(self._on_rename_list)
                self._grid_layout.addWidget(card, i // cols_per_row, i % cols_per_row)

    def _show_detail_view(self, list_id: int, list_name: str) -> None:
        self._hide_detail_view()
        self._grid_view.hide()
        detail = ReadingListDetailPage(list_id, list_name, self._repo)
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

    def _create_new_list(self) -> None:
        name, ok = QInputDialog.getText(self, "新建书单", "书单名称：")
        if ok and name.strip():
            try:
                self._repo.create_collection(name.strip())
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建失败：{e}")

    def _on_delete_list(self, list_id: int) -> None:
        reply = QMessageBox.question(
            self,
            "删除书单",
            "确定要删除这个书单吗？\n书本不会从图书馆中移除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._repo.delete_collection(list_id)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败：{e}")

    def _on_rename_list(self, list_id: int) -> None:
        try:
            collections = self._repo.get_all_collections()
            old_name = next((c["name"] for c in collections if c["id"] == list_id), "")
        except Exception:
            old_name = ""
        name, ok = QInputDialog.getText(self, "重命名书单", "新名称：", text=old_name)
        if ok and name.strip():
            try:
                self._repo.rename_collection(list_id, name.strip())
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重命名失败：{e}")