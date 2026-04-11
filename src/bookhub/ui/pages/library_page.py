from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr
from bookhub.ui.models.resource import ResourceItem
from bookhub.ui.resources.layout_config import GRID_DENSITY
from bookhub.ui.viewmodels.library_viewmodel import LibraryViewModel
from bookhub.ui.widgets.book_card import BookCardWidget


class LibraryPage(QWidget):
    def __init__(self, view_model: LibraryViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.view_model = view_model
        self.interaction_events: list[dict[str, str | None]] = []
        self._card_widgets: list[BookCardWidget] = []
        self._last_grid_columns = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 20)
        root.setSpacing(12)

        self.title = QLabel("Library")
        self.title.setObjectName("PageTitle")
        self.subtitle = QLabel("UI outline based on New UI references")
        self.subtitle.setObjectName("PageSubtitle")

        root.addWidget(self.title)
        root.addWidget(self.subtitle)

        toolbar = QHBoxLayout()
        self.density_panel = QFrame()
        self.density_panel.setObjectName("DensityPanel")
        density_layout = QHBoxLayout(self.density_panel)
        density_layout.setContentsMargins(10, 8, 10, 8)
        density_layout.setSpacing(10)

        self.card_width_label = QLabel("Card Width")
        self.card_width_spin = QSpinBox()
        self.card_width_spin.setRange(120, 360)
        self.card_width_spin.setValue(GRID_DENSITY.card_width)
        self.card_width_spin.valueChanged.connect(self._on_density_changed)

        self.spacing_label = QLabel("Min Spacing")
        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(4, 48)
        self.spacing_spin.setValue(GRID_DENSITY.min_grid_spacing)
        self.spacing_spin.valueChanged.connect(self._on_density_changed)

        density_layout.addWidget(self.card_width_label)
        density_layout.addWidget(self.card_width_spin)
        density_layout.addWidget(self.spacing_label)
        density_layout.addWidget(self.spacing_spin)
        density_layout.addStretch(1)
        toolbar.addWidget(self.density_panel, 1)

        self.grid_btn = QPushButton("Grid")
        self.grid_btn.clicked.connect(lambda: self.set_view_mode("waterfall"))
        self.list_btn = QPushButton("List")
        self.list_btn.clicked.connect(lambda: self.set_view_mode("list"))
        toolbar.addWidget(self.grid_btn)
        toolbar.addWidget(self.list_btn)
        root.addLayout(toolbar)

        self.view_stack = QStackedWidget()
        root.addWidget(self.view_stack, 1)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setHorizontalSpacing(GRID_DENSITY.min_grid_spacing)
        self.grid_layout.setVerticalSpacing(GRID_DENSITY.min_grid_spacing)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setWidget(self.grid_container)
        self.view_stack.addWidget(self.grid_scroll)

        self.list_table = QTableWidget(0, 5)
        self.list_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.list_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.list_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_table.customContextMenuRequested.connect(self._show_list_menu)
        self.list_table.horizontalHeader().setStretchLastSection(True)
        self.view_stack.addWidget(self.list_table)

        self.retranslate_ui()
        self.render()

    def retranslate_ui(self) -> None:
        self.title.setText(tr("library.title", "Library"))
        self.subtitle.setText(tr("library.subtitle", "UI outline based on New UI references"))
        self.card_width_label.setText(tr("library.density.card_width", "Card Width"))
        self.spacing_label.setText(tr("library.density.min_spacing", "Min Spacing"))
        self.grid_btn.setText(tr("library.grid", "Grid"))
        self.list_btn.setText(tr("library.list", "List"))
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
        items = self.view_model.filtered_resources()
        self._render_grid(items)
        self._render_list(items)

        is_list = self.view_model.view_mode == "list"
        self.view_stack.setCurrentIndex(1 if is_list else 0)
        self.grid_btn.setChecked(not is_list)
        self.list_btn.setChecked(is_list)
        self.grid_btn.setObjectName("PrimaryButton" if not is_list else "")
        self.list_btn.setObjectName("PrimaryButton" if is_list else "")
        self.style().polish(self.grid_btn)
        self.style().polish(self.list_btn)

    def _render_grid(self, items: list[ResourceItem]) -> None:
        columns = self._calculate_grid_columns()
        self._last_grid_columns = columns

        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child and child.widget():
                child.widget().deleteLater()
        self._card_widgets.clear()

        for idx, item in enumerate(items):
            row = idx // columns
            col = idx % columns
            card = BookCardWidget(item)
            card.setContextMenuPolicy(Qt.CustomContextMenu)
            card.customContextMenuRequested.connect(
                lambda pos, resource=item, widget=card: self._show_card_menu(resource, widget.mapToGlobal(pos))
            )
            self.grid_layout.addWidget(card, row, col, alignment=Qt.AlignLeft | Qt.AlignTop)
            self._card_widgets.append(card)

        add_card = QLabel(tr("library.add_new_book", "+\nADD NEW BOOK"))
        add_card.setObjectName("AddCard")
        add_card.setAlignment(Qt.AlignCenter)
        add_card.setFixedSize(GRID_DENSITY.card_width, GRID_DENSITY.add_card_height)
        self.grid_layout.addWidget(
            add_card,
            (len(items)) // columns,
            (len(items)) % columns,
            alignment=Qt.AlignLeft | Qt.AlignTop,
        )

    def _render_list(self, items: list[ResourceItem]) -> None:
        self.list_table.setRowCount(len(items))
        for row, item in enumerate(items):
            self.list_table.setItem(row, 0, QTableWidgetItem("COVER"))
            self.list_table.setItem(row, 1, QTableWidgetItem(item.title))
            self.list_table.setItem(row, 2, QTableWidgetItem(item.author))
            self.list_table.setItem(row, 3, QTableWidgetItem(item.status))
            self.list_table.setItem(row, 4, QTableWidgetItem(", ".join(item.tags)))
            self.list_table.item(row, 0).setData(Qt.UserRole, item.resource_id)

        self.list_table.resizeColumnsToContents()
        self.list_table.setColumnWidth(1, 240)

    def _show_card_menu(self, resource: ResourceItem, global_pos) -> None:
        menu = QMenu(self)
        open_action = menu.addAction(tr("library.menu.open_external", "Open External"))
        open_folder_action = menu.addAction(tr("library.menu.open_folder", "Open Folder"))
        menu.addSeparator()
        add_tag_action = menu.addAction(tr("library.menu.add_tag", "Add Tag"))
        remove_action = menu.addAction(tr("library.menu.remove_library", "Remove from Library"))
        chosen = menu.exec(global_pos)
        if chosen == open_action:
            self._track_event("open_external", resource.resource_id)
        elif chosen == open_folder_action:
            self._track_event("open_external", resource.resource_id)
        elif chosen == add_tag_action:
            self._track_event("sort", resource.resource_id)
        elif chosen == remove_action:
            self._track_event("paginate", resource.resource_id)

    def _show_list_menu(self, pos) -> None:
        row = self.list_table.rowAt(pos.y())
        if row < 0:
            return
        resource_id = self.list_table.item(row, 0).data(Qt.UserRole)
        menu = QMenu(self)
        open_action = menu.addAction(tr("library.menu.open_external", "Open External"))
        mark_action = menu.addAction(tr("library.menu.mark_reading", "Mark as Reading"))
        chosen = menu.exec(self.list_table.viewport().mapToGlobal(pos))
        if chosen == open_action:
            self._track_event("open_external", resource_id)
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
        cell_width = GRID_DENSITY.card_width + GRID_DENSITY.min_grid_spacing
        return max(1, available_width // max(1, cell_width))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.view_model.view_mode != "waterfall":
            return
        columns = self._calculate_grid_columns()
        if columns != self._last_grid_columns:
            self._render_grid(self.view_model.filtered_resources())

    def _on_density_changed(self) -> None:
        GRID_DENSITY.apply(
            card_width=self.card_width_spin.value(),
            min_grid_spacing=self.spacing_spin.value(),
        )
        self.grid_layout.setHorizontalSpacing(GRID_DENSITY.min_grid_spacing)
        self.grid_layout.setVerticalSpacing(GRID_DENSITY.min_grid_spacing)
        self.render()
