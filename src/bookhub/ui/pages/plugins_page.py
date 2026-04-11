from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QPushButton, QTextEdit, QVBoxLayout, QWidget

from bookhub.i18n import tr


class PluginsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 20)
        root.setSpacing(12)

        self.title = QLabel("Installed Tools")
        self.title.setObjectName("PageTitle")
        root.addWidget(self.title)

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
        self.configure_btn = QPushButton("CONFIGURE")
        self.configure_btn.setObjectName("PrimaryButton")
        self.disable_btn = QPushButton("DISABLE")
        row.addWidget(self.configure_btn)
        row.addWidget(self.disable_btn)
        row.addStretch(1)
        detail_layout.addLayout(row)

        self.body = QTextEdit()
        self.body.setReadOnly(True)
        self.body.setPlainText(
            "Automatically retrieves and updates book metadata.\n\n"
            "Features:\n"
            "- High-resolution cover art synchronization\n"
            "- Multi-language metadata support\n"
            "- Customizable data fields mapping"
        )
        detail_layout.addWidget(self.body, 1)

        self.uninstall_btn = QPushButton("UNINSTALL PLUGIN")
        self.uninstall_btn.setObjectName("DangerButton")
        detail_layout.addWidget(self.uninstall_btn)
        content.addWidget(detail, 2)

        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.title.setText(tr("plugins.title", "Installed Tools"))
        self.configure_btn.setText(tr("plugins.configure", "CONFIGURE"))
        self.disable_btn.setText(tr("plugins.disable", "DISABLE"))
        self.uninstall_btn.setText(tr("plugins.uninstall", "UNINSTALL PLUGIN"))
        self.body.setPlainText(
            tr(
                "plugins.description",
                "Automatically retrieves and updates book metadata.\n\n"
                "Features:\n"
                "- High-resolution cover art synchronization\n"
                "- Multi-language metadata support\n"
                "- Customizable data fields mapping",
            )
        )
