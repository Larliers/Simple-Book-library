from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr
from bookhub.ui.resources.assets import load_icon, load_pixmap


@dataclass(slots=True)
class SearchSuggestion:
    group: str
    label: str
    description: str
    query_value: str


class TopBarWidget(QWidget):
    query_changed = Signal(str)
    import_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TopBar")
        self._suggestions: list[SearchSuggestion] = []
        self._is_dropdown_open = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(16, 10, 16, 10)
        row_layout.setSpacing(10)

        self.search_panel = QFrame()
        self.search_panel.setObjectName("TopSearchPanel")
        search_panel_layout = QHBoxLayout(self.search_panel)
        search_panel_layout.setContentsMargins(8, 0, 8, 0)
        search_panel_layout.setSpacing(6)

        self.search_icon = QLabel()
        self.search_icon.setObjectName("TopSearchIcon")
        self.search_icon.setPixmap(load_pixmap("search.svg", 14, 14))
        search_panel_layout.addWidget(self.search_icon)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("TopSearchInput")
        self.search_input.setFrame(False)
        self.search_input.textChanged.connect(self._on_query_changed)
        self.search_input.returnPressed.connect(self._close_dropdown)
        search_panel_layout.addWidget(self.search_input, 1)
        row_layout.addWidget(self.search_panel, 1)

        self.import_button = QPushButton("IMPORT")
        self.import_button.clicked.connect(self.import_requested.emit)
        row_layout.addWidget(self.import_button)

        self.new_list_button = QPushButton("NEW LIST")
        self.new_list_button.setObjectName("PrimaryButton")
        row_layout.addWidget(self.new_list_button)

        self.refresh_button = QPushButton()
        self.refresh_button.setObjectName("FlatIconButton")
        self.refresh_button.setIcon(load_icon("refresh.svg"))
        self.refresh_button.setIconSize(QSize(14, 14))
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        row_layout.addWidget(self.refresh_button)

        self.menu_button = QPushButton()
        self.menu_button.setObjectName("FlatIconButton")
        self.menu_button.setIcon(load_icon("menu_vertical.svg"))
        self.menu_button.setIconSize(QSize(14, 14))
        self.menu_button.setCursor(Qt.PointingHandCursor)
        row_layout.addWidget(self.menu_button)

        root.addWidget(row)

        self.dropdown = QFrame()
        self.dropdown.setObjectName("PageSection")
        dropdown_layout = QVBoxLayout(self.dropdown)
        dropdown_layout.setContentsMargins(0, 0, 0, 0)
        dropdown_layout.setSpacing(0)
        self.dropdown_content = QWidget()
        self.dropdown_content_layout = QVBoxLayout(self.dropdown_content)
        self.dropdown_content_layout.setContentsMargins(0, 0, 0, 0)
        self.dropdown_content_layout.setSpacing(0)
        dropdown_layout.addWidget(self.dropdown_content)
        self.dropdown.hide()
        root.addWidget(self.dropdown)

        self.retranslate_ui()
        self.set_search_suggestions([])

    def retranslate_ui(self) -> None:
        self.search_input.setPlaceholderText(tr("topbar.search_placeholder", "Search library..."))
        self.import_button.setText(tr("topbar.import", "IMPORT"))
        self.new_list_button.setText(tr("topbar.new_list", "NEW LIST"))

    def set_search_suggestions(self, suggestions: list[SearchSuggestion]) -> None:
        self._suggestions = suggestions
        self._render_dropdown_items()

    def _on_query_changed(self, query: str) -> None:
        self.query_changed.emit(query)
        if query.strip():
            self._open_dropdown()
        else:
            self._close_dropdown()

    def _clear_layout_widgets(self) -> None:
        while self.dropdown_content_layout.count():
            item = self.dropdown_content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_dropdown_items(self) -> None:
        self._clear_layout_widgets()
        if not self._suggestions:
            empty = QLabel(tr("topbar.search.empty", "No suggestions"))
            empty.setContentsMargins(10, 8, 10, 8)
            empty.setObjectName("PageSubtitle")
            self.dropdown_content_layout.addWidget(empty)
            return

        current_group = ""
        for suggestion in self._suggestions:
            if suggestion.group != current_group:
                current_group = suggestion.group
                header = QLabel(current_group)
                header.setStyleSheet("padding: 8px 10px 4px 10px; color: #6a7382; font-size: 10px; font-weight: 700;")
                self.dropdown_content_layout.addWidget(header)

            item_button = QPushButton(suggestion.label)
            item_button.setObjectName("GhostButton")
            item_button.setStyleSheet("text-align: left; border: none; padding: 6px 10px;")
            item_button.setToolTip(suggestion.description)
            item_button.clicked.connect(
                lambda _=False, value=suggestion.query_value: self._select_suggestion(value)
            )
            self.dropdown_content_layout.addWidget(item_button)

    def _select_suggestion(self, value: str) -> None:
        self.search_input.setText(value)
        self._close_dropdown()

    def _open_dropdown(self) -> None:
        if not self._is_dropdown_open:
            self.dropdown.show()
            self._is_dropdown_open = True

    def _close_dropdown(self) -> None:
        if self._is_dropdown_open:
            self.dropdown.hide()
            self._is_dropdown_open = False
