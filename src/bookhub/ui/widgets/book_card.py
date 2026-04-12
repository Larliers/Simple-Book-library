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
