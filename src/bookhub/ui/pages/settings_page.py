from __future__ import annotations

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


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 20)
        root.setSpacing(14)

        title = QLabel("General Settings")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        startup = QFrame()
        startup_layout = QVBoxLayout(startup)
        startup_layout.addWidget(QLabel("Startup Options"))
        launch_check = QCheckBox("Launch at system startup")
        launch_check.setChecked(True)
        startup_layout.addWidget(launch_check)
        tray_check = QCheckBox("Minimize to tray on close")
        startup_layout.addWidget(tray_check)
        root.addWidget(startup)

        language_box = QFrame()
        language_layout = QFormLayout(language_box)
        language = QComboBox()
        language.addItems(["Chinese (Simplified)", "English"])
        language_layout.addRow("Display language", language)
        root.addWidget(language_box)

        library_box = QFrame()
        library_layout = QVBoxLayout(library_box)
        row = QHBoxLayout()
        row.addWidget(QLabel("Library Folders"), 1)
        row.addWidget(QPushButton("+ Add Path"))
        library_layout.addLayout(row)
        folders = QListWidget()
        folders.addItems([r"C:\Users\Admin\Documents\My Books", r"D:\External\E-Library\Archive"])
        library_layout.addWidget(folders)
        root.addWidget(library_box)

        action_row = QHBoxLayout()
        scan_btn = QPushButton("Scan folders for new books now")
        scan_btn.setObjectName("PrimaryButton")
        action_row.addWidget(scan_btn)
        action_row.addWidget(QPushButton("Manage Metadata"))
        action_row.addStretch(1)
        root.addLayout(action_row)

        root.addStretch(1)

