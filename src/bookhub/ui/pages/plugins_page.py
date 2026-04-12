from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr


class PluginsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(12)

        self.title = QLabel("Installed Tools")
        self.title.setObjectName("PageTitle")
        root.addWidget(self.title)

        shell = QHBoxLayout()
        shell.setSpacing(0)
        root.addLayout(shell, 1)

        self.plugin_list = QListWidget()
        self.plugin_list.setObjectName("PageSection")
        self.plugin_list.setMinimumWidth(270)
        self.plugin_list.currentTextChanged.connect(self._on_plugin_changed)
        for item in [
            "Metadata Fetcher v2.4.1",
            "PDF Converter Pro v1.2.0",
            "Universal Translator v3.0.5",
            "Cloud Sync Bridge v0.9.1",
            "ISBN Scanner v1.1.2",
            "Reading Statistics v2.1.0",
        ]:
            self.plugin_list.addItem(QListWidgetItem(item))
        shell.addWidget(self.plugin_list, 0)

        right = QWidget()
        right_layout = QHBoxLayout(right)
        right_layout.setContentsMargins(18, 0, 0, 0)
        right_layout.setSpacing(14)

        detail = QFrame()
        detail.setObjectName("PageSection")
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(10)

        self.plugin_name = QLabel("Metadata Fetcher")
        self.plugin_name.setStyleSheet("font-size: 44px; font-weight: 700;")
        detail_layout.addWidget(self.plugin_name)

        badge_row = QHBoxLayout()
        self.version_badge = QLabel("VERSION 2.4.1")
        self.version_badge.setObjectName("BookTags")
        badge_row.addWidget(self.version_badge)
        compatibility = QLabel("WINDOWS 10/11")
        compatibility.setObjectName("BookTags")
        badge_row.addWidget(compatibility)
        badge_row.addStretch(1)
        detail_layout.addLayout(badge_row)

        action_row = QHBoxLayout()
        self.configure_btn = QPushButton("CONFIGURE")
        self.configure_btn.setObjectName("PrimaryButton")
        self.disable_btn = QPushButton("DISABLE")
        self.disable_btn.setObjectName("GhostButton")
        action_row.addWidget(self.configure_btn)
        action_row.addWidget(self.disable_btn)
        action_row.addStretch(1)
        detail_layout.addLayout(action_row)

        desc_title = QLabel("DESCRIPTION")
        desc_title.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #6a7382;")
        detail_layout.addWidget(desc_title)

        self.body = QTextEdit()
        self.body.setReadOnly(True)
        detail_layout.addWidget(self.body, 1)

        feature_title = QLabel("FEATURES")
        feature_title.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #6a7382;")
        detail_layout.addWidget(feature_title)
        self.features = QLabel("")
        self.features.setWordWrap(True)
        detail_layout.addWidget(self.features)

        right_layout.addWidget(detail, 1)

        info_panel = QFrame()
        info_panel.setObjectName("SubtlePanel")
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(14, 14, 14, 14)
        info_layout.setSpacing(8)
        info_label = QLabel("INFORMATION")
        info_label.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #6a7382;")
        info_layout.addWidget(info_label)
        self.info_text = QLabel("Developer\nBookshelf Core Team\n\nLast updated\nOct 24, 2023")
        self.info_text.setWordWrap(True)
        self.info_text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        info_layout.addWidget(self.info_text)
        self.uninstall_btn = QPushButton("UNINSTALL PLUGIN")
        self.uninstall_btn.setObjectName("DangerButton")
        info_layout.addWidget(self.uninstall_btn)
        info_layout.addStretch(1)
        right_layout.addWidget(info_panel, 0)

        shell.addWidget(right, 1)

        self.retranslate_ui()
        self.plugin_list.setCurrentRow(0)

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
        self.features.setText(
            "- High-resolution cover art synchronization\n"
            "- Multi-language support\n"
            "- Automated series grouping\n"
            "- Customizable field mapping"
        )

    def _on_plugin_changed(self, text: str) -> None:
        if not text:
            return
        name = text.split(" v", 1)[0]
        self.plugin_name.setText(name)
        version = text.split(" v", 1)[1] if " v" in text else "1.0.0"
        self.version_badge.setText(f"VERSION {version}")
