from __future__ import annotations

DEFAULT_FONT_STACK = ["Inter", "Segoe UI", "Microsoft YaHei"]


def _quote_font_family(name: str) -> str:
    value = str(name or "").strip().replace('"', "")
    if not value:
        return ""
    return f'"{value}"'


def build_app_style(font_stack: list[str] | tuple[str, ...] | None = None) -> str:
    families = [_quote_font_family(item) for item in (font_stack or DEFAULT_FONT_STACK)]
    normalized = [item for item in families if item]
    if not normalized:
        normalized = [_quote_font_family(item) for item in DEFAULT_FONT_STACK]
    return _APP_STYLE_TEMPLATE.replace("__FONT_STACK__", ", ".join(normalized))

_APP_STYLE_TEMPLATE = """
QWidget {
    background: #f3f3f3;
    color: #1f2530;
    font-family: __FONT_STACK__;
    font-size: 13px;
}
QMainWindow {
    background: #f3f3f3;
}
QFrame#PageSection,
QFrame#CardPanel,
QFrame#SubtlePanel {
    border: 1px solid #d9dee7;
    border-radius: 0px;
    background: #ffffff;
}
QFrame#SubtlePanel {
    background: #f8f9fb;
}
#Sidebar {
    background: #eceff3;
    border-right: 1px solid #d4dae4;
}
#SidebarTitle {
    font-weight: 700;
}
#SidebarFoot {
    border-top: 1px solid #d4dae4;
    background: #eceff3;
}
QPushButton {
    border: 1px solid transparent;
    border-radius: 0px;
    padding: 6px 10px;
    text-align: left;
    background: transparent;
    color: #2e3848;
}
QPushButton:hover {
    background: #dfe5ee;
}
QPushButton:checked {
    background: #f7fbff;
    border-left: 3px solid #0078d7;
    color: #0f5fa8;
    font-weight: 600;
}
QPushButton[variant="sidebar_tab"] {
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    padding: 7px 10px;
    text-align: left;
    background: transparent;
    color: #2e3848;
}
QPushButton[variant="sidebar_tab"]:hover {
    background: #dde6f2;
    border-left: 3px solid #92b9e6;
    color: #173f70;
}
QPushButton[variant="sidebar_tab"]:pressed {
    background: #d2deee;
    border-left: 3px solid #6da4df;
}
QPushButton[variant="sidebar_tab"]:checked {
    background: #f4f9ff;
    border-left: 3px solid #0078d7;
    color: #0f5fa8;
    font-weight: 600;
}
QPushButton#FlatIconButton {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
    text-align: center;
}
QPushButton#PrimarySideButton,
QPushButton#PrimaryButton {
    background: #0078d7;
    color: #ffffff;
    border: 1px solid #0078d7;
    text-align: center;
    font-weight: 700;
    padding: 6px 12px;
}
QPushButton#PrimarySideButton:hover,
QPushButton#PrimaryButton:hover {
    background: #006cbe;
}
QPushButton#GhostButton {
    border: 1px solid #c4ccd8;
    background: #ffffff;
}
QPushButton#GhostButton:hover {
    background: #f1f4f8;
}
QPushButton#DangerButton {
    color: #ba1a1a;
    border: 1px solid #efc3c0;
}
QPushButton#DangerButton:hover {
    background: #ffefee;
}
QPushButton#PathDeleteButton {
    color: #ba1a1a;
    border: 1px solid #efc3c0;
    background: #ffffff;
    min-width: 96px;
    max-width: 96px;
    min-height: 40px;
    max-height: 40px;
    padding: 0px;
    text-align: center;
    font-weight: 700;
    font-size: 20px;
}
QPushButton#PathDeleteButton:hover {
    background: #ffefee;
}
QPushButton#PathRuleButton {
    color: #0f5fa8;
    border: 1px solid #b7d2f2;
    background: #ffffff;
    min-width: 96px;
    max-width: 96px;
    min-height: 40px;
    max-height: 40px;
    padding: 0px;
    text-align: center;
    font-weight: 700;
    font-size: 16px;
}
QPushButton#PathRuleButton:hover {
    background: #eef6ff;
}
#TopBar {
    background: #f9f9f9;
    border-bottom: 1px solid #d4dae4;
}
QFrame#TopSearchPanel {
    background: #ffffff;
    border: 1px solid #c8d0dc;
}
QLabel#TopSearchIcon {
    background: transparent;
    padding-left: 1px;
}
QLineEdit#TopSearchInput {
    background: transparent;
    border: none;
    padding: 0 0 0 2px;
}
QLineEdit#TopSearchInput:focus {
    background: transparent;
    border: none;
}
QLineEdit,
QComboBox,
QTextEdit,
QTableWidget {
    background: #ffffff;
    border: 1px solid #c8d0dc;
    border-radius: 0px;
    padding: 5px 8px;
}
QListWidget {
    background: #ffffff;
    border: 1px solid #c8d0dc;
    border-radius: 0px;
    padding: 0px;
}
QLineEdit:focus,
QComboBox:focus,
QTextEdit:focus,
QListWidget:focus,
QTableWidget:focus {
    border-color: #0078d7;
}
QListWidget#SettingsNav {
    background: #f8fafd;
    border: 1px solid #d7dfeb;
    padding: 8px;
    outline: none;
}
QListWidget#SettingsNav::item {
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    padding: 8px 10px;
    color: #2f3a4d;
}
QListWidget#SettingsNav::item:hover {
    background: #eaf2ff;
    border-left: 3px solid #8eb7e7;
    color: #17497f;
}
QListWidget#SettingsNav::item:selected {
    background: #f3f9ff;
    border-left: 3px solid #0078d7;
    color: #0f5fa8;
    font-weight: 600;
}
QLineEdit#SettingsSearchInput {
    background: #ffffff;
    border: 1px solid #c8d0dc;
    padding: 6px 10px;
}
QLineEdit#SettingsSearchInput:focus {
    border: 1px solid #0078d7;
}
QComboBox#SettingsLanguageCombo {
    background: #ffffff;
    border: 1px solid #c8d0dc;
    min-height: 30px;
    padding: 4px 10px;
}
QComboBox#SettingsLanguageCombo:hover {
    border-color: #9fb7d8;
}
QComboBox#SettingsLanguageCombo::drop-down {
    border: none;
    width: 22px;
    background: transparent;
}
QListWidget#LibraryPathList {
    background: #f8fafd;
    border: 1px solid #d7dfeb;
    padding: 0px;
}
QListWidget#LibraryPathList::item {
    border: none;
    background: transparent;
    margin: 1px 0px;
    padding: 0px;
}
QLabel#PathValueLabel {
    color: #4a5568;
    background: transparent;
    border: none;
    padding: 2px 8px 3px 8px;
}
QWidget#PathRow {
    background: transparent;
    border: none;
}
QWidget#PathRow {
    min-height: 40px;
}
QWidget#PathRow QLabel {
    background: transparent;
    border: none;
}
QLabel#PathValueLabel[pathFontPx="14"] { font-size: 14px; }
QLabel#PathValueLabel[pathFontPx="16"] { font-size: 16px; }
QLabel#PathValueLabel[pathFontPx="18"] { font-size: 18px; }
QLabel#PathValueLabel[pathFontPx="20"] { font-size: 20px; }
QLabel#PathValueLabel[pathFontPx="22"] { font-size: 22px; }
QLabel#PathValueLabel[pathFontPx="24"] { font-size: 24px; }
QProgressBar {
    border: 1px solid #c8d0dc;
    background: #ffffff;
    text-align: center;
    min-height: 18px;
}
QProgressBar::chunk {
    background: #0078d7;
}
#PageTitle {
    font-size: 46px;
    font-weight: 700;
}
#PageSubtitle {
    color: #6a7382;
    font-size: 13px;
    background: transparent;
    border: none;
}
#ViewTogglePanel {
    border: none;
    background: transparent;
}
QPushButton#ViewToggleButton {
    min-width: 32px;
    max-width: 32px;
    min-height: 28px;
    max-height: 28px;
    border: 1px solid transparent;
    border-left: 1px solid transparent;
    background: transparent;
    padding: 0;
    text-align: center;
}
QPushButton#ViewToggleButton:hover {
    background: #e7edf5;
    border: 1px solid #d2dbe8;
    border-left: 1px solid #d2dbe8;
}
QPushButton#ViewToggleButton:checked {
    background: transparent;
    border: 1px solid transparent;
    border-left: 1px solid transparent;
    color: #2e3848;
    font-weight: 400;
}
#BookCard {
    background: #ffffff;
    border: 1px solid #d6dde9;
}
#BookCard[variant="cover_only"] {
    background: #f7f7f7;
    border: 1px solid #cfd4dc;
}
#BookCard[variant="cover_only"][selected="true"] {
    background: #e6e9ee;
    border: 1px solid #8ea7c6;
}
#BookCover {
    background: #ffffff;
    color: #6b7280;
    border: none;
}
#BookTitle {
    font-size: 15px;
    font-weight: 700;
    background: transparent;
    border: none;
}
#BookMeta {
    color: #697286;
    font-size: 12px;
    background: transparent;
    border: none;
}
#BookStatus {
    color: #0f5fa8;
    font-size: 10px;
    font-weight: 700;
    background: #eaf3ff;
    border: 1px solid #bdd8fb;
    padding: 2px 4px;
}
#BookTags {
    color: #697286;
    font-size: 10px;
    border: 1px solid #d5dce7;
    padding: 1px 4px;
}
#AddCard {
    color: #677184;
    border: 1px dashed #c4cddd;
    background: #f6f8fb;
    font-size: 11px;
    font-weight: 600;
}
#LibraryMainPane {
    background: #ececec;
    border: 1px solid #d1d5dd;
}
QScrollArea#LibraryGridScroll {
    background: #ececec;
    border: none;
}
QWidget#LibraryGridContainer {
    background: #ececec;
}
#LibraryContentSplitter::handle {
    background: #d4d8e0;
}
#LibraryContentSplitter::handle:hover {
    background: #c0c6d2;
}
#LibraryDetailPanel {
    background: #f6f7f9;
    border: 1px solid #d5dae3;
}
#DetailEmpty {
    color: #6d7685;
    font-size: 12px;
}
#DetailCover {
    background: #ffffff;
    border: 1px solid #cfd6e1;
    color: #6d7685;
}
#DetailTitle {
    color: #1f2530;
    font-size: 16px;
    font-weight: 700;
}
#DetailMeta {
    color: #4a5568;
    font-size: 12px;
    background: transparent;
    border: none;
}
#DetailPath {
    color: #5b6474;
    font-size: 11px;
    background: transparent;
    border: none;
}
QScrollArea#DetailTextScroll {
    background: transparent;
    border: none;
}
QWidget#DetailTextContainer {
    background: transparent;
    border: none;
}
QLabel#DetailTextContent {
    color: #4a5568;
    font-size: 12px;
    background: transparent;
    border: none;
    padding: 0px;
}
QHeaderView::section {
    background: #eef2f7;
    border: none;
    border-right: 1px solid #dde4ef;
    border-bottom: 1px solid #dde4ef;
    padding: 8px;
    font-size: 11px;
    font-weight: 700;
}
QTableWidget {
    gridline-color: #e4e9f2;
}
QTableWidget::item {
    padding: 6px;
}
QMenu {
    background: #ffffff;
    border: 1px solid #cfd7e3;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px 6px 10px;
}
QMenu::item:selected {
    background: #eaf3ff;
    color: #0f5fa8;
}
QCheckBox::indicator {
    width: 34px;
    height: 18px;
    border: 1px solid #8f98a9;
    border-radius: 9px;
    background: #8f98a9;
}
QCheckBox::indicator:checked {
    border-color: #0078d7;
    background: #0078d7;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px 2px 2px 2px;
    border: none;
}
QScrollBar::handle:vertical {
    background: #bcc6d6;
    min-height: 36px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #9eabc0;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
    width: 0px;
    border: none;
    background: transparent;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 2px 2px 2px 2px;
    border: none;
}
QScrollBar::handle:horizontal {
    background: #bcc6d6;
    min-width: 36px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #9eabc0;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    height: 0px;
    width: 0px;
    border: none;
    background: transparent;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
}
"""

APP_STYLE = build_app_style(DEFAULT_FONT_STACK)

