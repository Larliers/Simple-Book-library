from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt, Signal
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
from bookhub.ui.resources.assets import load_pixmap


@dataclass(slots=True)
class SearchSuggestion:
    group: str
    label: str
    description: str
    query_value: str


class _SuggestionRow(QWidget):
    def __init__(self, on_selected: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_selected = on_selected
        self._query_value = ""
        self._font_size = 15

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._label = QLabel()
        self._label.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self._label)

        self._button = QPushButton()
        self._button.setObjectName("GhostButton")
        self._apply_button_style()
        self._button.setFocusPolicy(Qt.NoFocus)
        self._button.clicked.connect(self._emit_selected)
        layout.addWidget(self._button)

        self._label.hide()
        self._button.hide()
        self.hide()

    def _apply_button_style(self) -> None:
        self._button.setStyleSheet(
            f"text-align: left; border: none; padding: 6px 10px; font-size: {self._font_size}px;"
        )

    def set_font_size(self, size: int) -> None:
        self._font_size = max(12, int(size))
        self._apply_button_style()

    def _emit_selected(self) -> None:
        if self._query_value:
            self._on_selected(self._query_value)

    def show_header(self, text: str) -> None:
        self._query_value = ""
        self._button.hide()
        self._label.setText(text)
        self._label.setStyleSheet(
            f"padding: 8px 10px 4px 10px; color: #6a7382; font-size: {self._font_size}px; font-weight: 700;"
        )
        self._label.show()
        self.show()

    def show_empty(self, text: str) -> None:
        self._query_value = ""
        self._button.hide()
        self._label.setText(text)
        self._label.setStyleSheet(
            f"padding: 8px 10px 8px 10px; color: #6a7382; font-size: {self._font_size}px;"
        )
        self._label.show()
        self.show()

    def show_item(self, suggestion: SearchSuggestion) -> None:
        self._query_value = suggestion.query_value
        self._label.hide()
        self._button.setText(suggestion.label)
        self._button.setToolTip(suggestion.description)
        self._button.show()
        self.show()


class TopBarWidget(QWidget):
    query_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TopBar")
        self._suggestions: list[SearchSuggestion] = []
        self._is_dropdown_open = False
        self._row_pool: list[_SuggestionRow] = []
        self._search_font_size = 15
        self._search_placeholder_key = "topbar.search_placeholder"
        self._search_placeholder_fallback = "Search library..."

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        row = QWidget()
        self._row = row
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(16, 10, 16, 10)
        row_layout.setSpacing(10)

        self.search_panel = QFrame()
        self.search_panel.setObjectName("TopSearchPanel")
        self.search_panel.setMinimumHeight(36)
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
        self.search_input.setMinimumHeight(28)
        self.search_input.textChanged.connect(self._on_query_changed)
        self.search_input.returnPressed.connect(self._close_dropdown)
        search_panel_layout.addWidget(self.search_input, 1)
        row_layout.addWidget(self.search_panel, 1)

        root.addWidget(row)

        self.dropdown = QFrame()
        self.dropdown.setObjectName("PageSection")
        self.dropdown.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.dropdown.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.dropdown.setFocusPolicy(Qt.NoFocus)
        dropdown_layout = QVBoxLayout(self.dropdown)
        dropdown_layout.setContentsMargins(0, 0, 0, 0)
        dropdown_layout.setSpacing(0)
        self.dropdown_content = QWidget()
        self.dropdown_content_layout = QVBoxLayout(self.dropdown_content)
        self.dropdown_content_layout.setContentsMargins(0, 0, 0, 0)
        self.dropdown_content_layout.setSpacing(0)
        dropdown_layout.addWidget(self.dropdown_content)
        self.dropdown.hide()

        self.retranslate_ui()
        self.set_search_suggestions([])
        self.set_search_font_size(self._search_font_size)

    def retranslate_ui(self) -> None:
        self.search_input.setPlaceholderText(
            tr(self._search_placeholder_key, self._search_placeholder_fallback)
        )

    def set_search_placeholder(self, key: str, fallback: str) -> None:
        self._search_placeholder_key = key
        self._search_placeholder_fallback = fallback
        self.retranslate_ui()

    def set_search_font_size(self, size: int) -> None:
        self._search_font_size = max(12, min(20, int(size)))
        self.search_input.setStyleSheet(f"font-size: {self._search_font_size}px;")
        for row in self._row_pool:
            row.set_font_size(self._search_font_size)
        if self._suggestions:
            self._render_dropdown_items()

    def set_search_suggestions(self, suggestions: list[SearchSuggestion]) -> None:
        if suggestions == self._suggestions and self._row_pool:
            self.ensure_dropdown_on_top()
            return
        self._suggestions = suggestions
        self._render_dropdown_items()
        self.ensure_dropdown_on_top()

    def ensure_dropdown_on_top(self) -> None:
        if not self._is_dropdown_open:
            return
        self._place_dropdown()
        self.dropdown.raise_()

    def _on_query_changed(self, query: str) -> None:
        self.query_changed.emit(query)
        if query.strip():
            self._open_dropdown()
        else:
            self._close_dropdown()

    def _ensure_row_capacity(self, count: int) -> None:
        while len(self._row_pool) < count:
            row = _SuggestionRow(self._select_suggestion, self.dropdown_content)
            row.set_font_size(self._search_font_size)
            self.dropdown_content_layout.addWidget(row)
            self._row_pool.append(row)

    def _render_dropdown_items(self) -> None:
        row_models: list[tuple[str, str | SearchSuggestion]] = []
        if not self._suggestions:
            row_models.append(("empty", tr("topbar.search.empty", "No suggestions")))
        else:
            current_group = ""
            for suggestion in self._suggestions:
                if suggestion.group != current_group:
                    current_group = suggestion.group
                    row_models.append(("header", current_group))
                row_models.append(("item", suggestion))

        self.dropdown_content.setUpdatesEnabled(False)
        self._ensure_row_capacity(len(row_models))
        for idx, (kind, payload) in enumerate(row_models):
            row = self._row_pool[idx]
            if kind == "header":
                row.show_header(str(payload))
            elif kind == "item":
                row.show_item(payload)  # type: ignore[arg-type]
            else:
                row.show_empty(str(payload))

        for row in self._row_pool[len(row_models):]:
            row.hide()

        self.dropdown_content.setUpdatesEnabled(True)
        self.dropdown.adjustSize()

    def _select_suggestion(self, value: str) -> None:
        self.search_input.setText(value)
        self._close_dropdown()

    def reposition_dropdown(self) -> None:
        if not self._is_dropdown_open:
            return
        self._place_dropdown()

    def _place_dropdown(self) -> None:
        width = max(200, self._row.width())
        height = min(max(40, self.dropdown.sizeHint().height()), 360)
        global_pos = self._row.mapToGlobal(self._row.rect().bottomLeft())
        self.dropdown.setGeometry(global_pos.x(), global_pos.y(), width, height)

    def _open_dropdown(self) -> None:
        self._place_dropdown()
        if not self._is_dropdown_open:
            self.dropdown.show()
            self.dropdown.raise_()
            self._is_dropdown_open = True
        self.search_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _close_dropdown(self) -> None:
        if self._is_dropdown_open:
            self.dropdown.hide()
            self._is_dropdown_open = False

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.reposition_dropdown()
