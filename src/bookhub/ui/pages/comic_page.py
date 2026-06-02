from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr
from bookhub.ui.models.resource import ResourceItem
from bookhub.ui.pages.library_page import BookDetailPanel
from bookhub.ui.resources.layout_config import UI_LAYOUT
from bookhub.ui.widgets.book_card import BookCardWidget

COMIC_SORT_SETTING_KEY_MAIN = "comic_sort_order_main"
COMIC_SORT_SETTING_KEY_FAV = "comic_sort_order_fav"
COMIC_SORT_MTIME_ASC = "folder_mtime_asc"
COMIC_SORT_MTIME_DESC = "folder_mtime_desc"
COMIC_SORT_NAME_ASC = "folder_name_asc"
COMIC_SORT_NAME_DESC = "folder_name_desc"
COMIC_VIEW_MODE_WATERFALL = "waterfall"
COMIC_VIEW_MODE_PAGINATION = "pagination"
DEFAULT_COMIC_PAGE_SIZE = 48


def _normalize_sort_order(value: object) -> str:
    normalized = str(value or "").strip().lower()
    allowed = {COMIC_SORT_MTIME_ASC, COMIC_SORT_MTIME_DESC, COMIC_SORT_NAME_ASC, COMIC_SORT_NAME_DESC}
    return normalized if normalized in allowed else COMIC_SORT_MTIME_DESC


def _normalize_view_mode(value: object) -> str:
    normalized = str(value or "").strip().lower()
    return COMIC_VIEW_MODE_PAGINATION if normalized == COMIC_VIEW_MODE_PAGINATION else COMIC_VIEW_MODE_WATERFALL


def _normalize_page_size(value: object) -> int:
    try:
        size = int(value)
    except (TypeError, ValueError):
        size = DEFAULT_COMIC_PAGE_SIZE
    return size if size in {24, 48, 72, 96} else DEFAULT_COMIC_PAGE_SIZE


