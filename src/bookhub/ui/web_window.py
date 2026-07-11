from __future__ import annotations

import json

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMainWindow, QMessageBox
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

# Match CSS --bg-0 so Chromium clear-on-activate does not flash pure white.
_WEB_BG_DAY = QColor("#eef5f7")
_WEB_BG_NIGHT = QColor("#101925")

from bookhub.i18n import language_manager, tr
from bookhub.library import LibraryRepository, ScanWorker, ThumbnailTaskWorker
from bookhub.library.error_logs import append_conflict_if_new, read_latest_log_text
from bookhub.ui.dialogs.text_rule_dialog import TextRuleDialog
from bookhub.ui.resources.font_runtime import (
    DEFAULT_PROJECT_FONTS_DIR,
    resolve_effective_font,
    scan_project_fonts_and_register,
)
from bookhub.ui.resources.layout_config import (
    UI_LAYOUT,
    normalize_card_spacing,
    normalize_cover_selected_border_color,
    normalize_cover_selected_border_width,
    normalize_topbar_search_font_size,
)
from bookhub.ui.resources.styles import DEFAULT_FONT_STACK
from bookhub.ui.web_bridge import UiBridge
from bookhub.ui.web_scheme import AppSchemeHandler

APP_INDEX_URL = "app://app/index.html"


class WebAppWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._repository = LibraryRepository()
        language_manager.set_language(self._repository.get_language_code())
        self.setWindowTitle(tr("app.window_title", "Simple Book Library"))
        self.resize(1400, 860)

        UI_LAYOUT.set_card_spacing(self._repository.get_card_spacing())
        UI_LAYOUT.set_topbar_search_font_size(self._repository.get_topbar_search_font_size())
        UI_LAYOUT.set_cover_selected_border_width(self._repository.get_cover_selected_border_width())
        UI_LAYOUT.set_cover_selected_border_color(self._repository.get_cover_selected_border_color())

        self._allowed_images: set[str] = set()
        self._project_font_families: list[str] = []
        self._scan_worker: ScanWorker | None = None
        self._thumbnail_worker: ThumbnailTaskWorker | None = None
        self._active_thumbnail_task_kind: str | None = None
        self._active_thumbnail_task_scope: str | None = None

        self._view = QWebEngineView(self)
        # Suppress Chromium's default English context menu; JS owns all menus.
        self._view.setContextMenuPolicy(Qt.NoContextMenu)
        settings = self._view.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.ShowScrollBars, False)
        # Opaque page clear color: Windows focus restore otherwise flashes white.
        self._view.page().setBackgroundColor(_WEB_BG_DAY)
        self.setCentralWidget(self._view)

        self._scheme_handler = AppSchemeHandler(self._allowed_images, self)
        profile = self._view.page().profile()
        profile.installUrlSchemeHandler(b"app", self._scheme_handler)

        self._channel = QWebChannel(self)
        self._bridge = UiBridge(self._repository, self._allowed_images, self)
        self._bridge.set_host(self)
        self._channel.registerObject("bridge", self._bridge)
        self._view.page().setWebChannel(self._channel)

        self._refresh_project_fonts(ensure_dir=False)
        self._apply_font_to_app(self._repository.get_font_family())

        self._zoom_save_timer = QTimer(self)
        self._zoom_save_timer.setSingleShot(True)
        self._zoom_save_timer.setInterval(350)
        self._zoom_save_timer.timeout.connect(self._persist_web_zoom)
        self._last_persisted_zoom = self._clamp_zoom(self._repository.get_setting("web_zoom_factor", 1.0))
        self._view.setZoomFactor(self._last_persisted_zoom)
        self._view.loadFinished.connect(self._on_web_load_finished)

        self._zoom_poll_timer = QTimer(self)
        self._zoom_poll_timer.setInterval(500)
        self._zoom_poll_timer.timeout.connect(self._poll_web_zoom)
        self._zoom_poll_timer.start()

        self._view.load(QUrl(APP_INDEX_URL))

        if self._repository.get_scan_on_startup():
            QTimer.singleShot(400, lambda: self.start_scan("all"))

    def set_web_page_background(self, theme: str) -> None:
        color = _WEB_BG_NIGHT if theme == "night" else _WEB_BG_DAY
        self._view.page().setBackgroundColor(color)

    @staticmethod
    def _clamp_zoom(value: object) -> float:
        try:
            factor = float(value)
        except (TypeError, ValueError):
            factor = 1.0
        return max(0.5, min(2.5, factor))

    def _on_web_load_finished(self, ok: bool) -> None:
        if not ok:
            return
        # Chromium may reset zoom on navigation; re-apply persisted value.
        self._view.setZoomFactor(self._last_persisted_zoom)

    def _poll_web_zoom(self) -> None:
        current = round(float(self._view.zoomFactor()), 4)
        if abs(current - self._last_persisted_zoom) < 0.001:
            return
        self._zoom_save_timer.start()

    def _persist_web_zoom(self) -> None:
        factor = self._clamp_zoom(self._view.zoomFactor())
        if abs(factor - float(self._view.zoomFactor())) > 0.001:
            self._view.setZoomFactor(factor)
        if abs(factor - self._last_persisted_zoom) < 0.001:
            return
        self._last_persisted_zoom = factor
        self._repository.set_setting("web_zoom_factor", factor)

    # ---- exposed to bridge (project fonts) -----------------------------
    def project_fonts(self) -> list[str]:
        return list(self._project_font_families)

    def _refresh_project_fonts(self, *, ensure_dir: bool) -> None:
        scan_result = scan_project_fonts_and_register(DEFAULT_PROJECT_FONTS_DIR, ensure_dir=ensure_dir)
        self._project_font_families = list(scan_result.registered_families)

    def _apply_font_to_app(self, family: str) -> None:
        app = QApplication.instance()
        selected = str(family or "").strip()
        if app is not None and selected:
            app.setFont(QFont(selected))

    # ---- settings ------------------------------------------------------
    def apply_setting(self, key: str, value: str) -> None:
        repo = self._repository
        reload_needed = False
        if key == "language":
            language_manager.set_language(value)
            repo.set_language_code(value)
            self._reload_ui_strings()
            return
        if key == "fontSource" or key == "fontFamily":
            source = value if key == "fontSource" else repo.get_font_source()
            family = value if key == "fontFamily" else repo.get_font_family()
            self._apply_font_selection(source, family)
            return
        if key == "searchFontSize":
            repo.set_topbar_search_font_size(normalize_topbar_search_font_size(value))
        elif key == "scanDepth":
            repo.set_scan_depth(int(value))
        elif key == "hashStrategy":
            repo.set_hash_strategy(value)
        elif key == "cardSpacing":
            repo.set_card_spacing(normalize_card_spacing(value))
            UI_LAYOUT.set_card_spacing(repo.get_card_spacing())
        elif key == "coverBorderWidth":
            repo.set_cover_selected_border_width(normalize_cover_selected_border_width(value))
        elif key == "coverBorderColor":
            repo.set_cover_selected_border_color(normalize_cover_selected_border_color(value))
        elif key == "scanOnStartup":
            repo.set_scan_on_startup(self._as_bool(value))
        elif key == "autoScanOnPathChange":
            repo.set_auto_scan_on_path_change(self._as_bool(value))
        elif key == "textPreviewChars":
            repo.set_text_preview_chars(int(value))
        elif key == "comicViewMode":
            repo.set_comic_view_mode(value)
            reload_needed = True
        elif key == "comicPageSize":
            repo.set_comic_page_size(int(value))
            reload_needed = True
        if reload_needed:
            self._bridge.push_resources()

    @staticmethod
    def _as_bool(value: str) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _apply_font_selection(self, source: str, family: str) -> None:
        system_families = sorted({str(n).strip() for n in QFontDatabase.families() if str(n).strip()})
        resolved = resolve_effective_font(source, family, system_families, self._project_font_families)
        self._repository.set_font_source(resolved.source)
        self._repository.set_font_family(resolved.family)
        self._apply_font_to_app(resolved.family)

    def reload_fonts(self) -> None:
        self._refresh_project_fonts(ensure_dir=True)
        self._apply_font_selection(self._repository.get_font_source(), self._repository.get_font_family())
        self._bridge.push_settings()
        self._bridge.emit_toast(tr("settings.font.reload", "Reload Fonts"), tr("settings.font.toast.success", "Fonts reloaded."), "info")

    def _reload_ui_strings(self) -> None:
        # Rebuild bootstrap-driven strings in the web layer.
        self._view.page().runJavaScript("window.__reloadBootstrap && window.__reloadBootstrap();")

    # ---- roots ---------------------------------------------------------
    def add_root(self, kind: str) -> None:
        directory = QFileDialog.getExistingDirectory(self, tr("import.pick_dir", "Select folder"))
        if not directory:
            return
        repo = self._repository
        if kind == "comic":
            repo.add_comic_root(directory)
            scope = "comic"
        elif kind == "text":
            repo.add_text_root(directory)
            scope = "text"
        else:
            repo.add_root(directory)
            scope = "library"
        self._bridge.reload_data()
        self._bridge.push_resources()
        self._bridge.push_settings()
        if repo.get_auto_scan_on_path_change():
            self.start_scan(scope)

    def remove_root(self, kind: str, path: str) -> None:
        repo = self._repository
        if kind == "comic":
            repo.remove_comic_root(path)
        elif kind == "text":
            repo.remove_text_root(path)
        else:
            repo.remove_root(path)
        self._bridge.reload_data()
        self._bridge.push_resources()
        self._bridge.push_settings()

    def edit_cover(self, resource_id: str) -> None:
        """Native file pick + write thumbnail; mirrors library_page._edit_cover."""
        from pathlib import Path as _Path

        repo = self._repository
        book_id = repo.get_book_int_id(resource_id)
        if book_id is None:
            QMessageBox.warning(
                self,
                tr("cover.error_title", "Error"),
                tr("cover.book_missing", "Book record not found; cannot update cover."),
            )
            return

        image_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("cover.pick_title", "Select cover image"),
            "",
            tr(
                "cover.pick_filter",
                "Image files (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff *.tif)",
            ),
        )
        if not image_path:
            return

        src = _Path(image_path)
        if not src.exists():
            QMessageBox.warning(
                self,
                tr("cover.error_title", "Error"),
                tr("cover.file_missing", "File not found: {path}").format(path=src),
            )
            return

        try:
            import hashlib as _hashlib

            from PIL import Image as _Image

            from bookhub.library.repository import DEFAULT_PREVIEW_DIR

            DEFAULT_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
            name_hash = _hashlib.md5(str(src).encode("utf-8", errors="replace")).hexdigest()[:16]
            out_path = DEFAULT_PREVIEW_DIR / f"cover_{name_hash}.webp"

            img = _Image.open(str(src))
            img = img.convert("RGB")
            img.save(str(out_path), format="WebP", quality=80)

        except ImportError:
            import hashlib as _hashlib
            import shutil as _shutil

            from bookhub.library.repository import DEFAULT_PREVIEW_DIR

            DEFAULT_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
            name_hash = _hashlib.md5(str(src).encode("utf-8", errors="replace")).hexdigest()[:16]
            out_path = DEFAULT_PREVIEW_DIR / f"cover_{name_hash}{src.suffix.lower()}"
            _shutil.copy2(str(src), str(out_path))

        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("cover.update_failed", "Cover update failed"),
                tr("cover.image_error", "Image processing error: {err}").format(err=exc),
            )
            return

        file_url = out_path.as_uri()
        try:
            repo.update_book_thumbnail_path(book_id, file_url)
        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("cover.update_failed", "Cover update failed"),
                tr("cover.db_error", "Database write error: {err}").format(err=exc),
            )
            return

        self._bridge.reload_data()
        self._bridge.push_resources()
        self._bridge.emit_toast(
            tr("cover.updated_title", "Cover updated"),
            tr("cover.updated_msg", "Thumbnail saved."),
            "info",
        )

    def open_text_rules(self, root_path: str) -> None:
        repo = self._repository
        existing = repo.get_text_root_rules_json(root_path)
        dialog = TextRuleDialog(
            root_path,
            existing,
            self,
            preview_chars=repo.get_text_preview_chars(),
            preview_result_height=repo.get_text_rule_preview_result_height(),
            preview_result_height_changed=repo.set_text_rule_preview_result_height,
            dialog_size=repo.get_text_rule_dialog_size(),
            dialog_size_changed=repo.set_text_rule_dialog_size,
            rule_presets=repo.get_text_rule_presets(),
            rule_presets_changed=repo.set_text_rule_presets,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        repo.set_text_root_rules_json(root_path, dialog.rules_json())
        self._bridge.push_settings()
        if repo.get_auto_scan_on_path_change():
            self.start_scan("text")

    # ---- scan ----------------------------------------------------------
    def start_scan(self, scope: str = "all") -> None:
        if self._thumbnail_worker is not None and self._thumbnail_worker.isRunning():
            return
        if self._scan_worker is not None and self._scan_worker.isRunning():
            return
        repo = self._repository
        roots = repo.list_roots() if scope in {"all", "library"} else []
        comic_roots = repo.list_comic_roots() if scope in {"all", "comic"} else []
        text_roots = repo.list_text_roots_with_rules() if scope in {"all", "text"} else []
        if not roots and not comic_roots and not text_roots:
            self._bridge.emit_toast(tr("scan.none_title", "Nothing to scan"), tr("scan.none_msg", "Add a folder first."), "warning")
            return
        self._emit_scan_state(scope, True)
        worker = ScanWorker(
            db_path=repo.db_path,
            scan_report_path=repo.scan_report_path,
            roots=roots,
            comic_roots=comic_roots,
            text_roots=text_roots,
            text_preview_chars=repo.get_text_preview_chars(),
            scan_depth=repo.get_scan_depth(),
            hash_strategy=repo.get_hash_strategy(),
            comic_placeholder_copy_enabled=repo.get_comic_placeholder_copy_enabled(),
            comic_thumbnail_workers_used=repo.get_comic_thumbnail_workers(),
            trigger="manual_" + scope,
            scope=scope,
        )
        worker.scan_completed.connect(self._on_scan_completed)
        worker.scan_failed.connect(self._on_scan_failed)
        worker.progress.connect(self._on_scan_progress)
        worker.finished.connect(self._on_scan_worker_finished)
        self._scan_worker = worker
        worker.start()

    def _emit_scan_state(self, scope: str, running: bool) -> None:
        self._bridge.scanState.emit(json.dumps({"scope": scope, "running": running}, ensure_ascii=False))

    def _on_scan_progress(self, current: int, total: int, label: str, snapshot_obj: object) -> None:
        payload = {"current": current, "total": total, "label": label}
        self._bridge.scanProgress.emit(json.dumps(payload, ensure_ascii=False))

    def _on_scan_completed(self, summary_obj: object) -> None:
        summary = summary_obj if isinstance(summary_obj, dict) else {}
        scope = str(summary.get("scope") or "all")
        self._emit_scan_state(scope, False)
        self._bridge.reload_data()
        self._bridge.push_resources()
        self._bridge.push_settings()
        conflicts = summary.get("name_conflicts", [])
        if isinstance(conflicts, list) and conflicts:
            for item in conflicts:
                if isinstance(item, dict):
                    file_name = str(item.get("file_name") or "").strip()
                    src = str(item.get("source_path") or item.get("path") or "").strip()
                    existing = str(item.get("existing_path") or "").strip()
                    append_conflict_if_new(f"conflict={file_name} | source={src} | existing={existing}")
            self._bridge.errorLogsChanged.emit(read_latest_log_text())
        added = int(summary.get("added_count", 0) or 0) + int(summary.get("text_added_count", 0) or 0)
        self._bridge.emit_toast(
            tr("scan.done_title", "Scan completed"),
            tr("scan.done_msg", "Imported {count} new items.").format(count=added),
            "info",
        )

    def _on_scan_failed(self, message: str) -> None:
        self._emit_scan_state("all", False)
        self._bridge.emit_toast(tr("scan.failed_title", "Scan failed"), message, "warning")

    def _on_scan_worker_finished(self) -> None:
        self._scan_worker = None

    # ---- thumbnail tasks ----------------------------------------------
    def start_thumbnail_task(self, task_kind: str, scope: str) -> None:
        if self._scan_worker is not None and self._scan_worker.isRunning():
            return
        if self._thumbnail_worker is not None and self._thumbnail_worker.isRunning():
            return
        self._active_thumbnail_task_kind = task_kind
        self._active_thumbnail_task_scope = scope
        self._emit_scan_state(scope + ":thumb", True)
        repo = self._repository
        worker = ThumbnailTaskWorker(
            db_path=repo.db_path,
            scan_report_path=repo.scan_report_path,
            task_kind=task_kind,
            task_scope=scope,
            comic_workers=repo.get_comic_thumbnail_workers() if scope == "comic" else None,
        )
        worker.progress.connect(self._on_thumbnail_progress)
        worker.completed.connect(self._on_thumbnail_completed)
        worker.failed.connect(self._on_thumbnail_failed)
        worker.finished.connect(self._on_thumbnail_finished)
        self._thumbnail_worker = worker
        worker.start()

    def _on_thumbnail_progress(self, current: int, total: int, _label: str) -> None:
        self._bridge.scanProgress.emit(json.dumps({"current": current, "total": total, "label": "thumbnail"}, ensure_ascii=False))

    def _on_thumbnail_completed(self, summary_obj: object) -> None:
        summary = summary_obj if isinstance(summary_obj, dict) else {}
        scope = str(summary.get("task_scope") or self._active_thumbnail_task_scope or "library")
        self._emit_scan_state(scope + ":thumb", False)
        self._bridge.reload_data()
        self._bridge.push_resources()
        succeeded = int(summary.get("succeeded", 0) or 0)
        failed = int(summary.get("failed", 0) or 0)
        self._bridge.emit_toast(
            tr("settings.thumb.result_title", "Thumbnail task finished"),
            tr("settings.thumb.brief", "Success: {s}, Failed: {f}").format(s=succeeded, f=failed),
            "info",
        )

    def _on_thumbnail_failed(self, message: str) -> None:
        scope = self._active_thumbnail_task_scope or "library"
        self._emit_scan_state(scope + ":thumb", False)
        self._bridge.emit_toast(tr("settings.thumb.failed_title", "Thumbnail task failed"), message, "warning")

    def _on_thumbnail_finished(self) -> None:
        self._thumbnail_worker = None
        self._active_thumbnail_task_kind = None
        self._active_thumbnail_task_scope = None
