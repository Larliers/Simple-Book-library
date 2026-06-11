from __future__ import annotations

import os
from time import perf_counter
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import language_manager, tr
from bookhub.library import LibraryRepository, ScanWorker, ThumbnailTaskWorker
from bookhub.library.error_logs import append_conflict_if_new, read_latest_log_text
from bookhub.ui.models.resource import ResourceItem
from bookhub.ui.pages.library_page import LibraryPage
from bookhub.ui.pages.settings_page import SettingsPage
from bookhub.ui.pages.comic_page import (
    COMIC_SORT_SETTING_KEY_FAV,
    COMIC_SORT_SETTING_KEY_MAIN,
    ComicPage,
)
from bookhub.ui.pages.text_novel_page import TextNovelPage
from bookhub.ui.resources.layout_config import (
    UI_LAYOUT,
    normalize_cover_selected_border_color,
    normalize_cover_selected_border_width,
    normalize_card_spacing,
    normalize_topbar_search_font_size,
)
from bookhub.ui.resources.font_runtime import (
    DEFAULT_PROJECT_FONTS_DIR,
    FontScanResult,
    ResolvedFont,
    resolve_effective_font,
    scan_project_fonts_and_register,
)
from bookhub.ui.resources.styles import DEFAULT_FONT_STACK, build_app_style
from bookhub.ui.viewmodels.library_viewmodel import LibraryViewModel
from bookhub.ui.widgets.sidebar import SidebarWidget
from bookhub.ui.widgets.slide_toast import SlideToast
from bookhub.ui.widgets.topbar import SearchSuggestion, TopBarWidget

# Collections and Favorites (auto-added)
from bookhub.ui.pages.collections_page import CollectionsPage
from bookhub.ui.pages.favorites_page import FavoritesPage