class ComicPage(QWidget):
    favorites_changed = Signal()

    def __init__(
        self,
        repository,
        favorite_only: bool = False,
        parent: QWidget | None = None,
        sort_setting_key: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repository
        self._favorite_only = favorite_only
        self._sort_setting_key = sort_setting_key or (
            COMIC_SORT_SETTING_KEY_FAV if self._favorite_only else COMIC_SORT_SETTING_KEY_MAIN
        )
        self._sort_order = self._load_sort_order()
        self._view_mode = self._load_view_mode()
        self._page_size = self._load_page_size()
        self._current_page = 1
        self._resources: list[ResourceItem] = []
        self._resource_by_id: dict[str, ResourceItem] = {}
        self._comic_id_by_resource_id: dict[str, int] = {}
        self._selected_resource_id: str | None = None
        self._card_by_resource_id: dict[str, BookCardWidget] = {}
        self._card_signature_by_resource_id: dict[str, tuple[str, str, str, str, int]] = {}
        self._data_cache_valid = False
        self._last_columns = 0
        self._reflow_timer = QTimer(self)
        self._reflow_timer.setSingleShot(True)
        self._reflow_timer.setInterval(120)
        self._reflow_timer.timeout.connect(self._rerender_grid_for_layout)
        self._setup_ui()
        self.refresh(force=True)

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

        self._sort_label = QLabel()
        self._sort_label.setObjectName("PageSubtitle")
        self._sort_combo = QComboBox()
        self._sort_combo.setMinimumWidth(260)
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        header_row.addWidget(self._sort_label, 0, Qt.AlignRight | Qt.AlignVCenter)
        header_row.addWidget(self._sort_combo, 0, Qt.AlignRight | Qt.AlignVCenter)
        root.addLayout(header_row)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setObjectName("LibraryContentSplitter")
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.splitterMoved.connect(self._on_main_splitter_moved)

        self.main_pane = QWidget()
        pane_layout = QVBoxLayout(self.main_pane)
        pane_layout.setContentsMargins(0, 0, 0, 0)
        pane_layout.setSpacing(6)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setVerticalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setContentsMargins(UI_LAYOUT.grid_left_inset, 0, 0, 0)
        self._grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._scroll.setWidget(self._container)
        pane_layout.addWidget(self._scroll, 1)

        self._empty_label = QLabel()
        self._empty_label.setObjectName("PageSubtitle")
        self._empty_label.setAlignment(Qt.AlignCenter)
        pane_layout.addWidget(self._empty_label, 1)
        self._empty_label.hide()

        pagination_row = QHBoxLayout()
        self._prev_page_btn = QPushButton()
        self._prev_page_btn.setObjectName("GhostButton")
        self._prev_page_btn.clicked.connect(self._on_prev_page)
        self._pagination_label = QLabel()
        self._pagination_label.setObjectName("PageSubtitle")
        self._next_page_btn = QPushButton()
        self._next_page_btn.setObjectName("GhostButton")
        self._next_page_btn.clicked.connect(self._on_next_page)
        pagination_row.addStretch(1)
        pagination_row.addWidget(self._prev_page_btn)
        pagination_row.addWidget(self._pagination_label)
        pagination_row.addWidget(self._next_page_btn)
        pane_layout.addLayout(pagination_row)

        self.detail_panel = BookDetailPanel(repository=self._repo)
        self.detail_panel.setMinimumWidth(240)

        self.main_splitter.addWidget(self.main_pane)
        self.main_splitter.addWidget(self.detail_panel)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        self.main_splitter.setSizes([1020, 320])
        root.addWidget(self.main_splitter, 1)

        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        if self._favorite_only:
            self._title.setText(tr("comic_fav.page.title", "Comic Fav"))
            self._empty_label.setText(tr("comic_fav.page.empty", "No favorite comics yet."))
        else:
            self._title.setText(tr("comic.page.title", "Comic"))
            self._empty_label.setText(tr("comic.page.empty", "No comics found yet."))
        self._sort_label.setText(tr("comic.sort.label", "Sort"))
        self._sort_combo.blockSignals(True)
        self._sort_combo.clear()
        self._sort_combo.addItem(tr("comic.sort.folder_mtime_asc", "Folder Date: Oldest First"), COMIC_SORT_MTIME_ASC)
        self._sort_combo.addItem(tr("comic.sort.folder_mtime_desc", "Folder Date: Newest First"), COMIC_SORT_MTIME_DESC)
        self._sort_combo.addItem(tr("comic.sort.folder_name_asc", "Folder Name: A-Z"), COMIC_SORT_NAME_ASC)
        self._sort_combo.addItem(tr("comic.sort.folder_name_desc", "Folder Name: Z-A"), COMIC_SORT_NAME_DESC)
        selected = self._sort_combo.findData(self._sort_order)
        self._sort_combo.setCurrentIndex(selected if selected >= 0 else 1)
        self._sort_combo.blockSignals(False)
        self._prev_page_btn.setText(tr("comic.pagination.prev", "Prev"))
        self._next_page_btn.setText(tr("comic.pagination.next", "Next"))
        self._render_current_view()

    def invalidate_cache(self) -> None:
        self._data_cache_valid = False

    def refresh(self, force: bool = False) -> None:
        should_reload = force or not self._data_cache_valid
        if should_reload:
            self._reload_data_from_repository()
            self._data_cache_valid = True
        self._resource_by_id = {item.resource_id: item for item in self._resources}
        self._prune_card_cache_to_resource_ids(set(self._resource_by_id.keys()))
        count = len(self._resources)
        if self._favorite_only:
            self._subtitle.setText(tr("comic_fav.page.subtitle.count", "{count} comics in favorites").format(count=count))
        else:
            self._subtitle.setText(tr("comic.page.subtitle.count", "{count} comics detected").format(count=count))

        if self._selected_resource_id and self._selected_resource_id not in self._resource_by_id:
            self._selected_resource_id = None
        self._current_page = self._clamp_page(self._current_page)
        self._render_current_view()
        if self._selected_resource_id:
            self._update_detail_panel(self._selected_resource_id)
        else:
            self.detail_panel.clear_selection()

    def _reload_data_from_repository(self) -> None:
        if self._repo is None:
            self._resources = []
            self._comic_id_by_resource_id.clear()
            return
        if self._favorite_only:
            records = self._repo.get_favorite_comics(order_by=self._sort_order)
        else:
            records = self._repo.list_comics(include_missing=False, order_by=self._sort_order)
        self._resources = []
        self._comic_id_by_resource_id.clear()
        for record in records:
            resource_id = str(record.get("resource_id") or "").strip()
            if not resource_id:
                continue
            comic_id = record.get("id")
            if isinstance(comic_id, int):
                self._comic_id_by_resource_id[resource_id] = comic_id
            title = str(record.get("title") or "").strip() or Path(str(record.get("path") or "")).name or "Comic"
            self._resources.append(
                ResourceItem(
                    resource_id=resource_id,
                    title=title,
                    author="",
                    status="UNREAD",
                    tags=[],
                    resource_type="comic_folder",
                    path=str(record.get("path") or ""),
                    thumbnail_path=record.get("thumbnail_path"),
                    is_missing=bool(record.get("is_missing")),
                    info_text=str(record.get("info_text") or "") or None,
                    cover_image_path=str(record.get("cover_image_path") or "") or None,
                    image_count=int(record.get("image_count") or 0),
                )
            )

    def set_view_mode(self, mode: str, page_size: int) -> None:
        normalized_mode = _normalize_view_mode(mode)
        normalized_size = _normalize_page_size(page_size)
        changed = normalized_mode != self._view_mode or normalized_size != self._page_size
        self._view_mode = normalized_mode
        self._page_size = normalized_size
        if changed:
            self._current_page = 1
            self._render_current_view()

    def _render_current_view(self) -> None:
        if not self._resources:
            self._clear_grid()
            self._scroll.hide()
            self._empty_label.show()
            self._pagination_label.hide()
            self._prev_page_btn.hide()
            self._next_page_btn.hide()
            return

        self._empty_label.hide()
        self._scroll.show()
        visible_resources = self._visible_resources()
        self._render_grid(visible_resources)
        self._update_pagination_controls()

    def _render_grid(self, resources: list[ResourceItem]) -> None:
        self._grid.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setVerticalSpacing(UI_LAYOUT.card_spacing)
        self._detach_all_grid_widgets()
        self._last_columns = self._calculate_columns()
        columns = max(1, self._last_columns)
        for idx, resource in enumerate(resources):
            row = idx // columns
            col = idx % columns
            card = self._get_or_create_card(resource)
            card.set_selected(resource.resource_id == self._selected_resource_id)
            self._grid.addWidget(card, row, col, alignment=Qt.AlignLeft | Qt.AlignTop)

    def _visible_resources(self) -> list[ResourceItem]:
        if self._view_mode != COMIC_VIEW_MODE_PAGINATION:
            return list(self._resources)
        page_size = max(1, self._page_size)
        start = (self._current_page - 1) * page_size
        end = start + page_size
        return self._resources[start:end]

    def _total_pages(self) -> int:
        if self._view_mode != COMIC_VIEW_MODE_PAGINATION:
            return 1
        total = len(self._resources)
        page_size = max(1, self._page_size)
        return max(1, (total + page_size - 1) // page_size)

    def _clamp_page(self, page: int) -> int:
        return min(self._total_pages(), max(1, int(page)))

    def _update_pagination_controls(self) -> None:
        is_pagination = self._view_mode == COMIC_VIEW_MODE_PAGINATION
        self._prev_page_btn.setVisible(is_pagination)
        self._next_page_btn.setVisible(is_pagination)
        self._pagination_label.setVisible(is_pagination)
        if not is_pagination:
            return
        self._current_page = self._clamp_page(self._current_page)
        total_pages = self._total_pages()
        self._pagination_label.setText(
            tr("comic.pagination.status", "Page {current}/{total}").format(current=self._current_page, total=total_pages)
        )
        self._prev_page_btn.setEnabled(self._current_page > 1)
        self._next_page_btn.setEnabled(self._current_page < total_pages)

    def _on_prev_page(self) -> None:
        if self._view_mode != COMIC_VIEW_MODE_PAGINATION:
            return
        if self._current_page <= 1:
            return
        self._current_page -= 1
        self._render_current_view()

    def _on_next_page(self) -> None:
        if self._view_mode != COMIC_VIEW_MODE_PAGINATION:
            return
        if self._current_page >= self._total_pages():
            return
        self._current_page += 1
        self._render_current_view()

    def _clear_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)

    def _detach_all_grid_widgets(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)

    def _prune_card_cache_to_resource_ids(self, valid_ids: set[str]) -> None:
        for resource_id in list(self._card_by_resource_id.keys()):
            if resource_id in valid_ids:
                continue
            card = self._card_by_resource_id.pop(resource_id, None)
            self._card_signature_by_resource_id.pop(resource_id, None)
            if card is not None:
                card.deleteLater()

    @staticmethod
    def _resource_signature(resource: ResourceItem) -> tuple[str, str, str, str, int]:
        return (
            str(resource.title or ""),
            str(resource.path or ""),
            str(resource.cover_image_path or ""),
            str(resource.thumbnail_path or ""),
            int(resource.image_count or 0),
        )

    def _get_or_create_card(self, resource: ResourceItem) -> BookCardWidget:
        resource_id = resource.resource_id
        signature = self._resource_signature(resource)
        cached = self._card_by_resource_id.get(resource_id)
        cached_signature = self._card_signature_by_resource_id.get(resource_id)
        if cached is not None and cached_signature == signature:
            return cached
        if cached is not None:
            cached.deleteLater()
        card = BookCardWidget(resource, cover_only=True)
        self._card_by_resource_id[resource_id] = card
        self._card_signature_by_resource_id[resource_id] = signature
        card.clicked.connect(lambda res_id=resource_id: self._select_resource(res_id))
        card.open_requested.connect(lambda _pos, res_id=resource_id: self._open_resource_cover(res_id))
        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, res_id=resource_id, widget=card: self._show_card_menu_by_resource_id(
                res_id,
                widget.mapToGlobal(pos),
            )
        )
        return card

    def _open_resource_cover(self, resource_id: str) -> None:
        resource = self._resource_by_id.get(resource_id)
        if resource is None:
            return
        self._open_external(resource.cover_image_path or resource.path)

    def _show_card_menu_by_resource_id(self, resource_id: str, global_pos) -> None:
        resource = self._resource_by_id.get(resource_id)
        if resource is None:
            return
        self._show_card_menu(resource, global_pos)

    def _show_card_menu(self, resource: ResourceItem, global_pos) -> None:
        menu = QMenu(self)
        open_action = menu.addAction(tr("comic.menu.open_external", "Open Cover"))
        if self._favorite_only:
            fav_action = menu.addAction(tr("comic.menu.remove_favorite", "Remove from Comic Fav"))
        else:
            fav_action = menu.addAction(tr("comic.menu.add_favorite", "Add to Comic Fav"))
        chosen = menu.exec(global_pos)
        if chosen == open_action:
            self._open_external(resource.cover_image_path or resource.path)
        elif chosen == fav_action:
            self._toggle_favorite(resource)

    def _toggle_favorite(self, resource: ResourceItem) -> None:
        if self._repo is None:
            return
        comic_id = self._comic_id_by_resource_id.get(resource.resource_id)
        if comic_id is None:
            comic_id = self._repo.get_comic_int_id(resource.resource_id)
        if comic_id is None:
            return
        is_favorite = False
        if hasattr(self._repo, "is_favorite_comic"):
            is_favorite = bool(self._repo.is_favorite_comic(comic_id))
        if self._favorite_only or is_favorite:
            self._repo.remove_comic_from_favorites(comic_id)
        else:
            self._repo.add_comic_to_favorites(comic_id)
        self.invalidate_cache()
        self.favorites_changed.emit()
        self.refresh()

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
        for rid, card in self._card_by_resource_id.items():
            card.set_selected(rid == resource_id)
        self._update_detail_panel(resource_id)

    def _update_detail_panel(self, resource_id: str) -> None:
        resource = self._resource_by_id.get(resource_id)
        if resource is None:
            self.detail_panel.clear_selection()
            return
        self.detail_panel.set_resource(resource)

    def _calculate_columns(self) -> int:
        available_width = max(1, self._scroll.viewport().width())
        cell_width = UI_LAYOUT.card_width + UI_LAYOUT.card_spacing
        return max(1, available_width // max(1, cell_width))

    def _on_sort_changed(self, _index: int) -> None:
        selected = _normalize_sort_order(self._sort_combo.currentData())
        if selected == self._sort_order:
            return
        self._sort_order = selected
        self._save_sort_order(selected)
        self._current_page = 1
        self.invalidate_cache()
        self.refresh()

    def _load_sort_order(self) -> str:
        if self._repo is None:
            return COMIC_SORT_MTIME_DESC
        default_value = COMIC_SORT_MTIME_DESC
        if self._sort_setting_key == COMIC_SORT_SETTING_KEY_MAIN and hasattr(self._repo, "get_comic_sort_order_main"):
            return _normalize_sort_order(self._repo.get_comic_sort_order_main())
        if self._sort_setting_key == COMIC_SORT_SETTING_KEY_FAV and hasattr(self._repo, "get_comic_sort_order_fav"):
            return _normalize_sort_order(self._repo.get_comic_sort_order_fav())
        return _normalize_sort_order(self._repo.get_setting(self._sort_setting_key, default_value))

    def _load_view_mode(self) -> str:
        if self._repo is None or not hasattr(self._repo, "get_comic_view_mode"):
            return COMIC_VIEW_MODE_WATERFALL
        return _normalize_view_mode(self._repo.get_comic_view_mode())

    def _load_page_size(self) -> int:
        if self._repo is None or not hasattr(self._repo, "get_comic_page_size"):
            return DEFAULT_COMIC_PAGE_SIZE
        return _normalize_page_size(self._repo.get_comic_page_size())

    def _save_sort_order(self, order: str) -> None:
        if self._repo is None:
            return
        normalized = _normalize_sort_order(order)
        if self._sort_setting_key == COMIC_SORT_SETTING_KEY_MAIN and hasattr(self._repo, "set_comic_sort_order_main"):
            self._repo.set_comic_sort_order_main(normalized)
            return
        if self._sort_setting_key == COMIC_SORT_SETTING_KEY_FAV and hasattr(self._repo, "set_comic_sort_order_fav"):
            self._repo.set_comic_sort_order_fav(normalized)
            return
        self._repo.set_setting(self._sort_setting_key, normalized)

    def apply_card_spacing(self, _spacing: int) -> None:
        self._grid.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setVerticalSpacing(UI_LAYOUT.card_spacing)
        if self._resources:
            self._render_current_view()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self._resources:
            return
        columns = self._calculate_columns()
        if columns != self._last_columns:
            self._request_grid_reflow()

    def _on_main_splitter_moved(self, _pos: int, _index: int) -> None:
        if not self._resources:
            return
        columns = self._calculate_columns()
        if columns != self._last_columns:
            self._request_grid_reflow()

    def _request_grid_reflow(self) -> None:
        self._reflow_timer.start()

    def _rerender_grid_for_layout(self) -> None:
        if not self._resources:
            return
        self._render_current_view()
