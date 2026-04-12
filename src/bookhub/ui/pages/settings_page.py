from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr


class SettingsPage(QWidget):
    language_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        top = QHBoxLayout()
        self.app_title = QLabel("System Architect")
        self.app_title.setStyleSheet("font-size: 28px; font-weight: 700;")
        top.addWidget(self.app_title)
        top.addStretch(1)
        self.search_settings = QLineEdit()
        self.search_settings.setObjectName("SettingsSearchInput")
        self.search_settings.setPlaceholderText("Search settings")
        self.search_settings.setFixedWidth(260)
        top.addWidget(self.search_settings)
        root.addLayout(top)

        shell = QHBoxLayout()
        shell.setSpacing(14)
        root.addLayout(shell, 1)

        self.nav = QListWidget()
        self.nav.setObjectName("SettingsNav")
        self.nav.setFixedWidth(210)
        self.nav.addItems(["General", "Library", "Appearance", "About"])
        self.nav.setCurrentRow(0)
        shell.addWidget(self.nav)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        self.title = QLabel("General Settings")
        self.title.setObjectName("PageTitle")
        content_layout.addWidget(self.title)

        startup = QFrame()
        startup.setObjectName("PageSection")
        startup_layout = QVBoxLayout(startup)
        startup_layout.setContentsMargins(14, 14, 14, 14)
        self.startup_label = QLabel("STARTUP OPTIONS")
        self.startup_label.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #6a7382;")
        startup_layout.addWidget(self.startup_label)
        self.launch_check = QCheckBox("Launch at system startup")
        self.launch_check.setChecked(True)
        startup_layout.addWidget(self.launch_check)
        self.tray_check = QCheckBox("Minimize to tray on close")
        startup_layout.addWidget(self.tray_check)
        content_layout.addWidget(startup)

        lang = QFrame()
        lang.setObjectName("PageSection")
        lang_layout = QVBoxLayout(lang)
        lang_layout.setContentsMargins(14, 14, 14, 14)
        self.language_label = QLabel("Display language")
        lang_layout.addWidget(self.language_label)
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("SettingsLanguageCombo")
        self.language_combo.currentIndexChanged.connect(self._emit_language_changed)
        lang_layout.addWidget(self.language_combo)
        self.restart_hint = QLabel("Restart application to apply language changes.")
        self.restart_hint.setObjectName("PageSubtitle")
        lang_layout.addWidget(self.restart_hint)
        content_layout.addWidget(lang)

        library_box = QFrame()
        library_box.setObjectName("PageSection")
        library_layout = QVBoxLayout(library_box)
        library_layout.setContentsMargins(14, 14, 14, 14)
        row = QHBoxLayout()
        self.library_label = QLabel("LIBRARY FOLDERS")
        self.library_label.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #6a7382;")
        self.add_path_button = QPushButton("+ Add Path")
        self.add_path_button.setObjectName("PrimaryButton")
        row.addWidget(self.library_label, 1)
        row.addWidget(self.add_path_button)
        library_layout.addLayout(row)

        self.folders = QListWidget()
        self.folders.addItems([r"C:\Users\Admin\Documents\My Books", r"D:\External\E-Library\Archive"])
        library_layout.addWidget(self.folders)
        content_layout.addWidget(library_box)

        action_row = QHBoxLayout()
        self.scan_btn = QPushButton("Scan folders for new books now")
        self.scan_btn.setObjectName("PrimaryButton")
        self.manage_btn = QPushButton("Manage Metadata")
        self.manage_btn.setObjectName("GhostButton")
        action_row.addWidget(self.scan_btn)
        action_row.addWidget(self.manage_btn)
        action_row.addStretch(1)
        content_layout.addLayout(action_row)
        content_layout.addStretch(1)

        shell.addWidget(content, 1)

        self._set_language_options()
        self.set_language_selection("en")
        self.retranslate_ui()

    def set_language_selection(self, language_code: str) -> None:
        index = self.language_combo.findData(language_code)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)

    def retranslate_ui(self) -> None:
        self.title.setText(tr("settings.title", "General Settings"))
        self.startup_label.setText(tr("settings.startup_options", "Startup Options"))
        self.launch_check.setText(tr("settings.launch_startup", "Launch at system startup"))
        self.tray_check.setText(tr("settings.minimize_tray", "Minimize to tray on close"))
        self.language_label.setText(tr("settings.display_language", "Display language"))
        self.library_label.setText(tr("settings.library_folders", "Library Folders"))
        self.add_path_button.setText(tr("settings.add_path", "+ Add Path"))
        self.scan_btn.setText(tr("settings.scan_now", "Scan folders for new books now"))
        self.manage_btn.setText(tr("settings.manage_metadata", "Manage Metadata"))
        self.restart_hint.setText(tr("settings.restart_hint", "Restart application to apply language changes."))
        self.search_settings.setPlaceholderText(tr("settings.search_placeholder", "Search settings"))
        self._set_language_options()

    def _set_language_options(self) -> None:
        current = self.language_combo.currentData()
        self.language_combo.blockSignals(True)
        self.language_combo.clear()
        self.language_combo.addItem(tr("settings.lang.english", "English"), "en")
        self.language_combo.addItem(tr("settings.lang.zh_cn", "Chinese (Simplified)"), "zh-cn")
        index = self.language_combo.findData(current or "en")
        self.language_combo.setCurrentIndex(index if index >= 0 else 0)
        self.language_combo.blockSignals(False)

    def _emit_language_changed(self) -> None:
        code = self.language_combo.currentData() or "en"
        self.language_changed.emit(code)
