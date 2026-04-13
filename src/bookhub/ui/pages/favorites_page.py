# -*- coding: utf-8 -*-
"""
Favorites page - shows all books marked as favorites.
"""
try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QScrollArea, QFrame, QGridLayout, QSizePolicy, QMessageBox, QMenu
    )
    from PyQt5.QtCore import Qt, pyqtSignal as Signal, QSize
    from PyQt5.QtGui import QFont
except ImportError:
    try:
        from PySide6.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
            QScrollArea, QFrame, QGridLayout, QSizePolicy, QMessageBox, QMenu
        )
        from PySide6.QtCore import Qt, Signal, QSize
        from PySide6.QtGui import QFont
    except ImportError:
        from PySide2.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
            QScrollArea, QFrame, QGridLayout, QSizePolicy, QMessageBox, QMenu
        )
        from PySide2.QtCore import Qt, Signal, QSize
        from PySide2.QtGui import QFont

import hashlib


class FavoriteBookCard(QFrame):
    """Simple card widget for a favorite book."""
    remove_requested = Signal(int)  # book_id

    def __init__(self, book_data: dict, parent=None):
        super().__init__(parent)
        self._book = book_data
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("FavoriteBookCard")
        self.setFixedSize(160, 230)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Cover placeholder
        self._cover_label = QLabel()
        self._cover_label.setFixedSize(144, 170)
        self._cover_label.setAlignment(Qt.AlignCenter)
        self._render_cover()
        layout.addWidget(self._cover_label)

        # Title
        title = str(self._book.get('title', self._book.get('file_path', 'Unknown')))
        display_title = (title[:22] + '...') if len(title) > 22 else title
        title_label = QLabel(display_title)
        title_label.setObjectName("bookCardTitle")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        self._apply_styles()

    def _render_cover(self):
        title = str(self._book.get('title', ''))
        colors = ['#1565C0', '#2E7D32', '#B71C1C', '#E65100', '#4A148C', '#006064', '#37474F']
        idx = int(hashlib.md5(title.encode('utf-8', errors='replace')).hexdigest(), 16) % len(colors)
        color = colors[idx]
        initial = title[0].upper() if title else '?'
        self._cover_label.setText(initial)
        self._cover_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: 6px;
                font-size: 32pt;
                font-weight: bold;
            }}
        """)

    def _apply_styles(self):
        self.setStyleSheet("""
            QFrame#FavoriteBookCard {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            QFrame#FavoriteBookCard:hover {
                border: 1px solid #BDBDBD;
                background-color: #FAFAFA;
            }
            QLabel#bookCardTitle {
                font-size: 11px;
                color: #424242;
            }
        """)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        remove_act = menu.addAction("Remove from Favorites")
        act = menu.exec_(self.mapToGlobal(pos))
        if act == remove_act:
            book_id = self._book.get('id')
            if book_id is not None:
                self.remove_requested.emit(book_id)


class FavoritesPage(QWidget):
    """
    Page that shows all books marked as favorites.
    """
    book_removed_from_favorites = Signal(int)  # book_id

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self._repo = repository
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        self.setObjectName("FavoritesPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(0)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Favorites")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setObjectName("pageTitle")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        layout.addSpacing(8)

        # Book count label
        self._count_label = QLabel("")
        self._count_label.setObjectName("countLabel")
        layout.addWidget(self._count_label)
        layout.addSpacing(16)

        # Scroll area for favorite books
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("favoritesScroll")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.NoFrame)

        self._books_container = QWidget()
        self._books_container.setObjectName("booksContainer")
        self._books_grid = QGridLayout(self._books_container)
        self._books_grid.setContentsMargins(0, 0, 0, 0)
        self._books_grid.setSpacing(16)
        self._books_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._scroll.setWidget(self._books_container)
        layout.addWidget(self._scroll)

        # Empty state
        self._empty_label = QLabel(
            "No favorites yet.\n\nRight-click any book and select 'Add to Favorites'."
        )
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet("""
            FavoritesPage {
                background-color: #F5F5F5;
            }
            QLabel#pageTitle {
                color: #212121;
            }
            QLabel#countLabel {
                color: #757575;
                font-size: 13px;
            }
            QScrollArea#favoritesScroll {
                background-color: transparent;
                border: none;
            }
            QWidget#booksContainer {
                background-color: transparent;
            }
            QLabel#emptyLabel {
                color: #9E9E9E;
                font-size: 14px;
                padding: 40px;
            }
        """)

    def refresh(self):
        """Reload favorite books from database."""
        # Clear existing cards
        while self._books_grid.count():
            item = self._books_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            books = self._repo.get_favorite_books()
        except Exception as e:
            print(f'[FavoritesPage] get_favorite_books error: {e}')
            books = []

        count = len(books)
        self._count_label.setText(f"{count} book{'s' if count != 1 else ''}")

        if not books:
            self._empty_label.show()
            self._scroll.hide()
            self._count_label.hide()
        else:
            self._empty_label.hide()
            self._scroll.show()
            self._count_label.show()

            cols_per_row = 6
            for i, book_data in enumerate(books):
                card = FavoriteBookCard(book_data)
                card.remove_requested.connect(self._on_remove_from_favorites)
                row = i // cols_per_row
                col = i % cols_per_row
                self._books_grid.addWidget(card, row, col)

    def _on_remove_from_favorites(self, book_id: int):
        try:
            self._repo.remove_from_favorites(book_id)
            self.book_removed_from_favorites.emit(book_id)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to remove from favorites: {e}")