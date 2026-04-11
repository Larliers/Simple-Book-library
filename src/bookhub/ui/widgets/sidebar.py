from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QSpacerItem, QSizePolicy, QVBoxLayout, QWidget


class SidebarWidget(QWidget):
    page_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Bookshelf")
        title.setObjectName("SidebarTitle")
        layout.addWidget(title)

        self._buttons: dict[str, QPushButton] = {}
        for key, text in [
            ("library", "Library"),
            ("collections", "Collections"),
            ("reading_now", "Reading Now"),
            ("favorites", "Favorites"),
            ("tools", "Tools"),
            ("trash", "Trash"),
            ("settings", "Settings"),
        ]:
            button = QPushButton(text)
            button.setCheckable(True)
            button.clicked.connect(lambda _=False, page=key: self._emit_page(page))
            layout.addWidget(button)
            self._buttons[key] = button

        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        import_button = QPushButton("IMPORT BOOKS")
        import_button.setObjectName("PrimarySideButton")
        layout.addWidget(import_button)

        self.set_active("library")

    def set_active(self, page_name: str) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == page_name)

    def _emit_page(self, page_name: str) -> None:
        self.set_active(page_name)
        self.page_requested.emit(page_name)

