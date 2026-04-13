# -*- coding: utf-8 -*-
"""
QuickAddDialog - right-click quick-add popup for tags and custom reading lists.
Matches the UI design in 鼠标右键的菜单.html
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class _TagChip(QPushButton):
    """A small toggle-able tag chip button."""

    def __init__(self, tag: str, selected: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(tag, parent)
        self._tag = tag
        self._selected = selected
        self.setCheckable(True)
        self.setChecked(selected)
        self.setObjectName("TagChip")
        self._update_style()
        self.toggled.connect(lambda _: self._update_style())

    @property
    def tag(self) -> str:
        return self._tag

    def _update_style(self) -> None:
        if self.isChecked():
            self.setStyleSheet("""
                QPushButton#TagChip {
                    background-color: #005FAC;
                    color: white;
                    border: 1px solid #005FAC;
                    border-radius: 0px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton#TagChip {
                    background-color: #EEEEEE;
                    color: #414752;
                    border: 1px solid #C0C7D4;
                    border-radius: 0px;
                    padding: 3px 10px;
                    font-size: 11px;
                }
                QPushButton#TagChip:hover {
                    background-color: #E2E2E2;
                }
            """)


class _CollectionRow(QWidget):
    """A single row in the collections list with an 'Add' button."""

    def __init__(self, col_id: int, col_name: str, already_in: bool,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._col_id = col_id
        self._col_name = col_name
        self._added = already_in

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        icon_label = QLabel("📚")
        icon_label.setFixedWidth(20)
        layout.addWidget(icon_label)

        name_label = QLabel(col_name)
        name_label.setObjectName("colRowName")
        name_label.setSizePolicy(name_label.sizePolicy().horizontalPolicy(),
                                 name_label.sizePolicy().verticalPolicy())
        layout.addWidget(name_label, 1)

        self._btn = QPushButton("已添加" if already_in else "添加")
        self._btn.setObjectName("colAddBtn")
        self._btn.setFixedWidth(52)
        self._btn.clicked.connect(self._on_click)
        layout.addWidget(self._btn)

        self._update_style()

    @property
    def col_id(self) -> int:
        return self._col_id

    @property
    def is_added(self) -> bool:
        return self._added

    def _on_click(self) -> None:
        self._added = not self._added
        self._btn.setText("已添加" if self._added else "添加")
        self._update_style()

    def _update_style(self) -> None:
        if self._added:
            self._btn.setStyleSheet("""
                QPushButton#colAddBtn {
                    background-color: #E8F4FF;
                    color: #005FAC;
                    border: 1px solid #B3D4F5;
                    font-size: 10px; font-weight: bold;
                    padding: 2px 6px;
                }
            """)
        else:
            self._btn.setStyleSheet("""
                QPushButton#colAddBtn {
                    background-color: transparent;
                    color: #005FAC;
                    border: none;
                    font-size: 10px; font-weight: bold;
                    padding: 2px 6px;
                }
                QPushButton#colAddBtn:hover { text-decoration: underline; }
            """)


class QuickAddDialog(QDialog):
    """
    Quick-add dialog: add tags and add to custom reading lists.
    Opened by right-clicking a book card.
    """

    def __init__(
        self,
        book_id: int,
        book_title: str,
        repository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._book_id = book_id
        self._book_title = book_title
        self._repo = repository

        # State
        self._current_book_tags: list[str] = []
        self._all_tags: list[str] = []
        self._all_collections: list[dict] = []
        self._tag_chips: list[_TagChip] = []
        self._col_rows: list[_CollectionRow] = []

        self._load_data()
        self._setup_ui()

    # ------------------------------------------------------------------
    def _load_data(self) -> None:
        try:
            self._current_book_tags = self._repo.get_book_tags(self._book_id)
        except Exception:
            self._current_book_tags = []
        try:
            self._all_tags = self._repo.get_all_tags()
        except Exception:
            self._all_tags = []
        try:
            self._all_collections = self._repo.get_all_collections()
        except Exception:
            self._all_collections = []

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        self.setWindowTitle("快速添加")
        self.setFixedWidth(360)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Title bar ──────────────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(36)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(12, 0, 12, 0)

        title_lbl = QLabel("添加标签")
        title_lbl.setObjectName("dialogTitle")
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.reject)
        tb_layout.addWidget(close_btn)
        root.addWidget(title_bar)

        # ── Book name strip ───────────────────────────────────────────
        book_strip = QWidget()
        book_strip.setObjectName("bookStrip")
        bs_layout = QHBoxLayout(book_strip)
        bs_layout.setContentsMargins(12, 6, 12, 6)
        short_title = (self._book_title[:40] + "…") if len(self._book_title) > 40 else self._book_title
        book_lbl = QLabel(f"📖  {short_title}")
        book_lbl.setObjectName("bookLabel")
        book_lbl.setWordWrap(False)
        bs_layout.addWidget(book_lbl)
        root.addWidget(book_strip)

        # ── Body ───────────────────────────────────────────────────────
        body = QWidget()
        body.setObjectName("dialogBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(16, 14, 16, 14)
        body_layout.setSpacing(14)

        # Section: 标签名称 ─────────────────────────────────────────────
        sec1_title = QLabel("标签名称")
        sec1_title.setObjectName("sectionTitle")
        body_layout.addWidget(sec1_title)

        # Tag search bar
        tag_search_row = QWidget()
        tag_search_row.setObjectName("searchRow")
        ts_layout = QHBoxLayout(tag_search_row)
        ts_layout.setContentsMargins(0, 0, 0, 0)
        ts_layout.setSpacing(6)

        self._tag_input = QLineEdit()
        self._tag_input.setObjectName("tagInput")
        self._tag_input.setPlaceholderText("输入标签…")
        self._tag_input.textChanged.connect(self._on_tag_filter)
        ts_layout.addWidget(self._tag_input, 1)

        add_tag_btn = QPushButton("+ 创建")
        add_tag_btn.setObjectName("createTagBtn")
        add_tag_btn.clicked.connect(self._on_create_tag)
        ts_layout.addWidget(add_tag_btn)

        body_layout.addWidget(tag_search_row)

        # Existing tags chip area (scrollable)
        self._tags_scroll = QScrollArea()
        self._tags_scroll.setWidgetResizable(True)
        self._tags_scroll.setFixedHeight(100)
        self._tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tags_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._tags_scroll.setObjectName("tagsScroll")

        self._tags_container = QWidget()
        self._tags_flow = _FlowLayout(self._tags_container, h_spacing=6, v_spacing=6)
        self._tags_container.setLayout(self._tags_flow)
        self._tags_scroll.setWidget(self._tags_container)
        body_layout.addWidget(self._tags_scroll)
        self._populate_tag_chips(self._all_tags)

        # Divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.HLine)
        div1.setObjectName("divider")
        body_layout.addWidget(div1)

        # Section: 添加到自定义书单 ──────────────────────────────────────
        sec2_title = QLabel("添加到自定义书单")
        sec2_title.setObjectName("sectionTitle")
        body_layout.addWidget(sec2_title)

        # Collection search bar
        col_search_row = QWidget()
        cs_layout = QHBoxLayout(col_search_row)
        cs_layout.setContentsMargins(0, 0, 0, 0)
        cs_layout.setSpacing(6)

        self._col_input = QLineEdit()
        self._col_input.setObjectName("colInput")
        self._col_input.setPlaceholderText("搜索书单…")
        self._col_input.textChanged.connect(self._on_col_filter)
        cs_layout.addWidget(self._col_input, 1)

        new_list_btn = QPushButton("+ 新建")
        new_list_btn.setObjectName("createTagBtn")
        new_list_btn.clicked.connect(self._on_create_collection)
        cs_layout.addWidget(new_list_btn)

        body_layout.addWidget(col_search_row)

        # Collections list (scrollable)
        self._col_scroll = QScrollArea()
        self._col_scroll.setWidgetResizable(True)
        self._col_scroll.setFixedHeight(130)
        self._col_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._col_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._col_scroll.setObjectName("colScroll")

        self._col_container = QWidget()
        self._col_layout = QVBoxLayout(self._col_container)
        self._col_layout.setContentsMargins(0, 0, 0, 0)
        self._col_layout.setSpacing(0)
        self._col_layout.addStretch()
        self._col_scroll.setWidget(self._col_container)
        body_layout.addWidget(self._col_scroll)
        self._populate_col_rows(self._all_collections)

        # Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setObjectName("divider")
        body_layout.addWidget(div2)

        # Confirm / Cancel buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        confirm_btn = QPushButton("确认添加")
        confirm_btn.setObjectName("confirmBtn")
        confirm_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(confirm_btn, 1)

        body_layout.addLayout(btn_row)

        root.addWidget(body)

        self._apply_styles()

    # ------------------------------------------------------------------
    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #F9F9F9;
                border: 1px solid #C0C7D4;
            }
            QWidget#titleBar {
                background-color: #E2E2E2;
                border-bottom: 1px solid #C0C7D4;
            }
            QLabel#dialogTitle {
                font-size: 11px;
                font-weight: 700;
                color: #414752;
                letter-spacing: 1px;
            }
            QPushButton#closeBtn {
                background: transparent;
                border: none;
                color: #414752;
                font-size: 12px;
                padding: 0;
                text-align: center;
            }
            QPushButton#closeBtn:hover { color: #005FAC; }
            QWidget#bookStrip {
                background-color: #EEEEEE;
                border-bottom: 1px solid #E0E0E0;
            }
            QLabel#bookLabel { font-size: 12px; color: #414752; }
            QWidget#dialogBody { background-color: #F9F9F9; }
            QLabel#sectionTitle {
                font-size: 10px;
                font-weight: 700;
                color: #717784;
                letter-spacing: 1px;
                text-transform: uppercase;
            }
            QLineEdit#tagInput, QLineEdit#colInput {
                background-color: #EEEEEE;
                border: none;
                border-bottom: 2px solid #005FAC;
                padding: 5px 8px;
                font-size: 12px;
            }
            QLineEdit#tagInput:focus, QLineEdit#colInput:focus {
                background-color: #E8E8E8;
                border-bottom: 2px solid #0078D7;
            }
            QPushButton#createTagBtn {
                background-color: transparent;
                color: #005FAC;
                border: 1px solid #C0C7D4;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#createTagBtn:hover { background-color: #E8F4FF; }
            QScrollArea#tagsScroll, QScrollArea#colScroll {
                background-color: #F9F9F9;
                border: 1px solid #E0E0E0;
            }
            QFrame#divider { color: #E0E0E0; }
            QLabel#colRowName { font-size: 12px; color: #1A1C1C; }
            QPushButton#confirmBtn {
                background-color: #005FAC;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#confirmBtn:hover { background-color: #004A8C; }
            QPushButton#cancelBtn {
                background-color: transparent;
                color: #005FAC;
                border: 1px solid #C0C7D4;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#cancelBtn:hover { background-color: #F0F0F0; }
        """)

    # ------------------------------------------------------------------
    def _populate_tag_chips(self, tags: list[str]) -> None:
        """Clear and repopulate the tag chip area."""
        # Remove all existing chips
        while self._tags_flow.count():
            item = self._tags_flow.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._tag_chips.clear()

        if not tags:
            empty = QLabel("暂无标签")
            empty.setStyleSheet("color: #9E9E9E; font-size: 11px; padding: 6px;")
            self._tags_flow.addWidget(empty)
            return

        for tag in tags:
            selected = tag in self._current_book_tags
            chip = _TagChip(tag, selected)
            self._tags_flow.addWidget(chip)
            self._tag_chips.append(chip)

    def _populate_col_rows(self, collections: list[dict]) -> None:
        """Clear and repopulate the collections list."""
        # Remove all except the trailing stretch
        while self._col_layout.count() > 1:
            item = self._col_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._col_rows.clear()

        if not collections:
            empty = QLabel("暂无书单，点击「+ 新建」创建")
            empty.setStyleSheet("color: #9E9E9E; font-size: 11px; padding: 10px 12px;")
            self._col_layout.insertWidget(0, empty)
            return

        for i, col in enumerate(collections):
            col_id = col.get("id", -1)
            col_name = col.get("name", "")
            try:
                already_in = self._repo.is_book_in_collection(self._book_id, col_id)
            except Exception:
                already_in = False
            row = _CollectionRow(col_id, col_name, already_in)
            row.setObjectName("colRow" + ("Alt" if i % 2 else ""))
            row.setStyleSheet(
                "background-color: #F5F5F5; border-bottom: 1px solid #EEEEEE;"
                if i % 2 else
                "background-color: #FFFFFF; border-bottom: 1px solid #EEEEEE;"
            )
            self._col_layout.insertWidget(i, row)
            self._col_rows.append(row)

    # ------------------------------------------------------------------
    def _on_tag_filter(self, text: str) -> None:
        text = text.strip().lower()
        filtered = [t for t in self._all_tags if text in t.lower()] if text else self._all_tags
        self._populate_tag_chips(filtered)

    def _on_col_filter(self, text: str) -> None:
        text = text.strip().lower()
        filtered = [c for c in self._all_collections if text in c.get("name", "").lower()] \
            if text else self._all_collections
        self._populate_col_rows(filtered)

    def _on_create_tag(self) -> None:
        tag = self._tag_input.text().strip()
        if not tag:
            # Prompt for new tag name
            tag, ok = QInputDialog.getText(self, "创建标签", "标签名称：")
            if not ok or not tag.strip():
                return
            tag = tag.strip()
        if tag not in self._all_tags:
            self._all_tags.append(tag)
            self._all_tags.sort()
        if tag not in self._current_book_tags:
            self._current_book_tags.append(tag)
        self._tag_input.clear()
        self._populate_tag_chips(self._all_tags)
        # Find and check the newly created chip
        for chip in self._tag_chips:
            if chip.tag == tag:
                chip.setChecked(True)
                break

    def _on_create_collection(self) -> None:
        name = self._col_input.text().strip()
        if not name:
            name, ok = QInputDialog.getText(self, "新建书单", "书单名称：")
            if not ok or not name.strip():
                return
            name = name.strip()
        try:
            self._repo.create_collection(name)
            self._all_collections = self._repo.get_all_collections()
            self._col_input.clear()
            self._populate_col_rows(self._all_collections)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建书单失败：{e}")

    def _on_confirm(self) -> None:
        errors: list[str] = []

        # Apply tag changes
        selected_tags = {chip.tag for chip in self._tag_chips if chip.isChecked()}
        try:
            current = set(self._repo.get_book_tags(self._book_id))
            # Add new tags
            for tag in selected_tags - current:
                self._repo.add_tag_to_book(self._book_id, tag)
            # Remove deselected tags (only tags that were previously on the book and now deselected)
            for tag in current - selected_tags:
                if tag in {c.tag for c in self._tag_chips}:
                    # Only remove if it was shown in the chip list (user had a chance to deselect)
                    self._repo.remove_tag_from_book(self._book_id, tag)
        except Exception as e:
            errors.append(f"标签更新失败：{e}")

        # Apply collection changes
        for row in self._col_rows:
            try:
                if row.is_added:
                    self._repo.add_book_to_collection(self._book_id, row.col_id)
                else:
                    self._repo.remove_book_from_collection(self._book_id, row.col_id)
            except Exception as e:
                errors.append(f"书单「{row.col_id}」更新失败：{e}")

        if errors:
            QMessageBox.warning(self, "部分操作失败", "\n".join(errors))

        self.accept()


