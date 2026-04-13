# -*- coding: utf-8 -*-
"""
Dialog for adding a book to one or more collections (custom book lists).
Matches the design in 鼠标右键的菜单.html: search, list of collections, create new.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QCheckBox,
    QWidget, QFrame, QMessageBox, QSizePolicy, QScrollArea,
    QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QAction


class AddToCollectionDialog(QDialog):
    """
    Dialog that shows existing collections, lets user check/uncheck them,
    search them, and create new ones.
    """
    collections_updated = Signal()

    def __init__(
        self,
        book_id: int,
        book_title: str,
        repository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._book_id = book_id
        self._book_title = book_title
        self._repo = repository
        self._search_text: str = ""
        self._setup_ui()
        self._load_collections()

    # ------------------------------------------------------------------ #
    # UI setup
    # ------------------------------------------------------------------ #
    def _setup_ui(self) -> None:
        self.setWindowTitle("Add to Collection")
        self.setMinimumWidth(420)
        self.setMinimumHeight(520)
        self.setObjectName("AddToCollectionDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # Title
        title_lbl = QLabel("Add to Collection")
        f = QFont()
        f.setPointSize(15)
        f.setBold(True)
        title_lbl.setFont(f)
        layout.addWidget(title_lbl)

        # Book name
        book_lbl = QLabel(f"Book: {self._book_title}")
        book_lbl.setObjectName("bookTitleLabel")
        book_lbl.setWordWrap(True)
        layout.addWidget(book_lbl)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep1)

        # Search bar
        search_row = QHBoxLayout()
        search_icon = QLabel("🔍")
        search_row.addWidget(search_icon)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search collections...")
        self._search_input.setObjectName("searchInput")
        self._search_input.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self._search_input)
        layout.addLayout(search_row)

        # Collections list
        self._list_widget = QListWidget()
        self._list_widget.setObjectName("collectionsList")
        self._list_widget.setMinimumHeight(200)
        layout.addWidget(self._list_widget)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep2)

        # Create new collection row
        new_lbl = QLabel("Create new collection:")
        new_lbl.setObjectName("newCollLabel")
        layout.addWidget(new_lbl)

        new_row = QHBoxLayout()
        self._new_name_input = QLineEdit()
        self._new_name_input.setPlaceholderText("Collection name...")
        self._new_name_input.setObjectName("newCollectionInput")
        self._new_name_input.returnPressed.connect(self._create_collection)
        new_row.addWidget(self._new_name_input)

        create_btn = QPushButton("＋ Create")
        create_btn.setObjectName("createCollectionBtn")
        create_btn.clicked.connect(self._create_collection)
        new_row.addWidget(create_btn)
        layout.addLayout(new_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        confirm_btn = QPushButton("Confirm")
        confirm_btn.setObjectName("confirmBtn")
        confirm_btn.setDefault(True)
        confirm_btn.clicked.connect(self._confirm)
        btn_row.addWidget(confirm_btn)
        layout.addLayout(btn_row)

        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QDialog#AddToCollectionDialog { background-color: #FAFAFA; }
            QLabel#bookTitleLabel { color: #666; font-size: 12px; }
            QLineEdit#searchInput, QLineEdit#newCollectionInput {
                border: 1px solid #E0E0E0; border-radius: 4px;
                padding: 7px 10px; background-color: white; font-size: 13px;
            }
            QLineEdit:focus { border-color: #1565C0; }
            QListWidget#collectionsList {
                border: 1px solid #E0E0E0; border-radius: 6px;
                background-color: white;
            }
            QListWidget#collectionsList::item {
                padding: 2px 4px; border-bottom: 1px solid #F5F5F5;
            }
            QListWidget#collectionsList::item:hover { background-color: #F5F5F5; }
            QPushButton#createCollectionBtn {
                background-color: #1976D2; color: white; border: none;
                border-radius: 4px; padding: 8px 14px; font-size: 13px; min-width: 90px;
            }
            QPushButton#createCollectionBtn:hover { background-color: #1565C0; }
            QPushButton#cancelBtn {
                background-color: white; color: #333; border: 1px solid #DDD;
                border-radius: 4px; padding: 8px 20px; font-size: 13px;
            }
            QPushButton#cancelBtn:hover { background-color: #F5F5F5; }
            QPushButton#confirmBtn {
                background-color: #1565C0; color: white; border: none;
                border-radius: 4px; padding: 8px 20px; font-size: 13px; font-weight: bold;
            }
            QPushButton#confirmBtn:hover { background-color: #0D47A1; }
        """)

    # ------------------------------------------------------------------ #
    # Data loading
    # ------------------------------------------------------------------ #
    def _load_collections(self) -> None:
        self._list_widget.clear()
        try:
            collections = self._repo.get_all_collections()
        except Exception as e:
            print(f"[AddToCollectionDialog] get_all_collections error: {e}")
            collections = []

        search = self._search_text.lower()
        for col in collections:
            cid = col.get("id")
            name: str = col.get("name", "Unknown")
            if search and search not in name.lower():
                continue
            try:
                count = self._repo.get_collection_book_count(cid)
            except Exception:
                count = 0
            try:
                is_in = self._repo.is_book_in_collection(self._book_id, cid)
            except Exception:
                is_in = False

            item = QListWidgetItem()
            widget = QWidget()
            row = QHBoxLayout(widget)
            row.setContentsMargins(10, 4, 10, 4)
            row.setSpacing(8)

            cb = QCheckBox()
            cb.setChecked(is_in)
            cb.setProperty("collection_id", cid)
            row.addWidget(cb)

            name_lbl = QLabel(name)
            name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            row.addWidget(name_lbl)

            count_lbl = QLabel(f"{count}")
            count_lbl.setStyleSheet("color: #9E9E9E; font-size: 11px; min-width: 30px;")
            count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(count_lbl)

            item.setSizeHint(widget.sizeHint())
            self._list_widget.addItem(item)
            self._list_widget.setItemWidget(item, widget)

    def _on_search_changed(self, text: str) -> None:
        self._search_text = text
        self._load_collections()

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def _create_collection(self) -> None:
        name = self._new_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Collection name cannot be empty.")
            return
        try:
            self._repo.create_collection(name)
            self._new_name_input.clear()
            self._load_collections()
            self.collections_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create collection: {e}")

    def _confirm(self) -> None:
        """Apply all checkbox changes and close."""
        try:
            for i in range(self._list_widget.count()):
                item = self._list_widget.item(i)
                widget = self._list_widget.itemWidget(item)
                if widget is None:
                    continue
                cb = widget.findChild(QCheckBox)
                if cb is None:
                    continue
                cid = cb.property("collection_id")
                if cid is None:
                    continue
                try:
                    is_in = self._repo.is_book_in_collection(self._book_id, cid)
                except Exception:
                    is_in = False
                if cb.isChecked() and not is_in:
                    self._repo.add_book_to_collection(self._book_id, cid)
                elif not cb.isChecked() and is_in:
                    self._repo.remove_book_from_collection(self._book_id, cid)
            self.collections_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update collections: {e}")
        self.accept()