from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QPushButton, QTextEdit, QVBoxLayout, QWidget


class PluginsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 20)
        root.setSpacing(12)

        title = QLabel("Installed Tools")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        content = QHBoxLayout()
        root.addLayout(content, 1)

        plugin_list = QListWidget()
        plugin_list.addItems(
            [
                "Metadata Fetcher v2.4.1",
                "PDF Converter Pro v1.2.0",
                "Universal Translator v3.0.5",
                "Cloud Sync Bridge v0.9.1",
                "ISBN Scanner v1.1.2",
            ]
        )
        content.addWidget(plugin_list, 1)

        detail = QFrame()
        detail_layout = QVBoxLayout(detail)
        detail_layout.addWidget(QLabel("Metadata Fetcher"))

        row = QHBoxLayout()
        configure = QPushButton("CONFIGURE")
        configure.setObjectName("PrimaryButton")
        row.addWidget(configure)
        row.addWidget(QPushButton("DISABLE"))
        row.addStretch(1)
        detail_layout.addLayout(row)

        body = QTextEdit()
        body.setReadOnly(True)
        body.setPlainText(
            "Automatically retrieves and updates book metadata.\n\n"
            "Features:\n"
            "- High-resolution cover art synchronization\n"
            "- Multi-language metadata support\n"
            "- Customizable data fields mapping"
        )
        detail_layout.addWidget(body, 1)

        uninstall = QPushButton("UNINSTALL PLUGIN")
        uninstall.setObjectName("DangerButton")
        detail_layout.addWidget(uninstall)
        content.addWidget(detail, 2)

