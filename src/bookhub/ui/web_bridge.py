from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

from PySide6.QtCore import QObject, Signal, Slot

from bookhub.i18n import tr
from bookhub.ui.viewmodels.library_viewmodel import LibraryViewModel
from bookhub.ui.web_scheme import to_local_path

PAGE_LIBRARY = "library"
PAGE_TEXT = "text_novel"
PAGE_COLLECTIONS = "collections"
PAGE_FAVORITES = "favorites"
PAGE_COMIC = "comic"
PAGE_COMIC_FAV = "comic_fav"

NAV_ITEMS = [
    (PAGE_LIBRARY, "sidebar.library", "Library"),
    (PAGE_TEXT, "sidebar.text_novel", "Text Novel"),
    (PAGE_COLLECTIONS, "sidebar.collections", "Collections"),
    (PAGE_FAVORITES, "sidebar.favorites", "Favorites"),
    (PAGE_COMIC, "sidebar.comic", "Comic"),
    (PAGE_COMIC_FAV, "sidebar.comic_fav", "Comic Fav"),
]


def _web_strings() -> dict[str, str]:
    keys = [
        ("sidebar.title", "Bookshelf"),
        ("sidebar.subtitle", "Local Database"),
        ("sidebar.settings", "Settings"),
        ("sidebar.import_books", "Import Books"),
        ("sidebar.library", "Library"),
        ("sidebar.text_novel", "Text Novel"),
        ("sidebar.collections", "Collections"),
        ("sidebar.favorites", "Favorites"),
        ("sidebar.comic", "Comic"),
        ("sidebar.comic_fav", "Comic Fav"),
        ("view.grid", "Grid"),
        ("view.list", "List"),
        ("topbar.scan", "Scan"),
        ("topbar.search_placeholder", "Search library..."),
        ("topbar.search_text_placeholder", "Search text novels by title, author, tag, or path..."),
        ("detail.empty", "Select an item to see its details."),
        ("detail.author", "Author"),
        ("detail.publisher", "Publisher"),
        ("detail.tags", "Tags"),
        ("detail.collections", "Collections"),
        ("detail.file", "File"),
        ("detail.images", "Images"),
        ("detail.preview", "Text Preview"),
        ("detail.open", "Open"),
        ("detail.quick_add", "Quick Add"),
        ("detail.edit_cover", "Edit Cover"),
        ("detail.favorite_add", "Add to Favorites"),
        ("detail.favorite_remove", "Remove from Favorites"),
        ("menu.open_external", "Open External"),
        ("menu.open_cover", "Open Cover"),
        ("menu.quick_add", "Quick Add Tag / Collection"),
        ("menu.edit_cover", "Edit Cover..."),
        ("menu.remove_library", "Remove from Library"),
        ("library.remove.confirm_title", "Remove from Library"),
        ("library.remove.confirm_text", "Remove “{title}” from the library database?\nFiles on disk will not be deleted."),
        ("library.remove.done_title", "Removed"),
        ("library.remove.done_msg", "Item removed from the library database."),
        ("library.remove.failed_title", "Remove failed"),
        ("library.remove.failed_msg", "Record not found."),
        ("menu.favorite_add", "Add to Favorites"),
        ("menu.favorite_remove", "Remove from Favorites"),
        ("menu.comic_fav_add", "Add to Comic Fav"),
        ("menu.comic_fav_remove", "Remove from Comic Fav"),
        ("menu.collection_remove", "Remove from Collection"),
        ("menu.collection_open", "Open"),
        ("menu.collection_rename", "Rename"),
        ("menu.collection_delete", "Delete"),
        ("menu.open_folder", "Open Folder"),
        ("common.cancel", "Cancel"),
        ("common.confirm", "Confirm"),
        ("common.save", "Save"),
        ("common.close", "Close"),
        ("common.new_list", "New List"),
        ("common.back", "Back"),
        ("collections.count", "{count} books"),
        ("collections.empty", "No collections yet."),
        ("collections.rename_title", "Rename Collection"),
        ("collections.rename_placeholder", "New name..."),
        ("collections.delete_title", "Delete Collection"),
        ("collections.delete_msg", "Delete this collection? Books will not be removed from the library."),
        ("comic.sort.folder_mtime_desc", "Folder Date: Newest First"),
        ("comic.sort.folder_mtime_asc", "Folder Date: Oldest First"),
        ("comic.sort.folder_name_asc", "Folder Name: A-Z"),
        ("comic.sort.folder_name_desc", "Folder Name: Z-A"),
        ("favorites.sort.label", "Sort"),
        ("favorites.sort.added_desc", "Added Time: Newest First"),
        ("favorites.sort.added_asc", "Added Time: Oldest First"),
        ("comic.sort.label", "Sort"),
        ("comic.pagination.prev", "Prev"),
        ("comic.pagination.next", "Next"),
        ("comic.pagination.status", "Page {current}/{total}"),
        ("page.count", "{count} items"),
        ("topbar.scanning", "Scanning..."),
        ("detail.cover", "Cover"),
        ("detail.title", "Title"),
        ("detail.path", "Path"),
        ("quick_add.tag_placeholder", "Type tag..."),
        ("quick_add.collection_placeholder", "Search collections..."),
        ("quick_add.new_collection_placeholder", "New collection name..."),
        ("quick_add.recent_tags", "Recent tags"),
        ("quick_add.add", "Add"),
        ("quick_add.added", "Added"),
        ("quick_add.confirm", "Confirm add"),
        ("settings.title", "Settings"),
        ("settings.nav.general", "General"),
        ("settings.nav.paths", "Paths"),
        ("settings.nav.appearance", "Appearance & Theme"),
        ("settings.nav.tasks", "Scan & Tasks"),
        ("settings.nav.errors", "Error logs"),
        ("settings.language", "Display language"),
        ("settings.font_source", "Font source"),
        ("settings.font_family", "Font family"),
        ("settings.search_font", "Search font size"),
        ("settings.scan_depth", "Scan depth"),
        ("settings.hash", "Missed hash matching"),
        ("settings.hash.fast", "Fast"),
        ("settings.hash.strict", "Strict"),
        ("settings.hash.quick", "Quick"),
        ("settings.card_spacing", "Card spacing"),
        ("settings.cover_border_width", "Cover selected border width"),
        ("settings.cover_border_color", "Cover selected border color"),
        ("settings.scan_startup", "Scan on startup"),
        ("settings.auto_scan", "Auto scan on path change"),
        ("settings.text_preview_chars", "Text preview length"),
        ("settings.comic_view_mode", "Comic view mode"),
        ("settings.comic_view_waterfall", "Waterfall"),
        ("settings.comic_view_pagination", "Pagination"),
        ("settings.comic_page_size", "Comic page size"),
        ("settings.viewport_buffer_screens", "Viewport buffer screens"),
        ("settings.grid_columns", "Covers per row"),
        ("settings.comic.placeholder_copy", "Comic scan: copy first image as placeholder"),
        ("settings.comic.auto_thumb_after_scan", "Auto-complete comic thumbnails after scan"),
        ("settings.comic.thumbnail_workers", "Comic thumbnail workers"),
        ("settings.comic.workers.auto", "Auto"),
        ("settings.font_source.system", "System"),
        ("settings.font_source.project", "Project fonts"),
        ("settings.font_family.default", "(default)"),
        ("settings.night.title", "Night mode"),
        ("settings.night.desc", "Read local time periodically and transition between day and night UI."),
        ("settings.night.auto", "Auto by local time"),
        ("settings.night.mode", "Theme mode"),
        ("settings.night.start", "Night starts"),
        ("settings.night.resume", "Day resumes"),
        ("settings.night.frequency", "Check frequency (minutes)"),
        ("settings.night.transition", "Auto transition duration (minutes)"),
        ("theme.auto", "Auto"),
        ("theme.day", "Day"),
        ("theme.night", "Night"),
        ("settings.roots.library", "Library roots"),
        ("settings.roots.comic", "Comic roots"),
        ("settings.roots.text", "Text novel roots"),
        ("settings.roots.add", "Add folder"),
        ("settings.roots.rules", "Rules"),
        ("settings.roots.rules_hint", "Open Text Rules editor for this folder"),
        ("settings.roots.delete", "Delete"),
        ("text.rules.title", "Text Rules"),
        ("text.rules.root", "Path: {path}"),
        ("text.rules.fields", "Fields"),
        ("text.rules.chain", "Rule Chain"),
        ("text.rules.add_rule", "Add Rule"),
        ("text.rules.delete_rule", "Delete Rule"),
        ("text.rules.move_up", "Move up"),
        ("text.rules.move_down", "Move down"),
        ("text.rules.source", "Source"),
        ("text.rules.steps", "Steps"),
        ("text.rules.add_step", "Add Step"),
        ("text.rules.templates", "Templates"),
        ("text.rules.presets", "My Presets"),
        ("text.rules.preset.save", "Save as preset"),
        ("text.rules.preset.delete", "Delete preset"),
        ("text.rules.preset.name_prompt", "Preset name"),
        ("text.rules.preview", "Preview"),
        ("text.rules.sample", "Sample TXT"),
        ("text.rules.sample.empty", "(no TXT found)"),
        ("text.rules.multi", "Multi-sample"),
        ("text.rules.multi.run", "Run 20"),
        ("text.rules.preview.running", "Running…"),
        ("text.rules.save", "Save"),
        ("text.rules.cancel", "Cancel"),
        ("text.rules.save_failed", "Save failed"),
        ("text.rules.saved_title", "Text Rules saved"),
        ("text.rules.saved_msg", "Rules updated for this folder."),
        ("text.rules.open_failed", "Cannot open Text Rules"),
        ("text.rules.regex.button", "Common Regex"),
        ("text.rules.regex.title", "Common Regex"),
        ("text.rules.regex.copy", "Copy"),
        ("text.rules.help.button", "Usage Guide"),
        ("text.rules.help.title", "Text Rules Guide"),
        ("text.rules.field.title", "Title"),
        ("text.rules.field.author", "Author"),
        ("text.rules.field.series", "Series"),
        ("text.rules.field.tag", "Tag"),
        ("settings.delete_confirm_title", "Confirm Delete"),
        ("settings.delete_confirm_text", "Remove this folder from the library?\n{path}\nBooks under it will be removed from the database (files on disk are not deleted)."),
        ("settings.scan_summary_title", "Last scan summary"),
        ("settings.scan_summary_template", "Last scan: {updated_at}\nScope: {scope} | Added: {added} | Ignored unsupported: {ignored} | Name conflicts: {conflicts}\nRemoved missing: {removed_total} (library/text: {removed_books}, comic: {removed_comics})"),
        ("settings.scan_summary_skipped", "\nLibrary unchanged skipped: {skipped}"),
        ("settings.text.scan_summary", "\nText Novel - scanned:{scanned} added:{added} updated:{updated}"),
        ("settings.comic.scan_perf_summary", "\nComic - added:{added} updated:{updated} placeholders:{copied} thumbs queued:{queued} workers:{workers} downscaled:{downscaled}"),
        ("scan.done_msg_with_skipped", "Imported {count} new items ({skipped} unchanged skipped)."),
        ("scan.busy_title", "Busy"),
        ("scan.busy_scan_msg", "A scan is already running. Please wait."),
        ("scan.busy_thumb_msg", "A thumbnail task is running. Please wait."),
        ("topbar.thumb_busy", "Working..."),
        ("settings.thumb.auto.title", "Comic thumbnails queued"),
        ("settings.thumb.auto.msg", "Comic scan finished. Queued {count} thumbnails for background generation ({workers} workers)."),
        ("settings.tasks.scan_library", "Scan Library"),
        ("settings.tasks.scan_comic", "Scan Comic"),
        ("settings.tasks.scan_text", "Scan Text Novel"),
        ("settings.tasks.cleanup_library", "Cleanup Library Thumbnails"),
        ("settings.tasks.regen_library", "Regenerate Library Thumbnails"),
        ("settings.tasks.cleanup_comic", "Cleanup Comic Thumbnails"),
        ("settings.tasks.regen_comic", "Regenerate Comic Thumbnails"),
        ("settings.tasks.reload_fonts", "Reload Fonts"),
        ("settings.errors.refresh", "Refresh"),
        ("add_tag.title", "Add Tag"),
        ("empty.default", "Nothing here yet."),
    ]
    return {key: tr(key, fallback) for key, fallback in keys}


