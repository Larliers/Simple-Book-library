from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget


class TopBarWidget(QWidget):
    query_changed = Signal(str)
    import_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TopBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search library...")
        self.search_input.textChanged.connect(self.query_changed.emit)
        layout.addWidget(self.search_input, 1)

        self.import_button = QPushButton("IMPORT")
        self.import_button.clicked.connect(self.import_requested.emit)
        layout.addWidget(self.import_button)

        self.new_list_button = QPushButton("NEW LIST")
        self.new_list_button.setObjectName("PrimaryButton")
        layout.addWidget(self.new_list_button)

        self.refresh_button = QPushButton("↻")
        self.refresh_button.setFixedWidth(36)
        layout.addWidget(self.refresh_button)

        self.menu_button = QPushButton("⋮")
        self.menu_button.setFixedWidth(36)
        layout.addWidget(self.menu_button)

