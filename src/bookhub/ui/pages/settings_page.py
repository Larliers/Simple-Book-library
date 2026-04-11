from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
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
        root.setContentsMargins(20, 18, 20, 20)
        root.setSpacing(14)

        self.title = QLabel("General Settings")
        self.title.setObjectName("PageTitle")
        root.addWidget(self.title)

        startup = QFrame()
        startup_layout = QVBoxLayout(startup)
        self.startup_label = QLabel("Startup Options")
        startup_layout.addWidget(self.startup_label)
        self.launch_check = QCheckBox("Launch at system startup")
        self.launch_check.setChecked(True)
        startup_layout.addWidget(self.launch_check)
        self.tray_check = QCheckBox("Minimize to tray on close")
        startup_layout.addWidget(self.tray_check)
        root.addWidget(startup)

        language_box = QFrame()
        language_layout = QFormLayout(language_box)
        self.language_combo = QComboBox()
        self.language_combo.currentIndexChanged.connect(self._emit_language_changed)
        self.language_label = QLabel("Display language")
        language_layout.addRow(self.language_label, self.language_combo)
        root.addWidget(language_box)

        library_box = QFrame()
        library_layout = QVBoxLayout(library_box)
        row = QHBoxLayout()
        self.library_label = QLabel("Library Folders")
        self.add_path_button = QPushButton("+ Add Path")
        row.addWidget(self.library_label, 1)
        row.addWidget(self.add_path_button)
        library_layout.addLayout(row)
        self.folders = QListWidget()
        self.folders.addItems([r"C:\Users\Admin\Documents\My Books", r"D:\External\E-Library\Archive"])
        library_layout.addWidget(self.folders)
        root.addWidget(library_box)

        action_row = QHBoxLayout()
        self.scan_btn = QPushButton("Scan folders for new books now")
        self.scan_btn.setObjectName("PrimaryButton")
        self.manage_btn = QPushButton("Manage Metadata")
        action_row.addWidget(self.scan_btn)
        action_row.addWidget(self.manage_btn)
        action_row.addStretch(1)
        root.addLayout(action_row)

        self._set_language_options()
        self.set_language_selection("en")
        self.retranslate_ui()
        root.addStretch(1)

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
