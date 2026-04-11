from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from bookhub.ui.models.resource import ResourceItem


class BookCardWidget(QFrame):
    def __init__(self, resource: ResourceItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.resource = resource
        self.setObjectName("BookCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(170)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        cover = QLabel("COVER")
        cover.setFixedHeight(180)
        cover.setAlignment(Qt.AlignCenter)
        cover.setObjectName("BookCover")
        layout.addWidget(cover)

        title = QLabel(resource.title)
        title.setObjectName("BookTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        author = QLabel(resource.author)
        author.setObjectName("BookMeta")
        layout.addWidget(author)

        status = QLabel(resource.status)
        status.setObjectName("BookStatus")
        status.setAlignment(Qt.AlignLeft)
        layout.addWidget(status)

