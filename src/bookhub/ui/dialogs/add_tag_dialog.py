from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr


class AddTagDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("tag_dialog.title", "Add Tag"))
        self.resize(340, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel(tr("tag_dialog.title", "Add Tag"))
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        root.addWidget(title)

        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText(tr("tag_dialog.tag_placeholder", "Type tag..."))
        root.addWidget(self.tag_input)

        root.addWidget(QLabel(tr("tag_dialog.recent", "Recent tags")))
        self.recent_tags = QListWidget()
        self.recent_tags.addItems(["Psychology", "Technology", "To Buy"])
        self.recent_tags.itemClicked.connect(lambda item: self.tag_input.setText(item.text()))
        root.addWidget(self.recent_tags)

        root.addWidget(QLabel(tr("tag_dialog.lists", "Add to custom list")))
        self.custom_lists = QListWidget()
        self.custom_lists.addItems(["Must Read", "Professional", "References"])
        root.addWidget(self.custom_lists)

        actions = QHBoxLayout()
        self.confirm_btn = QPushButton(tr("tag_dialog.confirm", "Confirm"))
        self.confirm_btn.setObjectName("PrimaryButton")
        self.confirm_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton(tr("tag_dialog.cancel", "Cancel"))
        self.cancel_btn.setObjectName("GhostButton")
        self.cancel_btn.clicked.connect(self.reject)
        actions.addWidget(self.confirm_btn)
        actions.addWidget(self.cancel_btn)
        root.addLayout(actions)

    @property
    def selected_tag(self) -> str:
        return self.tag_input.text().strip()
