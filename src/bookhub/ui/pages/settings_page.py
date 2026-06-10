from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFontDatabase, QFontMetrics
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr
from bookhub.library.models import DEFAULT_TEXT_PREVIEW_CHARS, TEXT_PREVIEW_CHAR_OPTIONS
from bookhub.ui.dialogs.text_rule_dialog import TextRuleDialog
from bookhub.ui.resources.layout_config import (
    CARD_SPACING_MAX,
    CARD_SPACING_MIN,
    COVER_SELECTED_BORDER_WIDTH_MAX,
    COVER_SELECTED_BORDER_WIDTH_MIN,
    DEFAULT_CARD_SPACING,
    DEFAULT_COVER_SELECTED_BORDER_COLOR,
    DEFAULT_COVER_SELECTED_BORDER_WIDTH,
    DEFAULT_TOPBAR_SEARCH_FONT_SIZE,
    TOPBAR_SEARCH_FONT_SIZE_MAX,
    TOPBAR_SEARCH_FONT_SIZE_MIN,
    normalize_cover_selected_border_color,
    normalize_cover_selected_border_width,
    normalize_card_spacing,
    normalize_topbar_search_font_size,
)


class SettingsPage(QWidget):
    language_changed = Signal(str)
    scan_on_startup_changed = Signal(bool)
    auto_scan_on_path_change_changed = Signal(bool)
    add_root_requested = Signal(str)
    remove_root_requested = Signal(str)
    add_comic_root_requested = Signal(str)
    remove_comic_root_requested = Signal(str)
    add_text_root_requested = Signal(str)
    remove_text_root_requested = Signal(str)
    manage_text_rules_requested = Signal(str, str)
    scan_library_requested = Signal()
    scan_comic_requested = Signal()
    scan_text_requested = Signal()
    scan_depth_changed = Signal(int)
    hash_strategy_changed = Signal(str)
    comic_placeholder_copy_enabled_changed = Signal(bool)
    comic_thumbnail_workers_changed = Signal(str)
    comic_view_mode_changed = Signal(str)
    comic_page_size_changed = Signal(int)
    auto_generate_comic_thumbnails_after_scan_changed = Signal(bool)
    card_spacing_changed = Signal(int)
    topbar_search_font_size_changed = Signal(int)
    cover_selected_border_width_changed = Signal(int)
    cover_selected_border_color_changed = Signal(str)
    text_preview_chars_changed = Signal(int)
    cleanup_library_thumbnails_requested = Signal()
    regenerate_library_thumbnails_requested = Signal()
    cleanup_comic_thumbnails_requested = Signal()
    regenerate_comic_thumbnails_requested = Signal()
    font_changed = Signal(str, str)
    reload_fonts_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._last_summary: dict[str, object] = {}
        self._current_roots: list[str] = []
        self._current_comic_roots: list[str] = []
        self._current_text_roots: list[str] = []
        self._text_rules_by_path: dict[str, str] = {}
        self._thumbnail_task_kind: str | None = None
        self._project_font_families: list[str] = []
        self._font_source: str = "system"
        self._cover_selected_border_color = DEFAULT_COVER_SELECTED_BORDER_COLOR

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        top = QHBoxLayout()
        self.app_title = QLabel("System Architect")
        self.app_title.setStyleSheet("font-size: 28px; font-weight: 700;")
        top.addWidget(self.app_title)
        top.addStretch(1)
        root.addLayout(top)

        shell = QHBoxLayout()
        shell.setSpacing(14)
        root.addLayout(shell, 1)

        self.nav = QListWidget()
        self.nav.setObjectName("SettingsNav")
        self.nav.setFixedWidth(210)
        self._nav_labels = [
            ("settings.nav.general", "General"),
            ("settings.nav.error_logs", "Error logs"),
        ]
        self.nav.addItems([label for _, label in self._nav_labels])
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(self._on_nav_changed)
        shell.addWidget(self.nav)

        self.content_stack = QStackedWidget()
        shell.addWidget(self.content_stack, 1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        self.title = QLabel("General Settings")
        self.title.setObjectName("PageTitle")
        content_layout.addWidget(self.title)

        startup = QFrame()
        startup.setObjectName("PageSection")
        startup_layout = QVBoxLayout(startup)
        startup_layout.setContentsMargins(14, 14, 14, 14)
        self.startup_label = QLabel("STARTUP OPTIONS")
        self.startup_label.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #6a7382;")
        startup_layout.addWidget(self.startup_label)
        self.launch_check = QCheckBox("Scan on startup")
        self.launch_check.setChecked(False)
        self.launch_check.stateChanged.connect(self._emit_scan_on_startup_changed)
        startup_layout.addWidget(self.launch_check)
        self.tray_check = QCheckBox("Auto scan when path changed")
        self.tray_check.setChecked(True)
        self.tray_check.stateChanged.connect(self._emit_auto_scan_on_path_change_changed)
        startup_layout.addWidget(self.tray_check)
        content_layout.addWidget(startup)

        lang = QFrame()
        lang.setObjectName("PageSection")
        lang_layout = QVBoxLayout(lang)
        lang_layout.setContentsMargins(14, 14, 14, 14)
        self.language_label = QLabel("Display language")
        lang_layout.addWidget(self.language_label)
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("SettingsLanguageCombo")
        self.language_combo.currentIndexChanged.connect(self._emit_language_changed)
        lang_layout.addWidget(self.language_combo)
        self.restart_hint = QLabel("Restart application to apply language changes.")
        self.restart_hint.setObjectName("PageSubtitle")
        lang_layout.addWidget(self.restart_hint)
        content_layout.addWidget(lang)

        font_box = QFrame()
        font_box.setObjectName("PageSection")
        font_layout = QVBoxLayout(font_box)
        font_layout.setContentsMargins(14, 14, 14, 14)

        self.font_title = QLabel("Font")
        self.font_title.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #6a7382;")
        font_layout.addWidget(self.font_title)

        font_row = QHBoxLayout()
        font_row.setSpacing(10)

        self.font_source_label = QLabel("Font source")
        font_row.addWidget(self.font_source_label)
        self.font_source_combo = QComboBox()
        self.font_source_combo.setObjectName("SettingsLanguageCombo")
        self._set_font_source_options()
        self.font_source_combo.currentIndexChanged.connect(self._on_font_source_changed)
        font_row.addWidget(self.font_source_combo, 1)

        self.font_family_label = QLabel("Font family")
        font_row.addWidget(self.font_family_label)
        self.font_family_combo = QComboBox()
        self.font_family_combo.setObjectName("SettingsLanguageCombo")
        self.font_family_combo.currentIndexChanged.connect(self._emit_font_changed)
        font_row.addWidget(self.font_family_combo, 1)

        self.reload_fonts_btn = QPushButton("Reload Fonts")
        self.reload_fonts_btn.setObjectName("GhostButton")
        self.reload_fonts_btn.clicked.connect(self._on_reload_fonts_clicked)
        font_row.addWidget(self.reload_fonts_btn)

        font_layout.addLayout(font_row)

        self.font_preview_label = QLabel("Preview")
        self.font_preview_label.setObjectName("PageSubtitle")
        self.font_preview_label.setWordWrap(True)
        font_layout.addWidget(self.font_preview_label)

        content_layout.addWidget(font_box)

        library_box = QFrame()
        library_box.setObjectName("PageSection")
        library_layout = QVBoxLayout(library_box)
        library_layout.setContentsMargins(14, 14, 14, 14)
        row = QHBoxLayout()
        self.library_label = QLabel("LIBRARY FOLDERS")
        self.library_label.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #6a7382;")

        row.addWidget(self.library_label, 1)

        self.add_path_button = QPushButton("+ Add Path")
        self.add_path_button.setObjectName("PrimaryButton")
        self.add_path_button.clicked.connect(self._pick_folder)
        row.addWidget(self.add_path_button)
        library_layout.addLayout(row)

        self.folders = QListWidget()
        self.folders.setObjectName("LibraryPathList")
        self.folders.setSpacing(4)
        self.folders.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.folders.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.folders.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.folders.setViewportMargins(0, 0, 0, 0)
        library_layout.addWidget(self.folders)

        comic_row = QHBoxLayout()
        self.comic_label = QLabel("COMIC FOLDERS")
        self.comic_label.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #6a7382;")
        self.add_comic_path_button = QPushButton("+ Add Comic Path")
        self.add_comic_path_button.setObjectName("PrimaryButton")
        self.add_comic_path_button.clicked.connect(self._pick_comic_folder)
        comic_row.addWidget(self.comic_label, 1)
        comic_row.addWidget(self.add_comic_path_button)
        library_layout.addLayout(comic_row)

        self.comic_folders = QListWidget()
        self.comic_folders.setObjectName("LibraryPathList")
        self.comic_folders.setSpacing(4)
        self.comic_folders.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.comic_folders.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.comic_folders.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.comic_folders.setViewportMargins(0, 0, 0, 0)
        library_layout.addWidget(self.comic_folders)

        text_row = QHBoxLayout()
        self.text_label = QLabel("TEXT NOVEL FOLDERS")
        self.text_label.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #6a7382;")
        self.add_text_path_button = QPushButton("+ Add Text Path")
        self.add_text_path_button.setObjectName("PrimaryButton")
        self.add_text_path_button.clicked.connect(self._pick_text_folder)
        text_row.addWidget(self.text_label, 1)
        text_row.addWidget(self.add_text_path_button)
        library_layout.addLayout(text_row)

        self.text_folders = QListWidget()
        self.text_folders.setObjectName("LibraryPathList")
        self.text_folders.setSpacing(4)
        self.text_folders.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_folders.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.text_folders.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.text_folders.setViewportMargins(0, 0, 0, 0)
        library_layout.addWidget(self.text_folders)

        options_row = QHBoxLayout()
        options_row.setSpacing(10)
        self.scan_depth_label = QLabel("Scan depth")
        options_row.addWidget(self.scan_depth_label)
        self.scan_depth_combo = QComboBox()
        self.scan_depth_combo.setObjectName("SettingsLanguageCombo")
        self._set_scan_depth_options()
        self.scan_depth_combo.currentIndexChanged.connect(self._emit_scan_depth_changed)
        options_row.addWidget(self.scan_depth_combo, 1)

        self.hash_strategy_label = QLabel("Missed hash matching")
        options_row.addWidget(self.hash_strategy_label)
        self.hash_strategy_combo = QComboBox()
        self.hash_strategy_combo.setObjectName("SettingsLanguageCombo")
        self._set_hash_strategy_options()
        self.hash_strategy_combo.currentIndexChanged.connect(self._emit_hash_strategy_changed)
        options_row.addWidget(self.hash_strategy_combo, 1)

        self.card_spacing_label = QLabel("Card spacing")
        options_row.addWidget(self.card_spacing_label)
        self.card_spacing_combo = QComboBox()
        self.card_spacing_combo.setObjectName("SettingsLanguageCombo")
        for spacing in range(CARD_SPACING_MIN, CARD_SPACING_MAX + 1, 2):
            self.card_spacing_combo.addItem(f"{spacing}px", spacing)
        self.card_spacing_combo.currentIndexChanged.connect(self._emit_card_spacing_changed)
        options_row.addWidget(self.card_spacing_combo, 1)

        self.topbar_search_font_size_label = QLabel("Search font size")
        options_row.addWidget(self.topbar_search_font_size_label)
        self.topbar_search_font_size_combo = QComboBox()
        self.topbar_search_font_size_combo.setObjectName("SettingsLanguageCombo")
        for size in range(TOPBAR_SEARCH_FONT_SIZE_MIN, TOPBAR_SEARCH_FONT_SIZE_MAX + 1):
            self.topbar_search_font_size_combo.addItem(f"{size}px", size)
        self.topbar_search_font_size_combo.currentIndexChanged.connect(
            self._emit_topbar_search_font_size_changed
        )
        options_row.addWidget(self.topbar_search_font_size_combo, 1)

        self.text_preview_chars_label = QLabel("Text preview chars")
        options_row.addWidget(self.text_preview_chars_label)
        self.text_preview_chars_combo = QComboBox()
        self.text_preview_chars_combo.setObjectName("SettingsLanguageCombo")
        for size in TEXT_PREVIEW_CHAR_OPTIONS:
            self.text_preview_chars_combo.addItem(f"{size}", int(size))
        self.text_preview_chars_combo.currentIndexChanged.connect(self._emit_text_preview_chars_changed)
        options_row.addWidget(self.text_preview_chars_combo, 1)
        library_layout.addLayout(options_row)

        cover_border_row = QHBoxLayout()
        cover_border_row.setSpacing(10)
        self.cover_selected_border_title = QLabel("Cover selected border")
        cover_border_row.addWidget(self.cover_selected_border_title)
        self.cover_selected_border_width_label = QLabel("Width (px)")
        cover_border_row.addWidget(self.cover_selected_border_width_label)
        self.cover_selected_border_width_spin = QSpinBox()
        self.cover_selected_border_width_spin.setRange(
            COVER_SELECTED_BORDER_WIDTH_MIN,
            COVER_SELECTED_BORDER_WIDTH_MAX,
        )
        self.cover_selected_border_width_spin.setValue(DEFAULT_COVER_SELECTED_BORDER_WIDTH)
        self.cover_selected_border_width_spin.valueChanged.connect(self._emit_cover_selected_border_width_changed)
        cover_border_row.addWidget(self.cover_selected_border_width_spin)
        self.cover_selected_border_color_label = QLabel("Color")
        cover_border_row.addWidget(self.cover_selected_border_color_label)
        self.cover_selected_border_color_btn = QPushButton("Pick Color")
        self.cover_selected_border_color_btn.setObjectName("GhostButton")
        self.cover_selected_border_color_btn.clicked.connect(self._pick_cover_selected_border_color)
        cover_border_row.addWidget(self.cover_selected_border_color_btn)
        self.cover_selected_border_color_preview = QLabel("")
        self.cover_selected_border_color_preview.setObjectName("PathValueLabel")
        self.cover_selected_border_color_preview.setAlignment(Qt.AlignCenter)
        self.cover_selected_border_color_preview.setFixedWidth(100)
        cover_border_row.addWidget(self.cover_selected_border_color_preview)
        cover_border_row.addStretch(1)
        library_layout.addLayout(cover_border_row)

        comic_perf_row = QHBoxLayout()
        comic_perf_row.setSpacing(10)
        self.comic_placeholder_copy_check = QCheckBox("Comic scan: copy first image as placeholder")
        self.comic_placeholder_copy_check.setChecked(True)
        self.comic_placeholder_copy_check.stateChanged.connect(self._emit_comic_placeholder_copy_enabled_changed)
        comic_perf_row.addWidget(self.comic_placeholder_copy_check, 2)
        self.auto_comic_thumb_check = QCheckBox("Auto generate comic thumbnails after scan")
        self.auto_comic_thumb_check.setChecked(True)
        self.auto_comic_thumb_check.stateChanged.connect(self._emit_auto_generate_comic_thumbnails_after_scan_changed)
        comic_perf_row.addWidget(self.auto_comic_thumb_check, 2)
        self.comic_thumbnail_workers_label = QLabel("Comic thumbnail workers")
        comic_perf_row.addWidget(self.comic_thumbnail_workers_label)
        self.comic_thumbnail_workers_combo = QComboBox()
        self.comic_thumbnail_workers_combo.setObjectName("SettingsLanguageCombo")
        self._set_comic_thumbnail_worker_options()
        self.comic_thumbnail_workers_combo.currentIndexChanged.connect(self._emit_comic_thumbnail_workers_changed)
        comic_perf_row.addWidget(self.comic_thumbnail_workers_combo, 1)
        self.comic_view_mode_label = QLabel("Comic view mode")
        comic_perf_row.addWidget(self.comic_view_mode_label)
        self.comic_view_mode_combo = QComboBox()
        self.comic_view_mode_combo.setObjectName("SettingsLanguageCombo")
        self.comic_view_mode_combo.addItem("Waterfall", "waterfall")
        self.comic_view_mode_combo.addItem("Pagination", "pagination")
        self.comic_view_mode_combo.currentIndexChanged.connect(self._emit_comic_view_mode_changed)
        comic_perf_row.addWidget(self.comic_view_mode_combo, 1)
        self.comic_page_size_label = QLabel("Comic page size")
        comic_perf_row.addWidget(self.comic_page_size_label)
        self.comic_page_size_combo = QComboBox()
        self.comic_page_size_combo.setObjectName("SettingsLanguageCombo")
        for page_size in (24, 48, 72, 96):
            self.comic_page_size_combo.addItem(str(page_size), page_size)
        self.comic_page_size_combo.currentIndexChanged.connect(self._emit_comic_page_size_changed)
        comic_perf_row.addWidget(self.comic_page_size_combo, 1)
        library_layout.addLayout(comic_perf_row)

        self.formats_hint = QLabel(
            "Library supports PDF/EPUB. Text Novel roots support TXT with configurable preview extraction."
        )
        self.formats_hint.setObjectName("PageSubtitle")
        self.formats_hint.setWordWrap(True)
        library_layout.addWidget(self.formats_hint)

        self.scan_summary = QLabel("")
        self.scan_summary.setObjectName("PageSubtitle")
        self.scan_summary.setWordWrap(True)
        library_layout.addWidget(self.scan_summary)

        scan_row = QHBoxLayout()
        scan_row.setSpacing(8)
        self.scan_library_btn = QPushButton("Scan Library Folders")
        self.scan_library_btn.setObjectName("PrimaryButton")
        self.scan_library_btn.clicked.connect(self.scan_library_requested.emit)
        scan_row.addWidget(self.scan_library_btn)
        self.scan_comic_btn = QPushButton("Scan Comic Folders")
        self.scan_comic_btn.setObjectName("PrimaryButton")
        self.scan_comic_btn.clicked.connect(self.scan_comic_requested.emit)
        scan_row.addWidget(self.scan_comic_btn)
        self.scan_text_btn = QPushButton("Scan Text Novel Folders")
        self.scan_text_btn.setObjectName("PrimaryButton")
        self.scan_text_btn.clicked.connect(self.scan_text_requested.emit)
        scan_row.addWidget(self.scan_text_btn)
        scan_row.addStretch(1)
        library_layout.addLayout(scan_row)

        library_thumb_row = QHBoxLayout()
        library_thumb_row.setSpacing(8)
        self.cleanup_library_thumbnails_btn = QPushButton("Clean Library Thumbnails")
        self.cleanup_library_thumbnails_btn.setObjectName("GhostButton")
        self.cleanup_library_thumbnails_btn.clicked.connect(self.cleanup_library_thumbnails_requested.emit)
        library_thumb_row.addWidget(self.cleanup_library_thumbnails_btn)
        self.regenerate_library_thumbnails_btn = QPushButton("Regenerate Library Thumbnails")
        self.regenerate_library_thumbnails_btn.setObjectName("GhostButton")
        self.regenerate_library_thumbnails_btn.clicked.connect(self.regenerate_library_thumbnails_requested.emit)
        library_thumb_row.addWidget(self.regenerate_library_thumbnails_btn)
        library_thumb_row.addStretch(1)
        library_layout.addLayout(library_thumb_row)

        comic_thumb_row = QHBoxLayout()
        comic_thumb_row.setSpacing(8)
        self.cleanup_comic_thumbnails_btn = QPushButton("Clean Comic Thumbnails")
        self.cleanup_comic_thumbnails_btn.setObjectName("GhostButton")
        self.cleanup_comic_thumbnails_btn.clicked.connect(self.cleanup_comic_thumbnails_requested.emit)
        comic_thumb_row.addWidget(self.cleanup_comic_thumbnails_btn)
        self.regenerate_comic_thumbnails_btn = QPushButton("Regenerate Comic Thumbnails")
        self.regenerate_comic_thumbnails_btn.setObjectName("GhostButton")
        self.regenerate_comic_thumbnails_btn.clicked.connect(self.regenerate_comic_thumbnails_requested.emit)
        comic_thumb_row.addWidget(self.regenerate_comic_thumbnails_btn)
        comic_thumb_row.addStretch(1)
        library_layout.addLayout(comic_thumb_row)

        self.thumbnail_task_panel = QFrame()
        self.thumbnail_task_panel.setObjectName("PageSection")
        self.thumbnail_task_panel.hide()
        panel_layout = QHBoxLayout(self.thumbnail_task_panel)
        panel_layout.setContentsMargins(10, 8, 10, 8)
        panel_layout.setSpacing(10)
        self.thumbnail_task_progress = QProgressBar()
        self.thumbnail_task_progress.setRange(0, 100)
        self.thumbnail_task_progress.setValue(0)
        panel_layout.addWidget(self.thumbnail_task_progress, 1)
        self.thumbnail_task_status = QLabel("")
        self.thumbnail_task_status.setObjectName("PageSubtitle")
        panel_layout.addWidget(self.thumbnail_task_status)
        library_layout.addWidget(self.thumbnail_task_panel)

        content_layout.addWidget(library_box)

        self._scan_buttons: dict[str, QPushButton] = {
            "library": self.scan_library_btn,
            "comic": self.scan_comic_btn,
            "text": self.scan_text_btn,
        }
        self._thumbnail_buttons: dict[str, dict[str, QPushButton]] = {
            "library": {
                "cleanup": self.cleanup_library_thumbnails_btn,
                "regenerate": self.regenerate_library_thumbnails_btn,
            },
            "comic": {
                "cleanup": self.cleanup_comic_thumbnails_btn,
                "regenerate": self.regenerate_comic_thumbnails_btn,
            },
        }
        content_layout.addStretch(1)

        self.content_stack.addWidget(content)

        self.error_logs_page = QFrame()
        self.error_logs_page.setObjectName("PageSection")
        error_logs_layout = QVBoxLayout(self.error_logs_page)
        error_logs_layout.setContentsMargins(18, 18, 18, 18)
        error_logs_layout.setSpacing(12)
        self.error_logs_title = QLabel("Error logs")
        self.error_logs_title.setObjectName("PageTitle")
        error_logs_layout.addWidget(self.error_logs_title)
        self.error_logs_hint = QLabel("Startup/scan conflict logs are listed below.")
        self.error_logs_hint.setObjectName("PageSubtitle")
        self.error_logs_hint.setWordWrap(True)
        error_logs_layout.addWidget(self.error_logs_hint)
        self.error_logs_text = QTextEdit()
        self.error_logs_text.setObjectName("ErrorLogsText")
        self.error_logs_text.setReadOnly(True)
        error_logs_layout.addWidget(self.error_logs_text, 1)
        self.content_stack.addWidget(self.error_logs_page)

        self._set_language_options()
        self.set_language_selection("en")
        self.retranslate_ui()
        self.set_scan_summary({})
        self._on_nav_changed(self.nav.currentRow())

    def set_language_selection(self, language_code: str) -> None:
        index = self.language_combo.findData(language_code)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)

    def set_scan_on_startup(self, enabled: bool) -> None:
        self.launch_check.blockSignals(True)
        self.launch_check.setChecked(bool(enabled))
        self.launch_check.blockSignals(False)

    def set_auto_scan_on_path_change(self, enabled: bool) -> None:
        self.tray_check.blockSignals(True)
        self.tray_check.setChecked(bool(enabled))
        self.tray_check.blockSignals(False)

    def set_library_roots(self, paths: list[str]) -> None:
        self._current_roots = list(paths)
        self.folders.clear()
        for path in self._current_roots:
            self._append_path_item(path)

    def set_comic_roots(self, paths: list[str]) -> None:
        self._current_comic_roots = list(paths)
        self.comic_folders.clear()
        for path in self._current_comic_roots:
            self._append_comic_path_item(path)

    def set_text_roots(self, paths: list[str]) -> None:
        self._current_text_roots = list(paths)
        self._text_rules_by_path = {path: self._text_rules_by_path.get(path, "{}") for path in self._current_text_roots}
        self.text_folders.clear()
        for path in self._current_text_roots:
            self._append_text_path_item(path)

    def set_text_roots_with_rules(self, rows: list[dict[str, str]]) -> None:
        normalized: list[str] = []
        mapping: dict[str, str] = {}
        for item in rows:
            path = str(item.get("path") or "").strip()
            if not path:
                continue
            normalized.append(path)
            mapping[path] = str(item.get("rules_json") or "{}")
        self._text_rules_by_path = mapping
        self.set_text_roots(normalized)

    def set_scan_depth(self, depth: int) -> None:
        index = self.scan_depth_combo.findData(depth)
        self.scan_depth_combo.blockSignals(True)
        self.scan_depth_combo.setCurrentIndex(index if index >= 0 else 1)
        self.scan_depth_combo.blockSignals(False)

    def set_hash_strategy(self, strategy: str) -> None:
        index = self.hash_strategy_combo.findData(strategy)
        self.hash_strategy_combo.blockSignals(True)
        self.hash_strategy_combo.setCurrentIndex(index if index >= 0 else 0)
        self.hash_strategy_combo.blockSignals(False)

    def set_comic_placeholder_copy_enabled(self, enabled: bool) -> None:
        self.comic_placeholder_copy_check.blockSignals(True)
        self.comic_placeholder_copy_check.setChecked(bool(enabled))
        self.comic_placeholder_copy_check.blockSignals(False)

    def set_comic_thumbnail_workers(self, value: str) -> None:
        raw = str(value or "auto").strip().lower()
        index = self.comic_thumbnail_workers_combo.findData(raw)
        if index < 0:
            index = self.comic_thumbnail_workers_combo.findData("auto")
        if index < 0:
            index = 0
        self.comic_thumbnail_workers_combo.blockSignals(True)
        self.comic_thumbnail_workers_combo.setCurrentIndex(index)
        self.comic_thumbnail_workers_combo.blockSignals(False)

    def set_comic_view_mode(self, mode: str) -> None:
        normalized = "pagination" if str(mode or "").strip().lower() == "pagination" else "waterfall"
        index = self.comic_view_mode_combo.findData(normalized)
        if index < 0:
            index = self.comic_view_mode_combo.findData("waterfall")
        if index < 0:
            index = 0
        self.comic_view_mode_combo.blockSignals(True)
        self.comic_view_mode_combo.setCurrentIndex(index)
        self.comic_view_mode_combo.blockSignals(False)
        self._update_comic_page_size_enabled()

    def set_comic_page_size(self, size: int) -> None:
        try:
            value = int(size)
        except (TypeError, ValueError):
            value = 48
        if value not in {24, 48, 72, 96}:
            value = 48
        index = self.comic_page_size_combo.findData(value)
        if index < 0:
            index = self.comic_page_size_combo.findData(48)
        if index < 0:
            index = 0
        self.comic_page_size_combo.blockSignals(True)
        self.comic_page_size_combo.setCurrentIndex(index)
        self.comic_page_size_combo.blockSignals(False)
        self._update_comic_page_size_enabled()

    def set_auto_generate_comic_thumbnails_after_scan(self, enabled: bool) -> None:
        self.auto_comic_thumb_check.blockSignals(True)
        self.auto_comic_thumb_check.setChecked(bool(enabled))
        self.auto_comic_thumb_check.blockSignals(False)

    def set_card_spacing(self, spacing: int) -> None:
        value = normalize_card_spacing(spacing)
        index = self.card_spacing_combo.findData(value)
        if index < 0:
            index = self.card_spacing_combo.findData(DEFAULT_CARD_SPACING)
        if index < 0:
            index = 0
        self.card_spacing_combo.blockSignals(True)
        self.card_spacing_combo.setCurrentIndex(index)
        self.card_spacing_combo.blockSignals(False)

    def set_topbar_search_font_size(self, size: int) -> None:
        value = normalize_topbar_search_font_size(size)
        index = self.topbar_search_font_size_combo.findData(value)
        if index < 0:
            index = self.topbar_search_font_size_combo.findData(DEFAULT_TOPBAR_SEARCH_FONT_SIZE)
        if index < 0:
            index = 0
        self.topbar_search_font_size_combo.blockSignals(True)
        self.topbar_search_font_size_combo.setCurrentIndex(index)
        self.topbar_search_font_size_combo.blockSignals(False)

    def set_cover_selected_border_width(self, width: int) -> None:
        value = normalize_cover_selected_border_width(width)
        self.cover_selected_border_width_spin.blockSignals(True)
        self.cover_selected_border_width_spin.setValue(value)
        self.cover_selected_border_width_spin.blockSignals(False)

    def set_cover_selected_border_color(self, color: str) -> None:
        normalized = normalize_cover_selected_border_color(color)
        self._cover_selected_border_color = normalized
        self._refresh_cover_selected_border_color_preview()

    def set_text_preview_chars(self, size: int) -> None:
        index = self.text_preview_chars_combo.findData(int(size))
        if index < 0:
            index = self.text_preview_chars_combo.findData(DEFAULT_TEXT_PREVIEW_CHARS)
        if index < 0:
            index = 0
        self.text_preview_chars_combo.blockSignals(True)
        self.text_preview_chars_combo.setCurrentIndex(index)
        self.text_preview_chars_combo.blockSignals(False)

    def set_available_project_fonts(self, families: list[str]) -> None:
        self._project_font_families = sorted({str(item).strip() for item in families if str(item).strip()})
        current = str(self.font_family_combo.currentData() or "")
        self._rebuild_font_family_options(preferred_family=current)

    def set_font_selection(self, source: str, family: str) -> None:
        source_value = "project" if source == "project" else "system"
        source_index = self.font_source_combo.findData(source_value)
        self.font_source_combo.blockSignals(True)
        self.font_source_combo.setCurrentIndex(source_index if source_index >= 0 else 0)
        self.font_source_combo.blockSignals(False)
        self._font_source = source_value
        self._rebuild_font_family_options(preferred_family=family)

    def set_scan_summary(self, summary: dict[str, object]) -> None:
        self._last_summary = dict(summary)
        added_count = int(summary.get("added_count", 0) or 0)
        ignored = int(summary.get("ignored_unsupported", 0) or 0)
        removed_missing_total = int(summary.get("removed_missing_count", 0) or 0)
        removed_missing_books = int(summary.get("removed_missing_book_count", 0) or 0)
        removed_missing_comics = int(summary.get("removed_missing_comic_count", 0) or 0)
        conflicts = summary.get("name_conflicts", [])
        conflict_count = len(conflicts) if isinstance(conflicts, list) else 0
        updated_at = str(summary.get("updated_at") or tr("settings.summary.never", "never"))
        scope = str(summary.get("scope") or "all")
        self.scan_summary.setText(
            tr(
                "settings.scan_summary_template",
                "Last scan: {updated_at}\nScope: {scope} | Added: {added} | Ignored unsupported: {ignored} | "
                "Name conflicts: {conflicts}\nRemoved missing: {removed_total} (library/text: {removed_books}, comic: {removed_comics})",
            ).format(
                updated_at=updated_at,
                scope=scope,
                added=added_count,
                ignored=ignored,
                conflicts=conflict_count,
                removed_total=removed_missing_total,
                removed_books=removed_missing_books,
                removed_comics=removed_missing_comics,
            )
        )
        text_added = int(summary.get("text_added_count", 0) or 0)
        text_updated = int(summary.get("text_updated_count", 0) or 0)
        text_scanned = int(summary.get("text_scanned_files", 0) or 0)
        text_suffix = tr(
            "settings.text.scan_summary",
            "\nText Novel - scanned:{scanned} added:{added} updated:{updated}",
        ).format(scanned=text_scanned, added=text_added, updated=text_updated)
        self.scan_summary.setText(self.scan_summary.text() + text_suffix)
        comic_placeholder_copied = int(summary.get("comic_placeholder_copied_count", 0) or 0)
        comic_thumbnail_enqueued = int(summary.get("comic_thumbnail_enqueued_count", 0) or 0)
        comic_workers_used = int(summary.get("comic_thumbnail_workers_used", 0) or 0)
        comic_large_downscaled = int(summary.get("comic_large_image_downscaled_count", 0) or 0)
        comic_perf_suffix = tr(
            "settings.comic.scan_perf_summary",
            "\nComic - placeholder copied:{copied} queued thumbnails:{queued} workers:{workers} large-image downscaled:{downscaled}",
        ).format(
            copied=comic_placeholder_copied,
            queued=comic_thumbnail_enqueued,
            workers=comic_workers_used,
            downscaled=comic_large_downscaled,
        )
        self.scan_summary.setText(self.scan_summary.text() + comic_perf_suffix)
        warnings = summary.get("warnings", [])
        if isinstance(warnings, list):
            pdf_warning = next(
                (item for item in warnings if isinstance(item, dict) and str(item.get("code") or "") == "pdf_backend_unavailable"),
                None,
            )
            if isinstance(pdf_warning, dict):
                skipped_count = int(pdf_warning.get("count", 0) or 0)
                warning_suffix = tr(
                    "settings.scan_warning_pdf_backend",
                    "\nPDF backend unavailable, skipped metadata/thumbnail processing ({count} files).",
                ).format(count=skipped_count)
                self.scan_summary.setText(self.scan_summary.text() + warning_suffix)
        thumb_task = summary.get("thumbnail_task")
        if isinstance(thumb_task, dict):
            task_kind = str(thumb_task.get("task_kind") or "")
            task_scope = str(thumb_task.get("task_scope") or "library")
            total = int(thumb_task.get("total", 0) or 0)
            succeeded = int(thumb_task.get("succeeded", 0) or 0)
            failed = int(thumb_task.get("failed", 0) or 0)
            skipped = int(thumb_task.get("skipped", 0) or 0)
            suffix = tr(
                "settings.thumb.summary",
                "\nThumbnail task({scope}/{kind}) - total:{total} success:{succeeded} skipped:{skipped} failed:{failed}",
            ).format(
                scope=task_scope,
                kind=task_kind,
                total=total,
                succeeded=succeeded,
                skipped=skipped,
                failed=failed,
            )
            self.scan_summary.setText(self.scan_summary.text() + suffix)

    def set_scan_running(self, running: bool, scope: str = "all") -> None:
        target_scopes = {"library", "comic", "text"} if scope == "all" else {scope}
        for button_scope, button in self._scan_buttons.items():
            if button_scope in target_scopes:
                button.setEnabled(not running)
        if running:
            for target_scope in target_scopes:
                button = self._scan_buttons.get(target_scope)
                if button is None:
                    continue
                button.setText(
                    tr(
                        f"settings.scan_running.{target_scope}",
                        f"Scanning {target_scope} folders...",
                    )
                )
        else:
            self._update_scan_button_texts()

    def _update_scan_button_texts(self) -> None:
        self.scan_library_btn.setText(tr("settings.scan.library", "Scan Library Folders"))
        self.scan_comic_btn.setText(tr("settings.scan.comic", "Scan Comic Folders"))
        self.scan_text_btn.setText(tr("settings.scan.text", "Scan Text Novel Folders"))

    def _update_thumbnail_button_texts(self) -> None:
        self.cleanup_library_thumbnails_btn.setText(tr("settings.thumb.library.clean", "Clean Library Thumbnails"))
        self.regenerate_library_thumbnails_btn.setText(
            tr("settings.thumb.library.regenerate", "Regenerate Library Thumbnails")
        )
        self.cleanup_comic_thumbnails_btn.setText(tr("settings.thumb.comic.clean", "Clean Comic Thumbnails"))
        self.regenerate_comic_thumbnails_btn.setText(
            tr("settings.thumb.comic.regenerate", "Regenerate Comic Thumbnails")
        )

    def retranslate_ui(self) -> None:
        for idx, (key, fallback) in enumerate(self._nav_labels):
            item = self.nav.item(idx)
            if item is not None:
                item.setText(tr(key, fallback))
        self.app_title.setText(tr("settings.app_title", "System Architect"))
        self.title.setText(tr("settings.title", "General Settings"))
        self.startup_label.setText(tr("settings.startup_options", "Startup Options"))
        self.launch_check.setText(tr("settings.scan_on_startup", "Scan on startup"))
        self.tray_check.setText(tr("settings.auto_scan_on_path_change", "Auto scan when path changed"))
        self.language_label.setText(tr("settings.display_language", "Display language"))
        self.library_label.setText(tr("settings.library_folders", "Library Folders"))
        self.add_path_button.setText(tr("settings.add_path", "+ Add Path"))
        self.comic_label.setText(tr("settings.comic_folders", "Comic Folders"))
        self.add_comic_path_button.setText(tr("settings.add_comic_path", "+ Add Comic Path"))
        self.text_label.setText(tr("settings.text_folders", "Text Novel Folders"))
        self.add_text_path_button.setText(tr("settings.add_text_path", "+ Add Text Path"))
        self.restart_hint.setText(tr("settings.restart_hint", "Restart application to apply language changes."))
        self.scan_depth_label.setText(tr("settings.scan_depth", "Scan depth"))
        self.hash_strategy_label.setText(tr("settings.hash_strategy", "Missed hash matching"))
        self.card_spacing_label.setText(tr("settings.card_spacing", "Card spacing"))
        self.topbar_search_font_size_label.setText(tr("settings.topbar_search_font_size", "Search font size"))
        self.cover_selected_border_title.setText(tr("settings.cover_selected_border", "Cover selected border"))
        self.cover_selected_border_width_label.setText(tr("settings.cover_selected_border.width", "Width (px)"))
        self.cover_selected_border_color_label.setText(tr("settings.cover_selected_border.color", "Color"))
        self.cover_selected_border_color_btn.setText(tr("settings.cover_selected_border.pick", "Pick Color"))
        self.text_preview_chars_label.setText(tr("settings.text_preview_chars", "Text preview chars"))
        self.comic_placeholder_copy_check.setText(
            tr("settings.comic.placeholder_copy", "Comic scan: copy first image as placeholder")
        )
        self.auto_comic_thumb_check.setText(
            tr("settings.comic.auto_thumb_after_scan", "Auto generate comic thumbnails after scan")
        )
        self.comic_thumbnail_workers_label.setText(
            tr("settings.comic.thumbnail_workers", "Comic thumbnail workers")
        )
        self.comic_view_mode_label.setText(
            tr("settings.comic.view_mode", "Comic view mode")
        )
        self.comic_page_size_label.setText(
            tr("settings.comic.page_size", "Comic page size")
        )
        self.comic_view_mode_combo.blockSignals(True)
        self.comic_view_mode_combo.setItemText(0, tr("settings.comic.view_mode.waterfall", "Waterfall"))
        self.comic_view_mode_combo.setItemText(1, tr("settings.comic.view_mode.pagination", "Pagination"))
        self.comic_view_mode_combo.blockSignals(False)
        self.font_title.setText(tr("settings.font.title", "Font"))
        self.font_source_label.setText(tr("settings.font.source", "Font source"))
        self.font_family_label.setText(tr("settings.font.family", "Font family"))
        self.reload_fonts_btn.setText(tr("settings.font.reload", "Reload Fonts"))
        self.font_preview_label.setText(
            tr("settings.font.preview", "Preview: The quick brown fox jumps over the lazy dog 你好，世界")
        )
        self._update_scan_button_texts()
        self._update_thumbnail_button_texts()
        self.formats_hint.setText(
            tr(
                "settings.formats_hint",
                "Library supports PDF/EPUB. Text Novel roots support TXT with configurable preview extraction.",
            )
        )
        if self._thumbnail_task_kind:
            self.thumbnail_task_status.setText(tr("settings.thumb.done", "Task completed"))
        self.set_library_roots(self._current_roots)
        self.set_comic_roots(self._current_comic_roots)
        self.set_text_roots(self._current_text_roots)
        self.set_text_preview_chars(int(self.text_preview_chars_combo.currentData() or DEFAULT_TEXT_PREVIEW_CHARS))
        self._set_language_options()
        self._set_scan_depth_options()
        self._set_hash_strategy_options()
        self._set_font_source_options()
        self._set_comic_thumbnail_worker_options()
        self._update_comic_page_size_enabled()
        self._refresh_cover_selected_border_color_preview()
        self.set_scan_summary(self._last_summary)

    def _set_language_options(self) -> None:
        current = self.language_combo.currentData()
        self.language_combo.blockSignals(True)
        self.language_combo.clear()
        self.language_combo.addItem(tr("settings.lang.english", "English"), "en")
        self.language_combo.addItem(tr("settings.lang.zh_cn", "Chinese (Simplified)"), "zh-cn")
        index = self.language_combo.findData(current or "en")
        self.language_combo.setCurrentIndex(index if index >= 0 else 0)
        self.language_combo.blockSignals(False)

    def _set_scan_depth_options(self) -> None:
        current = self.scan_depth_combo.currentData()
        self.scan_depth_combo.blockSignals(True)
        self.scan_depth_combo.clear()
        self.scan_depth_combo.addItem(tr("settings.scan_depth.option.1", "1 - Root only"), 1)
        self.scan_depth_combo.addItem(tr("settings.scan_depth.option.2", "2 - Include child folders"), 2)
        self.scan_depth_combo.addItem(tr("settings.scan_depth.option.3", "3 - Include grandchild folders"), 3)
        index = self.scan_depth_combo.findData(current if current is not None else 2)
        self.scan_depth_combo.setCurrentIndex(index if index >= 0 else 1)
        self.scan_depth_combo.blockSignals(False)

    def _set_hash_strategy_options(self) -> None:
        current = self.hash_strategy_combo.currentData()
        self.hash_strategy_combo.blockSignals(True)
        self.hash_strategy_combo.clear()
        self.hash_strategy_combo.addItem(
            tr("settings.hash.option.size_mtime", "File size + modified time"),
            "size_mtime",
        )
        self.hash_strategy_combo.addItem(
            tr("settings.hash.option.sha256", "SHA-256 full file"),
            "sha256",
        )
        self.hash_strategy_combo.addItem(
            tr("settings.hash.option.quick", "Quick hash (first 4MB)"),
            "quick",
        )
        index = self.hash_strategy_combo.findData(current if current is not None else "size_mtime")
        self.hash_strategy_combo.setCurrentIndex(index if index >= 0 else 0)
        self.hash_strategy_combo.blockSignals(False)

    def _set_font_source_options(self) -> None:
        current = self.font_source_combo.currentData()
        self.font_source_combo.blockSignals(True)
        self.font_source_combo.clear()
        self.font_source_combo.addItem(tr("settings.font.source.system", "System"), "system")
        self.font_source_combo.addItem(tr("settings.font.source.project", "Project (src/fonts)"), "project")
        index = self.font_source_combo.findData(current if current is not None else "system")
        self.font_source_combo.setCurrentIndex(index if index >= 0 else 0)
        self.font_source_combo.blockSignals(False)

    def _set_comic_thumbnail_worker_options(self) -> None:
        current = self.comic_thumbnail_workers_combo.currentData()
        self.comic_thumbnail_workers_combo.blockSignals(True)
        self.comic_thumbnail_workers_combo.clear()
        self.comic_thumbnail_workers_combo.addItem(tr("settings.comic.workers.auto", "Auto"), "auto")
        for worker in (2, 4, 6, 8, 12, 16):
            self.comic_thumbnail_workers_combo.addItem(str(worker), str(worker))
        index = self.comic_thumbnail_workers_combo.findData(current if current is not None else "auto")
        self.comic_thumbnail_workers_combo.setCurrentIndex(index if index >= 0 else 0)
        self.comic_thumbnail_workers_combo.blockSignals(False)

    def _pick_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, tr("settings.pick_folder", "Select Library Folder"))
        if not directory:
            return
        self.add_root_requested.emit(directory)

    def _pick_comic_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, tr("settings.pick_comic_folder", "Select Comic Folder"))
        if not directory:
            return
        self.add_comic_root_requested.emit(directory)

    def _pick_text_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, tr("settings.pick_text_folder", "Select Text Novel Folder"))
        if not directory:
            return
        self.add_text_root_requested.emit(directory)

    def _on_nav_changed(self, row: int) -> None:
        self.content_stack.setCurrentIndex(1 if row == 1 else 0)

    def set_error_logs_text(self, text: str) -> None:
        value = str(text or "").strip()
        if not value:
            value = tr("settings.error_logs.empty", "No error logs yet.")
        self.error_logs_text.setPlainText(value)

    def _append_path_item(self, path: str) -> None:
        self._append_root_row(
            list_widget=self.folders,
            path=path,
            remove_callback=lambda target: self.remove_root_requested.emit(target),
        )

    def _append_comic_path_item(self, path: str) -> None:
        self._append_root_row(
            list_widget=self.comic_folders,
            path=path,
            remove_callback=lambda target: self.remove_comic_root_requested.emit(target),
        )

    def _append_text_path_item(self, path: str) -> None:
        self._append_root_row(
            list_widget=self.text_folders,
            path=path,
            remove_callback=lambda target: self.remove_text_root_requested.emit(target),
            manage_rules_callback=self._open_text_rule_dialog,
        )

    def _append_root_row(
        self,
        list_widget: QListWidget,
        path: str,
        remove_callback,
        manage_rules_callback=None,
    ) -> None:
        item = QListWidgetItem()
        row = QWidget()
        row.setObjectName("PathRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 4, 12, 4)
        layout.setSpacing(10)
        row.setMinimumHeight(40)

        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("PathDeleteButton")
        delete_btn.setToolTip(tr("settings.delete_path", "Delete"))
        delete_btn.setFixedSize(96, 40)
        delete_btn.clicked.connect(
            lambda _=False, target=path: self._confirm_and_remove_root(target, remove_callback)
        )
        layout.addWidget(delete_btn, 0, Qt.AlignLeft)

        if callable(manage_rules_callback):
            rule_btn = QPushButton(tr("settings.rules_btn", "Rules"))
            rule_btn.setObjectName("PathRuleButton")
            rule_btn.setFixedSize(96, 40)
            rule_btn.clicked.connect(lambda _=False, target=path: manage_rules_callback(target))
            layout.addWidget(rule_btn, 0, Qt.AlignLeft)

        path_label = QLabel(path)
        path_label.setObjectName("PathValueLabel")
        path_label.setWordWrap(False)
        path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path_label.setToolTip(path)
        path_label.setMinimumHeight(40)
        path_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        layout.addWidget(path_label, 1)

        item.setSizeHint(row.sizeHint())
        list_widget.addItem(item)
        list_widget.setItemWidget(item, row)

    def _confirm_and_remove_root(self, target: str, remove_callback) -> None:
        title = tr("settings.delete_confirm_title", "Confirm Delete")
        text = tr(
            "settings.delete_confirm_text",
            "Delete this folder path?\n{path}",
        ).format(path=target)
        result = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result == QMessageBox.Yes:
            remove_callback(target)

    def _open_text_rule_dialog(self, target: str) -> None:
        existing_rules = self._text_rules_by_path.get(target, "{}")
        preview_chars = int(self.text_preview_chars_combo.currentData() or DEFAULT_TEXT_PREVIEW_CHARS)
        dialog = TextRuleDialog(target, existing_rules, self, preview_chars=preview_chars)
        if dialog.exec() != QDialog.Accepted:
            return
        updated_json = dialog.rules_json()
        self._text_rules_by_path[target] = updated_json
        self.manage_text_rules_requested.emit(target, updated_json)

    def _emit_scan_on_startup_changed(self) -> None:
        self.scan_on_startup_changed.emit(self.launch_check.isChecked())

    def _emit_auto_scan_on_path_change_changed(self) -> None:
        self.auto_scan_on_path_change_changed.emit(self.tray_check.isChecked())

    def _emit_language_changed(self) -> None:
        code = self.language_combo.currentData() or "en"
        self.language_changed.emit(code)

    def _emit_scan_depth_changed(self) -> None:
        value = int(self.scan_depth_combo.currentData() or 2)
        self.scan_depth_changed.emit(value)

    def _emit_hash_strategy_changed(self) -> None:
        strategy = str(self.hash_strategy_combo.currentData() or "size_mtime")
        self.hash_strategy_changed.emit(strategy)

    def _emit_comic_placeholder_copy_enabled_changed(self) -> None:
        self.comic_placeholder_copy_enabled_changed.emit(self.comic_placeholder_copy_check.isChecked())

    def _emit_comic_thumbnail_workers_changed(self) -> None:
        value = str(self.comic_thumbnail_workers_combo.currentData() or "auto")
        self.comic_thumbnail_workers_changed.emit(value)

    def _emit_comic_view_mode_changed(self) -> None:
        mode = str(self.comic_view_mode_combo.currentData() or "waterfall")
        self._update_comic_page_size_enabled()
        self.comic_view_mode_changed.emit(mode)

    def _emit_comic_page_size_changed(self) -> None:
        value = int(self.comic_page_size_combo.currentData() or 48)
        self.comic_page_size_changed.emit(value)

    def _update_comic_page_size_enabled(self) -> None:
        mode = str(self.comic_view_mode_combo.currentData() or "waterfall")
        enabled = mode == "pagination"
        self.comic_page_size_label.setEnabled(enabled)
        self.comic_page_size_combo.setEnabled(enabled)

    def _emit_auto_generate_comic_thumbnails_after_scan_changed(self) -> None:
        self.auto_generate_comic_thumbnails_after_scan_changed.emit(self.auto_comic_thumb_check.isChecked())

    def _emit_card_spacing_changed(self) -> None:
        value = normalize_card_spacing(self.card_spacing_combo.currentData())
        self.card_spacing_changed.emit(value)

    def _emit_topbar_search_font_size_changed(self) -> None:
        value = normalize_topbar_search_font_size(self.topbar_search_font_size_combo.currentData())
        self.topbar_search_font_size_changed.emit(value)

    def _emit_text_preview_chars_changed(self) -> None:
        value = int(self.text_preview_chars_combo.currentData() or DEFAULT_TEXT_PREVIEW_CHARS)
        self.text_preview_chars_changed.emit(value)

    def _emit_cover_selected_border_width_changed(self, value: int) -> None:
        normalized = normalize_cover_selected_border_width(value)
        self.cover_selected_border_width_changed.emit(normalized)

    def _pick_cover_selected_border_color(self) -> None:
        current = QColor(self._cover_selected_border_color)
        selected = QColorDialog.getColor(current, self, tr("settings.cover_selected_border.pick", "Pick Color"))
        if not selected.isValid():
            return
        self._cover_selected_border_color = normalize_cover_selected_border_color(selected.name())
        self._refresh_cover_selected_border_color_preview()
        self.cover_selected_border_color_changed.emit(self._cover_selected_border_color)

    def _refresh_cover_selected_border_color_preview(self) -> None:
        normalized = normalize_cover_selected_border_color(self._cover_selected_border_color)
        self._cover_selected_border_color = normalized
        self.cover_selected_border_color_preview.setText(normalized)
        self.cover_selected_border_color_preview.setStyleSheet(
            "QLabel {"
            f"background: {normalized};"
            "color: #ffffff;"
            "border: 1px solid #c8d0dc;"
            "padding: 4px 6px;"
            "}"
        )

    def _on_reload_fonts_clicked(self) -> None:
        self.reload_fonts_requested.emit()

    def _on_font_source_changed(self) -> None:
        self._font_source = str(self.font_source_combo.currentData() or "system")
        self._rebuild_font_family_options()
        self._emit_font_changed()

    def _rebuild_font_family_options(self, preferred_family: str | None = None) -> None:
        source = str(self.font_source_combo.currentData() or self._font_source or "system")
        self._font_source = source
        self.font_family_combo.blockSignals(True)
        self.font_family_combo.clear()

        if source == "project":
            families = list(self._project_font_families)
        else:
            families = sorted({family for family in QFontDatabase.families() if family})

        if not families:
            empty_label = tr("settings.font.none", "No fonts available")
            self.font_family_combo.addItem(empty_label, "")
        else:
            for family in families:
                self.font_family_combo.addItem(family, family)

        target = preferred_family or ""
        index = self.font_family_combo.findData(target) if target else -1
        if index < 0:
            index = 0
        self.font_family_combo.setCurrentIndex(index)
        self.font_family_combo.blockSignals(False)

    def _emit_font_changed(self) -> None:
        source = str(self.font_source_combo.currentData() or "system")
        family = str(self.font_family_combo.currentData() or "")
        if not family:
            return
        self.font_changed.emit(source, family)

    def set_thumbnail_task_running(self, task_kind: str, running: bool, scope: str = "library") -> None:
        self._thumbnail_task_kind = task_kind if running else self._thumbnail_task_kind
        target_buttons = self._thumbnail_buttons.get(scope, {})
        for button in target_buttons.values():
            button.setEnabled(not running)
        if running:
            self.thumbnail_task_panel.show()
            self.thumbnail_task_progress.setValue(0)
            self.thumbnail_task_status.setText(
                tr("settings.thumb.running", "Running {scope} {task} task...").format(scope=scope, task=task_kind)
            )
        else:
            self._update_thumbnail_button_texts()

    def set_thumbnail_task_progress(self, current: int, total: int, task_kind: str, scope: str = "library") -> None:
        self._thumbnail_task_kind = task_kind
        self.thumbnail_task_panel.show()
        safe_total = max(1, total)
        value = int((max(0, current) / safe_total) * 100)
        self.thumbnail_task_progress.setValue(min(100, max(0, value)))
        self.thumbnail_task_status.setText(
            tr("settings.thumb.progress", "{scope} {task}: {current}/{total}").format(
                scope=scope, task=task_kind, current=current, total=total
            )
        )

    def set_thumbnail_task_finished(self, task_kind: str, summary: dict[str, object], scope: str = "library") -> None:
        self._thumbnail_task_kind = task_kind
        self.thumbnail_task_panel.show()
        self.thumbnail_task_progress.setValue(100)
        if task_kind == "cleanup":
            self.thumbnail_task_status.setText(tr("settings.thumb.cleanup_done", "{scope} cleanup finished").format(scope=scope))
        elif task_kind == "regenerate_missing":
            self.thumbnail_task_status.setText(
                tr("settings.thumb.regenerate_missing_done", "{scope} missing thumbnail generation finished").format(
                    scope=scope
                )
            )
        else:
            self.thumbnail_task_status.setText(
                tr("settings.thumb.regenerate_done", "{scope} regenerate finished").format(scope=scope)
            )

        previous = self._last_summary.get("thumbnail_task")
        if not isinstance(previous, dict):
            previous = {}
        task_summary = dict(summary)
        task_summary["task_scope"] = str(task_summary.get("task_scope") or scope)
        task_summary["updated_at"] = self._last_summary.get("updated_at")
        self._last_summary["thumbnail_task"] = task_summary
