from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    def __init__(self, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        layout.addWidget(title_label)

        detail = QLabel(description)
        detail.setObjectName("PageSubtitle")
        detail.setWordWrap(True)
        detail.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(detail)
        layout.addStretch(1)

