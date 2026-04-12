from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    def __init__(self, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        layout.addWidget(title_label)

        panel = QFrame()
        panel.setObjectName("PageSection")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 16, 16, 16)

        detail = QLabel(description)
        detail.setObjectName("PageSubtitle")
        detail.setWordWrap(True)
        detail.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        panel_layout.addWidget(detail)

        hint = QLabel("This section is intentionally kept as a skeleton in this UI phase.")
        hint.setObjectName("PageSubtitle")
        panel_layout.addWidget(hint)

        layout.addWidget(panel)
        layout.addStretch(1)
