from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ImportDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import Books")
        self.resize(940, 620)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(8)
        title = QLabel("ImportBooks")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        header_layout.addWidget(QLabel("File"))
        header_layout.addWidget(QLabel("Home"))
        header_layout.addWidget(QLabel("Share"))
        header_layout.addWidget(QLabel("View"))
        root.addWidget(header)

        breadcrumb = QWidget()
        crumb_layout = QHBoxLayout(breadcrumb)
        crumb_layout.setContentsMargins(10, 8, 10, 8)
        self.path_input = QLineEdit(r"This PC > Documents > Books")
        crumb_layout.addWidget(self.path_input, 1)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Books")
        self.search_input.setFixedWidth(230)
        crumb_layout.addWidget(self.search_input)
        root.addWidget(breadcrumb)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        root.addLayout(body, 1)

        self.quick_access = QListWidget()
        self.quick_access.setFixedWidth(220)
        self.quick_access.addItems(["Quick access", "This PC", "Desktop", "Documents", "Downloads"])
        body.addWidget(self.quick_access)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(10, 10, 10, 10)

        self.preview = QTableWidget(0, 2)
        self.preview.setHorizontalHeaderLabels(["Name", "Type"])
        self.preview.verticalHeader().setVisible(False)
        self.preview.horizontalHeader().setStretchLastSection(True)
        self.preview.setSelectionBehavior(QTableWidget.SelectRows)
        for name, kind in [
            ("Introduction_to_AI.pdf", "PDF"),
            ("Design_Patterns.epub", "EPUB"),
            ("Advanced_Calculus.pdf", "PDF"),
            ("Cloud_Native_Apps.mobi", "MOBI"),
            ("Typography_101.pdf", "PDF"),
        ]:
            row = self.preview.rowCount()
            self.preview.insertRow(row)
            self.preview.setItem(row, 0, QTableWidgetItem(name))
            self.preview.setItem(row, 1, QTableWidgetItem(kind))
        center_layout.addWidget(self.preview, 1)
        body.addWidget(center, 1)

        footer = QWidget()
        footer_layout = QGridLayout(footer)
        footer_layout.setContentsMargins(10, 8, 10, 8)
        footer_layout.setHorizontalSpacing(8)
        footer_layout.setVerticalSpacing(8)

        footer_layout.addWidget(QLabel("File name:"), 0, 0)
        self.file_name = QLineEdit("Introduction_to_AI.pdf")
        footer_layout.addWidget(self.file_name, 0, 1)

        footer_layout.addWidget(QLabel("File type:"), 1, 0)
        self.file_types = QComboBox()
        self.file_types.addItems([
            "All books (*.pdf *.epub *.txt *.mobi)",
            "PDF (*.pdf)",
            "EPUB (*.epub)",
            "TXT (*.txt)",
        ])
        footer_layout.addWidget(self.file_types, 1, 1)

        actions = QHBoxLayout()
        self.open_btn = QPushButton("Open")
        self.open_btn.setObjectName("PrimaryButton")
        self.open_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("GhostButton")
        self.cancel_btn.clicked.connect(self.reject)
        actions.addWidget(self.open_btn)
        actions.addWidget(self.cancel_btn)
        action_wrap = QWidget()
        action_wrap.setLayout(actions)
        footer_layout.addWidget(action_wrap, 0, 2, 2, 1)

        root.addWidget(footer)

        self.preview.itemSelectionChanged.connect(self._sync_selected_name)
        self.preview.selectRow(0)

    def _sync_selected_name(self) -> None:
        current_row = self.preview.currentRow()
        if current_row >= 0:
            selected_item = self.preview.item(current_row, 0)
            if selected_item:
                self.file_name.setText(selected_item.text())

    def _pick_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Books (*.pdf *.epub *.txt *.mobi)")
        if file_path:
            self.path_input.setText(file_path)

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.path_input.setText(folder)
