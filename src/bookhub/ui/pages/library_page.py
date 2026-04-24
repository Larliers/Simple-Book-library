from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QPoint, QSize, QTimer, Qt
from PySide6.QtGui import QCursor, QIcon, QPixmap
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
from bookhub.ui.widgets.book_card import BookCardWidget, format_author_publisher_meta


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
        self._resource_by_id: dict[str, ResourceItem] = {}
        self._active_toasts: list[QLabel] = []

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
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

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
        self._resource_by_id = {item.resource_id: item for item in items}
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
        self.grid_layout.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self.grid_layout.setVerticalSpacing(UI_LAYOUT.card_spacing)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        previous_columns = self._last_grid_columns
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
            card.open_requested.connect(
                lambda global_pos, resource=item: self._open_book_external(resource, global_pos)
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

        max_columns_to_reset = max(previous_columns, columns) + 1
        for col in range(max_columns_to_reset + 1):
            self.grid_layout.setColumnStretch(col, 0)
        self.grid_layout.setColumnStretch(columns, 1)

    def _render_list(self, items: list[ResourceItem]) -> None:
        self.list_table.setRowCount(len(items))
        for row, item in enumerate(items):
            cover_item = QTableWidgetItem("  ")
            cover_item.setData(Qt.UserRole, item.resource_id)
            cover_item.setIcon(self._build_thumbnail_icon(item))
            self.list_table.setItem(row, 0, cover_item)
            self.list_table.setItem(row, 1, QTableWidgetItem(item.title))
            self.list_table.setItem(
                row,
                2,
                QTableWidgetItem(format_author_publisher_meta(item.author, item.publisher)),
            )
            self.list_table.setItem(row, 3, QTableWidgetItem(item.status))
            self.list_table.setItem(row, 4, QTableWidgetItem(", ".join(item.tags)))

        self.list_table.resizeColumnsToContents()
        self.list_table.setColumnWidth(1, 260)

    def _build_thumbnail_icon(self, item: ResourceItem) -> QIcon:
        if item.thumbnail_path:
            thumb = item.thumbnail_path
            # Support both file:// URLs (new format) and legacy bare filesystem paths
            if thumb.startswith("file://"):
                from urllib.parse import urlparse
                from urllib.request import url2pathname
                parsed = urlparse(thumb)
                file_path = Path(url2pathname(parsed.path))
            else:
                file_path = Path(thumb)
            if file_path.exists():
                pixmap = QPixmap(str(file_path))
                if not pixmap.isNull():
                    return QIcon(
                        pixmap.scaled(26, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
        fallback = QPixmap(26, 38)
        fallback.fill(Qt.lightGray)
        return QIcon(fallback)

    def _show_card_menu(self, resource: ResourceItem, global_pos) -> None:
        menu = QMenu(self)
        open_action = menu.addAction(tr("library.menu.open_external", "Open External"))
        open_folder_action = menu.addAction(tr("library.menu.open_folder", "Open Folder"))
        add_favorite_action = None
        if self._repository is not None and not self.missing_mode:
            add_favorite_action = menu.addAction(tr("library.menu.add_to_favorites", "Add to Favorites"))
        menu.addSeparator()
        remove_action = menu.addAction(tr("library.menu.remove_library", "Remove from Library"))

        # Quick-add (tags + custom reading lists) — only when repository available
        quick_add_action = None
        edit_cover_action = None
        if self._repository is not None:
            menu.addSeparator()
            quick_add_action = menu.addAction(
                tr("library.menu.quick_add", "Add Tags / Add to List...")
            )
            edit_cover_action = menu.addAction(
                tr("library.menu.edit_cover", "Edit Cover...")
            )

        chosen = menu.exec(global_pos)

        if chosen == open_action:
            self._open_book_external(resource)
        elif chosen == open_folder_action:
            self._open_book_folder(resource)
        elif add_favorite_action is not None and chosen == add_favorite_action:
            self._add_to_favorites(resource)
        elif chosen == remove_action:
            self._track_event("paginate", resource.resource_id)
        elif quick_add_action is not None and chosen == quick_add_action:
            self._open_quick_add_dialog(resource, global_pos)
        elif edit_cover_action is not None and chosen == edit_cover_action:
            self._edit_cover(resource)

    def _edit_cover(self, resource: ResourceItem) -> None:
        """Right-click → 编辑封面 flow:
        1. Open file dialog (upload接口 equivalent)
        2. Convert picked image to WebP, save to img_preview/
        3. Build file:// URL (returned URL from upload接口)
        4. Update DB thumbnail_path (coverUrl update)
        5. Refresh UI card
        """
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path as _Path

        if self._repository is None:
            return

        # Step 1: File picker (the "upload" entry point)
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择封面图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff *.tif)",
        )
        if not image_path:
            return

        src = _Path(image_path)
        if not src.exists():
            QMessageBox.warning(self, "错误", f"文件不存在：{src}")
            return

        # Step 2: Convert to WebP and save to img_preview/
        try:
            from PIL import Image as _Image
            from bookhub.library.repository import DEFAULT_PREVIEW_DIR
            import hashlib as _hashlib

            DEFAULT_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
            # Stable collision-free filename from source path hash
            name_hash = _hashlib.md5(str(src).encode("utf-8", errors="replace")).hexdigest()[:16]
            out_path = DEFAULT_PREVIEW_DIR / f"cover_{name_hash}.webp"

            img = _Image.open(str(src))
            img = img.convert("RGB")
            img.save(str(out_path), format="WebP", quality=80)

        except ImportError:
            # Pillow not available — copy file as-is
            import shutil as _shutil
            from bookhub.library.repository import DEFAULT_PREVIEW_DIR
            import hashlib as _hashlib

            DEFAULT_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
            name_hash = _hashlib.md5(str(src).encode("utf-8", errors="replace")).hexdigest()[:16]
            out_path = DEFAULT_PREVIEW_DIR / f"cover_{name_hash}{src.suffix.lower()}"
            _shutil.copy2(str(src), str(out_path))

        except Exception as exc:
            QMessageBox.critical(self, "封面更新失败", f"图片处理错误：{exc}")
            return

        # Step 3: Build file:// URL (the value returned by the upload接口)
        file_url = out_path.as_uri()

        # Step 4: Update DB — coverUrl update
        try:
            book_id = self._repository.get_book_int_id(resource.resource_id)
            if book_id is None:
                QMessageBox.warning(self, "错误", "找不到书籍记录，无法更新封面。")
                return
            self._repository.update_book_thumbnail_path(book_id, file_url)
        except Exception as exc:
            QMessageBox.critical(self, "封面更新失败", f"数据库写入错误：{exc}")
            return

        # Step 5: Update in-memory ResourceItem so render() picks it up immediately
        resource.thumbnail_path = file_url

        # Refresh the view
        self.render()

    def _open_book_external(self, resource: ResourceItem, global_pos: QPoint | None = None) -> None:
        self._open_path_external(resource.path, resource.resource_id, global_pos)

    def _open_path_external(
        self,
        path: str,
        resource_id: str | None,
        global_pos: QPoint | None = None,
    ) -> None:
        import os
        import subprocess
        import sys
        file_path = Path(path).expanduser()
        if not str(file_path).strip() or not file_path.exists():
            self._show_open_error_toast(
                tr("library.toast.file_missing", "File not found or moved."),
                global_pos,
            )
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(file_path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(file_path)])
            else:
                subprocess.Popen(["xdg-open", str(file_path)])
        except Exception as e:
            print(f"[LibraryPage] open external error: {e}")
            self._show_open_error_toast(
                tr("library.toast.open_failed", "Unable to open with default app."),
                global_pos,
            )
            return
        self._track_event("open_external", resource_id)

    def _open_book_folder(self, resource: ResourceItem) -> None:
        import subprocess
        import sys
        from pathlib import Path as _Path
        try:
            folder = str(_Path(resource.path).parent)
            if sys.platform == "win32":
                subprocess.Popen(["explorer", folder])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            print(f"[LibraryPage] open folder error: {e}")
        self._track_event("open_external", resource.resource_id)

    def _open_quick_add_dialog(self, resource: ResourceItem, global_pos) -> None:
        if self._repository is None:
            return
        book_id = self._repository.get_book_int_id(resource.resource_id)
        if book_id is None:
            return
        try:
            from bookhub.ui.dialogs.quick_add_dialog import QuickAddDialog
        except ImportError as e:
            print(f"[LibraryPage] QuickAddDialog import error: {e}")
            return
        dlg = QuickAddDialog(book_id, resource.title, self._repository, self)
        # Position near the cursor
        dlg.move(global_pos)
        dlg.exec()

    def _show_list_menu(self, pos) -> None:
        row = self.list_table.rowAt(pos.y())
        if row < 0:
            return
        resource_id = self.list_table.item(row, 0).data(Qt.UserRole)
        global_pos = self.list_table.viewport().mapToGlobal(pos)
        menu = QMenu(self)
        open_action = menu.addAction(tr("library.menu.open_external", "Open External"))
        add_favorite_action = None
        if self._repository is not None and not self.missing_mode:
            add_favorite_action = menu.addAction(tr("library.menu.add_to_favorites", "Add to Favorites"))
        add_tag_action = menu.addAction(tr("library.menu.add_tag", "Add Tag"))
        mark_action = menu.addAction(tr("library.menu.mark_reading", "Mark as Reading"))
        chosen = menu.exec(global_pos)

        if chosen == open_action:
            resource = self._resource_by_id.get(str(resource_id or ""))
            if resource is not None:
                self._open_book_external(resource, global_pos)
            else:
                self._show_open_error_toast(
                    tr("library.toast.open_failed", "Unable to open with default app."),
                    global_pos,
                )
        elif add_favorite_action is not None and chosen == add_favorite_action:
            resource = self._resource_by_id.get(str(resource_id or ""))
            if resource is not None:
                self._add_to_favorites(resource)
        elif chosen == add_tag_action:
            dialog = AddTagDialog(self)
            if dialog.exec():
                self._track_event("sort", resource_id)
        elif chosen == mark_action:
            self._track_event("sort", resource_id)

    def _add_to_favorites(self, resource: ResourceItem) -> None:
        if self._repository is None:
            return
        book_id = self._repository.get_book_int_id(resource.resource_id)
        if book_id is None:
            return
        try:
            self._repository.add_to_favorites(book_id)
            self._track_event("sort", resource.resource_id)
        except Exception as e:
            print(f"[LibraryPage] add to favorites error: {e}")

    def _show_open_error_toast(self, message: str, global_pos: QPoint | None = None) -> None:
        anchor = global_pos or QCursor.pos()
        toast = QLabel(message)
        toast.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        toast.setAttribute(Qt.WA_ShowWithoutActivating, True)
        toast.setStyleSheet(
            "QLabel {"
            "background: #fff5f5;"
            "color: #8e2c2c;"
            "border: 1px solid #f0b8b8;"
            "border-radius: 8px;"
            "padding: 6px 10px;"
            "font-size: 12px;"
            "}"
        )
        toast.adjustSize()
        toast.move(anchor + QPoint(12, 12))
        toast.show()
        self._active_toasts.append(toast)

        def _cleanup() -> None:
            if toast in self._active_toasts:
                self._active_toasts.remove(toast)
            toast.close()
            toast.deleteLater()

        QTimer.singleShot(2000, _cleanup)

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

    def apply_card_spacing(self, _spacing: int) -> None:
        self.grid_layout.setHorizontalSpacing(UI_LAYOUT.card_spacing)
        self.grid_layout.setVerticalSpacing(UI_LAYOUT.card_spacing)
        if self.view_model.view_mode == "waterfall":
            self._render_grid(self.view_model.filtered_resources(include_missing=self.missing_mode))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.view_model.view_mode != "waterfall":
            return
        columns = self._calculate_grid_columns()
        if columns != self._last_grid_columns:
            self._render_grid(self.view_model.filtered_resources(include_missing=self.missing_mode))
