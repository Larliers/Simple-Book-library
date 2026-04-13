from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr
from bookhub.ui.dialogs.add_tag_dialog import AddTagDialog
from bookhub.ui.models.resource import ResourceItem
from bookhub.ui.resources.assets import load_icon
from bookhub.ui.resources.layout_config import UI_LAYOUT
from bookhub.ui.viewmodels.library_viewmodel import LibraryViewModel
from bookhub.ui.widgets.book_card import BookCardWidget


class LibraryPage(QWidget):
    def __init__(
        self,
        view_model: LibraryViewModel,
        parent: QWidget | None = None,
        missing_mode: bool = False,
        repository=None,
    ) -> None:
        super().__init__(parent)
        self.view_model = view_model
        self.missing_mode = missing_mode
        self._repository = repository
        self.interaction_events: list[dict[str, str | None]] = []
        self._last_grid_columns = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.title = QLabel("Library")
        self.title.setObjectName("PageTitle")
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("PageSubtitle")
        title_col.addWidget(self.title)
        title_col.addWidget(self.subtitle)
        header_row.addLayout(title_col, 1)

        self.view_toggle_panel = QFrame()
        self.view_toggle_panel.setObjectName("ViewTogglePanel")
        self.view_toggle_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        panel_layout = QHBoxLayout(self.view_toggle_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(2)

        self.grid_btn = QPushButton()
        self.grid_btn.setObjectName("ViewToggleButton")
        self.grid_btn.setCheckable(True)
        self.grid_btn.setIcon(load_icon("view_grid.svg"))
        self.grid_btn.setIconSize(QSize(14, 14))
        self.grid_btn.clicked.connect(lambda: self.set_view_mode("waterfall"))

        self.list_btn = QPushButton()
        self.list_btn.setObjectName("ViewToggleButton")
        self.list_btn.setCheckable(True)
        self.list_btn.setIcon(load_icon("view_list.svg"))
        self.list_btn.setIconSize(QSize(14, 14))
        self.list_btn.clicked.connect(lambda: self.set_view_mode("list"))

        panel_layout.addWidget(self.grid_btn)
        panel_layout.addWidget(self.list_btn)
        header_row.addWidget(self.view_toggle_panel, 0, Qt.AlignTop)
        root.addLayout(header_row)

        self.view_stack = QStackedWidget()
        root.addWidget(self.view_stack, 1)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self.grid_layout.setVerticalSpacing(UI_LAYOUT.card_spacing)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setFrameShape(QFrame.NoFrame)
        self.grid_scroll.setWidget(self.grid_container)
        self.view_stack.addWidget(self.grid_scroll)

        self.list_table = QTableWidget(0, 5)
        self.list_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.list_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.list_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_table.customContextMenuRequested.connect(self._show_list_menu)
        self.list_table.horizontalHeader().setStretchLastSection(True)
        self.list_table.verticalHeader().setVisible(False)
        self.view_stack.addWidget(self.list_table)

        self.retranslate_ui()
        self.render()

    def retranslate_ui(self) -> None:
        if self.missing_mode:
            self.title.setText(tr("missed.title", "Missed"))
        else:
            self.title.setText(tr("library.title", "Library"))
        self.grid_btn.setToolTip(tr("library.grid", "Grid"))
        self.list_btn.setToolTip(tr("library.list", "List"))
        self.list_table.setHorizontalHeaderLabels(
            [
                tr("library.table.cover", "Cover"),
                tr("library.table.title", "Title"),
                tr("library.table.author", "Author"),
                tr("library.table.status", "Status"),
                tr("library.table.tags", "Tags"),
            ]
        )
        self.render()

    def set_query(self, query: str) -> None:
        self.view_model.set_query(query)
        self._track_event("filter", None)
        self.render()

    def set_view_mode(self, mode: str) -> None:
        self.view_model.set_view_mode(mode)
        self._track_event("paginate", None)
        self.render()

    def render(self) -> None:
        items = self.view_model.filtered_resources(include_missing=self.missing_mode)
        if self.missing_mode:
            self.subtitle.setText(
                tr("missed.subtitle.count", "{count} missing books waiting restore").format(count=len(items))
            )
        else:
            self.subtitle.setText(
                tr("library.subtitle.count", "{count} books in your local collection").format(count=len(items))
            )
        self._render_grid(items)
        self._render_list(items)

        is_list = self.view_model.view_mode == "list"
        self.view_stack.setCurrentIndex(1 if is_list else 0)
        self.grid_btn.setChecked(not is_list)
        self.list_btn.setChecked(is_list)

    def _render_grid(self, items: list[ResourceItem]) -> None:
        columns = self._calculate_grid_columns()
        self._last_grid_columns = columns

        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child and child.widget():
                child.widget().deleteLater()

        for idx, item in enumerate(items):
            row = idx // columns
            col = idx % columns
            card = BookCardWidget(item)
            card.setContextMenuPolicy(Qt.CustomContextMenu)
            card.customContextMenuRequested.connect(
                lambda pos, resource=item, widget=card: self._show_card_menu(resource, widget.mapToGlobal(pos))
            )
            self.grid_layout.addWidget(card, row, col, alignment=Qt.AlignLeft | Qt.AlignTop)

        if not self.missing_mode:
            add_card = QLabel(tr("library.add_new_book", "+\nADD NEW BOOK"))
            add_card.setObjectName("AddCard")
            add_card.setAlignment(Qt.AlignCenter)
            add_card.setFixedSize(UI_LAYOUT.card_width, UI_LAYOUT.add_card_height)
            self.grid_layout.addWidget(
                add_card,
                len(items) // columns,
                len(items) % columns,
                alignment=Qt.AlignLeft | Qt.AlignTop,
            )

    def _render_list(self, items: list[ResourceItem]) -> None:
        self.list_table.setRowCount(len(items))
        for row, item in enumerate(items):
            cover_item = QTableWidgetItem("  ")
            cover_item.setData(Qt.UserRole, item.resource_id)
            cover_item.setIcon(self._build_thumbnail_icon(item))
            self.list_table.setItem(row, 0, cover_item)
            self.list_table.setItem(row, 1, QTableWidgetItem(item.title))
            self.list_table.setItem(row, 2, QTableWidgetItem(item.author))
            self.list_table.setItem(row, 3, QTableWidgetItem(item.status))
            self.list_table.setItem(row, 4, QTableWidgetItem(", ".join(item.tags)))

        self.list_table.resizeColumnsToContents()
        self.list_table.setColumnWidth(1, 260)

    def _build_thumbnail_icon(self, item: ResourceItem) -> QIcon:
        if item.thumbnail_path:
            file_path = Path(item.thumbnail_path)
            if file_path.exists():
                pixmap = QPixmap(str(file_path))
                if not pixmap.isNull():
                    return QIcon(
                        pixmap.scaled(26, 38, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    )
        fallback = QPixmap(26, 38)
        fallback.fill(Qt.lightGray)
        return QIcon(fallback)

    def _show_card_menu(self, resource: ResourceItem, global_pos) -> None:
        menu = QMenu(self)
        open_action = menu.addAction(tr("library.menu.open_external", "Open External"))
        open_folder_action = menu.addAction(tr("library.menu.open_folder", "Open Folder"))
        menu.addSeparator()
        add_tag_action = menu.addAction(tr("library.menu.add_tag", "Add Tag"))
        remove_action = menu.addAction(tr("library.menu.remove_library", "Remove from Library"))

        # Favorites and Collections (only when repository is available)
        fav_action = None
        col_action = None
        if self._repository is not None:
            menu.addSeparator()
            book_id = self._repository.get_book_int_id(resource.resource_id)
            if book_id is not None:
                try:
                    is_fav = self._repository.is_favorite(book_id)
                except Exception:
                    is_fav = False
                if is_fav:
                    fav_action = menu.addAction("★  Remove from Favorites")
                else:
                    fav_action = menu.addAction("☆  Add to Favorites")
                col_action = menu.addAction("📚  Add to Collection…")

        chosen = menu.exec(global_pos)

        if chosen == open_action:
            self._track_event("open_external", resource.resource_id)
        elif chosen == open_folder_action:
            self._track_event("open_external", resource.resource_id)
        elif chosen == add_tag_action:
            dialog = AddTagDialog(self)
            if dialog.exec():
                self._track_event("sort", resource.resource_id)
        elif chosen == remove_action:
            self._track_event("paginate", resource.resource_id)
        elif fav_action is not None and chosen == fav_action:
            self._toggle_favorite(resource)
        elif col_action is not None and chosen == col_action:
            self._add_to_collection(resource)

    def _toggle_favorite(self, resource: ResourceItem) -> None:
        if self._repository is None:
            return
        book_id = self._repository.get_book_int_id(resource.resource_id)
        if book_id is None:
            return
        try:
            if self._repository.is_favorite(book_id):
                self._repository.remove_from_favorites(book_id)
                from PySide6.QtWidgets import QToolTip
                from PySide6.QtCore import QPoint
                QToolTip.showText(
                    self.mapToGlobal(QPoint(0, 0)),
                    "Removed from Favorites",
                    self, self.rect(), 1800,
                )
            else:
                self._repository.add_to_favorites(book_id)
                from PySide6.QtWidgets import QToolTip
                from PySide6.QtCore import QPoint
                QToolTip.showText(
                    self.mapToGlobal(QPoint(0, 0)),
                    "Added to Favorites  ★",
                    self, self.rect(), 1800,
                )
        except Exception as e:
            print(f"[LibraryPage] favorite error: {e}")

    def _add_to_collection(self, resource: ResourceItem) -> None:
        if self._repository is None:
            return
        book_id = self._repository.get_book_int_id(resource.resource_id)
        if book_id is None:
            return
        try:
            from bookhub.ui.dialogs.add_to_collection_dialog import AddToCollectionDialog
        except ImportError:
            return
        dlg = AddToCollectionDialog(book_id, resource.title, self._repository, self)
        dlg.exec()

    def _show_list_menu(self, pos) -> None:
        row = self.list_table.rowAt(pos.y())
        if row < 0:
            return
        resource_id = self.list_table.item(row, 0).data(Qt.UserRole)
        menu = QMenu(self)
        open_action = menu.addAction(tr("library.menu.open_external", "Open External"))
        add_tag_action = menu.addAction(tr("library.menu.add_tag", "Add Tag"))
        mark_action = menu.addAction(tr("library.menu.mark_reading", "Mark as Reading"))
        chosen = menu.exec(self.list_table.viewport().mapToGlobal(pos))

        if chosen == open_action:
            self._track_event("open_external", resource_id)
        elif chosen == add_tag_action:
            dialog = AddTagDialog(self)
            if dialog.exec():
                self._track_event("sort", resource_id)
        elif chosen == mark_action:
            self._track_event("sort", resource_id)

    def _track_event(self, event_type: str, resource_id: str | None) -> None:
        self.interaction_events.append(
            {
                "event": event_type,
                "resource_id": resource_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def _calculate_grid_columns(self) -> int:
        available_width = max(1, self.grid_scroll.viewport().width())
        cell_width = UI_LAYOUT.card_width + UI_LAYOUT.card_spacing
        return max(1, available_width // max(1, cell_width))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.view_model.view_mode != "waterfall":
            return
        columns = self._calculate_grid_columns()
        if columns != self._last_grid_columns:
            self._render_grid(self.view_model.filtered_resources(include_missing=self.missing_mode))
