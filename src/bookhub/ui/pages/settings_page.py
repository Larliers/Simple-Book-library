from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr
from bookhub.ui.resources.layout_config import (
    CARD_SPACING_MAX,
    CARD_SPACING_MIN,
    DEFAULT_CARD_SPACING,
    normalize_card_spacing,
)


class SettingsPage(QWidget):
    language_changed = Signal(str)
    add_root_requested = Signal(str)
    remove_root_requested = Signal(str)
    scan_requested = Signal()
    scan_depth_changed = Signal(int)
    hash_strategy_changed = Signal(str)
    card_spacing_changed = Signal(int)
    cleanup_all_thumbnails_requested = Signal()
    regenerate_thumbnails_requested = Signal()
    font_changed = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._last_summary: dict[str, object] = {}
        self._current_roots: list[str] = []
        self._thumbnail_task_kind: str | None = None
        self._project_font_families: list[str] = []
        self._font_source: str = "system"

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        top = QHBoxLayout()
        self.app_title = QLabel("System Architect")
        self.app_title.setStyleSheet("font-size: 28px; font-weight: 700;")
        top.addWidget(self.app_title)
        top.addStretch(1)
        self.search_settings = QLineEdit()
        self.search_settings.setObjectName("SettingsSearchInput")
        self.search_settings.setPlaceholderText("Search settings")
        self.search_settings.setFixedWidth(260)
        top.addWidget(self.search_settings)
        root.addLayout(top)

        shell = QHBoxLayout()
        shell.setSpacing(14)
        root.addLayout(shell, 1)

        self.nav = QListWidget()
        self.nav.setObjectName("SettingsNav")
        self.nav.setFixedWidth(210)
        self._nav_labels = [
            ("settings.nav.general", "General"),
            ("settings.nav.library", "Library"),
            ("settings.nav.appearance", "Appearance"),
            ("settings.nav.about", "About"),
            ("settings.nav.shortcuts", "Shortcuts"),
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
        self.launch_check = QCheckBox("Launch at system startup")
        self.launch_check.setChecked(True)
        startup_layout.addWidget(self.launch_check)
        self.tray_check = QCheckBox("Minimize to tray on close")
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
        self.font_source_combo.addItem("System", "system")
        self.font_source_combo.addItem("Project (src/fonts)", "project")
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
        self.add_path_button = QPushButton("+ Add Path")
        self.add_path_button.setObjectName("PrimaryButton")
        self.add_path_button.clicked.connect(self._pick_folder)
        row.addWidget(self.library_label, 1)
        row.addWidget(self.add_path_button)
        library_layout.addLayout(row)

        self.folders = QListWidget()
        self.folders.setObjectName("LibraryPathList")
        self.folders.setSpacing(4)
        library_layout.addWidget(self.folders)

        options_row = QHBoxLayout()
        options_row.setSpacing(10)
        self.scan_depth_label = QLabel("Scan depth")
        options_row.addWidget(self.scan_depth_label)
        self.scan_depth_combo = QComboBox()
        self.scan_depth_combo.setObjectName("SettingsLanguageCombo")
        self.scan_depth_combo.addItem("1 - Root only", 1)
        self.scan_depth_combo.addItem("2 - Include child folders", 2)
        self.scan_depth_combo.addItem("3 - Include grandchild folders", 3)
        self.scan_depth_combo.currentIndexChanged.connect(self._emit_scan_depth_changed)
        options_row.addWidget(self.scan_depth_combo, 1)

        self.hash_strategy_label = QLabel("Missed hash matching")
        options_row.addWidget(self.hash_strategy_label)
        self.hash_strategy_combo = QComboBox()
        self.hash_strategy_combo.setObjectName("SettingsLanguageCombo")
        self.hash_strategy_combo.addItem("File size + modified time", "size_mtime")
        self.hash_strategy_combo.addItem("SHA-256 full file", "sha256")
        self.hash_strategy_combo.addItem("Quick hash (first 4MB)", "quick")
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
        library_layout.addLayout(options_row)

        self.formats_hint = QLabel(
            "Supported formats: PDF, EPUB. Unsupported formats are ignored and recorded in scan summary."
        )
        self.formats_hint.setObjectName("PageSubtitle")
        self.formats_hint.setWordWrap(True)
        library_layout.addWidget(self.formats_hint)

        self.scan_summary = QLabel("")
        self.scan_summary.setObjectName("PageSubtitle")
        self.scan_summary.setWordWrap(True)
        library_layout.addWidget(self.scan_summary)

        thumb_task_row = QHBoxLayout()
        thumb_task_row.setSpacing(8)
        self.cleanup_thumbnails_btn = QPushButton("Clean All Thumbnails")
        self.cleanup_thumbnails_btn.setObjectName("GhostButton")
        self.cleanup_thumbnails_btn.clicked.connect(self.cleanup_all_thumbnails_requested.emit)
        thumb_task_row.addWidget(self.cleanup_thumbnails_btn)

        self.regenerate_thumbnails_btn = QPushButton("Regenerate Thumbnails")
        self.regenerate_thumbnails_btn.setObjectName("GhostButton")
        self.regenerate_thumbnails_btn.clicked.connect(self.regenerate_thumbnails_requested.emit)
        thumb_task_row.addWidget(self.regenerate_thumbnails_btn)
        thumb_task_row.addStretch(1)
        library_layout.addLayout(thumb_task_row)

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

        action_row = QHBoxLayout()
        self.scan_btn = QPushButton("Scan folders for new books now")
        self.scan_btn.setObjectName("PrimaryButton")
        self.scan_btn.clicked.connect(self.scan_requested.emit)
        self.manage_btn = QPushButton("Manage Metadata")
        self.manage_btn.setObjectName("GhostButton")
        self.manage_btn.setEnabled(False)
        action_row.addWidget(self.scan_btn)
        action_row.addWidget(self.manage_btn)
        action_row.addStretch(1)
        content_layout.addLayout(action_row)
        content_layout.addStretch(1)

        self.content_stack.addWidget(content)
        self.shortcuts_page = self._build_shortcuts_page()
        self.content_stack.addWidget(self.shortcuts_page)

        self._set_language_options()
        self.set_language_selection("en")
        self.retranslate_ui()
        self.set_scan_summary({})
        self._on_nav_changed(self.nav.currentRow())

    def set_language_selection(self, language_code: str) -> None:
        index = self.language_combo.findData(language_code)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)

    def set_library_roots(self, paths: list[str]) -> None:
        self._current_roots = list(paths)
        self.folders.clear()
        for path in self._current_roots:
            self._append_path_item(path)

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

    def set_available_project_fonts(self, families: list[str]) -> None:
        self._project_font_families = sorted({str(item).strip() for item in families if str(item).strip()})
        self._rebuild_font_family_options()

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
        restored = int(summary.get("restored_from_missed", 0) or 0)
        moved = int(summary.get("moved_to_missed_count", 0) or 0)
        conflicts = summary.get("name_conflicts", [])
        conflict_count = len(conflicts) if isinstance(conflicts, list) else 0
        updated_at = str(summary.get("updated_at") or tr("settings.summary.never", "never"))
        self.scan_summary.setText(
            tr(
                "settings.scan_summary_template",
                "Last scan: {updated_at}\nAdded: {added} | Restored from Missed: {restored} | "
                "Moved to Missed: {moved} | Ignored unsupported: {ignored} | Name conflicts: {conflicts}",
            ).format(
                updated_at=updated_at,
                added=added_count,
                restored=restored,
                moved=moved,
                ignored=ignored,
                conflicts=conflict_count,
            )
        )
        thumb_task = summary.get("thumbnail_task")
        if isinstance(thumb_task, dict):
            task_kind = str(thumb_task.get("task_kind") or "")
            total = int(thumb_task.get("total", 0) or 0)
            succeeded = int(thumb_task.get("succeeded", 0) or 0)
            failed = int(thumb_task.get("failed", 0) or 0)
            skipped = int(thumb_task.get("skipped", 0) or 0)
            suffix = tr(
                "settings.thumb.summary",
                "\nThumbnail task({kind}) - total:{total} success:{succeeded} skipped:{skipped} failed:{failed}",
            ).format(
                kind=task_kind,
                total=total,
                succeeded=succeeded,
                skipped=skipped,
                failed=failed,
            )
            self.scan_summary.setText(self.scan_summary.text() + suffix)

    def set_scan_running(self, running: bool) -> None:
        self.scan_btn.setEnabled(not running)
        if running:
            self.scan_btn.setText(tr("settings.scan_running", "Scanning..."))
        else:
            self.scan_btn.setText(tr("settings.scan_now", "Scan folders for new books now"))

    def retranslate_ui(self) -> None:
        for idx, (key, fallback) in enumerate(self._nav_labels):
            item = self.nav.item(idx)
            if item is not None:
                item.setText(tr(key, fallback))
        self.title.setText(tr("settings.title", "General Settings"))
        self.startup_label.setText(tr("settings.startup_options", "Startup Options"))
        self.launch_check.setText(tr("settings.launch_startup", "Launch at system startup"))
        self.tray_check.setText(tr("settings.minimize_tray", "Minimize to tray on close"))
        self.language_label.setText(tr("settings.display_language", "Display language"))
        self.library_label.setText(tr("settings.library_folders", "Library Folders"))
        self.add_path_button.setText(tr("settings.add_path", "+ Add Path"))
        self.scan_btn.setText(tr("settings.scan_now", "Scan folders for new books now"))
        self.manage_btn.setText(tr("settings.manage_metadata", "Manage Metadata"))
        self.restart_hint.setText(tr("settings.restart_hint", "Restart application to apply language changes."))
        self.search_settings.setPlaceholderText(tr("settings.search_placeholder", "Search settings"))
        self.scan_depth_label.setText(tr("settings.scan_depth", "Scan depth"))
        self.hash_strategy_label.setText(tr("settings.hash_strategy", "Missed hash matching"))
        self.card_spacing_label.setText(tr("settings.card_spacing", "Card spacing"))
        self.font_title.setText(tr("settings.font.title", "Font"))
        self.font_source_label.setText(tr("settings.font.source", "Font source"))
        self.font_family_label.setText(tr("settings.font.family", "Font family"))
        self.reload_fonts_btn.setText(tr("settings.font.reload", "Reload Fonts"))
        self.font_preview_label.setText(
            tr("settings.font.preview", "Preview: The quick brown fox jumps over the lazy dog 你好，世界")
        )
        self.cleanup_thumbnails_btn.setText(tr("settings.thumb.clean_all", "Clean All Thumbnails"))
        self.regenerate_thumbnails_btn.setText(tr("settings.thumb.regenerate", "Regenerate Thumbnails"))
        self.formats_hint.setText(
            tr(
                "settings.formats_hint",
                "Supported formats: PDF, EPUB. Unsupported formats are ignored and recorded in scan summary.",
            )
        )
        self.shortcuts_title.setText(tr("settings.shortcuts.title", "Shortcuts"))
        self.shortcuts_placeholder.setText(
            tr(
                "settings.shortcuts.placeholder",
                "Shortcut customization will be available in a future update.",
            )
        )
        self.shortcuts_modify_btn.setText(
            tr("settings.shortcuts.modify_disabled", "Modify Shortcuts (Coming Soon)")
        )
        if self._thumbnail_task_kind:
            self.thumbnail_task_status.setText(tr("settings.thumb.done", "Task completed"))
        self.set_library_roots(self._current_roots)
        self._set_language_options()
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

    def _pick_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, tr("settings.pick_folder", "Select Library Folder"))
        if not directory:
            return
        self.add_root_requested.emit(directory)

    def _build_shortcuts_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("PageSection")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        self.shortcuts_title = QLabel()
        self.shortcuts_title.setObjectName("PageTitle")
        layout.addWidget(self.shortcuts_title)
        self.shortcuts_placeholder = QLabel()
        self.shortcuts_placeholder.setObjectName("PageSubtitle")
        self.shortcuts_placeholder.setWordWrap(True)
        layout.addWidget(self.shortcuts_placeholder)
        self.shortcuts_modify_btn = QPushButton()
        self.shortcuts_modify_btn.setObjectName("GhostButton")
        self.shortcuts_modify_btn.setEnabled(False)
        layout.addWidget(self.shortcuts_modify_btn, 0)
        layout.addStretch(1)
        return page

    def _on_nav_changed(self, row: int) -> None:
        if row == len(self._nav_labels) - 1:
            self.content_stack.setCurrentIndex(1)
            return
        self.content_stack.setCurrentIndex(0)

    def _append_path_item(self, path: str) -> None:
        item = QListWidgetItem()
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        path_label = QLabel(path)
        path_label.setObjectName("PageSubtitle")
        path_label.setWordWrap(True)
        layout.addWidget(path_label, 1)

        delete_btn = QPushButton(tr("settings.delete_path", "Delete"))
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(lambda _=False, target=path: self.remove_root_requested.emit(target))
        layout.addWidget(delete_btn, 0)

        item.setSizeHint(row.sizeHint())
        self.folders.addItem(item)
        self.folders.setItemWidget(item, row)

    def _emit_language_changed(self) -> None:
        code = self.language_combo.currentData() or "en"
        self.language_changed.emit(code)

    def _emit_scan_depth_changed(self) -> None:
        value = int(self.scan_depth_combo.currentData() or 2)
        self.scan_depth_changed.emit(value)

    def _emit_hash_strategy_changed(self) -> None:
        strategy = str(self.hash_strategy_combo.currentData() or "size_mtime")
        self.hash_strategy_changed.emit(strategy)

    def _emit_card_spacing_changed(self) -> None:
        value = normalize_card_spacing(self.card_spacing_combo.currentData())
        self.card_spacing_changed.emit(value)

    def _on_reload_fonts_clicked(self) -> None:
        self._emit_font_changed()

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
            families = [tr("settings.font.none", "No fonts available")]

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

    def set_thumbnail_task_running(self, task_kind: str, running: bool) -> None:
        self._thumbnail_task_kind = task_kind if running else self._thumbnail_task_kind
        self.cleanup_thumbnails_btn.setEnabled(not running)
        self.regenerate_thumbnails_btn.setEnabled(not running)
        if running:
            self.thumbnail_task_panel.show()
            self.thumbnail_task_progress.setValue(0)
            self.thumbnail_task_status.setText(
                tr("settings.thumb.progress", "第{current}个/共{total}个").format(current=0, total=0)
            )
        else:
            self.cleanup_thumbnails_btn.setEnabled(True)
            self.regenerate_thumbnails_btn.setEnabled(True)

    def set_thumbnail_task_progress(self, current: int, total: int, task_kind: str) -> None:
        self._thumbnail_task_kind = task_kind
        self.thumbnail_task_panel.show()
        safe_total = max(1, total)
        value = int((max(0, current) / safe_total) * 100)
        self.thumbnail_task_progress.setValue(min(100, max(0, value)))
        self.thumbnail_task_status.setText(
            tr("settings.thumb.progress", "第{current}个/共{total}个").format(current=current, total=total)
        )

    def set_thumbnail_task_finished(self, task_kind: str, summary: dict[str, object]) -> None:
        self._thumbnail_task_kind = task_kind
        self.thumbnail_task_panel.show()
        self.thumbnail_task_progress.setValue(100)
        if task_kind == "cleanup":
            self.thumbnail_task_status.setText(tr("settings.thumb.cleanup_done", "清理完毕"))
        else:
            self.thumbnail_task_status.setText(tr("settings.thumb.regenerate_done", "重建完毕"))

        previous = self._last_summary.get("thumbnail_task")
        if not isinstance(previous, dict):
            previous = {}
        task_summary = dict(summary)
        task_summary["updated_at"] = self._last_summary.get("updated_at")
        self._last_summary["thumbnail_task"] = task_summary
