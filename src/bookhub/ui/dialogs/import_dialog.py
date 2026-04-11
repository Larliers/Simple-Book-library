from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ImportDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ImportBooks")
        self.resize(820, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        preview = QListWidget()
        for item in [
            "Introduction_to_AI.pdf",
            "Design_Patterns.epub",
            "Advanced_Calculus.pdf",
            "Cloud_Native_Apps.mobi",
        ]:
            preview.addItem(item)
        root.addWidget(QLabel("Preview Files"))
        root.addWidget(preview, 1)

        self.path_input = QLineEdit()
        browse_file = QPushButton("Select File")
        browse_file.clicked.connect(self._pick_file)
        browse_dir = QPushButton("Select Folder")
        browse_dir.clicked.connect(self._pick_folder)

        path_bar = QHBoxLayout()
        path_bar.addWidget(self.path_input, 1)
        path_bar.addWidget(browse_file)
        path_bar.addWidget(browse_dir)
        root.addLayout(path_bar)

        form = QFormLayout()
        file_types = QComboBox()
        file_types.addItems(["*.pdf *.epub *.txt *.doc *.mobi", "*.pdf", "*.epub", "*.txt"])
        form.addRow("File Types", file_types)
        root.addLayout(form)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        open_btn = QPushButton("Import")
        open_btn.setObjectName("PrimaryButton")
        open_btn.clicked.connect(self.accept)
        actions.addWidget(cancel_btn)
        actions.addWidget(open_btn)
        root.addLayout(actions)

    def _pick_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Books (*.pdf *.epub *.txt *.doc *.mobi)")
        if file_path:
            self.path_input.setText(file_path)

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.path_input.setText(folder)