class UiBridge(QObject):
    resourcesChanged = Signal(str)
    toast = Signal(str)
    scanProgress = Signal(str)
    scanState = Signal(str)
    settingsChanged = Signal(str)
    errorLogsChanged = Signal(str)
    languageChanged = Signal(str)
    textRulesOpen = Signal(str)

    def __init__(self, repository, allowed_images: set[str], parent=None) -> None:
        super().__init__(parent)
        self._repo = repository
        self._allowed_images = allowed_images
        self._host = None
        self._library_vm = LibraryViewModel()
        self._text_vm = LibraryViewModel()
        self._current_collection_id: int | None = None
        self.reload_data()

    def set_host(self, host) -> None:
        self._host = host

    # ---- data loading --------------------------------------------------
    def reload_data(self) -> None:
        records = self._repo.list_books(include_missing=None)
        library, text = [], []
        for record in records:
            if str(record.get("resource_type") or "") == "text_novel":
                text.append(record)
            else:
                library.append(record)
        self._library_records = library
        self._text_records = text
        self._library_vm.set_resources([self._record_to_item(r) for r in library])
        self._text_vm.set_resources([self._record_to_item(r) for r in text])

    def _record_to_item(self, record: dict[str, Any]):
        from bookhub.ui.models.resource import ResourceItem
        return ResourceItem(
            resource_id=record.get("resource_id", ""),
            title=record.get("title") or record.get("file_name") or "",
            author=record.get("author") or "",
            tags=list(record.get("tags") or []),
            resource_type=record.get("resource_type") or "book",
            path=record.get("path") or "",
            thumbnail_path=record.get("thumbnail_path"),
            publisher=record.get("publisher"),
            language=record.get("language"),
            is_missing=bool(record.get("is_missing")),
            info_text=str(record.get("info_text") or "") or None,
        )

    # ---- cover url -----------------------------------------------------
    def _cover_url(self, *candidates: str | None) -> str | None:
        for candidate in candidates:
            local = to_local_path(candidate)
            if not local:
                continue
            path = Path(local)
            if path.suffix.lower() not in {".webp", ".png", ".jpg", ".jpeg", ".gif", ".bmp"}:
                continue
            if not path.is_file():
                continue
            self._allowed_images.add(os.path.normcase(os.path.normpath(local)))
            return "app://img/x?p=" + quote(local, safe="")
        return None

    @staticmethod
    def _row_tags(row: dict[str, Any]) -> list[str]:
        if "tags" in row and isinstance(row["tags"], list):
            return [str(t) for t in row["tags"]]
        raw = row.get("tags_json") or "[]"
        try:
            tags = json.loads(raw)
        except (TypeError, ValueError):
            tags = []
        return [str(t) for t in tags] if isinstance(tags, list) else []

    def _book_payload(self, row: dict[str, Any]) -> dict[str, Any]:
        tags = self._row_tags(row)
        author = str(row.get("author") or "")
        publisher = str(row.get("publisher") or "")
        meta_parts = [p for p in [author, publisher] if p and p.lower() != "unknown"]
        return {
            "id": row.get("resource_id", ""),
            "title": row.get("title") or row.get("file_name") or "",
            "author": author,
            "publisher": publisher,
            "language": row.get("language") or "",
            "tags": tags,
            "path": row.get("path") or "",
            "type": row.get("resource_type") or "book",
            "cover": self._cover_url(row.get("thumbnail_path")),
            "meta": " · ".join(meta_parts),
            "info": str(row.get("info_text") or "") or "",
            "fileName": row.get("file_name") or "",
        }

    def _comic_payload(self, row: dict[str, Any]) -> dict[str, Any]:
        count = int(row.get("image_count") or 0)
        return {
            "id": row.get("resource_id", ""),
            "title": row.get("title") or Path(str(row.get("path") or "")).name or "Comic",
            "author": "",
            "tags": [],
            "path": row.get("path") or "",
            "type": "comic_folder",
            "cover": self._cover_url(row.get("thumbnail_path"), row.get("cover_image_path")),
            "coverImage": str(row.get("cover_image_path") or ""),
            "meta": tr("comic.meta.images", "{count} images").format(count=count),
            "imageCount": count,
            "info": str(row.get("info_text") or "") or "",
        }

    def _item_payload(self, item) -> dict[str, Any]:
        author = str(item.author or "")
        meta_parts = [p for p in [author] if p and p.lower() != "unknown"]
        return {
            "id": item.resource_id,
            "title": item.title,
            "author": author,
            "publisher": item.publisher or "",
            "language": item.language or "",
            "tags": list(item.tags or []),
            "path": item.path or "",
            "type": item.resource_type or "book",
            "cover": self._cover_url(item.thumbnail_path),
            "meta": " · ".join(meta_parts),
            "info": item.info_text or "",
            "fileName": item.file_name or "",
        }

    # ---- page payloads -------------------------------------------------
    def _page_resources(self, page: str) -> dict[str, Any]:
        if page == PAGE_LIBRARY:
            items = self._library_vm.filtered_resources(include_missing=False)
            return {"mode": "grid_or_list", "items": [self._item_payload(i) for i in items]}
        if page == PAGE_TEXT:
            items = self._text_vm.filtered_resources(include_missing=False)
            return {"mode": "list", "items": [self._item_payload(i) for i in items]}
        if page == PAGE_FAVORITES:
            order = str(self._repo.get_setting("favorites_sort_order", "desc") or "desc").strip().lower()
            if order not in {"asc", "desc"}:
                order = "desc"
            rows = self._repo.get_favorite_books(order=order)
            return {"mode": "grid_or_list", "sort": order, "items": [self._book_payload(r) for r in rows]}
        if page == PAGE_COMIC:
            order = self._repo.get_comic_sort_order_main()
            rows = self._repo.list_comics(include_missing=False, order_by=order)
            return self._comic_page_payload(rows, favorite=False)
        if page == PAGE_COMIC_FAV:
            order = self._repo.get_comic_sort_order_fav()
            rows = self._repo.get_favorite_comics(order_by=order)
            return self._comic_page_payload(rows, favorite=True)
        if page == PAGE_COLLECTIONS:
            return self._collections_payload()
        return {"mode": "grid_or_list", "items": []}

    def _comic_page_payload(self, rows: list[dict[str, Any]], *, favorite: bool) -> dict[str, Any]:
        return {
            "mode": "comic",
            "viewMode": self._repo.get_comic_view_mode(),
            "pageSize": self._repo.get_comic_page_size(),
            "sort": self._repo.get_comic_sort_order_fav() if favorite else self._repo.get_comic_sort_order_main(),
            "items": [self._comic_payload(r) for r in rows],
        }

    def _collections_payload(self) -> dict[str, Any]:
        if self._current_collection_id is not None:
            rows = self._repo.get_books_in_collection(self._current_collection_id)
            name = next(
                (c.get("name") for c in self._repo.get_all_collections() if int(c.get("id")) == self._current_collection_id),
                "",
            )
            return {
                "mode": "collection_detail",
                "collectionId": self._current_collection_id,
                "collectionName": name,
                "items": [self._book_payload(r) for r in rows],
            }
        collections = self._repo.get_all_collections()
        items = []
        for collection in collections:
            cid = int(collection.get("id"))
            books = self._repo.get_books_in_collection(cid)
            cover = None
            for book in books:
                cover = self._cover_url(book.get("thumbnail_path"))
                if cover:
                    break
            items.append({
                "id": str(cid),
                "collectionId": cid,
                "title": collection.get("name") or "",
                "meta": tr("collections.count", "{count} books").format(count=len(books)),
                "cover": cover,
                "type": "collection",
                "tags": [],
                "path": "",
            })
        return {"mode": "collections", "items": items}

    def _pages_payload(self) -> dict[str, Any]:
        return {page: self._page_resources(page) for page, _, _ in NAV_ITEMS}

    # ---- bootstrap / settings -----------------------------------------
    def _settings_payload(self) -> dict[str, Any]:
        repo = self._repo
        return {
            "language": repo.get_language_code(),
            "fontSource": repo.get_font_source(),
            "fontFamily": repo.get_font_family(),
            "projectFonts": getattr(self._host, "project_fonts", lambda: [])() if self._host else [],
            "searchFontSize": repo.get_topbar_search_font_size(),
            "scanDepth": repo.get_scan_depth(),
            "hashStrategy": repo.get_hash_strategy(),
            "cardSpacing": repo.get_card_spacing(),
            "coverBorderWidth": repo.get_cover_selected_border_width(),
            "coverBorderColor": repo.get_cover_selected_border_color(),
            "scanOnStartup": repo.get_scan_on_startup(),
            "autoScanOnPathChange": repo.get_auto_scan_on_path_change(),
            "textPreviewChars": repo.get_text_preview_chars(),
            "comicViewMode": repo.get_comic_view_mode(),
            "comicPageSize": repo.get_comic_page_size(),
            "viewportBufferScreens": repo.get_viewport_buffer_screens(),
            "gridColumns": repo.get_grid_columns(),
            "comicPlaceholderCopy": repo.get_comic_placeholder_copy_enabled(),
            "autoGenerateComicThumbs": repo.get_auto_generate_comic_thumbnails_after_scan(),
            "comicThumbnailWorkers": repo.get_comic_thumbnail_workers_raw(),
            "libraryRoots": repo.list_roots(),
            "comicRoots": repo.list_comic_roots(),
            "textRoots": repo.list_text_roots_with_rules(),
            "theme": self._theme_payload(),
            "scanReport": repo.read_scan_report(),
        }

    def _theme_payload(self) -> dict[str, Any]:
        repo = self._repo
        return {
            "mode": repo.get_setting("theme_mode", "auto"),
            "autoEnabled": bool(int(repo.get_setting("theme_auto_enabled", 1) or 0)),
            "nightStart": repo.get_setting("theme_night_start", "22:00"),
            "dayResume": repo.get_setting("theme_day_resume", "07:00"),
            "checkFrequency": int(repo.get_setting("theme_check_frequency", 5) or 5),
            "transitionMinutes": int(repo.get_setting("theme_transition_minutes", 3) or 3),
        }

    @Slot(result=str)
    def getBootstrap(self) -> str:
        from bookhub.library.error_logs import read_latest_log_text
        payload = {
            "strings": _web_strings(),
            "language": self._repo.get_language_code(),
            "nav": [{"page": page, "labelKey": key, "label": tr(key, fb)} for page, key, fb in NAV_ITEMS],
            "settings": self._settings_payload(),
            "pages": self._pages_payload(),
            "errorLogs": read_latest_log_text(),
        }
        return json.dumps(payload, ensure_ascii=False)

    @Slot(str)
    def setPageBackgroundTheme(self, theme: str) -> None:
        host = getattr(self, "_host", None)
        if host is not None and hasattr(host, "set_web_page_background"):
            host.set_web_page_background("night" if theme == "night" else "day")

    def push_resources(self) -> None:
        self.resourcesChanged.emit(json.dumps({"pages": self._pages_payload()}, ensure_ascii=False))

    def push_settings(self) -> None:
        self.settingsChanged.emit(json.dumps(self._settings_payload(), ensure_ascii=False))

    def emit_toast(self, title: str, message: str = "", kind: str = "info") -> None:
        self.toast.emit(json.dumps({"title": title, "message": message, "kind": kind}, ensure_ascii=False))

    # ---- navigation / search ------------------------------------------
    @Slot(str, str, result=str)
    def search(self, context: str, query: str) -> str:
        vm = self._text_vm if context == PAGE_TEXT else self._library_vm
        vm.set_query(query)
        page = PAGE_TEXT if context == PAGE_TEXT else PAGE_LIBRARY
        return json.dumps(self._page_resources(page), ensure_ascii=False)

    @Slot(str, str, result=str)
    def getSuggestions(self, context: str, query: str) -> str:
        vm = self._text_vm if context == PAGE_TEXT else self._library_vm
        return json.dumps(vm.search_suggestions_for_query(query), ensure_ascii=False)

    @Slot(int, result=str)
    def openCollection(self, collection_id: int) -> str:
        self._current_collection_id = int(collection_id) if collection_id else None
        return json.dumps(self._page_resources(PAGE_COLLECTIONS), ensure_ascii=False)

    @Slot(result=str)
    def closeCollection(self) -> str:
        self._current_collection_id = None
        return json.dumps(self._page_resources(PAGE_COLLECTIONS), ensure_ascii=False)

    @Slot(str, str, result=str)
    def setPageSort(self, page: str, order: str) -> str:
        value = str(order or "").strip().lower()
        if page == PAGE_FAVORITES:
            self._repo.set_setting("favorites_sort_order", "asc" if value == "asc" else "desc")
        elif page == PAGE_COMIC:
            self._repo.set_comic_sort_order_main(value)
        elif page == PAGE_COMIC_FAV:
            self._repo.set_comic_sort_order_fav(value)
        else:
            return json.dumps(self._page_resources(page), ensure_ascii=False)
        self.push_resources()
        return json.dumps(self._page_resources(page), ensure_ascii=False)

    # ---- detail --------------------------------------------------------
    @Slot(str, str, result=str)
    def getDetail(self, page: str, resource_id: str) -> str:
        detail = self._detail_for(page, resource_id)
        return json.dumps(detail or {}, ensure_ascii=False)

    def _detail_for(self, page: str, resource_id: str) -> dict[str, Any] | None:
        if page in {PAGE_COMIC, PAGE_COMIC_FAV}:
            order = self._repo.get_comic_sort_order_fav() if page == PAGE_COMIC_FAV else self._repo.get_comic_sort_order_main()
            rows = (
                self._repo.get_favorite_comics(order_by=order)
                if page == PAGE_COMIC_FAV
                else self._repo.list_comics(include_missing=False, order_by=order)
            )
            row = next((r for r in rows if str(r.get("resource_id")) == resource_id), None)
            if not row:
                return None
            payload = self._comic_payload(row)
            payload["isFavorite"] = page == PAGE_COMIC_FAV or self._is_comic_favorite(resource_id)
            return payload
        # books-like
        row = self._find_book_row(resource_id)
        if not row:
            return None
        payload = self._book_payload(row)
        book_id = self._repo.get_book_int_id(resource_id)
        payload["isFavorite"] = bool(book_id is not None and self._repo.is_favorite(book_id))
        payload["bookCollections"] = (
            [{"id": int(c.get("id")), "name": c.get("name")} for c in self._repo.get_collections_for_book(book_id)]
            if book_id is not None
            else []
        )
        return payload

    def _find_book_row(self, resource_id: str) -> dict[str, Any] | None:
        for row in self._repo.list_books(include_missing=None):
            if str(row.get("resource_id")) == resource_id:
                return row
        return None

    def _is_comic_favorite(self, resource_id: str) -> bool:
        comic_id = self._repo.get_comic_int_id(resource_id)
        return bool(comic_id is not None and self._repo.is_favorite_comic(comic_id))

    # ---- actions -------------------------------------------------------
    @Slot(str, str)
    def openResource(self, page: str, resource_id: str) -> None:
        detail = self._detail_for(page, resource_id)
        if not detail:
            return
        target = detail.get("coverImage") or detail.get("path") if page in {PAGE_COMIC, PAGE_COMIC_FAV} else detail.get("path")
        self._open_external(str(target or ""))

    def _open_external(self, path: str) -> None:
        file_path = Path(path).expanduser()
        if not str(file_path).strip() or not file_path.exists():
            self.emit_toast(tr("open.failed_title", "Cannot open"), tr("open.failed_msg", "File or folder not found."), "warning")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(file_path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(file_path)])
            else:
                subprocess.Popen(["xdg-open", str(file_path)])
        except Exception:
            self.emit_toast(tr("open.failed_title", "Cannot open"), str(file_path), "warning")

    @Slot(str, str, result=bool)
    def toggleFavorite(self, page: str, resource_id: str) -> bool:
        if page in {PAGE_COMIC, PAGE_COMIC_FAV}:
            comic_id = self._repo.get_comic_int_id(resource_id)
            if comic_id is None:
                return False
            if self._repo.is_favorite_comic(comic_id):
                self._repo.remove_comic_from_favorites(comic_id)
                now_fav = False
            else:
                self._repo.add_comic_to_favorites(comic_id)
                now_fav = True
            self.push_resources()
            return now_fav
        book_id = self._repo.get_book_int_id(resource_id)
        if book_id is None:
            return False
        if self._repo.is_favorite(book_id):
            self._repo.remove_from_favorites(book_id)
            now_fav = False
        else:
            self._repo.add_to_favorites(book_id)
            now_fav = True
        self.push_resources()
        return now_fav

    @Slot(result=str)
    def getTags(self) -> str:
        return json.dumps(self._repo.get_all_tags(), ensure_ascii=False)

    @Slot(result=str)
    def getCollections(self) -> str:
        collections = self._repo.get_all_collections()
        return json.dumps([{"id": int(c.get("id")), "name": c.get("name")} for c in collections], ensure_ascii=False)

    @Slot(str, str)
    def addTag(self, resource_id: str, tag: str) -> None:
        book_id = self._repo.get_book_int_id(resource_id)
        if book_id is None or not tag.strip():
            return
        self._repo.add_tag_to_book(book_id, tag.strip())
        self.reload_data()
        self.push_resources()

    @Slot(str, str)
    def removeTag(self, resource_id: str, tag: str) -> None:
        book_id = self._repo.get_book_int_id(resource_id)
        if book_id is None:
            return
        self._repo.remove_tag_from_book(book_id, tag)
        self.reload_data()
        self.push_resources()

    @Slot(str, result=int)
    def createCollection(self, name: str) -> int:
        if not name.strip():
            return -1
        cid = self._repo.create_collection(name.strip())
        self.push_resources()
        return int(cid)

    @Slot(int, str, result=bool)
    def renameCollection(self, collection_id: int, name: str) -> bool:
        if not name.strip():
            return False
        self._repo.rename_collection(int(collection_id), name.strip())
        self.push_resources()
        return True

    @Slot(int, result=bool)
    def deleteCollection(self, collection_id: int) -> bool:
        self._repo.delete_collection(int(collection_id))
        if self._current_collection_id == int(collection_id):
            self._current_collection_id = None
        self.push_resources()
        return True

    @Slot(str)
    def openFolder(self, resource_id: str) -> None:
        row = self._find_book_row(resource_id)
        if not row:
            detail = self._detail_for(PAGE_COMIC, resource_id) or self._detail_for(PAGE_COMIC_FAV, resource_id)
            path = str((detail or {}).get("path") or "")
        else:
            path = str(row.get("path") or "")
        if not path:
            self.emit_toast(tr("open.failed_title", "Cannot open"), tr("open.failed_msg", "File or folder not found."), "warning")
            return
        folder = Path(path).expanduser()
        if folder.is_file():
            folder = folder.parent
        self._open_external(str(folder))

    @Slot(str)
    def editCover(self, resource_id: str) -> None:
        if self._host is not None and hasattr(self._host, "edit_cover"):
            self._host.edit_cover(resource_id)

    @Slot(str, str, result=bool)
    def removeFromLibrary(self, page: str, resource_id: str) -> bool:
        if self._host is not None and hasattr(self._host, "remove_from_library"):
            return bool(self._host.remove_from_library(page, resource_id))
        return False

    @Slot(str, int, bool)
    def setCollectionMembership(self, resource_id: str, collection_id: int, member: bool) -> None:
        book_id = self._repo.get_book_int_id(resource_id)
        if book_id is None:
            return
        if member:
            self._repo.add_book_to_collection(book_id, int(collection_id))
        else:
            self._repo.remove_book_from_collection(book_id, int(collection_id))
        self.push_resources()

    @Slot(str, int)
    def removeFromCollection(self, resource_id: str, collection_id: int) -> None:
        book_id = self._repo.get_book_int_id(resource_id)
        if book_id is None:
            return
        self._repo.remove_book_from_collection(book_id, int(collection_id))
        self.push_resources()

    # ---- settings ------------------------------------------------------
    @Slot(str, str)
    def setSetting(self, key: str, value: str) -> None:
        if self._host is not None and hasattr(self._host, "apply_setting"):
            self._host.apply_setting(key, value)
        self.push_settings()

    @Slot(str)
    def setThemeSettings(self, payload_json: str) -> None:
        try:
            payload = json.loads(payload_json)
        except (TypeError, ValueError):
            return
        repo = self._repo
        if "mode" in payload:
            repo.set_setting("theme_mode", str(payload["mode"]))
        if "autoEnabled" in payload:
            repo.set_setting("theme_auto_enabled", 1 if payload["autoEnabled"] else 0)
        if "nightStart" in payload:
            repo.set_setting("theme_night_start", str(payload["nightStart"]))
        if "dayResume" in payload:
            repo.set_setting("theme_day_resume", str(payload["dayResume"]))
        if "checkFrequency" in payload:
            repo.set_setting("theme_check_frequency", int(payload["checkFrequency"]))
        if "transitionMinutes" in payload:
            repo.set_setting("theme_transition_minutes", int(payload["transitionMinutes"]))

    # ---- host-delegated (native dialogs / workers) --------------------
    @Slot(str)
    def addRoot(self, kind: str) -> None:
        if self._host is not None:
            self._host.add_root(kind)

    @Slot(str, str)
    def removeRoot(self, kind: str, path: str) -> None:
        if self._host is not None:
            self._host.remove_root(kind, path)

    @Slot(str)
    def openTextRules(self, root_path: str) -> None:
        payload = self.getTextRules(root_path)
        data = json.loads(payload)
        if data.get("ok"):
            self.textRulesOpen.emit(payload)
        else:
            self.emit_toast(
                tr("text.rules.open_failed", "Cannot open Text Rules"),
                str(data.get("error") or ""),
                "warning",
            )

    @Slot(str, result=str)
    def getTextRules(self, root_path: str) -> str:
        from bookhub.library.text_rules.rule_catalog import describe_step_catalog
        from bookhub.library.text_rules.rule_models import load_rules_from_json, dump_rules_to_json

        root = self._resolve_text_root(root_path)
        if root is None:
            return json.dumps({"ok": False, "error": "Unknown text root"}, ensure_ascii=False)
        raw = self._repo.get_text_root_rules_json(root)
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            rule_map = load_rules_from_json(parsed)
            rules = dump_rules_to_json(rule_map)
        except Exception as exc:  # noqa: BLE001
            return json.dumps({"ok": False, "error": f"Invalid rules JSON: {exc}"}, ensure_ascii=False)
        catalog = describe_step_catalog()
        samples = self._list_txt_samples(root, limit=40)
        sample_path = samples[0]["path"] if samples else None
        return json.dumps(
            {
                "ok": True,
                "path": root,
                "rules": rules,
                "catalog": catalog,
                "samples": samples,
                "samplePath": sample_path,
                "presets": self._repo.get_text_rule_presets(),
                "previewChars": self._repo.get_text_preview_chars(),
            },
            ensure_ascii=False,
        )

    @Slot(str, str, str, result=str)
    def previewTextRule(self, root_path: str, field_rules_json: str, sample_path: str = "") -> str:
        from bookhub.library.text_rules.rule_models import ImportRule, load_rules_from_json
        from bookhub.library.text_rules.rule_preview import (
            build_preview_context,
            find_first_txt_file,
            preview_rule_chain,
            read_txt_preview_sample,
        )

        root = self._resolve_text_root(root_path)
        if root is None:
            return json.dumps({"ok": False, "error": "Unknown text root"}, ensure_ascii=False)
        try:
            parsed = json.loads(field_rules_json or "[]")
        except (TypeError, ValueError) as exc:
            return json.dumps({"ok": False, "error": f"Invalid rule JSON: {exc}"}, ensure_ascii=False)
        if isinstance(parsed, dict):
            # Accept either a single rule or {field:[rules]} for one field.
            if "source" in parsed:
                rules = [ImportRule.from_dict(parsed)]
            else:
                nested = load_rules_from_json(parsed)
                rules = next(iter(nested.values()), []) if nested else []
        elif isinstance(parsed, list):
            rules = [ImportRule.from_dict(item) for item in parsed]
        else:
            return json.dumps({"ok": False, "error": "Rules must be a list or object"}, ensure_ascii=False)

        chosen = str(sample_path or "").strip()
        if chosen:
            safe = self._safe_sample_under_root(root, chosen)
            if safe is None:
                return json.dumps({"ok": False, "error": "Sample path outside text root"}, ensure_ascii=False)
            file_path = safe
        else:
            file_path = find_first_txt_file(root)
        if not file_path:
            return json.dumps(
                {"ok": True, "success": False, "value": "", "error": "No TXT sample found", "warning": None, "samplePath": None},
                ensure_ascii=False,
            )
        sample = read_txt_preview_sample(file_path, self._repo.get_text_preview_chars())
        if sample is None:
            return json.dumps(
                {"ok": True, "success": False, "value": "", "error": "Cannot read sample", "warning": None, "samplePath": file_path},
                ensure_ascii=False,
            )
        context = build_preview_context(sample.file_path, sample.txt_first_line, sample.txt_head_text)
        result = preview_rule_chain(rules, context)
        return json.dumps(
            {
                "ok": True,
                "success": bool(result.success),
                "value": result.value or "",
                "error": result.error_message,
                "warning": result.warning_message,
                "failedStep": result.failed_step,
                "samplePath": sample.file_path,
                "txtFirstLine": sample.txt_first_line,
                "txtHeadText": sample.txt_head_text,
            },
            ensure_ascii=False,
        )

    @Slot(str, str, result=str)
    def previewTextRulesMulti(self, root_path: str, field_rules_json: str) -> str:
        samples = []
        root = self._resolve_text_root(root_path)
        if root is None:
            return json.dumps({"ok": False, "error": "Unknown text root", "items": []}, ensure_ascii=False)
        for row in self._list_txt_samples(root, limit=20):
            one = json.loads(self.previewTextRule(root_path, field_rules_json, row["path"]))
            samples.append(
                {
                    "path": row["path"],
                    "name": row["name"],
                    "success": bool(one.get("success")),
                    "value": one.get("value") or "",
                    "error": one.get("error"),
                }
            )
        return json.dumps({"ok": True, "items": samples}, ensure_ascii=False)

    @Slot(str, str, result=str)
    def saveTextRules(self, root_path: str, rules_json: str) -> str:
        from bookhub.library.text_rules.rule_models import dump_rules_to_json, load_rules_from_json

        root = self._resolve_text_root(root_path)
        if root is None:
            return json.dumps({"ok": False, "error": "Unknown text root"}, ensure_ascii=False)
        try:
            parsed = json.loads(rules_json or "{}")
            rule_map = load_rules_from_json(parsed)
            normalized = json.dumps(dump_rules_to_json(rule_map), ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001
            return json.dumps({"ok": False, "error": f"Invalid rules: {exc}"}, ensure_ascii=False)
        self._repo.set_text_root_rules_json(root, normalized)
        self.push_settings()
        scanned = False
        if self._repo.get_auto_scan_on_path_change() and self._host is not None:
            self._host.start_scan("text")
            scanned = True
        self.emit_toast(
            tr("text.rules.saved_title", "Text Rules saved"),
            tr("text.rules.saved_msg", "Rules updated for this folder."),
            "info",
        )
        return json.dumps({"ok": True, "scanned": scanned, "rules": json.loads(normalized)}, ensure_ascii=False)

    @Slot(result=str)
    def getTextRulePresets(self) -> str:
        return json.dumps({"ok": True, "presets": self._repo.get_text_rule_presets()}, ensure_ascii=False)

    @Slot(str, result=str)
    def setTextRulePresets(self, presets_json: str) -> str:
        try:
            presets = json.loads(presets_json or "[]")
        except (TypeError, ValueError) as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
        if not isinstance(presets, list):
            return json.dumps({"ok": False, "error": "presets must be a list"}, ensure_ascii=False)
        self._repo.set_text_rule_presets(presets)
        return json.dumps({"ok": True, "presets": self._repo.get_text_rule_presets()}, ensure_ascii=False)

    def _resolve_text_root(self, root_path: str) -> str | None:
        target = os.path.normcase(os.path.normpath(str(root_path or "").strip()))
        if not target:
            return None
        for path in self._repo.list_text_roots():
            if os.path.normcase(os.path.normpath(path)) == target:
                return os.path.normpath(path)
        return None

    def _safe_sample_under_root(self, root: str, sample_path: str) -> str | None:
        try:
            root_r = Path(root).resolve()
            cand = Path(sample_path).resolve()
            cand.relative_to(root_r)
        except (OSError, ValueError):
            return None
        if not cand.is_file():
            return None
        return str(cand)

    def _list_txt_samples(self, root: str, limit: int = 40) -> list[dict[str, str]]:
        from bookhub.library.models import TEXT_FILE_EXTENSION

        root_path = Path(root)
        out: list[dict[str, str]] = []
        if not root_path.is_dir():
            return out
        for current_dir, dir_names, file_names in os.walk(root_path):
            dir_names[:] = sorted(dir_names)
            for name in sorted(file_names):
                if Path(name).suffix.lower() != TEXT_FILE_EXTENSION:
                    continue
                full = Path(current_dir) / name
                try:
                    rel = str(full.relative_to(root_path))
                except ValueError:
                    rel = name
                out.append({"path": str(full.resolve(strict=False)), "name": name, "rel": rel})
                if len(out) >= max(1, int(limit)):
                    return out
        return out

    @Slot(str)
    def startScan(self, scope: str) -> None:
        if self._host is not None:
            self._host.start_scan(scope)

    @Slot(str, str)
    def startThumbnailTask(self, kind: str, scope: str) -> None:
        if self._host is not None:
            self._host.start_thumbnail_task(kind, scope)

    @Slot()
    def reloadFonts(self) -> None:
        if self._host is not None:
            self._host.reload_fonts()

    @Slot(result=str)
    def getErrorLogs(self) -> str:
        from bookhub.library.error_logs import read_latest_log_text
        return read_latest_log_text()