# ---------------------------------------------------------------------------
# FlowLayout  (simple wrapping layout for tag chips)
# ---------------------------------------------------------------------------

class _FlowLayout:
    """Minimal wrapping flow layout adapter using a QWidget + manual re-layout.
    We use a simple QVBoxLayout of QHBoxLayouts approach instead to stay simple.
    """
    # Actually, implement a real flow using a custom QLayout subclass is complex.
    # Use a simpler approach: just a plain wrapping container via QWidget + re-wrap.
    pass


# Replace the above stub with a proper implementation using a flat container:
from PySide6.QtWidgets import QLayout, QSizePolicy as _QSP
from PySide6.QtCore import QRect, QSize, QPoint


class _FlowLayout(QLayout):  # type: ignore[no-redef]
    """A simple flow (wrapping) layout for chips."""

    def __init__(self, parent: QWidget | None = None,
                 h_spacing: int = 4, v_spacing: int = 4) -> None:
        super().__init__(parent)
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._items: list = []

    def addItem(self, item) -> None:  # type: ignore[override]
        self._items.append(item)

    def addWidget(self, widget: QWidget) -> None:
        from PySide6.QtWidgets import QWidgetItem
        self.addItem(QWidgetItem(widget))
        if widget.parent() is None and self.parentWidget():
            widget.setParent(self.parentWidget())
        widget.show()

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        from PySide6.QtCore import Qt as _Qt
        return _Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        left, top, right, bottom = self.getContentsMargins()
        effective = rect.adjusted(left, top, -right, -bottom)
        x = effective.x()
        y = effective.y()
        line_height = 0
        for item in self._items:
            wid = item.widget()
            hint = item.sizeHint()
            next_x = x + hint.width() + self._h_spacing
            if next_x - self._h_spacing > effective.right() and line_height > 0:
                x = effective.x()
                y = y + line_height + self._v_spacing
                next_x = x + hint.width() + self._h_spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + bottom