class AppWindow(QMainWindow):
    SEARCH_RENDER_DEBOUNCE_MS = 150
    PERF_LOG_ENV_KEY = "BOOKHUB_PERF_LOG"

    def __init__(self) -> None:
        super().__init__()
        self._repository = LibraryRepository()
        language_manager.set_language(self._repository.get_language_code())
        self.setWindowTitle(tr("app.window_title", "Simple Book Library - UI Outline"))
        self.resize(1400, 860)
        UI_LAYOUT.set_card_spacing(self._repository.get_card_spacing())
        UI_LAYOUT.set_topbar_search_font_size(self._repository.get_topbar_search_font_size())
        UI_LAYOUT.set_cover_selected_border_width(self._repository.get_cover_selected_border_width())
        UI_LAYOUT.set_cover_selected_border_color(self._repository.get_cover_selected_border_color())
        self._library_vm = LibraryViewModel()
        self._text_vm = LibraryViewModel()
        self._pages: dict[str, int] = {}
        self._scan_worker: ScanWorker | None = None
        self._thumbnail_worker: ThumbnailTaskWorker | None = None
        self._active_thumbnail_task_kind: str | None = None
        self._active_thumbnail_task_scope: str | None = None
        self._pending_auto_comic_thumbnail = False
        self._scan_conflict_toast = SlideToast(self)
        self._scan_warning_toast = SlideToast(self)
        self._scan_missing_removed_toast = SlideToast(self)
        self._font_toast = SlideToast(self)
        self._project_font_families: list[str] = []
        self._search_render_timer = QTimer(self)
        self._search_render_timer.setSingleShot(True)
        self._search_render_timer.setInterval(self.SEARCH_RENDER_DEBOUNCE_MS)
        self._search_render_timer.timeout.connect(self._commit_search_query)
        self._pending_query = ""
        self._last_committed_query = ""

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = SidebarWidget()
        self.sidebar.setFixedWidth(UI_LAYOUT.sidebar_width)
        self.sidebar.page_requested.connect(self._show_page)
        self.sidebar.import_button.clicked.connect(self._import_directory)
        root.addWidget(self.sidebar)

        main_panel = QWidget()
        panel_layout = QVBoxLayout(main_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        self.topbar = TopBarWidget()
        self.topbar.set_search_font_size(UI_LAYOUT.topbar_search_font_size)
        self.topbar.query_changed.connect(self._on_query_changed)
        panel_layout.addWidget(self.topbar)

        self.page_stack = QStackedWidget()
        panel_layout.addWidget(self.page_stack, 1)
        root.addWidget(main_panel, 1)

        self.library_page = LibraryPage(self._library_vm, repository=self._repository)
        self._register_page("library", self.library_page)
        self.text_page = TextNovelPage(repository=self._repository)
        self._register_page("text_novel", self.text_page)
        self._register_page("collections", CollectionsPage(self._repository))
        self._register_page("favorites", FavoritesPage(self._repository))
        self.comic_page = ComicPage(
            self._repository,
            favorite_only=False,
            sort_setting_key=COMIC_SORT_SETTING_KEY_MAIN,
        )
        self.comic_page.favorites_changed.connect(self._on_comic_favorites_changed)
        self._register_page("comic", self.comic_page)
        self.comic_fav_page = ComicPage(
            self._repository,
            favorite_only=True,
            sort_setting_key=COMIC_SORT_SETTING_KEY_FAV,
        )
        self.comic_fav_page.favorites_changed.connect(self._on_comic_favorites_changed)
        self._register_page("comic_fav", self.comic_fav_page)
        self.settings_page = SettingsPage()
        self.settings_page.language_changed.connect(self._on_language_changed)
        self.settings_page.scan_on_startup_changed.connect(self._on_scan_on_startup_changed)
        self.settings_page.auto_scan_on_path_change_changed.connect(self._on_auto_scan_on_path_change_changed)
        self.settings_page.add_root_requested.connect(self._on_add_root)
        self.settings_page.remove_root_requested.connect(self._on_remove_root)
        self.settings_page.add_comic_root_requested.connect(self._on_add_comic_root)
        self.settings_page.remove_comic_root_requested.connect(self._on_remove_comic_root)
        self.settings_page.add_text_root_requested.connect(self._on_add_text_root)
        self.settings_page.remove_text_root_requested.connect(self._on_remove_text_root)
        self.settings_page.text_preview_chars_changed.connect(self._on_text_preview_chars_changed)
        self.settings_page.text_rule_preview_result_height_changed.connect(
            self._on_text_rule_preview_result_height_changed
        )
        self.settings_page.manage_text_rules_requested.connect(self._on_manage_text_rules)
        self.settings_page.scan_library_requested.connect(lambda: self._start_scan("manual_library", scope="library"))
        self.settings_page.scan_comic_requested.connect(lambda: self._start_scan("manual_comic", scope="comic"))
        self.settings_page.scan_text_requested.connect(lambda: self._start_scan("manual_text", scope="text"))
        self.settings_page.scan_depth_changed.connect(self._on_scan_depth_changed)
        self.settings_page.hash_strategy_changed.connect(self._on_hash_strategy_changed)
        self.settings_page.comic_placeholder_copy_enabled_changed.connect(
            self._on_comic_placeholder_copy_enabled_changed
        )
        self.settings_page.comic_thumbnail_workers_changed.connect(self._on_comic_thumbnail_workers_changed)
        self.settings_page.comic_view_mode_changed.connect(self._on_comic_view_mode_changed)
        self.settings_page.comic_page_size_changed.connect(self._on_comic_page_size_changed)
        self.settings_page.auto_generate_comic_thumbnails_after_scan_changed.connect(
            self._on_auto_generate_comic_thumbnails_after_scan_changed
        )
        self.settings_page.card_spacing_changed.connect(self._on_card_spacing_changed)
        self.settings_page.topbar_search_font_size_changed.connect(self._on_topbar_search_font_size_changed)
        self.settings_page.cover_selected_border_width_changed.connect(self._on_cover_selected_border_width_changed)
        self.settings_page.cover_selected_border_color_changed.connect(self._on_cover_selected_border_color_changed)
        self.settings_page.font_changed.connect(self._on_font_changed)
        self.settings_page.reload_fonts_requested.connect(self._on_reload_fonts_requested)
        self.settings_page.cleanup_library_thumbnails_requested.connect(
            lambda: self._start_thumbnail_task("cleanup", scope="library")
        )
        self.settings_page.regenerate_library_thumbnails_requested.connect(
            lambda: self._start_thumbnail_task("regenerate", scope="library")
        )
        self.settings_page.cleanup_comic_thumbnails_requested.connect(
            lambda: self._start_thumbnail_task("cleanup", scope="comic")
        )
        self.settings_page.regenerate_comic_thumbnails_requested.connect(
            lambda: self._start_thumbnail_task("regenerate", scope="comic")
        )
        self._register_page("settings", self.settings_page)

        self._apply_runtime_style(DEFAULT_FONT_STACK)
        self.retranslate_ui()
        self._reload_resources_from_repository()
        self._refresh_settings_state()
        self._refresh_fonts_runtime(ensure_project_dir=False, show_feedback=False)
        self._refresh_search_suggestions()
        self._last_committed_query = self._library_vm.ui_state.filter
        self._show_page("library")
        if self._repository.get_scan_on_startup():
            QTimer.singleShot(100, lambda: self._start_scan("startup", scope="all"))

    def _register_page(self, page_name: str, widget: QWidget) -> None:
        index = self.page_stack.addWidget(widget)
        self._pages[page_name] = index

    def _show_page(self, page_name: str) -> None:
        index = self._pages.get(page_name)
        if index is None:
            return
        started_at = perf_counter()
        self.page_stack.setCurrentIndex(index)
        self.sidebar.set_active(page_name)
        current = self.page_stack.currentWidget()
        refresh_fn = getattr(current, "refresh", None)
        if callable(refresh_fn):
            refresh_fn()
        if current is self.library_page:
            self.library_page.render()
        elif current is self.text_page:
            self.text_page.render()
        self._stabilize_dropdown_layer()
        self._log_perf("show_page", started_at, page=page_name)

    def _perf_log_enabled(self) -> bool:
        raw = str(os.getenv(self.PERF_LOG_ENV_KEY, "") or "").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _log_perf(self, phase: str, started_at: float, **extra: str) -> None:
        if not self._perf_log_enabled():
            return
        elapsed_ms = (perf_counter() - started_at) * 1000.0
        payload = " ".join([f"{key}={value}" for key, value in extra.items() if value is not None])
        if payload:
            print(f"[perf] {phase} elapsed_ms={elapsed_ms:.2f} {payload}")
            return
        print(f"[perf] {phase} elapsed_ms={elapsed_ms:.2f}")

    def _invalidate_page_caches(self, page_names: list[str] | tuple[str, ...]) -> None:
        for page_name in page_names:
            index = self._pages.get(page_name)
            if index is None:
                continue
            widget = self.page_stack.widget(index)
            invalidate_fn = getattr(widget, "invalidate_cache", None)
            if callable(invalidate_fn):
                invalidate_fn()

    def _on_comic_favorites_changed(self) -> None:
        self._invalidate_page_caches(("comic", "comic_fav"))

    def _on_query_changed(self, query: str) -> None:
        self._pending_query = query
        self._refresh_search_suggestions(query)
        self._search_render_timer.start()

    def _commit_search_query(self) -> None:
        normalized = self._pending_query.strip().lower()
        if normalized == self._last_committed_query:
            self._stabilize_dropdown_layer()
            return

        self._library_vm.set_query(self._pending_query)
        self._last_committed_query = normalized
        current_page = self.page_stack.currentWidget()
        if current_page in {self.library_page}:
            current_page.render()  # type: ignore[call-arg]
        self._stabilize_dropdown_layer()

    def _refresh_search_suggestions(self, query: str | None = None) -> None:
        raw_query = self._library_vm.ui_state.filter if query is None else query
        suggestion_items = self._library_vm.search_suggestions_for_query(raw_query)
        self._library_vm.ui_state.search_suggestions = suggestion_items
        suggestions = [
            SearchSuggestion(
                group=item["group"],
                label=item["label"],
                description=item["description"],
                query_value=item["query_value"],
            )
            for item in suggestion_items
        ]
        self.topbar.set_search_suggestions(suggestions)

    def _stabilize_dropdown_layer(self) -> None:
        QTimer.singleShot(0, self.topbar.ensure_dropdown_on_top)

    def _reload_resources_from_repository(self) -> None:
        started_at = perf_counter()
        self._invalidate_page_caches(("comic", "comic_fav", "favorites", "collections", "library"))
        records = self._repository.list_books(include_missing=None)
        self._repository.backfill_comic_folder_modified_at()
        library_resources: list[ResourceItem] = []
        text_resources: list[ResourceItem] = []
        for record in records:
            resource = ResourceItem(
                resource_id=record["resource_id"],
                title=record["title"] or record["file_name"],
                author=record["author"] or "",
                status=record.get("status") or "UNREAD",
                tags=record.get("tags") or [],
                resource_type=record.get("resource_type") or "book",
                path=record["path"],
                thumbnail_path=record.get("thumbnail_path"),
                publisher=record.get("publisher"),
                language=record.get("language"),
                is_missing=bool(record.get("is_missing")),
                file_name=record.get("file_name") or "",
                extension=record.get("extension") or "",
                info_text=str(record.get("info_text") or "") or None,
            )
            if resource.resource_type == "text_novel":
                text_resources.append(resource)
            else:
                library_resources.append(resource)

        self._library_vm.set_resources(library_resources)
        self._text_vm.set_resources(text_resources)
        self.text_page.set_resources(text_resources)
        self._last_committed_query = self._library_vm.ui_state.filter
        self.library_page.render()
        self.text_page.render()
        self.comic_page.refresh(force=True)
        self.comic_fav_page.refresh(force=True)
        self._refresh_search_suggestions()
        self._log_perf("reload_resources", started_at)

    def _refresh_settings_state(self) -> None:
        self.settings_page.set_library_roots(self._repository.list_roots())
        self.settings_page.set_comic_roots(self._repository.list_comic_roots())
        self.settings_page.set_text_roots_with_rules(self._repository.list_text_roots_with_rules())
        self.settings_page.set_text_preview_chars(self._repository.get_text_preview_chars())
        self.settings_page.set_text_rule_preview_result_height(
            self._repository.get_text_rule_preview_result_height()
        )
        self.settings_page.set_language_selection(self._repository.get_language_code())
        self.settings_page.set_scan_on_startup(self._repository.get_scan_on_startup())
        self.settings_page.set_auto_scan_on_path_change(self._repository.get_auto_scan_on_path_change())
        self.settings_page.set_font_selection(self._repository.get_font_source(), self._repository.get_font_family())
        self.settings_page.set_scan_depth(self._repository.get_scan_depth())
        self.settings_page.set_hash_strategy(self._repository.get_hash_strategy())
        self.settings_page.set_comic_placeholder_copy_enabled(self._repository.get_comic_placeholder_copy_enabled())
        self.settings_page.set_comic_thumbnail_workers(self._repository.get_comic_thumbnail_workers_raw())
        comic_view_mode = self._repository.get_comic_view_mode()
        comic_page_size = self._repository.get_comic_page_size()
        self.settings_page.set_comic_view_mode(comic_view_mode)
        self.settings_page.set_comic_page_size(comic_page_size)
        self.settings_page.set_auto_generate_comic_thumbnails_after_scan(
            self._repository.get_auto_generate_comic_thumbnails_after_scan()
        )
        self.comic_page.set_view_mode(comic_view_mode, comic_page_size)
        self.comic_fav_page.set_view_mode(comic_view_mode, comic_page_size)
        self.settings_page.set_card_spacing(self._repository.get_card_spacing())
        self.settings_page.set_topbar_search_font_size(self._repository.get_topbar_search_font_size())
        cover_border_width = self._repository.get_cover_selected_border_width()
        cover_border_color = self._repository.get_cover_selected_border_color()
        UI_LAYOUT.set_cover_selected_border_width(cover_border_width)
        UI_LAYOUT.set_cover_selected_border_color(cover_border_color)
        self.settings_page.set_cover_selected_border_width(cover_border_width)
        self.settings_page.set_cover_selected_border_color(cover_border_color)
        self.settings_page.set_scan_summary(self._repository.read_scan_report())
        self.settings_page.set_error_logs_text(read_latest_log_text())
        self._apply_runtime_style(self._build_font_stack(self._repository.get_font_family()))

    def _import_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, tr("import.pick_dir", "Select library folder to import"))
        if not directory:
            return
        self._repository.add_root(directory)
        self._refresh_settings_state()
        if self._repository.get_auto_scan_on_path_change():
            self._start_scan("import", scope="library")

    def _on_add_root(self, path: str) -> None:
        self._repository.add_root(path)
        self._invalidate_page_caches(("library",))
        self._refresh_settings_state()
        if self._repository.get_auto_scan_on_path_change():
            self._start_scan("add_path", scope="library")

    def _on_add_comic_root(self, path: str) -> None:
        self._repository.add_comic_root(path)
        self._invalidate_page_caches(("comic", "comic_fav"))
        self._refresh_settings_state()
        if self._repository.get_auto_scan_on_path_change():
            self._start_scan("add_comic_path", scope="comic")

    def _on_add_text_root(self, path: str) -> None:
        self._repository.add_text_root(path)
        self._invalidate_page_caches(("text_novel",))
        self._refresh_settings_state()
        if self._repository.get_auto_scan_on_path_change():
            self._start_scan("add_text_path", scope="text")

    def _on_remove_comic_root(self, path: str) -> None:
        removed_count = self._repository.remove_comic_root(path)
        summary = self._repository.read_scan_report()
        summary["removed_missing_comic_count"] = removed_count
        summary["removed_missing_count"] = int(summary.get("removed_missing_count", 0) or 0) + removed_count
        summary["trigger"] = "remove_comic_root"
        self._repository.write_scan_report(summary)
        self._repository.record_scan_event("remove_comic_root", summary)
        self._reload_resources_from_repository()
        self._refresh_settings_state()

    def _on_remove_text_root(self, path: str) -> None:
        removed_count = self._repository.remove_text_root(path)
        summary = self._repository.read_scan_report()
        summary["removed_missing_book_count"] = int(summary.get("removed_missing_book_count", 0) or 0) + removed_count
        summary["removed_missing_count"] = int(summary.get("removed_missing_count", 0) or 0) + removed_count
        summary["trigger"] = "remove_text_root"
        self._repository.write_scan_report(summary)
        self._repository.record_scan_event("remove_text_root", summary)
        self._reload_resources_from_repository()
        self._refresh_settings_state()

    def _on_remove_root(self, path: str) -> None:
        removed_count = self._repository.remove_root(path)
        summary = self._repository.read_scan_report()
        summary["removed_missing_book_count"] = int(summary.get("removed_missing_book_count", 0) or 0) + removed_count
        summary["removed_missing_count"] = int(summary.get("removed_missing_count", 0) or 0) + removed_count
        summary["trigger"] = "remove_root"
        self._repository.write_scan_report(summary)
        self._repository.record_scan_event("remove_root", summary)
        self._reload_resources_from_repository()
        self._refresh_settings_state()
        self._scan_missing_removed_toast.show_toast(
            title=tr("scan.missing_removed.title", "Missing files removed"),
            message=tr("scan.missing_removed.msg", "Removed {count} stale records after root removal.").format(
                count=removed_count
            ),
            duration_seconds=6,
        )

    def _on_text_preview_chars_changed(self, size: int) -> None:
        self._repository.set_text_preview_chars(size)

    def _on_text_rule_preview_result_height_changed(self, height: int) -> None:
        self._repository.set_text_rule_preview_result_height(height)

    def _on_manage_text_rules(self, root_path: str, rules_json: str) -> None:
        self._repository.set_text_root_rules_json(root_path, rules_json)
        self._refresh_settings_state()
        if self._repository.get_auto_scan_on_path_change():
            self._start_scan("update_text_rules", scope="text")

    def _on_scan_on_startup_changed(self, enabled: bool) -> None:
        self._repository.set_scan_on_startup(enabled)

    def _on_auto_scan_on_path_change_changed(self, enabled: bool) -> None:
        self._repository.set_auto_scan_on_path_change(enabled)

    def _on_font_changed(self, source: str, family: str) -> None:
        self._apply_font_selection(source=source, family=family, persist=True)

    def _on_reload_fonts_requested(self) -> None:
        self._refresh_fonts_runtime(ensure_project_dir=True, show_feedback=True)

    def _refresh_fonts_runtime(self, *, ensure_project_dir: bool, show_feedback: bool) -> None:
        scan_result = self._reload_project_fonts(ensure_project_dir=ensure_project_dir)
        source = self._repository.get_font_source()
        family = self._repository.get_font_family()
        resolved = self._apply_font_selection(source=source, family=family, persist=True)
        if show_feedback:
            self._show_font_reload_feedback(scan_result=scan_result, resolved=resolved)

    def _reload_project_fonts(self, *, ensure_project_dir: bool) -> FontScanResult:
        scan_result = scan_project_fonts_and_register(DEFAULT_PROJECT_FONTS_DIR, ensure_dir=ensure_project_dir)
        self._project_font_families = list(scan_result.registered_families)
        self.settings_page.set_available_project_fonts(self._project_font_families)
        return scan_result

    def _apply_font_selection(self, *, source: str, family: str, persist: bool) -> ResolvedFont:
        system_families = sorted({str(name).strip() for name in QFontDatabase.families() if str(name).strip()})
        resolved = resolve_effective_font(source, family, system_families, self._project_font_families)
        self.settings_page.set_font_selection(resolved.source, resolved.family)
        self._apply_font_to_ui(resolved.family)
        if persist:
            self._repository.set_font_source(resolved.source)
            self._repository.set_font_family(resolved.family)
        return resolved

    def _apply_font_to_ui(self, family: str) -> None:
        app = QApplication.instance()
        selected = str(family or "").strip()
        if app is not None and selected:
            app.setFont(QFont(selected))
        self._apply_runtime_style(self._build_font_stack(selected))
        self._stabilize_dropdown_layer()

    def _apply_runtime_style(self, font_stack: list[str] | tuple[str, ...]) -> None:
        self.setStyleSheet(
            build_app_style(
                font_stack,
                cover_selected_border_width_px=UI_LAYOUT.cover_selected_border_width_px,
                cover_selected_border_color_hex=UI_LAYOUT.cover_selected_border_color_hex,
            )
        )

    def _build_font_stack(self, selected_family: str) -> list[str]:
        stack: list[str] = []
        selected = str(selected_family or "").strip()
        if selected:
            stack.append(selected)
        for fallback in DEFAULT_FONT_STACK:
            if fallback not in stack:
                stack.append(fallback)
        return stack

    def _show_font_reload_feedback(self, *, scan_result: FontScanResult, resolved: ResolvedFont) -> None:
        lines: list[str] = []
        if scan_result.directory_created:
            lines.append(
                tr(
                    "settings.font.toast.dir_created",
                    "Created {path}. Put font files there and reload again.",
                ).format(path=str(Path(scan_result.directory)))
            )
        if not scan_result.registered_families:
            lines.append(
                tr(
                    "settings.font.toast.project_empty",
                    "No project fonts found in {path}.",
                ).format(path=str(Path(scan_result.directory)))
            )
        if scan_result.failed_files:
            lines.append(
                tr(
                    "settings.font.toast.failed_files",
                    "Failed to load {count} font files: {files}",
                ).format(count=len(scan_result.failed_files), files=", ".join(scan_result.failed_files[:3]))
            )
        if resolved.fallback_reason:
            lines.append(
                tr(
                    "settings.font.toast.fallback",
                    "Selected font is unavailable. Applied fallback font: {family}.",
                ).format(family=resolved.family or tr("settings.font.none", "No fonts available"))
            )
        if not lines:
            lines.append(
                tr("settings.font.toast.success", "Fonts reloaded and applied: {family}.").format(
                    family=resolved.family or tr("settings.font.none", "No fonts available")
                )
            )
        self._font_toast.show_toast(
            title=tr("settings.font.reload", "Reload Fonts"),
            message="\n".join(lines),
            duration_seconds=8,
        )

    def _on_scan_depth_changed(self, depth: int) -> None:
        self._repository.set_scan_depth(depth)

    def _on_hash_strategy_changed(self, strategy: str) -> None:
        self._repository.set_hash_strategy(strategy)

    def _on_comic_placeholder_copy_enabled_changed(self, enabled: bool) -> None:
        self._repository.set_comic_placeholder_copy_enabled(enabled)

    def _on_comic_thumbnail_workers_changed(self, value: str) -> None:
        self._repository.set_comic_thumbnail_workers(value)

    def _on_comic_view_mode_changed(self, mode: str) -> None:
        self._repository.set_comic_view_mode(mode)
        normalized_mode = self._repository.get_comic_view_mode()
        page_size = self._repository.get_comic_page_size()
        self.settings_page.set_comic_view_mode(normalized_mode)
        self.comic_page.set_view_mode(normalized_mode, page_size)
        self.comic_fav_page.set_view_mode(normalized_mode, page_size)

    def _on_comic_page_size_changed(self, value: int) -> None:
        self._repository.set_comic_page_size(value)
        page_size = self._repository.get_comic_page_size()
        mode = self._repository.get_comic_view_mode()
        self.settings_page.set_comic_page_size(page_size)
        self.comic_page.set_view_mode(mode, page_size)
        self.comic_fav_page.set_view_mode(mode, page_size)

    def _on_auto_generate_comic_thumbnails_after_scan_changed(self, enabled: bool) -> None:
        self._repository.set_auto_generate_comic_thumbnails_after_scan(enabled)

    def _on_card_spacing_changed(self, spacing: int) -> None:
        normalized = normalize_card_spacing(spacing)
        self._repository.set_card_spacing(normalized)
        UI_LAYOUT.set_card_spacing(normalized)
        for index in self._pages.values():
            widget = self.page_stack.widget(index)
            apply_spacing = getattr(widget, "apply_card_spacing", None)
            if callable(apply_spacing):
                apply_spacing(normalized)

    def _on_topbar_search_font_size_changed(self, size: int) -> None:
        normalized = normalize_topbar_search_font_size(size)
        self._repository.set_topbar_search_font_size(normalized)
        UI_LAYOUT.set_topbar_search_font_size(normalized)
        self.topbar.set_search_font_size(normalized)

    def _on_cover_selected_border_width_changed(self, width: int) -> None:
        normalized = normalize_cover_selected_border_width(width)
        self._repository.set_cover_selected_border_width(normalized)
        UI_LAYOUT.set_cover_selected_border_width(normalized)
        self._apply_runtime_style(self._build_font_stack(self._repository.get_font_family()))

    def _on_cover_selected_border_color_changed(self, color: str) -> None:
        normalized = normalize_cover_selected_border_color(color)
        self._repository.set_cover_selected_border_color(normalized)
        UI_LAYOUT.set_cover_selected_border_color(normalized)
        self._apply_runtime_style(self._build_font_stack(self._repository.get_font_family()))

    def _start_scan(self, trigger: str, *, scope: str = "all") -> None:
        if self._thumbnail_worker is not None and self._thumbnail_worker.isRunning():
            return
        if self._scan_worker is not None and self._scan_worker.isRunning():
            return
        roots = self._repository.list_roots() if scope in {"all", "library"} else []
        comic_roots = self._repository.list_comic_roots() if scope in {"all", "comic"} else []
        text_roots = self._repository.list_text_roots_with_rules() if scope in {"all", "text"} else []
        if not roots and not comic_roots and not text_roots:
            return
        self.settings_page.set_scan_running(True, scope)
        worker = ScanWorker(
            db_path=self._repository.db_path,
            scan_report_path=self._repository.scan_report_path,
            roots=roots,
            comic_roots=comic_roots,
            text_roots=text_roots,
            text_preview_chars=self._repository.get_text_preview_chars(),
            scan_depth=self._repository.get_scan_depth(),
            hash_strategy=self._repository.get_hash_strategy(),
            comic_placeholder_copy_enabled=self._repository.get_comic_placeholder_copy_enabled(),
            comic_thumbnail_workers_used=self._repository.get_comic_thumbnail_workers(),
            trigger=trigger,
            scope=scope,
        )
        worker.scan_completed.connect(self._on_scan_completed)
        worker.scan_failed.connect(self._on_scan_failed)
        worker.finished.connect(self._on_worker_finished)
        self._scan_worker = worker
        worker.start()

    def _on_scan_completed(self, summary_obj: object) -> None:
        summary = summary_obj if isinstance(summary_obj, dict) else {}
        scope = str(summary.get("scope") or "all")
        self.settings_page.set_scan_running(False, scope)
        self.settings_page.set_scan_summary(summary)
        self._reload_resources_from_repository()
        conflicts = summary.get("name_conflicts", [])
        if isinstance(conflicts, list) and conflicts:
            self._show_name_conflicts(conflicts)
        errors = summary.get("errors", [])
        if isinstance(errors, list) and errors:
            self._show_scan_errors(errors)
        warnings = summary.get("warnings", [])
        if isinstance(warnings, list) and warnings:
            self._show_scan_warnings(warnings)
        removed_missing_count = int(summary.get("removed_missing_count", 0) or 0)
        if removed_missing_count > 0:
            self._show_missing_removed_toast(removed_missing_count)
        should_auto_queue = (
            self._repository.get_auto_generate_comic_thumbnails_after_scan()
            and scope in {"comic", "all"}
            and int(summary.get("comic_thumbnail_enqueued_count", 0) or 0) > 0
        )
        self._pending_auto_comic_thumbnail = should_auto_queue
        if should_auto_queue:
            queued = int(summary.get("comic_thumbnail_enqueued_count", 0) or 0)
            workers = int(summary.get("comic_thumbnail_workers_used", self._repository.get_comic_thumbnail_workers()) or 0)
            self._scan_warning_toast.show_toast(
                title=tr("settings.thumb.auto.title", "Comic thumbnails queued"),
                message=tr(
                    "settings.thumb.auto.msg",
                    "Comic scan finished. Queued {count} thumbnails for background generation ({workers} workers).",
                ).format(count=queued, workers=workers),
                duration_seconds=7,
            )

    def _on_scan_failed(self, message: str) -> None:
        self.settings_page.set_scan_running(False, "all")
        QMessageBox.critical(self, tr("scan.failed_title", "Scan failed"), message)

    def _on_worker_finished(self) -> None:
        self._scan_worker = None
        if self._pending_auto_comic_thumbnail:
            self._pending_auto_comic_thumbnail = False
            if self._thumbnail_worker is None or not self._thumbnail_worker.isRunning():
                self._start_thumbnail_task("regenerate_missing", scope="comic")

    def _show_name_conflicts(self, conflicts: list[object]) -> None:
        normalized = [item for item in conflicts if isinstance(item, dict)]
        if not normalized:
            return

        new_logged_count = 0
        for item in normalized:
            file_name = str(item.get("file_name") or "").strip()
            src = str(item.get("source_path") or item.get("path") or "").strip()
            existing = str(item.get("existing_path") or "").strip()
            line = f"conflict={file_name} | source={src} | existing={existing}"
            if append_conflict_if_new(line):
                new_logged_count += 1

        self.settings_page.set_error_logs_text(read_latest_log_text())

        if new_logged_count <= 0:
            return

        count = len(normalized)
        message = tr(
            "scan.conflict.toast_msg",
            "Skipped {count} files because same file name + extension already exists.",
        ).format(count=count)
        hint = tr(
            "scan.conflict.settings_hint",
            "New conflict logs were added. Check Settings > Error logs.",
        )
        self._scan_conflict_toast.show_toast(
            title=tr("scan.conflict_title", "Duplicate name and extension detected"),
            message=f"{message}\n{hint}",
            duration_seconds=7,
        )

    def _show_scan_errors(self, errors: list[object]) -> None:
        lines = [f"- {str(item)}" for item in errors[:6]]
        if len(errors) > 6:
            lines.append(f"... and {len(errors) - 6} more errors")
        QMessageBox.warning(
            self,
            tr("scan.error_title", "Scan completed with errors"),
            "\n".join(lines),
        )

    def _show_scan_warnings(self, warnings: list[object]) -> None:
        normalized = [item for item in warnings if isinstance(item, dict)]
        if not normalized:
            return

        pdf_warning = next(
            (item for item in normalized if str(item.get("code") or "") == "pdf_backend_unavailable"),
            None,
        )
        if not pdf_warning:
            comic_warning = next(
                (item for item in normalized if str(item.get("code") or "") == "comic_large_image_downscaled"),
                None,
            )
            if not comic_warning:
                return
            comic_count = int(comic_warning.get("count", 0) or 0)
            self._scan_warning_toast.show_toast(
                title=tr("scan.warning_title", "Scan warning"),
                message=tr(
                    "scan.warning.comic_large_image_downscaled",
                    "Downscaled {count} large comic covers for placeholder rendering to avoid Qt decode limit.",
                ).format(count=comic_count),
                duration_seconds=8,
            )
            return

        count = int(pdf_warning.get("count", 0) or 0)
        reason = str(pdf_warning.get("reason") or "").strip()
        message = tr(
            "scan.warning.pdf_backend_unavailable",
            "PyMuPDF unavailable. Imported PDF files with fallback title only; skipped PDF metadata and thumbnails ({count} files).",
        ).format(count=count)
        if reason:
            message = f"{message}\n{reason}"
        comic_warning = next(
            (item for item in normalized if str(item.get("code") or "") == "comic_large_image_downscaled"),
            None,
        )
        if comic_warning:
            comic_count = int(comic_warning.get("count", 0) or 0)
            message = f"{message}\n" + tr(
                "scan.warning.comic_large_image_downscaled",
                "Downscaled {count} large comic covers for placeholder rendering to avoid Qt decode limit.",
            ).format(count=comic_count)
        self._scan_warning_toast.show_toast(
            title=tr("scan.warning_title", "Scan warning"),
            message=message,
            duration_seconds=8,
        )

    def _show_missing_removed_toast(self, removed_count: int) -> None:
        self.settings_page.set_error_logs_text(read_latest_log_text())
        message = tr(
            "scan.missing_removed.msg",
            "Removed {count} stale records. Check Settings > Error logs for details.",
        ).format(count=removed_count)
        self._scan_missing_removed_toast.show_toast(
            title=tr("scan.missing_removed.title", "Missing files removed"),
            message=message,
            duration_seconds=8,
        )

    def _on_language_changed(self, language_code: str) -> None:
        language_manager.set_language(language_code)
        self._repository.set_language_code(language_code)
        self.retranslate_ui()

    def _start_thumbnail_task(self, task_kind: str, *, scope: str) -> None:
        if self._scan_worker is not None and self._scan_worker.isRunning():
            return
        if self._thumbnail_worker is not None and self._thumbnail_worker.isRunning():
            return
        self._active_thumbnail_task_kind = task_kind
        self._active_thumbnail_task_scope = scope
        self.settings_page.set_thumbnail_task_running(task_kind, True, scope)
        worker = ThumbnailTaskWorker(
            db_path=self._repository.db_path,
            scan_report_path=self._repository.scan_report_path,
            task_kind=task_kind,
            task_scope=scope,
            comic_workers=self._repository.get_comic_thumbnail_workers() if scope == "comic" else None,
        )
        worker.progress.connect(self._on_thumbnail_task_progress)
        worker.completed.connect(self._on_thumbnail_task_completed)
        worker.failed.connect(self._on_thumbnail_task_failed)
        worker.finished.connect(self._on_thumbnail_worker_finished)
        self._thumbnail_worker = worker
        worker.start()

    def _on_thumbnail_task_progress(self, current: int, total: int, _label: str) -> None:
        task_kind = self._active_thumbnail_task_kind or "regenerate"
        scope = self._active_thumbnail_task_scope or "library"
        self.settings_page.set_thumbnail_task_progress(current, total, task_kind, scope)

    def _on_thumbnail_task_completed(self, summary_obj: object) -> None:
        summary = summary_obj if isinstance(summary_obj, dict) else {}
        task_kind = str(summary.get("task_kind") or self._active_thumbnail_task_kind or "cleanup")
        scope = str(summary.get("task_scope") or self._active_thumbnail_task_scope or "library")
        self.settings_page.set_thumbnail_task_running(task_kind, False, scope)
        self.settings_page.set_thumbnail_task_finished(task_kind, summary, scope)
        self._reload_resources_from_repository()

        scan_summary = self._repository.read_scan_report()
        scan_summary["thumbnail_task"] = summary
        self._repository.write_scan_report(scan_summary)
        self.settings_page.set_scan_summary(scan_summary)

        total = int(summary.get("total", 0) or 0)
        succeeded = int(summary.get("succeeded", 0) or 0)
        skipped = int(summary.get("skipped", 0) or 0)
        failed = int(summary.get("failed", 0) or 0)
        self._repository.record_scan_event(f"thumbnail_{task_kind}", summary)
        if task_kind == "regenerate_missing" and scope == "comic":
            self._scan_warning_toast.show_toast(
                title=tr("settings.thumb.auto.done_title", "Comic thumbnails updated"),
                message=tr(
                    "settings.thumb.auto.done_msg",
                    "Background comic thumbnail update finished. Success: {succeeded}, Skipped: {skipped}, Failed: {failed}.",
                ).format(succeeded=succeeded, skipped=skipped, failed=failed),
                duration_seconds=7,
            )
            return
        QMessageBox.information(
            self,
            tr("settings.thumb.result_title", "Thumbnail task finished"),
            tr(
                "settings.thumb.result_msg",
                "Scope: {scope}\nTask: {task}\nTotal: {total}\nSuccess: {succeeded}\nSkipped: {skipped}\nFailed: {failed}",
            ).format(
                scope=scope,
                task=task_kind,
                total=total,
                succeeded=succeeded,
                skipped=skipped,
                failed=failed,
            ),
        )

    def _on_thumbnail_task_failed(self, message: str) -> None:
        task_kind = self._active_thumbnail_task_kind or "cleanup"
        scope = self._active_thumbnail_task_scope or "library"
        self.settings_page.set_thumbnail_task_running(task_kind, False, scope)
        QMessageBox.critical(self, tr("settings.thumb.failed_title", "Thumbnail task failed"), message)

    def _on_thumbnail_worker_finished(self) -> None:
        self._thumbnail_worker = None
        self._active_thumbnail_task_kind = None
        self._active_thumbnail_task_scope = None

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._scan_conflict_toast.reposition()
        self._scan_warning_toast.reposition()
        self._scan_missing_removed_toast.reposition()
        self._font_toast.reposition()
        self._stabilize_dropdown_layer()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("app.window_title", "Simple Book Library - UI Outline"))
        self.sidebar.retranslate_ui()
        self.topbar.retranslate_ui()
        self.library_page.retranslate_ui()
        self.text_page.retranslate_ui()
        favorites_retranslate = getattr(self.page_stack.widget(self._pages["favorites"]), "retranslate_ui", None)
        if callable(favorites_retranslate):
            favorites_retranslate()
        comic_retranslate = getattr(self.page_stack.widget(self._pages["comic"]), "retranslate_ui", None)
        if callable(comic_retranslate):
            comic_retranslate()
        comic_fav_retranslate = getattr(self.page_stack.widget(self._pages["comic_fav"]), "retranslate_ui", None)
        if callable(comic_fav_retranslate):
            comic_fav_retranslate()
        self.settings_page.retranslate_ui()
