from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

from bookhub.ui.models.resource import ResourceItem
from bookhub.ui.resources.layout_config import GRID_DENSITY


class BookCardWidget(QFrame):
    def __init__(self, resource: ResourceItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.resource = resource
        self.setObjectName("BookCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedWidth(GRID_DENSITY.card_width)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            GRID_DENSITY.card_inner_padding,
            GRID_DENSITY.card_inner_padding,
            GRID_DENSITY.card_inner_padding,
            GRID_DENSITY.card_inner_padding,
        )
        layout.setSpacing(6)

        cover_width, cover_height = GRID_DENSITY.cover_size()
        cover = QLabel("COVER")
        cover.setFixedSize(cover_width, cover_height)
        cover.setAlignment(Qt.AlignCenter)
        cover.setObjectName("BookCover")
        cover.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
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
