from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr
from bookhub.ui.models.resource import ResourceItem
from bookhub.ui.pages.library_page import BookDetailPanel
from bookhub.ui.widgets.book_card import format_author_publisher_meta


class TextNovelPage(QWidget):
    def __init__(self, repository=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repository = repository
        self._resources: list[ResourceItem] = []
        self._resource_by_id: dict[str, ResourceItem] = {}
        self._selected_resource_id: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        self._title = QLabel()
        self._title.setObjectName("PageTitle")
        self._subtitle = QLabel()
        self._subtitle.setObjectName("PageSubtitle")
        title_col.addWidget(self._title)
        title_col.addWidget(self._subtitle)
        header_row.addLayout(title_col, 1)
        root.addLayout(header_row)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setObjectName("LibraryContentSplitter")
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(6)

        self.main_pane = QWidget()
        pane_layout = QVBoxLayout(self.main_pane)
        pane_layout.setContentsMargins(0, 0, 0, 0)
        pane_layout.setSpacing(0)

        self.list_table = QTableWidget(0, 4)
        self.list_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.list_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.list_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_table.customContextMenuRequested.connect(self._show_list_menu)
        self.list_table.horizontalHeader().setStretchLastSection(True)
        self.list_table.verticalHeader().setVisible(False)
        self.list_table.cellClicked.connect(self._on_list_row_clicked)
        self.list_table.cellDoubleClicked.connect(self._on_list_row_double_clicked)
        pane_layout.addWidget(self.list_table, 1)

        self._empty_label = QLabel()
        self._empty_label.setObjectName("PageSubtitle")
        self._empty_label.setAlignment(Qt.AlignCenter)
        pane_layout.addWidget(self._empty_label, 1)
        self._empty_label.hide()

        self.detail_panel = BookDetailPanel(repository=self._repository)
        self.detail_panel.setMinimumWidth(240)

        self.main_splitter.addWidget(self.main_pane)
        self.main_splitter.addWidget(self.detail_panel)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        self.main_splitter.setSizes([1020, 320])

        root.addWidget(self.main_splitter, 1)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self._title.setText(tr("text.page.title", "Text Novel"))
        self._empty_label.setText(tr("text.page.empty", "No text novels found yet."))
        self.list_table.setHorizontalHeaderLabels(
            [
                tr("text.table.title", "Title"),
                tr("text.table.author", "Author"),
                tr("text.table.tags", "Tags"),
                tr("text.table.path", "Path"),
            ]
        )
        self.render()

    def set_resources(self, resources: list[ResourceItem]) -> None:
        self._resources = list(resources)
        self._resource_by_id = {item.resource_id: item for item in self._resources}
        if self._selected_resource_id and self._selected_resource_id not in self._resource_by_id:
            self._selected_resource_id = None
        self.render()

    def refresh(self) -> None:
        self.render()

    def render(self) -> None:
        self._subtitle.setText(
            tr("text.page.subtitle.count", "{count} text novels detected").format(count=len(self._resources))
        )
        if not self._resources:
            self.list_table.hide()
            self._empty_label.show()
            self.detail_panel.clear_selection()
            return

        self._empty_label.hide()
        self.list_table.show()
        self._render_list()
        if self._selected_resource_id:
            self._update_detail_panel(self._selected_resource_id)
        else:
            self.detail_panel.clear_selection()

    def _render_list(self) -> None:
        self.list_table.setRowCount(len(self._resources))
        for row, item in enumerate(self._resources):
            title_item = QTableWidgetItem(item.title)
            title_item.setData(Qt.UserRole, item.resource_id)
            self.list_table.setItem(row, 0, title_item)
            self.list_table.setItem(
                row,
                1,
                QTableWidgetItem(format_author_publisher_meta(item.author, item.publisher)),
            )
            self.list_table.setItem(row, 2, QTableWidgetItem(", ".join(item.tags)))
            self.list_table.setItem(row, 3, QTableWidgetItem(item.path))

        self.list_table.resizeColumnsToContents()
        self.list_table.setColumnWidth(0, 280)
        self._sync_list_selection()

    def _on_list_row_clicked(self, row: int, _column: int) -> None:
        item = self.list_table.item(row, 0)
        if item is None:
            return
        resource_id = str(item.data(Qt.UserRole) or "")
        self._select_resource(resource_id)

    def _on_list_row_double_clicked(self, row: int, _column: int) -> None:
        item = self.list_table.item(row, 0)
        if item is None:
            return
        resource_id = str(item.data(Qt.UserRole) or "")
        resource = self._resource_by_id.get(resource_id)
        if resource is not None:
            self._open_external(resource.path)

    def _show_list_menu(self, pos) -> None:
        row = self.list_table.rowAt(pos.y())
        if row < 0:
            return
        item = self.list_table.item(row, 0)
        if item is None:
            return
        resource_id = str(item.data(Qt.UserRole) or "")
        resource = self._resource_by_id.get(resource_id)
        if resource is None:
            return

        menu = QMenu(self)
        open_action = menu.addAction(tr("text.menu.open_external", "Open External"))
        chosen = menu.exec(self.list_table.viewport().mapToGlobal(pos))
        if chosen == open_action:
            self._open_external(resource.path)

    def _open_external(self, path: str) -> None:
        file_path = Path(path).expanduser()
        if not str(file_path).strip() or not file_path.exists():
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(file_path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(file_path)])
            else:
                subprocess.Popen(["xdg-open", str(file_path)])
        except Exception:
            return

    def _select_resource(self, resource_id: str) -> None:
        if resource_id not in self._resource_by_id:
            return
        self._selected_resource_id = resource_id
        self._sync_list_selection()
        self._update_detail_panel(resource_id)

    def _sync_list_selection(self) -> None:
        if not self._selected_resource_id:
            self.list_table.clearSelection()
            return
        for row in range(self.list_table.rowCount()):
            item = self.list_table.item(row, 0)
            if item is None:
                continue
            if str(item.data(Qt.UserRole) or "") == self._selected_resource_id:
                self.list_table.selectRow(row)
                return

    def _update_detail_panel(self, resource_id: str) -> None:
        resource = self._resource_by_id.get(resource_id)
        if resource is None:
            self.detail_panel.clear_selection()
            return
        self.detail_panel.set_resource(resource)
