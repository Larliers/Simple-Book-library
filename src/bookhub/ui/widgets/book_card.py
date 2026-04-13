from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from bookhub.ui.models.resource import ResourceItem
from bookhub.ui.resources.layout_config import UI_LAYOUT


class BookCardWidget(QFrame):
    def __init__(self, resource: ResourceItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.resource = resource
        self.setObjectName("BookCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedWidth(UI_LAYOUT.card_width)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            UI_LAYOUT.card_inner_padding,
            UI_LAYOUT.card_inner_padding,
            UI_LAYOUT.card_inner_padding,
            UI_LAYOUT.card_inner_padding,
        )
        layout.setSpacing(6)

        cover_width, cover_height = UI_LAYOUT.cover_size()
        self.cover = QLabel("COVER")
        self.cover.setFixedSize(cover_width, cover_height)
        self.cover.setAlignment(Qt.AlignCenter)
        self.cover.setObjectName("BookCover")
        self.cover.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(self.cover)
        self._render_cover()

        title = QLabel(resource.title)
        title.setObjectName("BookTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        author = QLabel(resource.author)
        author.setObjectName("BookMeta")
        layout.addWidget(author)

        status = QLabel(resource.status)
        status.setObjectName("BookStatus")
        status.setAlignment(Qt.AlignCenter)
        status.setFixedWidth(58)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(status, 0)
        row.addStretch(1)
        layout.addLayout(row)

        tags_row = QHBoxLayout()
        tags_row.setContentsMargins(0, 0, 0, 0)
        tags_row.setSpacing(4)
        for tag in resource.tags[:2]:
            tag_label = QLabel(tag)
            tag_label.setObjectName("BookTags")
            tags_row.addWidget(tag_label)
        tags_row.addStretch(1)
        layout.addLayout(tags_row)

    def _render_cover(self) -> None:
        if not self.resource.thumbnail_path:
            return
        thumbnail_path = Path(self.resource.thumbnail_path)
        if not thumbnail_path.exists():
            return
        pixmap = QPixmap(str(thumbnail_path))
        if pixmap.isNull():
            return
        scaled = pixmap.scaled(
            self.cover.width(),
            self.cover.height(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        self.cover.setPixmap(scaled)
        self.cover.setText("")


# =======================================================================
# Right-click context menu support for BookCardWidget
# Added by _final_implement.py
# =======================================================================

def install_book_context_menu(card_widget, repository) -> None:
    """
    Install a right-click context menu on a BookCard widget.
    
    Usage:
        card = BookCardWidget(resource)
        install_book_context_menu(card, repository)
    """
    from PySide6.QtWidgets import QMenu
    from PySide6.QtGui import QAction
    from PySide6.QtCore import Qt

    def _get_book_id():
        # ResourceItem-based cards
        res = getattr(card_widget, 'resource', None) or getattr(card_widget, '_resource', None)
        if res is not None:
            return getattr(res, 'id', None) or getattr(res, 'book_id', None)
        # dict-based
        book = getattr(card_widget, 'book', None) or getattr(card_widget, '_book', None)
        if isinstance(book, dict):
            return book.get('id')
        if book is not None:
            return getattr(book, 'id', None)
        return None

    def _get_book_title():
        res = getattr(card_widget, 'resource', None) or getattr(card_widget, '_resource', None)
        if res is not None:
            return getattr(res, 'title', None) or 'Unknown'
        book = getattr(card_widget, 'book', None) or getattr(card_widget, '_book', None)
        if isinstance(book, dict):
            return book.get('title', 'Unknown')
        if book is not None:
            return getattr(book, 'title', 'Unknown')
        return 'Unknown'

    def show_context_menu(pos) -> None:
        book_id = _get_book_id()
        book_title = _get_book_title()
        menu = QMenu(card_widget)

        # Favorites toggle
        if book_id is not None and repository is not None:
            try:
                is_fav = repository.is_favorite(book_id)
            except Exception:
                is_fav = False

            if is_fav:
                fav_act = QAction("★ Remove from Favorites", card_widget)
                fav_act.triggered.connect(
                    lambda: _do_remove_favorite(book_id, repository, card_widget)
                )
            else:
                fav_act = QAction("☆ Add to Favorites", card_widget)
                fav_act.triggered.connect(
                    lambda: _do_add_favorite(book_id, repository, card_widget)
                )
            menu.addAction(fav_act)

            # Add to Collection
            col_act = QAction("Add to Collection…", card_widget)
            col_act.triggered.connect(
                lambda: _do_add_to_collection(book_id, book_title, repository, card_widget)
            )
            menu.addAction(col_act)

        if menu.actions():
            menu.exec(card_widget.mapToGlobal(pos))

    card_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    card_widget.customContextMenuRequested.connect(show_context_menu)


def _do_add_favorite(book_id: int, repository, parent_widget) -> None:
    try:
        repository.add_to_favorites(book_id)
        from PySide6.QtWidgets import QToolTip
        from PySide6.QtCore import QPoint
        QToolTip.showText(
            parent_widget.mapToGlobal(QPoint(0, 0)),
            "Added to Favorites ★",
            parent_widget,
            parent_widget.rect(),
            2000,
        )
    except Exception as e:
        print(f"[BookCard] add_to_favorites error: {e}")


def _do_remove_favorite(book_id: int, repository, parent_widget) -> None:
    try:
        repository.remove_from_favorites(book_id)
        from PySide6.QtWidgets import QToolTip
        from PySide6.QtCore import QPoint
        QToolTip.showText(
            parent_widget.mapToGlobal(QPoint(0, 0)),
            "Removed from Favorites",
            parent_widget,
            parent_widget.rect(),
            2000,
        )
    except Exception as e:
        print(f"[BookCard] remove_from_favorites error: {e}")


def _do_add_to_collection(book_id: int, book_title: str, repository, parent_widget) -> None:
    try:
        from bookhub.ui.dialogs.add_to_collection_dialog import AddToCollectionDialog
    except ImportError:
        print("[BookCard] Cannot import AddToCollectionDialog")
        return
    dlg = AddToCollectionDialog(book_id, book_title, repository, parent_widget)
    dlg.exec()
