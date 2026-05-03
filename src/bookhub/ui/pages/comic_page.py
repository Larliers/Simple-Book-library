from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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


class ComicPage(QWidget):
    def __init__(self, repository, favorite_only: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repository
        self._favorite_only = favorite_only
        self._resources: list[ResourceItem] = []
        self._resource_by_id: dict[str, ResourceItem] = {}
        self._comic_id_by_resource_id: dict[str, int] = {}
        self._selected_resource_id: str | None = None
        self._card_by_resource_id: dict[str, BookCardWidget] = {}
        self._last_columns = 0
        self._setup_ui()
        self.refresh()

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
        self.main_splitter.splitterMoved.connect(self._on_main_splitter_moved)

        self.main_pane = QWidget()
        pane_layout = QVBoxLayout(self.main_pane)
        pane_layout.setContentsMargins(0, 0, 0, 0)
        pane_layout.setSpacing(0)

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
        self.refresh()

    def refresh(self) -> None:
        if self._repo is None:
            self._resources = []
        else:
            records = self._repo.get_favorite_comics() if self._favorite_only else self._repo.list_comics(include_missing=False)
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

        self._resource_by_id = {item.resource_id: item for item in self._resources}
        count = len(self._resources)
        if self._favorite_only:
            self._subtitle.setText(tr("comic_fav.page.subtitle.count", "{count} comics in favorites").format(count=count))
        else:
            self._subtitle.setText(tr("comic.page.subtitle.count", "{count} comics detected").format(count=count))

        if self._selected_resource_id and self._selected_resource_id not in self._resource_by_id:
            self._selected_resource_id = None

        if not self._resources:
            while self._grid.count():
                item = self._grid.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
            self._card_by_resource_id.clear()
            self._scroll.hide()
            self._empty_label.show()
            self.detail_panel.clear_selection()
            return

        self._empty_label.hide()
        self._scroll.show()
        self._render_grid()
        if self._selected_resource_id:
            self._update_detail_panel(self._selected_resource_id)
        else:
            self.detail_panel.clear_selection()

    def _render_grid(self) -> None:
        self._grid.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setVerticalSpacing(UI_LAYOUT.card_spacing)
        self._card_by_resource_id.clear()
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        columns = self._calculate_columns()
        self._last_columns = columns
        for idx, resource in enumerate(self._resources):
            row = idx // columns
            col = idx % columns
            card = BookCardWidget(resource, cover_only=True)
            self._card_by_resource_id[resource.resource_id] = card
            card.set_selected(resource.resource_id == self._selected_resource_id)
            card.clicked.connect(lambda res_id=resource.resource_id: self._select_resource(res_id))
            card.open_requested.connect(lambda _pos, res=resource: self._open_external(res.cover_image_path or res.path))
            card.setContextMenuPolicy(Qt.CustomContextMenu)
            card.customContextMenuRequested.connect(
                lambda pos, res=resource, widget=card: self._show_card_menu(res, widget.mapToGlobal(pos))
            )
            self._grid.addWidget(card, row, col, alignment=Qt.AlignLeft | Qt.AlignTop)

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
        comic_id = self._repo.get_comic_int_id(resource.resource_id)
        if comic_id is None:
            return
        if self._favorite_only:
            self._repo.remove_comic_from_favorites(comic_id)
        else:
            self._repo.add_comic_to_favorites(comic_id)
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
        collection_names = []
        if resource.info_text:
            collection_names.append(resource.info_text)
        self.detail_panel.set_resource(resource, collection_names)

    def _calculate_columns(self) -> int:
        available_width = max(1, self._scroll.viewport().width())
        cell_width = UI_LAYOUT.card_width + UI_LAYOUT.card_spacing
        return max(1, available_width // max(1, cell_width))

    def apply_card_spacing(self, _spacing: int) -> None:
        self._grid.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self._grid.setVerticalSpacing(UI_LAYOUT.card_spacing)
        if self._resources:
            self._render_grid()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        columns = self._calculate_columns()
        if columns != self._last_columns and self._resources:
            self._render_grid()

    def _on_main_splitter_moved(self, _pos: int, _index: int) -> None:
        columns = self._calculate_columns()
        if columns != self._last_columns and self._resources:
            self._render_grid()