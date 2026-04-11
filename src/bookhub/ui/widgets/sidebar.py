from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QSpacerItem, QSizePolicy, QVBoxLayout, QWidget

from bookhub.i18n import tr


class SidebarWidget(QWidget):
    page_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)

        self.title = QLabel("Bookshelf")
        self.title.setObjectName("SidebarTitle")
        layout.addWidget(self.title)

        self._buttons: dict[str, QPushButton] = {}
        self._button_english = {
            "library": "Library",
            "collections": "Collections",
            "reading_now": "Reading Now",
            "favorites": "Favorites",
            "tools": "Tools",
            "trash": "Trash",
            "settings": "Settings",
        }
        for key, text in self._button_english.items():
            button = QPushButton(text)
            button.setCheckable(True)
            button.clicked.connect(lambda _=False, page=key: self._emit_page(page))
            layout.addWidget(button)
            self._buttons[key] = button

        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.import_button = QPushButton("IMPORT BOOKS")
        self.import_button.setObjectName("PrimarySideButton")
        layout.addWidget(self.import_button)

        self.retranslate_ui()
        self.set_active("library")

    def retranslate_ui(self) -> None:
        self.title.setText(tr("sidebar.title", "Bookshelf"))
        self._buttons["library"].setText(tr("sidebar.library", "Library"))
        self._buttons["collections"].setText(tr("sidebar.collections", "Collections"))
        self._buttons["reading_now"].setText(tr("sidebar.reading_now", "Reading Now"))
        self._buttons["favorites"].setText(tr("sidebar.favorites", "Favorites"))
        self._buttons["tools"].setText(tr("sidebar.tools", "Tools"))
        self._buttons["trash"].setText(tr("sidebar.trash", "Trash"))
        self._buttons["settings"].setText(tr("sidebar.settings", "Settings"))
        self.import_button.setText(tr("sidebar.import_books", "IMPORT BOOKS"))

    def set_active(self, page_name: str) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == page_name)

    def _emit_page(self, page_name: str) -> None:
        self.set_active(page_name)
        self.page_requested.emit(page_name)
