from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
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
from bookhub.ui.models.resource import ResourceItem
from bookhub.ui.pages.library_page import LibraryPage
from bookhub.ui.pages.placeholder_page import PlaceholderPage
from bookhub.ui.pages.plugins_page import PluginsPage
from bookhub.ui.pages.settings_page import SettingsPage
from bookhub.ui.resources.layout_config import UI_LAYOUT
from bookhub.ui.resources.styles import APP_STYLE
from bookhub.ui.viewmodels.library_viewmodel import LibraryViewModel
from bookhub.ui.widgets.sidebar import SidebarWidget
from bookhub.ui.widgets.topbar import SearchSuggestion, TopBarWidget

# Collections and Favorites (auto-added)
from bookhub.ui.pages.collections_page import CollectionsPage
from bookhub.ui.pages.favorites_page import FavoritesPage



class AppWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        language_manager.set_language("en")
        self.setWindowTitle(tr("app.window_title", "Simple Book Library - UI Outline"))
        self.resize(1400, 860)

        self._repository = LibraryRepository()
        self._library_vm = LibraryViewModel()
        self._pages: dict[str, int] = {}
        self._scan_worker: ScanWorker | None = None
        self._thumbnail_worker: ThumbnailTaskWorker | None = None
        self._active_thumbnail_task_kind: str | None = None

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
        self.topbar.query_changed.connect(self._on_query_changed)
        self.topbar.import_requested.connect(self._import_directory)
        panel_layout.addWidget(self.topbar)

        self.page_stack = QStackedWidget()
        panel_layout.addWidget(self.page_stack, 1)
        root.addWidget(main_panel, 1)

        self.library_page = LibraryPage(self._library_vm, missing_mode=False, repository=self._repository)
        self._register_page("library", self.library_page)
        self._register_page("collections", CollectionsPage(self._repository))
        self._register_page("reading_now", PlaceholderPage("Reading Now", "Reading queue page skeleton."))
        self._register_page("favorites", FavoritesPage(self._repository))
        self.plugins_page = PluginsPage()
        self._register_page("tools", self.plugins_page)
        self.missed_page = LibraryPage(self._library_vm, missing_mode=True, repository=self._repository)
        self._register_page("missed", self.missed_page)
        self.settings_page = SettingsPage()
        self.settings_page.language_changed.connect(self._on_language_changed)
        self.settings_page.add_root_requested.connect(self._on_add_root)
        self.settings_page.remove_root_requested.connect(self._on_remove_root)
        self.settings_page.scan_requested.connect(lambda: self._start_scan("manual"))
        self.settings_page.scan_depth_changed.connect(self._on_scan_depth_changed)
        self.settings_page.hash_strategy_changed.connect(self._on_hash_strategy_changed)
        self.settings_page.cleanup_all_thumbnails_requested.connect(self._start_cleanup_thumbnails)
        self.settings_page.regenerate_thumbnails_requested.connect(self._start_regenerate_thumbnails)
        self._register_page("settings", self.settings_page)

        self.setStyleSheet(APP_STYLE)
        self.retranslate_ui()
        self._reload_resources_from_repository()
        self._refresh_settings_state()
        self._refresh_search_suggestions()
        self._show_page("library")
        QTimer.singleShot(100, lambda: self._start_scan("startup"))

    def _register_page(self, page_name: str, widget: QWidget) -> None:
        index = self.page_stack.addWidget(widget)
        self._pages[page_name] = index

    def _show_page(self, page_name: str) -> None:
        index = self._pages.get(page_name)
        if index is None:
            return
        self.page_stack.setCurrentIndex(index)
        self.sidebar.set_active(page_name)
        current = self.page_stack.currentWidget()
        if current in {self.library_page, self.missed_page}:
            self.library_page.render()
            self.missed_page.render()

    def _on_query_changed(self, query: str) -> None:
        self._library_vm.set_query(query)
        self._refresh_search_suggestions()
        current_page = self.page_stack.currentWidget()
        if current_page in {self.library_page, self.missed_page}:
            current_page.render()  # type: ignore[call-arg]

    def _refresh_search_suggestions(self) -> None:
        suggestions = [
            SearchSuggestion(
                group=item["group"],
                label=item["label"],
                description=item["description"],
                query_value=item["query_value"],
            )
            for item in self._library_vm.ui_state.search_suggestions
        ]
        self.topbar.set_search_suggestions(suggestions)

    def _reload_resources_from_repository(self) -> None:
        records = self._repository.list_books(include_missing=None)
        resources: list[ResourceItem] = []
        for record in records:
            resources.append(
                ResourceItem(
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
                )
            )
        self._library_vm.set_resources(resources)
        self.library_page.render()
        self.missed_page.render()
        self._refresh_search_suggestions()

    def _refresh_settings_state(self) -> None:
        self.settings_page.set_library_roots(self._repository.list_roots())
        self.settings_page.set_scan_depth(self._repository.get_scan_depth())
        self.settings_page.set_hash_strategy(self._repository.get_hash_strategy())
        self.settings_page.set_scan_summary(self._repository.read_scan_report())

    def _import_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, tr("import.pick_dir", "Select library folder to import"))
        if not directory:
            return
        self._repository.add_root(directory)
        self._refresh_settings_state()
        self._start_scan("import")

    def _on_add_root(self, path: str) -> None:
        self._repository.add_root(path)
        self._refresh_settings_state()
        self._start_scan("add_path")

    def _on_remove_root(self, path: str) -> None:
        moved_count = self._repository.remove_root(path)
        summary = self._repository.read_scan_report()
        summary["moved_to_missed_count"] = moved_count
        summary["trigger"] = "remove_root"
        self._repository.write_scan_report(summary)
        self._repository.record_scan_event("remove_root", summary)
        self._reload_resources_from_repository()
        self._refresh_settings_state()
        QMessageBox.information(
            self,
            tr("settings.root_removed_title", "Library folder removed"),
            tr(
                "settings.root_removed_msg",
                "{count} books moved to Missed because the folder was removed from scan roots.",
            ).format(count=moved_count),
        )

    def _on_scan_depth_changed(self, depth: int) -> None:
        self._repository.set_scan_depth(depth)

    def _on_hash_strategy_changed(self, strategy: str) -> None:
        self._repository.set_hash_strategy(strategy)

    def _start_scan(self, trigger: str) -> None:
        if self._thumbnail_worker is not None and self._thumbnail_worker.isRunning():
            return
        if self._scan_worker is not None and self._scan_worker.isRunning():
            return
        roots = self._repository.list_roots()
        if not roots:
            return
        self.settings_page.set_scan_running(True)
        worker = ScanWorker(
            db_path=self._repository.db_path,
            scan_report_path=self._repository.scan_report_path,
            roots=roots,
            scan_depth=self._repository.get_scan_depth(),
            hash_strategy=self._repository.get_hash_strategy(),
            trigger=trigger,
        )
        worker.scan_completed.connect(self._on_scan_completed)
        worker.scan_failed.connect(self._on_scan_failed)
        worker.finished.connect(self._on_worker_finished)
        self._scan_worker = worker
        worker.start()

    def _on_scan_completed(self, summary_obj: object) -> None:
        summary = summary_obj if isinstance(summary_obj, dict) else {}
        self.settings_page.set_scan_running(False)
        self.settings_page.set_scan_summary(summary)
        self._reload_resources_from_repository()
        conflicts = summary.get("name_conflicts", [])
        if isinstance(conflicts, list) and conflicts:
            self._show_name_conflicts(conflicts)
        errors = summary.get("errors", [])
        if isinstance(errors, list) and errors:
            self._show_scan_errors(errors)

    def _on_scan_failed(self, message: str) -> None:
        self.settings_page.set_scan_running(False)
        QMessageBox.critical(self, tr("scan.failed_title", "Scan failed"), message)

    def _on_worker_finished(self) -> None:
        self._scan_worker = None

    def _show_name_conflicts(self, conflicts: list[object]) -> None:
        lines = []
        for item in conflicts[:10]:
            if not isinstance(item, dict):
                continue
            file_name = str(item.get("file_name") or "")
            incoming = str(item.get("incoming_path") or "")
            existing_title = str(item.get("existing_title") or "")
            lines.append(f"- {file_name} | {existing_title}\n  new: {incoming}")
        extra_count = max(0, len(conflicts) - len(lines))
        if extra_count:
            lines.append(f"... and {extra_count} more conflicts")
        message = "\n".join(lines) if lines else tr("scan.conflict.empty", "Name conflicts detected.")
        QMessageBox.warning(
            self,
            tr("scan.conflict_title", "Duplicate name and extension detected"),
            tr(
                "scan.conflict_msg",
                "Some files were skipped because same file name + extension already exists.\n\n{details}",
            ).format(details=message),
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

    def _on_language_changed(self, language_code: str) -> None:
        language_manager.set_language(language_code)
        self.retranslate_ui()

    def _start_cleanup_thumbnails(self) -> None:
        self._start_thumbnail_task("cleanup")

    def _start_regenerate_thumbnails(self) -> None:
        self._start_thumbnail_task("regenerate")

    def _start_thumbnail_task(self, task_kind: str) -> None:
        if self._scan_worker is not None and self._scan_worker.isRunning():
            return
        if self._thumbnail_worker is not None and self._thumbnail_worker.isRunning():
            return
        self._active_thumbnail_task_kind = task_kind
        self.settings_page.set_thumbnail_task_running(task_kind, True)
        worker = ThumbnailTaskWorker(
            db_path=self._repository.db_path,
            scan_report_path=self._repository.scan_report_path,
            task_kind=task_kind,
        )
        worker.progress.connect(self._on_thumbnail_task_progress)
        worker.completed.connect(self._on_thumbnail_task_completed)
        worker.failed.connect(self._on_thumbnail_task_failed)
        worker.finished.connect(self._on_thumbnail_worker_finished)
        self._thumbnail_worker = worker
        worker.start()

    def _on_thumbnail_task_progress(self, current: int, total: int, _label: str) -> None:
        task_kind = self._active_thumbnail_task_kind or "regenerate"
        self.settings_page.set_thumbnail_task_progress(current, total, task_kind)

    def _on_thumbnail_task_completed(self, summary_obj: object) -> None:
        summary = summary_obj if isinstance(summary_obj, dict) else {}
        task_kind = str(summary.get("task_kind") or self._active_thumbnail_task_kind or "cleanup")
        self.settings_page.set_thumbnail_task_running(task_kind, False)
        self.settings_page.set_thumbnail_task_finished(task_kind, summary)
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
        QMessageBox.information(
            self,
            tr("settings.thumb.result_title", "Thumbnail task finished"),
            tr(
                "settings.thumb.result_msg",
                "Task: {task}\nTotal: {total}\nSuccess: {succeeded}\nSkipped: {skipped}\nFailed: {failed}",
            ).format(
                task=task_kind,
                total=total,
                succeeded=succeeded,
                skipped=skipped,
                failed=failed,
            ),
        )

    def _on_thumbnail_task_failed(self, message: str) -> None:
        task_kind = self._active_thumbnail_task_kind or "cleanup"
        self.settings_page.set_thumbnail_task_running(task_kind, False)
        QMessageBox.critical(self, tr("settings.thumb.failed_title", "Thumbnail task failed"), message)

    def _on_thumbnail_worker_finished(self) -> None:
        self._thumbnail_worker = None
        self._active_thumbnail_task_kind = None

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("app.window_title", "Simple Book Library - UI Outline"))
        self.sidebar.retranslate_ui()
        self.topbar.retranslate_ui()
        self.library_page.retranslate_ui()
        self.missed_page.retranslate_ui()
        self.plugins_page.retranslate_ui()
        self.settings_page.retranslate_ui()
