from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from bookhub.library.data_paths import DEFAULT_PREVIEW_DIR, resolve_preview_dir
from bookhub.library.error_logs import append_scan_log
from bookhub.library.models import (
    COMIC_SCAN_STRATEGIES,
    COMIC_SCAN_STRATEGY_SNAPSHOT,
    COMIC_TITLE_CONFLICT_POLICIES,
    COMIC_TITLE_CONFLICT_SKIP_INCOMING,
    HASH_STRATEGIES,
    HASH_STRATEGY_QUICK,
    DEFAULT_TEXT_PREVIEW_CHARS,
    TEXT_ENCODING_PREFERENCES,
    TEXT_ENCODING_SIMPLIFIED,
    TEXT_PREVIEW_CHAR_OPTIONS,
    ComicScanStrategy,
    HashStrategy,
)
from bookhub.library.preview_paths import ensure_preview_structure

DEFAULT_CARD_SPACING = 14
CARD_SPACING_MIN = 6
CARD_SPACING_MAX = 40
DEFAULT_TOPBAR_SEARCH_FONT_SIZE = 15
TOPBAR_SEARCH_FONT_SIZE_MIN = 12
TOPBAR_SEARCH_FONT_SIZE_MAX = 20
DEFAULT_COVER_SELECTED_BORDER_WIDTH = 2
COVER_SELECTED_BORDER_WIDTH_MIN = 1
COVER_SELECTED_BORDER_WIDTH_MAX = 6
DEFAULT_COVER_SELECTED_BORDER_COLOR = "#8EA7C6"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_DB_PATH = SRC_ROOT / "sql" / "library.db"
DEFAULT_SCAN_REPORT_PATH = SRC_ROOT / "sql" / "scan_report.json"


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_card_spacing(value: int | str | None) -> int:
    try:
        spacing = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        spacing = DEFAULT_CARD_SPACING
    return min(CARD_SPACING_MAX, max(CARD_SPACING_MIN, spacing))


def _normalize_topbar_search_font_size(value: int | str | None) -> int:
    try:
        size = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        size = DEFAULT_TOPBAR_SEARCH_FONT_SIZE
    return min(TOPBAR_SEARCH_FONT_SIZE_MAX, max(TOPBAR_SEARCH_FONT_SIZE_MIN, size))


def _normalize_cover_selected_border_width(value: int | str | None) -> int:
    try:
        width = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        width = DEFAULT_COVER_SELECTED_BORDER_WIDTH
    return min(COVER_SELECTED_BORDER_WIDTH_MAX, max(COVER_SELECTED_BORDER_WIDTH_MIN, width))


def _normalize_cover_selected_border_color(value: str | None) -> str:
    text = str(value or "").strip().upper()
    if text.startswith("#"):
        text = text[1:]
    if len(text) != 6:
        return DEFAULT_COVER_SELECTED_BORDER_COLOR
    valid = "0123456789ABCDEF"
    if any(ch not in valid for ch in text):
        return DEFAULT_COVER_SELECTED_BORDER_COLOR
    return f"#{text}"


class LibraryRepository:
    def __init__(
        self,
        db_path: str | Path | None = None,
        scan_report_path: str | Path | None = None,
        preview_dir: str | Path | None = None,
    ) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.scan_report_path = Path(scan_report_path) if scan_report_path else DEFAULT_SCAN_REPORT_PATH
        self._preview_dir_override = Path(preview_dir) if preview_dir is not None else None
        self.preview_dir = DEFAULT_PREVIEW_DIR.resolve(strict=False)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.scan_report_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._init_collections_tables()
        self._ensure_defaults()
        self._apply_preview_dir_from_settings_or_override()
        self.purge_marked_missing_records()

    def _apply_preview_dir_from_settings_or_override(self) -> None:
        if self._preview_dir_override is not None:
            resolved, _used_default = resolve_preview_dir(str(self._preview_dir_override), create=True)
        else:
            raw = self.get_preview_cache_dir_setting()
            resolved, _used_default = resolve_preview_dir(raw or None, create=True)
        self.preview_dir = resolved
        ensure_preview_structure(self.preview_dir)

    def get_preview_cache_dir_setting(self) -> str:
        raw = self.get_setting("preview_cache_dir", "")
        return str(raw or "").strip()

    def set_preview_cache_dir(self, path: str | None) -> None:
        text = str(path or "").strip()
        self.set_setting("preview_cache_dir", text)

    def get_preview_dir_effective(self) -> Path:
        return self.preview_dir.resolve(strict=False)

    def iter_thumbnail_uris(self, *, limit: int | None = None) -> list[str]:
        uris: list[str] = []
        with self._connection() as conn:
            book_sql = "SELECT thumbnail_path FROM books WHERE thumbnail_path IS NOT NULL AND thumbnail_path != ''"
            comic_sql = "SELECT thumbnail_path FROM comics WHERE thumbnail_path IS NOT NULL AND thumbnail_path != ''"
            if limit is not None and limit > 0:
                book_sql += f" LIMIT {int(limit)}"
                comic_sql += f" LIMIT {int(limit)}"
            for row in conn.execute(book_sql).fetchall():
                uris.append(str(row["thumbnail_path"]))
            for row in conn.execute(comic_sql).fetchall():
                uris.append(str(row["thumbnail_path"]))
        return uris

    def rewrite_thumbnail_uris_for_root_move(self, old_root: Path, new_root: Path) -> int:
        """Rewrite books/comics thumbnail_path URIs that live under old_root to new_root."""
        from bookhub.library.preview_cache_migrate import rewire_thumbnail_uri

        rewritten = 0
        old_resolved = Path(old_root).resolve(strict=False)
        new_resolved = Path(new_root).resolve(strict=False)
        with self._connection() as conn:
            for table in ("books", "comics"):
                rows = conn.execute(
                    f"SELECT id, thumbnail_path FROM {table} "  # noqa: S608
                    "WHERE thumbnail_path IS NOT NULL AND thumbnail_path != ''"
                ).fetchall()
                for row in rows:
                    old_uri = str(row["thumbnail_path"] or "")
                    new_uri = rewire_thumbnail_uri(old_uri, old_resolved, new_resolved)
                    if new_uri is None or new_uri == old_uri:
                        continue
                    conn.execute(
                        f"UPDATE {table} SET thumbnail_path = ?, updated_at = ? WHERE id = ?",  # noqa: S608
                        (new_uri, now_utc_iso(), int(row["id"])),
                    )
                    rewritten += 1
        return rewritten

    def purge_marked_missing_records(self) -> int:
        """Delete legacy is_missing=1 rows (product rule: missing sources are removed, not restored)."""
        with self._connection() as conn:
            book_rows = conn.execute("SELECT id, title, path FROM books WHERE is_missing = 1").fetchall()
            comic_rows = conn.execute("SELECT id, title, path FROM comics WHERE is_missing = 1").fetchall()
            book_ids = [int(row["id"]) for row in book_rows]
            comic_ids = [int(row["id"]) for row in comic_rows]
            if book_ids:
                self._purge_book_links(conn, book_ids)
                placeholders = ",".join(["?"] * len(book_ids))
                conn.execute(f"DELETE FROM books WHERE id IN ({placeholders})", tuple(book_ids))  # noqa: S608
            if comic_ids:
                self._purge_comic_links(conn, comic_ids)
                placeholders = ",".join(["?"] * len(comic_ids))
                conn.execute(f"DELETE FROM comics WHERE id IN ({placeholders})", tuple(comic_ids))  # noqa: S608
        deleted = len(book_ids) + len(comic_ids)
        if deleted > 0:
            for row in book_rows:
                append_scan_log(
                    "missing_removed | type=book | title="
                    f"{row['title'] or 'Unknown'} | path={row['path'] or ''} | reason=legacy is_missing purged"
                )
            for row in comic_rows:
                append_scan_log(
                    "missing_removed | type=comic_folder | title="
                    f"{row['title'] or 'Unknown'} | path={row['path'] or ''} | reason=legacy is_missing purged"
                )
        return deleted

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _purge_book_links(conn: sqlite3.Connection, book_ids: list[int]) -> None:
        ids = [int(item) for item in book_ids if int(item) > 0]
        if not ids:
            return
        placeholders = ",".join(["?"] * len(ids))
        conn.execute(f"DELETE FROM favorite_books WHERE book_id IN ({placeholders})", tuple(ids))  # noqa: S608
        conn.execute(f"DELETE FROM collection_books WHERE book_id IN ({placeholders})", tuple(ids))  # noqa: S608

    @staticmethod
    def _purge_comic_links(conn: sqlite3.Connection, comic_ids: list[int]) -> None:
        ids = [int(item) for item in comic_ids if int(item) > 0]
        if not ids:
            return
        placeholders = ",".join(["?"] * len(ids))
        conn.execute(f"DELETE FROM favorite_comics WHERE comic_id IN ({placeholders})", tuple(ids))  # noqa: S608

    def _cleanup_orphan_links(self, conn: sqlite3.Connection) -> None:
        tables = {
            str(row[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "favorite_books" in tables and "books" in tables:
            conn.execute("DELETE FROM favorite_books WHERE book_id NOT IN (SELECT id FROM books)")
        if "collection_books" in tables and "books" in tables:
            conn.execute("DELETE FROM collection_books WHERE book_id NOT IN (SELECT id FROM books)")
        if "favorite_comics" in tables and "comics" in tables:
            conn.execute("DELETE FROM favorite_comics WHERE comic_id NOT IN (SELECT id FROM comics)")

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS library_roots (
                    path TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS comic_roots (
                    path TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS text_roots (
                    path TEXT PRIMARY KEY,
                    rules_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_id TEXT NOT NULL UNIQUE,
                    file_name TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    title TEXT,
                    author TEXT,
                    publisher TEXT,
                    language TEXT,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'UNREAD',
                    resource_type TEXT NOT NULL DEFAULT 'book',
                    path TEXT NOT NULL UNIQUE,
                    thumbnail_path TEXT,
                    info_text TEXT,
                    is_missing INTEGER NOT NULL DEFAULT 0,
                    missing_reason TEXT,
                    fingerprint_sha256 TEXT,
                    fingerprint_size_mtime TEXT,
                    fingerprint_quick TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_books_name_ext ON books(file_name, extension);
                CREATE INDEX IF NOT EXISTS idx_books_missing ON books(is_missing);
                CREATE INDEX IF NOT EXISTS idx_books_fp_sha256 ON books(fingerprint_sha256);
                CREATE INDEX IF NOT EXISTS idx_books_fp_size_mtime ON books(fingerprint_size_mtime);
                CREATE INDEX IF NOT EXISTS idx_books_fp_quick ON books(fingerprint_quick);

                CREATE TABLE IF NOT EXISTS comics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    comic_root TEXT,
                    cover_image_path TEXT,
                    thumbnail_path TEXT,
                    cover_fingerprint TEXT,
                    folder_size_mtime TEXT,
                    folder_mtime INTEGER NOT NULL DEFAULT 0,
                    folder_modified_at INTEGER NOT NULL DEFAULT 0,
                    image_count INTEGER NOT NULL DEFAULT 0,
                    info_text TEXT,
                    is_missing INTEGER NOT NULL DEFAULT 0,
                    missing_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_comics_title ON comics(title);
                CREATE INDEX IF NOT EXISTS idx_comics_missing ON comics(is_missing);

                CREATE TABLE IF NOT EXISTS favorite_comics (
                    comic_id INTEGER PRIMARY KEY,
                    added_at TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS scan_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    summary_json TEXT NOT NULL
                );
                """
            )
            self._ensure_column(conn, "books", "info_text", "ALTER TABLE books ADD COLUMN info_text TEXT")
            self._ensure_column(conn, "comics", "cover_fingerprint", "ALTER TABLE comics ADD COLUMN cover_fingerprint TEXT")
            self._ensure_column(conn, "comics", "folder_size_mtime", "ALTER TABLE comics ADD COLUMN folder_size_mtime TEXT")
            self._ensure_column(conn, "comics", "folder_mtime", "ALTER TABLE comics ADD COLUMN folder_mtime INTEGER")
            self._ensure_column(conn, "comics", "folder_modified_at", "ALTER TABLE comics ADD COLUMN folder_modified_at INTEGER")
            self._ensure_column(
                conn,
                "library_roots",
                "scan_strategy",
                "ALTER TABLE library_roots ADD COLUMN scan_strategy TEXT",
            )
            self._ensure_column(
                conn,
                "comic_roots",
                "scan_strategy",
                "ALTER TABLE comic_roots ADD COLUMN scan_strategy TEXT",
            )
            self._ensure_column(
                conn,
                "text_roots",
                "scan_strategy",
                "ALTER TABLE text_roots ADD COLUMN scan_strategy TEXT",
            )

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, ddl_sql: str) -> None:
        columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()  # noqa: S608
        names = {str(row["name"]) for row in columns}
        if column_name in names:
            return
        conn.execute(ddl_sql)

    def _ensure_defaults(self) -> None:
        if self.get_setting("scan_depth", None) is None:
            self.set_setting("scan_depth", 2)
        if self.get_setting("hash_strategy", None) is None:
            self.set_setting("hash_strategy", HASH_STRATEGY_QUICK)
        if self.get_setting("per_root_scan_strategy_enabled", None) is None:
            self.set_setting("per_root_scan_strategy_enabled", False)
        if self.get_setting("comic_scan_strategy", None) is None:
            self.set_setting("comic_scan_strategy", COMIC_SCAN_STRATEGY_SNAPSHOT)
        if self.get_setting("comic_title_conflict_policy", None) is None:
            self.set_setting("comic_title_conflict_policy", COMIC_TITLE_CONFLICT_SKIP_INCOMING)
        if self.get_setting("text_encoding_preference", None) is None:
            self.set_setting("text_encoding_preference", TEXT_ENCODING_SIMPLIFIED)
        if self.get_setting("card_spacing", None) is None:
            self.set_setting("card_spacing", DEFAULT_CARD_SPACING)
        if self.get_setting("topbar_search_font_size", None) is None:
            self.set_setting("topbar_search_font_size", DEFAULT_TOPBAR_SEARCH_FONT_SIZE)
        if self.get_setting("cover_selected_border_width_px", None) is None:
            self.set_setting("cover_selected_border_width_px", DEFAULT_COVER_SELECTED_BORDER_WIDTH)
        if self.get_setting("cover_selected_border_color_hex", None) is None:
            self.set_setting("cover_selected_border_color_hex", DEFAULT_COVER_SELECTED_BORDER_COLOR)
        if self.get_setting("text_preview_chars", None) is None:
            self.set_setting("text_preview_chars", DEFAULT_TEXT_PREVIEW_CHARS)
        if self.get_setting("text_rule_preview_result_height", None) is None:
            self.set_setting("text_rule_preview_result_height", 180)
        if self.get_setting("text_rule_dialog_size", None) is None:
            self.set_setting("text_rule_dialog_size", [1320, 820])
        if self.get_setting("text_rule_presets", None) is None:
            self.set_setting("text_rule_presets", [])
        if self.get_setting("scan_on_startup", None) is None:
            self.set_setting("scan_on_startup", False)
        if self.get_setting("auto_scan_on_path_change", None) is None:
            self.set_setting("auto_scan_on_path_change", True)
        if self.get_setting("language_code", None) is None:
            self.set_setting("language_code", "en")
        if self.get_setting("font_source", None) is None:
            self.set_setting("font_source", "system")
        if self.get_setting("font_family", None) is None:
            self.set_setting("font_family", "")
        if self.get_setting("comic_placeholder_copy_enabled", None) is None:
            self.set_setting("comic_placeholder_copy_enabled", True)
        if self.get_setting("auto_generate_comic_thumbnails_after_scan", None) is None:
            self.set_setting("auto_generate_comic_thumbnails_after_scan", True)
        if self.get_setting("comic_thumbnail_workers", None) is None:
            self.set_setting("comic_thumbnail_workers", "auto")
        if self.get_setting("comic_view_mode", None) is None:
            self.set_setting("comic_view_mode", "pagination")
        if self.get_setting("comic_page_size", None) is None:
            self.set_setting("comic_page_size", 48)
        if self.get_setting("viewport_buffer_screens", None) is None:
            self.set_setting("viewport_buffer_screens", 3)
        if self.get_setting("grid_columns", None) is None:
            self.set_setting("grid_columns", 6)
        if self.get_setting("comic_sort_order_main", None) is None:
            self.set_setting("comic_sort_order_main", "folder_mtime_desc")
        if self.get_setting("comic_sort_order_fav", None) is None:
            self.set_setting("comic_sort_order_fav", "folder_mtime_desc")
        if self.get_setting("preview_cache_dir", None) is None:
            self.set_setting("preview_cache_dir", "")
        with self._connection() as conn:
            self._cleanup_orphan_links(conn)

    @staticmethod
    def normalize_path(path: str | Path) -> str:
        expanded = Path(path).expanduser()
        return str(expanded.resolve(strict=False))

    def set_setting(self, key: str, value: Any) -> None:
        serialized = json.dumps(value, ensure_ascii=False)
        with self._connection() as conn:
            existing = conn.execute("SELECT key FROM app_settings WHERE key = ?", (key,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE app_settings SET value = ?, updated_at = ? WHERE key = ?",
                    (serialized, now_utc_iso(), key),
                )
            else:
                conn.execute(
                    "INSERT INTO app_settings(key, value, updated_at) VALUES(?, ?, ?)",
                    (key, serialized, now_utc_iso()),
                )

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._connection() as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            return default

    def get_scan_depth(self) -> int:
        raw = self.get_setting("scan_depth", 2)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = 2
        return min(3, max(1, value))

    def set_scan_depth(self, depth: int) -> None:
        self.set_setting("scan_depth", min(3, max(1, int(depth))))

    def get_hash_strategy(self) -> HashStrategy:
        strategy = str(self.get_setting("hash_strategy", HASH_STRATEGY_QUICK))
        if strategy not in HASH_STRATEGIES:
            strategy = HASH_STRATEGY_QUICK
        return strategy  # type: ignore[return-value]

    def set_hash_strategy(self, strategy: str) -> None:
        normalized = strategy if strategy in HASH_STRATEGIES else HASH_STRATEGY_QUICK
        self.set_setting("hash_strategy", normalized)

    def get_per_root_scan_strategy_enabled(self) -> bool:
        return bool(self.get_setting("per_root_scan_strategy_enabled", False))

    def set_per_root_scan_strategy_enabled(self, enabled: bool) -> None:
        self.set_setting("per_root_scan_strategy_enabled", bool(enabled))

    def get_comic_scan_strategy(self) -> ComicScanStrategy:
        strategy = str(self.get_setting("comic_scan_strategy", COMIC_SCAN_STRATEGY_SNAPSHOT))
        if strategy not in COMIC_SCAN_STRATEGIES:
            strategy = COMIC_SCAN_STRATEGY_SNAPSHOT
        return strategy  # type: ignore[return-value]

    def set_comic_scan_strategy(self, strategy: str) -> None:
        normalized = strategy if strategy in COMIC_SCAN_STRATEGIES else COMIC_SCAN_STRATEGY_SNAPSHOT
        self.set_setting("comic_scan_strategy", normalized)

    def get_comic_title_conflict_policy(self) -> str:
        policy = str(self.get_setting("comic_title_conflict_policy", COMIC_TITLE_CONFLICT_SKIP_INCOMING))
        if policy not in COMIC_TITLE_CONFLICT_POLICIES:
            return COMIC_TITLE_CONFLICT_SKIP_INCOMING
        return policy

    def set_comic_title_conflict_policy(self, policy: str) -> None:
        normalized = policy if policy in COMIC_TITLE_CONFLICT_POLICIES else COMIC_TITLE_CONFLICT_SKIP_INCOMING
        self.set_setting("comic_title_conflict_policy", normalized)

    def get_text_encoding_preference(self) -> str:
        value = str(self.get_setting("text_encoding_preference", TEXT_ENCODING_SIMPLIFIED))
        if value not in TEXT_ENCODING_PREFERENCES:
            return TEXT_ENCODING_SIMPLIFIED
        return value

    def set_text_encoding_preference(self, preference: str) -> None:
        normalized = preference if preference in TEXT_ENCODING_PREFERENCES else TEXT_ENCODING_SIMPLIFIED
        self.set_setting("text_encoding_preference", normalized)

    def get_card_spacing(self) -> int:
        raw = self.get_setting("card_spacing", DEFAULT_CARD_SPACING)
        return _normalize_card_spacing(raw)

    def set_card_spacing(self, spacing: int) -> None:
        self.set_setting("card_spacing", _normalize_card_spacing(spacing))

    def get_topbar_search_font_size(self) -> int:
        raw = self.get_setting("topbar_search_font_size", DEFAULT_TOPBAR_SEARCH_FONT_SIZE)
        return _normalize_topbar_search_font_size(raw)

    def set_topbar_search_font_size(self, size: int) -> None:
        self.set_setting("topbar_search_font_size", _normalize_topbar_search_font_size(size))

    def get_cover_selected_border_width(self) -> int:
        raw = self.get_setting("cover_selected_border_width_px", DEFAULT_COVER_SELECTED_BORDER_WIDTH)
        return _normalize_cover_selected_border_width(raw)

    def set_cover_selected_border_width(self, width: int) -> None:
        self.set_setting("cover_selected_border_width_px", _normalize_cover_selected_border_width(width))

    def get_cover_selected_border_color(self) -> str:
        raw = self.get_setting("cover_selected_border_color_hex", DEFAULT_COVER_SELECTED_BORDER_COLOR)
        return _normalize_cover_selected_border_color(raw)

    def set_cover_selected_border_color(self, color: str) -> None:
        self.set_setting("cover_selected_border_color_hex", _normalize_cover_selected_border_color(color))

    def get_text_preview_chars(self) -> int:
        raw = self.get_setting("text_preview_chars", DEFAULT_TEXT_PREVIEW_CHARS)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = DEFAULT_TEXT_PREVIEW_CHARS
        if value not in TEXT_PREVIEW_CHAR_OPTIONS:
            value = DEFAULT_TEXT_PREVIEW_CHARS
        return value

    def set_text_preview_chars(self, size: int) -> None:
        value = int(size)
        if value not in TEXT_PREVIEW_CHAR_OPTIONS:
            value = DEFAULT_TEXT_PREVIEW_CHARS
        self.set_setting("text_preview_chars", value)

    def get_text_rule_preview_result_height(self) -> int:
        raw = self.get_setting("text_rule_preview_result_height", 180)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = 180
        return min(420, max(96, value))

    def set_text_rule_preview_result_height(self, height: int) -> None:
        self.set_setting("text_rule_preview_result_height", min(420, max(96, int(height))))

    def get_text_rule_dialog_size(self) -> tuple[int, int]:
        raw = self.get_setting("text_rule_dialog_size", [1320, 820])
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            return (1320, 820)
        try:
            width = int(raw[0])
            height = int(raw[1])
        except (TypeError, ValueError):
            return (1320, 820)
        return (min(1920, max(1100, width)), min(1200, max(700, height)))

    def set_text_rule_dialog_size(self, width: int, height: int) -> None:
        normalized_width = min(1920, max(1100, int(width)))
        normalized_height = min(1200, max(700, int(height)))
        self.set_setting("text_rule_dialog_size", [normalized_width, normalized_height])

    def get_text_rule_presets(self) -> list[dict[str, Any]]:
        return self._normalize_text_rule_presets(self.get_setting("text_rule_presets", []))

    def set_text_rule_presets(self, presets: list[dict[str, Any]]) -> None:
        self.set_setting("text_rule_presets", self._normalize_text_rule_presets(presets))

    @staticmethod
    def _normalize_text_rule_presets(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        normalized: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            preset_id = str(item.get("id") or "").strip()
            kind = str(item.get("kind") or "").strip()
            if not preset_id or kind not in {"rule", "steps"}:
                continue
            steps = LibraryRepository._normalize_text_rule_preset_steps(item.get("steps"))
            payload: dict[str, Any] = {
                "id": preset_id,
                "kind": kind,
                "name": str(item.get("name") or "Preset").strip() or "Preset",
                "steps": steps,
            }
            if kind == "rule":
                payload["source"] = str(item.get("source") or "filename").strip() or "filename"
            normalized.append(payload)
        return normalized

    @staticmethod
    def _normalize_text_rule_preset_steps(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        steps: list[dict[str, Any]] = []
        for step in value:
            if not isinstance(step, dict):
                continue
            step_type = str(step.get("type") or "").strip()
            if not step_type:
                continue
            payload = {str(key): data for key, data in step.items()}
            payload["type"] = step_type
            steps.append(payload)
        return steps

    def get_scan_on_startup(self) -> bool:
        return bool(self.get_setting("scan_on_startup", False))

    def set_scan_on_startup(self, enabled: bool) -> None:
        self.set_setting("scan_on_startup", bool(enabled))

    def get_auto_scan_on_path_change(self) -> bool:
        return bool(self.get_setting("auto_scan_on_path_change", True))

    def set_auto_scan_on_path_change(self, enabled: bool) -> None:
        self.set_setting("auto_scan_on_path_change", bool(enabled))

    def get_language_code(self) -> str:
        code = str(self.get_setting("language_code", "en") or "en").strip().lower()
        return code or "en"

    def set_language_code(self, code: str) -> None:
        self.set_setting("language_code", str(code or "en").strip().lower() or "en")

    def get_font_source(self) -> str:
        raw = str(self.get_setting("font_source", "system") or "system").strip().lower()
        return "project" if raw == "project" else "system"

    def set_font_source(self, source: str) -> None:
        self.set_setting("font_source", "project" if str(source).strip().lower() == "project" else "system")

    def get_font_family(self) -> str:
        return str(self.get_setting("font_family", "") or "")

    def set_font_family(self, family: str) -> None:
        self.set_setting("font_family", str(family or ""))

    @staticmethod
    def _default_comic_workers() -> int:
        cpu = os.cpu_count() or 4
        return max(2, min(8, cpu - 1))

    def get_comic_placeholder_copy_enabled(self) -> bool:
        return bool(self.get_setting("comic_placeholder_copy_enabled", True))

    def set_comic_placeholder_copy_enabled(self, enabled: bool) -> None:
        self.set_setting("comic_placeholder_copy_enabled", bool(enabled))

    def get_auto_generate_comic_thumbnails_after_scan(self) -> bool:
        return bool(self.get_setting("auto_generate_comic_thumbnails_after_scan", True))

    def set_auto_generate_comic_thumbnails_after_scan(self, enabled: bool) -> None:
        self.set_setting("auto_generate_comic_thumbnails_after_scan", bool(enabled))

    def get_comic_thumbnail_workers_raw(self) -> str:
        raw = self.get_setting("comic_thumbnail_workers", "auto")
        if isinstance(raw, int):
            return str(max(1, min(16, int(raw))))
        text = str(raw or "auto").strip().lower()
        if text == "auto":
            return "auto"
        try:
            return str(max(1, min(16, int(text))))
        except ValueError:
            return "auto"

    def get_comic_thumbnail_workers(self) -> int:
        raw = self.get_comic_thumbnail_workers_raw()
        if raw == "auto":
            return self._default_comic_workers()
        return max(1, min(16, int(raw)))

    def set_comic_thumbnail_workers(self, value: str | int) -> None:
        text = str(value or "").strip().lower()
        if text == "auto":
            self.set_setting("comic_thumbnail_workers", "auto")
            return
        try:
            worker_count = max(1, min(16, int(text)))
        except ValueError:
            self.set_setting("comic_thumbnail_workers", "auto")
            return
        self.set_setting("comic_thumbnail_workers", worker_count)

    @staticmethod
    def _normalize_comic_view_mode(value: str | None) -> str:
        return "pagination" if str(value or "").strip().lower() == "pagination" else "waterfall"

    def get_comic_view_mode(self) -> str:
        return self._normalize_comic_view_mode(self.get_setting("comic_view_mode", "pagination"))

    def set_comic_view_mode(self, value: str) -> None:
        self.set_setting("comic_view_mode", self._normalize_comic_view_mode(value))

    @staticmethod
    def _normalize_comic_page_size(value: int | str | None) -> int:
        try:
            size = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            size = 48
        allowed = {24, 48, 72, 96}
        return size if size in allowed else 48

    def get_comic_page_size(self) -> int:
        return self._normalize_comic_page_size(self.get_setting("comic_page_size", 48))

    def set_comic_page_size(self, value: int | str) -> None:
        self.set_setting("comic_page_size", self._normalize_comic_page_size(value))

    @staticmethod
    def _normalize_viewport_buffer_screens(value: int | str | None) -> int:
        try:
            parsed = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 3
        if parsed in {3, 4, 5, 6}:
            return parsed
        return 3

    def get_viewport_buffer_screens(self) -> int:
        return self._normalize_viewport_buffer_screens(self.get_setting("viewport_buffer_screens", 3))

    def set_viewport_buffer_screens(self, value: int | str) -> None:
        self.set_setting("viewport_buffer_screens", self._normalize_viewport_buffer_screens(value))

    @staticmethod
    def _normalize_grid_columns(value: int | str | None) -> int:
        try:
            parsed = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 6
        allowed = {4, 5, 6, 7, 8, 10, 12}
        return parsed if parsed in allowed else 6

    def get_grid_columns(self) -> int:
        return self._normalize_grid_columns(self.get_setting("grid_columns", 6))

    def set_grid_columns(self, value: int | str) -> None:
        self.set_setting("grid_columns", self._normalize_grid_columns(value))

    @staticmethod
    def _normalize_comic_sort_order(value: str | None) -> str:
        normalized = str(value or "").strip().lower()
        allowed = {"folder_mtime_asc", "folder_mtime_desc", "folder_name_asc", "folder_name_desc"}
        return normalized if normalized in allowed else "folder_mtime_desc"

    def get_comic_sort_order_main(self) -> str:
        return self._normalize_comic_sort_order(self.get_setting("comic_sort_order_main", "folder_mtime_desc"))

    def set_comic_sort_order_main(self, value: str) -> None:
        self.set_setting("comic_sort_order_main", self._normalize_comic_sort_order(value))

    def get_comic_sort_order_fav(self) -> str:
        return self._normalize_comic_sort_order(self.get_setting("comic_sort_order_fav", "folder_mtime_desc"))

    def set_comic_sort_order_fav(self, value: str) -> None:
        self.set_setting("comic_sort_order_fav", self._normalize_comic_sort_order(value))

    def list_roots(self) -> list[str]:
        with self._connection() as conn:
            rows = conn.execute("SELECT path FROM library_roots ORDER BY lower(path)").fetchall()
        return [str(row["path"]) for row in rows]

    def list_roots_with_strategy(self) -> list[dict[str, str | None]]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT path, scan_strategy FROM library_roots ORDER BY lower(path)"
            ).fetchall()
        return [
            {
                "path": str(row["path"]),
                "scan_strategy": self._normalize_root_scan_strategy(row["scan_strategy"]),
            }
            for row in rows
        ]

    @staticmethod
    def _normalize_root_scan_strategy(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def set_root_scan_strategy(self, kind: str, path: str | Path, strategy: str | None) -> None:
        normalized_kind = str(kind or "").strip().lower()
        if normalized_kind not in {"library", "comic", "text"}:
            raise ValueError(f"Unsupported root kind: {kind}")
        normalized_path = self.normalize_path(path)
        normalized_strategy = self._normalize_root_scan_strategy(strategy)
        if normalized_strategy is not None:
            allowed = COMIC_SCAN_STRATEGIES if normalized_kind == "comic" else HASH_STRATEGIES
            if normalized_strategy not in allowed:
                raise ValueError(f"Unsupported scan strategy: {strategy}")
        table_name = {
            "library": "library_roots",
            "comic": "comic_roots",
            "text": "text_roots",
        }[normalized_kind]
        timestamp = now_utc_iso()
        with self._connection() as conn:
            cursor = conn.execute(
                f"""
                UPDATE {table_name}
                SET scan_strategy = ?, updated_at = ?
                WHERE path = ?
                """,  # noqa: S608
                (normalized_strategy, timestamp, normalized_path),
            )
            if int(cursor.rowcount or 0) <= 0:
                raise ValueError(f"Root not found: {normalized_path}")

    def add_root(self, path: str | Path) -> str:
        normalized = self.normalize_path(path)
        timestamp = now_utc_iso()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO library_roots(path, created_at, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (normalized, timestamp, timestamp),
            )
        return normalized

    def remove_root(self, path: str | Path) -> int:
        normalized = self.normalize_path(path)
        root_prefix = normalized.rstrip("\\/") + os.sep + "%"
        with self._connection() as conn:
            conn.execute("DELETE FROM library_roots WHERE path = ?", (normalized,))
            rows = conn.execute(
                """
                SELECT id FROM books
                WHERE 1=1
                AND resource_type != 'text_novel'
                AND (path = ? OR path LIKE ?)
                """,
                (normalized, root_prefix),
            ).fetchall()
            book_ids = [int(row["id"]) for row in rows]
            self._purge_book_links(conn, book_ids)
            cursor = conn.execute(
                """
                DELETE FROM books
                WHERE 1=1
                AND resource_type != 'text_novel'
                AND (path = ? OR path LIKE ?)
                """,
                (normalized, root_prefix),
            )
            deleted_count = cursor.rowcount if cursor.rowcount is not None else 0
        return max(0, int(deleted_count))

    def list_comic_roots(self) -> list[str]:
        with self._connection() as conn:
            rows = conn.execute("SELECT path FROM comic_roots ORDER BY lower(path)").fetchall()
        return [str(row["path"]) for row in rows]

    def list_comic_roots_with_strategy(self) -> list[dict[str, str | None]]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT path, scan_strategy FROM comic_roots ORDER BY lower(path)"
            ).fetchall()
        return [
            {
                "path": str(row["path"]),
                "scan_strategy": self._normalize_root_scan_strategy(row["scan_strategy"]),
            }
            for row in rows
        ]

    def add_comic_root(self, path: str | Path) -> str:
        normalized = self.normalize_path(path)
        timestamp = now_utc_iso()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO comic_roots(path, created_at, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (normalized, timestamp, timestamp),
            )
        return normalized

    def remove_comic_root(self, path: str | Path) -> int:
        normalized = self.normalize_path(path)
        root_prefix = normalized.rstrip("\\/") + os.sep + "%"
        with self._connection() as conn:
            conn.execute("DELETE FROM comic_roots WHERE path = ?", (normalized,))
            rows = conn.execute(
                """
                SELECT id FROM comics
                WHERE 1=1
                AND (path = ? OR path LIKE ?)
                """,
                (normalized, root_prefix),
            ).fetchall()
            comic_ids = [int(row["id"]) for row in rows]
            self._purge_comic_links(conn, comic_ids)
            cursor = conn.execute(
                """
                DELETE FROM comics
                WHERE 1=1
                AND (path = ? OR path LIKE ?)
                """,
                (normalized, root_prefix),
            )
            deleted_count = cursor.rowcount if cursor.rowcount is not None else 0
        return max(0, int(deleted_count))

    def list_text_roots(self) -> list[str]:
        with self._connection() as conn:
            rows = conn.execute("SELECT path FROM text_roots ORDER BY lower(path)").fetchall()
        return [str(row["path"]) for row in rows]

    def list_text_roots_with_rules(self) -> list[dict[str, str | None]]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT path, rules_json, scan_strategy FROM text_roots ORDER BY lower(path)"
            ).fetchall()
        return [
            {
                "path": str(row["path"]),
                "rules_json": str(row["rules_json"] or "{}"),
                "scan_strategy": self._normalize_root_scan_strategy(row["scan_strategy"]),
            }
            for row in rows
        ]

    def add_text_root(self, path: str | Path) -> str:
        normalized = self.normalize_path(path)
        timestamp = now_utc_iso()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO text_roots(path, rules_json, created_at, updated_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (normalized, "{}", timestamp, timestamp),
            )
        return normalized

    def remove_text_root(self, path: str | Path) -> int:
        normalized = self.normalize_path(path)
        root_prefix = normalized.rstrip("\\/") + os.sep + "%"
        with self._connection() as conn:
            conn.execute("DELETE FROM text_roots WHERE path = ?", (normalized,))
            rows = conn.execute(
                """
                SELECT id FROM books
                WHERE 1=1
                AND resource_type = 'text_novel'
                AND (path = ? OR path LIKE ?)
                """,
                (normalized, root_prefix),
            ).fetchall()
            book_ids = [int(row["id"]) for row in rows]
            self._purge_book_links(conn, book_ids)
            cursor = conn.execute(
                """
                DELETE FROM books
                WHERE 1=1
                AND resource_type = 'text_novel'
                AND (path = ? OR path LIKE ?)
                """,
                (normalized, root_prefix),
            )
            deleted_count = cursor.rowcount if cursor.rowcount is not None else 0
        return max(0, int(deleted_count))

    def get_text_root_rules_json(self, path: str | Path) -> str:
        normalized = self.normalize_path(path)
        with self._connection() as conn:
            row = conn.execute("SELECT rules_json FROM text_roots WHERE path = ?", (normalized,)).fetchone()
        if not row:
            return "{}"
        return str(row["rules_json"] or "{}")

    def set_text_root_rules_json(self, path: str | Path, rules_json: str) -> None:
        normalized = self.normalize_path(path)
        timestamp = now_utc_iso()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO text_roots(path, rules_json, created_at, updated_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET rules_json = excluded.rules_json, updated_at = excluded.updated_at
                """,
                (normalized, str(rules_json or "{}"), timestamp, timestamp),
            )

    def find_duplicate_name(self, file_name: str, extension: str, incoming_path: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT id, path, title, file_name, resource_type
                FROM books
                WHERE lower(file_name) = lower(?)
                AND lower(extension) = lower(?)
                AND is_missing = 0
                AND path != ?
                LIMIT 1
                """,
                (file_name, extension, incoming_path),
            ).fetchone()
        return dict(row) if row else None

    def find_comic_title_conflict(
        self,
        comic_root: str,
        title: str,
        incoming_path: str,
    ) -> dict[str, Any] | None:
        """Same comic_root + same title (case-insensitive), different path."""
        normalized_root = self.normalize_path(comic_root)
        normalized_incoming = self.normalize_path(incoming_path)
        title_text = str(title or "").strip()
        if not normalized_root or not title_text:
            return None
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT id, path, title, comic_root, folder_mtime, folder_modified_at
                FROM comics
                WHERE comic_root = ?
                  AND lower(title) = lower(?)
                  AND is_missing = 0
                  AND path != ?
                LIMIT 1
                """,
                (normalized_root, title_text, normalized_incoming),
            ).fetchone()
        return dict(row) if row else None

    def delete_book_by_id(self, book_id: int) -> None:
        with self._connection() as conn:
            self._purge_book_links(conn, [int(book_id)])
            conn.execute("DELETE FROM books WHERE id = ?", (int(book_id),))

    def delete_books_by_ids(self, book_ids: list[int]) -> int:
        ids = [int(item) for item in book_ids if int(item) > 0]
        if not ids:
            return 0
        placeholders = ",".join(["?"] * len(ids))
        with self._connection() as conn:
            self._purge_book_links(conn, ids)
            cursor = conn.execute(f"DELETE FROM books WHERE id IN ({placeholders})", tuple(ids))  # noqa: S608
            deleted = cursor.rowcount if cursor.rowcount is not None else 0
        return max(0, int(deleted))

    def delete_comics_by_ids(self, comic_ids: list[int]) -> int:
        ids = [int(item) for item in comic_ids if int(item) > 0]
        if not ids:
            return 0
        placeholders = ",".join(["?"] * len(ids))
        with self._connection() as conn:
            self._purge_comic_links(conn, ids)
            cursor = conn.execute(f"DELETE FROM comics WHERE id IN ({placeholders})", tuple(ids))  # noqa: S608
            deleted = cursor.rowcount if cursor.rowcount is not None else 0
        return max(0, int(deleted))

    @staticmethod
    def _comic_order_clause(order_by: str | None) -> str:
        normalized = str(order_by or "").strip().lower()
        mtime_expr = "COALESCE(NULLIF(folder_modified_at, 0), folder_mtime, 0)"
        if normalized == "folder_mtime_asc":
            return f"{mtime_expr} ASC, lower(title) ASC"
        if normalized == "folder_name_asc":
            return "lower(title) ASC"
        if normalized == "folder_name_desc":
            return "lower(title) DESC"
        return f"{mtime_expr} DESC, lower(title) ASC"

    @staticmethod
    def _fingerprint_or_none(value: object) -> str | None:
        text = str(value or "").strip()
        return text or None

    def map_library_books_for_scan(self, roots: list[str]) -> dict[str, dict[str, Any]]:
        """Lightweight path→fingerprint/thumb map for Library incremental scan (excludes text_novel)."""
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT path, thumbnail_path, fingerprint_sha256, fingerprint_size_mtime, fingerprint_quick
                FROM books
                WHERE is_missing = 0
                  AND COALESCE(resource_type, '') != 'text_novel'
                """
            ).fetchall()
        mapped: dict[str, dict[str, Any]] = {}
        for row in rows:
            path_value = str(row["path"] or "")
            if not path_value or not self._path_in_roots(path_value, roots):
                continue
            mapped[path_value] = {
                "path": path_value,
                "thumbnail_path": row["thumbnail_path"],
                "fingerprint_sha256": row["fingerprint_sha256"] or "",
                "fingerprint_size_mtime": row["fingerprint_size_mtime"] or "",
                "fingerprint_quick": row["fingerprint_quick"] or "",
            }
        return mapped

    def map_text_novels_for_scan(self, roots: list[str]) -> dict[str, dict[str, Any]]:
        """Lightweight path→fingerprint map for Text Novel incremental scan."""
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT path, fingerprint_sha256, fingerprint_size_mtime, fingerprint_quick
                FROM books
                WHERE is_missing = 0
                  AND COALESCE(resource_type, '') = 'text_novel'
                """
            ).fetchall()
        mapped: dict[str, dict[str, Any]] = {}
        for row in rows:
            path_value = str(row["path"] or "")
            if not path_value or not self._path_in_roots(path_value, roots):
                continue
            mapped[path_value] = {
                "path": path_value,
                "fingerprint_sha256": row["fingerprint_sha256"] or "",
                "fingerprint_size_mtime": row["fingerprint_size_mtime"] or "",
                "fingerprint_quick": row["fingerprint_quick"] or "",
            }
        return mapped

    def upsert_book(self, payload: dict[str, Any]) -> bool:
        path = payload["path"]
        timestamp = now_utc_iso()
        fp_sha = self._fingerprint_or_none(payload.get("fingerprint_sha256"))
        fp_size = self._fingerprint_or_none(payload.get("fingerprint_size_mtime"))
        fp_quick = self._fingerprint_or_none(payload.get("fingerprint_quick"))
        with self._connection() as conn:
            existing = conn.execute("SELECT id, resource_id FROM books WHERE path = ?", (path,)).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE books
                    SET file_name = ?, extension = ?, title = ?, author = ?, publisher = ?, language = ?,
                        tags_json = ?, status = ?, resource_type = ?, thumbnail_path = ?, info_text = ?,
                        is_missing = 0, missing_reason = NULL,
                        fingerprint_sha256 = COALESCE(?, fingerprint_sha256),
                        fingerprint_size_mtime = COALESCE(?, fingerprint_size_mtime),
                        fingerprint_quick = COALESCE(?, fingerprint_quick),
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        payload["file_name"],
                        payload["extension"],
                        payload.get("title"),
                        payload.get("author"),
                        payload.get("publisher"),
                        payload.get("language"),
                        payload["tags_json"],
                        payload.get("status", "UNREAD"),
                        payload.get("resource_type", "book"),
                        payload.get("thumbnail_path"),
                        payload.get("info_text"),
                        fp_sha,
                        fp_size,
                        fp_quick,
                        timestamp,
                        existing["id"],
                    ),
                )
                return False

            resource_id = payload.get("resource_id") or uuid4().hex
            conn.execute(
                """
                INSERT INTO books(
                    resource_id, file_name, extension, title, author, publisher, language, tags_json,
                    status, resource_type, path, thumbnail_path, info_text, is_missing, missing_reason,
                    fingerprint_sha256, fingerprint_size_mtime, fingerprint_quick, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?, ?, ?, ?)
                """,
                (
                    resource_id,
                    payload["file_name"],
                    payload["extension"],
                    payload.get("title"),
                    payload.get("author"),
                    payload.get("publisher"),
                    payload.get("language"),
                    payload["tags_json"],
                    payload.get("status", "UNREAD"),
                    payload.get("resource_type", "book"),
                    path,
                    payload.get("thumbnail_path"),
                    payload.get("info_text"),
                    fp_sha,
                    fp_size,
                    fp_quick,
                    timestamp,
                    timestamp,
                ),
            )
            return True

    def list_books(self, include_missing: bool | None = None) -> list[dict[str, Any]]:
        where_clause = ""
        params: tuple[Any, ...] = ()
        if include_missing is True:
            where_clause = "WHERE is_missing = 1"
        elif include_missing is False:
            where_clause = "WHERE is_missing = 0"

        query = f"""
            SELECT resource_id, file_name, extension, title, author, publisher, language, tags_json, status,
                   resource_type, path, thumbnail_path, info_text, is_missing, missing_reason
            FROM books
            {where_clause}
            ORDER BY lower(COALESCE(title, file_name))
        """
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()

        records: list[dict[str, Any]] = []
        for row in rows:
            tags_value = row["tags_json"] or "[]"
            try:
                tags = json.loads(tags_value)
            except json.JSONDecodeError:
                tags = []
            if not isinstance(tags, list):
                tags = []
            records.append(
                {
                    "resource_id": row["resource_id"],
                    "file_name": row["file_name"],
                    "extension": row["extension"],
                    "title": row["title"] or Path(row["file_name"]).stem,
                    "author": row["author"] or "",
                    "publisher": row["publisher"],
                    "language": row["language"],
                    "tags": [str(item) for item in tags],
                    "status": row["status"],
                    "resource_type": row["resource_type"],
                    "path": row["path"],
                    "thumbnail_path": row["thumbnail_path"],
                    "info_text": row["info_text"],
                    "is_missing": bool(row["is_missing"]),
                    "missing_reason": row["missing_reason"],
                }
            )
        return records

    @staticmethod
    def _path_in_roots(path_value: str, roots: list[str]) -> bool:
        normalized_path = os.path.normcase(os.path.normpath(str(path_value or "")))
        for root in roots:
            normalized_root = os.path.normcase(os.path.normpath(str(root or "")))
            if not normalized_root:
                continue
            if normalized_path == normalized_root:
                return True
            if normalized_path.startswith(normalized_root + os.sep):
                return True
        return False

    def list_books_in_roots(self, roots: list[str], *, resource_type: str | None = None) -> list[dict[str, Any]]:
        records = self.list_books(include_missing=False)
        scoped: list[dict[str, Any]] = []
        for record in records:
            if resource_type is not None and str(record.get("resource_type") or "") != resource_type:
                continue
            if self._path_in_roots(str(record.get("path") or ""), roots):
                scoped.append(record)
        return scoped

    def list_comics_in_roots(self, roots: list[str]) -> list[dict[str, Any]]:
        records = self.list_comics(include_missing=False)
        return [record for record in records if self._path_in_roots(str(record.get("path") or ""), roots)]

    def read_scan_report(self) -> dict[str, Any]:
        default: dict[str, Any] = {
            "added_count": 0,
            "updated_count": 0,
            "ignored_unsupported": 0,
            "skipped_unchanged_count": 0,
            "name_conflicts": [],
            "removed_missing_count": 0,
            "removed_missing_book_count": 0,
            "removed_missing_comic_count": 0,
            "errors": [],
            "warnings": [],
            "unsupported_files": [],
            "scanned_files": 0,
            "text_added_count": 0,
            "text_updated_count": 0,
            "text_scanned_files": 0,
            "text_errors": [],
            "comic_placeholder_copied_count": 0,
            "comic_thumbnail_enqueued_count": 0,
            "comic_thumbnail_workers_used": 0,
            "comic_large_image_downscaled_count": 0,
            "updated_at": None,
        }
        if not self.scan_report_path.exists():
            return default
        try:
            data = json.loads(self.scan_report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(data, dict):
            return default
        merged = dict(default)
        merged.update(data)
        return merged

    def write_scan_report(self, summary: dict[str, Any]) -> None:
        payload = dict(summary)
        payload["updated_at"] = now_utc_iso()
        self.scan_report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def record_scan_event(self, trigger: str, summary: dict[str, Any]) -> None:
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO scan_events(created_at, trigger, summary_json) VALUES(?, ?, ?)",
                (now_utc_iso(), trigger, json.dumps(summary, ensure_ascii=False)),
            )

    def list_active_books_for_thumbnail_task(self, roots: list[str] | None = None) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, resource_id, file_name, extension, title, path, thumbnail_path
                FROM books
                WHERE is_missing = 0
                AND resource_type != 'text_novel'
                ORDER BY lower(COALESCE(title, file_name))
                """
            ).fetchall()
        records = [dict(row) for row in rows]
        if not roots:
            return records
        return [record for record in records if self._path_in_roots(str(record.get("path") or ""), roots)]

    def list_active_comics_for_thumbnail_task(self, roots: list[str] | None = None) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, resource_id, title, path, cover_image_path, thumbnail_path
                     , cover_fingerprint
                FROM comics
                WHERE is_missing = 0
                ORDER BY lower(title)
                """
            ).fetchall()
        records = [dict(row) for row in rows]
        if not roots:
            return records
        return [record for record in records if self._path_in_roots(str(record.get("path") or ""), roots)]

    def clear_all_thumbnail_paths(self, roots: list[str] | None = None) -> int:
        if roots:
            records = self.list_active_books_for_thumbnail_task(roots=roots)
            ids = [int(record["id"]) for record in records if record.get("thumbnail_path")]
            if not ids:
                return 0
            placeholders = ",".join(["?"] * len(ids))
            with self._connection() as conn:
                cursor = conn.execute(
                    f"UPDATE books SET thumbnail_path = NULL, updated_at = ? WHERE id IN ({placeholders})",  # noqa: S608
                    (now_utc_iso(), *ids),
                )
                changed = cursor.rowcount if cursor.rowcount is not None else 0
            return max(0, int(changed))
        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE books
                SET thumbnail_path = NULL, updated_at = ?
                WHERE thumbnail_path IS NOT NULL AND thumbnail_path != ''
                """,
                (now_utc_iso(),),
            )
            changed = cursor.rowcount if cursor.rowcount is not None else 0
        return max(0, int(changed))

    def update_book_thumbnail_path(self, book_id: int, thumbnail_path: str | None) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE books SET thumbnail_path = ?, updated_at = ? WHERE id = ?",
                (thumbnail_path, now_utc_iso(), int(book_id)),
            )

    def clear_all_comic_thumbnail_paths(self, roots: list[str] | None = None) -> int:
        if roots:
            records = self.list_active_comics_for_thumbnail_task(roots=roots)
            ids = [int(record["id"]) for record in records if record.get("thumbnail_path")]
            if not ids:
                return 0
            placeholders = ",".join(["?"] * len(ids))
            with self._connection() as conn:
                cursor = conn.execute(
                    f"UPDATE comics SET thumbnail_path = NULL, updated_at = ? WHERE id IN ({placeholders})",  # noqa: S608
                    (now_utc_iso(), *ids),
                )
                changed = cursor.rowcount if cursor.rowcount is not None else 0
            return max(0, int(changed))
        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE comics
                SET thumbnail_path = NULL, updated_at = ?
                WHERE thumbnail_path IS NOT NULL AND thumbnail_path != ''
                """,
                (now_utc_iso(),),
            )
            changed = cursor.rowcount if cursor.rowcount is not None else 0
        return max(0, int(changed))

    def update_comic_thumbnail_path(self, comic_id: int, thumbnail_path: str | None) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE comics SET thumbnail_path = ?, updated_at = ? WHERE id = ?",
                (thumbnail_path, now_utc_iso(), int(comic_id)),
            )

    def update_comic_thumbnail_state(
        self,
        comic_id: int,
        *,
        thumbnail_path: str | None,
        cover_fingerprint: str | None = None,
    ) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE comics SET thumbnail_path = ?, cover_fingerprint = ?, updated_at = ? WHERE id = ?",
                (thumbnail_path, cover_fingerprint, now_utc_iso(), int(comic_id)),
            )

    def get_book_int_id(self, resource_id: str) -> int | None:
        """Return the integer primary key for a given resource_id (UUID hex)."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id FROM books WHERE resource_id = ?",
                (resource_id,),
            ).fetchone()
        return int(row["id"]) if row else None

    def upsert_comic(self, payload: dict[str, Any]) -> bool:
        path = payload["path"]
        timestamp = now_utc_iso()
        with self._connection() as conn:
            existing = conn.execute("SELECT id FROM comics WHERE path = ?", (path,)).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE comics
                    SET title = ?, comic_root = ?, cover_image_path = ?, thumbnail_path = ?,
                        cover_fingerprint = ?, folder_size_mtime = ?, folder_mtime = ?, folder_modified_at = ?, image_count = ?,
                        info_text = ?, is_missing = 0, missing_reason = NULL, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        payload["title"],
                        payload.get("comic_root"),
                        payload.get("cover_image_path"),
                        payload.get("thumbnail_path"),
                        payload.get("cover_fingerprint"),
                        payload.get("folder_size_mtime"),
                        int(payload.get("folder_mtime") or 0),
                        int(payload.get("folder_modified_at") or 0),
                        int(payload.get("image_count") or 0),
                        payload.get("info_text"),
                        timestamp,
                        existing["id"],
                    ),
                )
                return False

            resource_id = payload.get("resource_id") or uuid4().hex
            conn.execute(
                """
                INSERT INTO comics(
                    resource_id, title, path, comic_root, cover_image_path, thumbnail_path, cover_fingerprint,
                    folder_size_mtime, folder_mtime, folder_modified_at, image_count, info_text, is_missing, missing_reason, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
                """,
                (
                    resource_id,
                    payload["title"],
                    path,
                    payload.get("comic_root"),
                    payload.get("cover_image_path"),
                    payload.get("thumbnail_path"),
                    payload.get("cover_fingerprint"),
                    payload.get("folder_size_mtime"),
                    int(payload.get("folder_mtime") or 0),
                    int(payload.get("folder_modified_at") or 0),
                    int(payload.get("image_count") or 0),
                    payload.get("info_text"),
                    timestamp,
                    timestamp,
                ),
            )
            return True

    def list_comics(self, include_missing: bool | None = None, order_by: str = "folder_mtime_desc") -> list[dict[str, Any]]:
        where_clause = ""
        if include_missing is True:
            where_clause = "WHERE is_missing = 1"
        elif include_missing is False:
            where_clause = "WHERE is_missing = 0"
        order_clause = self._comic_order_clause(order_by)

        query = f"""
            SELECT resource_id, title, path, comic_root, cover_image_path, thumbnail_path,
                   cover_fingerprint, folder_size_mtime, folder_mtime, folder_modified_at,
                   image_count, info_text, is_missing, missing_reason
            FROM comics
            {where_clause}
            ORDER BY {order_clause}
        """
        with self._connection() as conn:
            rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]

    def backfill_comic_folder_modified_at(self) -> int:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, path
                FROM comics
                WHERE COALESCE(folder_modified_at, 0) <= 0
                """
            ).fetchall()
            updated = 0
            for row in rows:
                comic_id = int(row["id"])
                path_value = str(row["path"] or "")
                folder_path = Path(path_value)
                if not path_value or not folder_path.exists() or not folder_path.is_dir():
                    continue
                try:
                    folder_mtime = int(folder_path.stat().st_mtime)
                except OSError as exc:
                    append_scan_log(
                        f"comic_folder_mtime_backfill_failed | id={comic_id} | path={path_value} | reason={exc}"
                    )
                    continue
                conn.execute(
                    "UPDATE comics SET folder_modified_at = ?, updated_at = ? WHERE id = ?",
                    (folder_mtime, now_utc_iso(), comic_id),
                )
                updated += 1
        return updated

    def get_comic_int_id(self, resource_id: str) -> int | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id FROM comics WHERE resource_id = ?",
                (resource_id,),
            ).fetchone()
        return int(row["id"]) if row else None

    def add_comic_to_favorites(self, comic_id: int) -> None:
        import datetime
        with self._connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO favorite_comics (comic_id, added_at) VALUES (?, ?)",
                (comic_id, datetime.datetime.now().isoformat()),
            )

    def remove_comic_from_favorites(self, comic_id: int) -> None:
        with self._connection() as conn:
            conn.execute(
                "DELETE FROM favorite_comics WHERE comic_id = ?",
                (comic_id,),
            )

    def get_favorite_comics(self, order: str = "desc", order_by: str | None = None) -> list[dict[str, Any]]:
        order_text = str(order or "").strip().lower()
        order_sql = "ASC" if order_text == "asc" else "DESC"
        order_clause = self._comic_order_clause(order_by) if order_by else f"fc.added_at {order_sql}"
        query = f"""SELECT c.*, fc.added_at AS favorite_added_at
                    FROM comics c
                    INNER JOIN favorite_comics fc ON c.id = fc.comic_id
                    ORDER BY {order_clause}, fc.added_at DESC"""
        with self._connection() as conn:
            rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]

    def is_favorite_comic(self, comic_id: int) -> bool:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM favorite_comics WHERE comic_id = ?",
                (comic_id,),
            ).fetchone()
        return row is not None


    # ==================================================================
    # Collections & Favorites (added by _final_implement.py)
    # ==================================================================

    def _init_collections_tables(self) -> None:
        """Create collections/favorites tables if they don't exist."""
        with self._connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS collections (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL,
                    description TEXT    NOT NULL DEFAULT '',
                    created_at  TEXT    NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS collection_books (
                    collection_id INTEGER NOT NULL,
                    book_id       INTEGER NOT NULL,
                    added_at      TEXT    NOT NULL DEFAULT '',
                    PRIMARY KEY (collection_id, book_id),
                    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS favorite_books (
                    book_id  INTEGER PRIMARY KEY,
                    added_at TEXT    NOT NULL DEFAULT ''
                );
            """)

    # -- Collections --------------------------------------------------

    def create_collection(self, name: str, description: str = "") -> int:
        """Create a new collection and return its id."""
        import datetime
        self._init_collections_tables()
        with self._connection() as conn:
            cur = conn.execute(
                "INSERT INTO collections (name, description, created_at) VALUES (?, ?, ?)",
                (name, description, datetime.datetime.now().isoformat()),
            )
            return cur.lastrowid

    def get_all_collections(self) -> list[dict]:
        """Return all collections ordered by creation time (newest first)."""
        self._init_collections_tables()
        with self._connection() as conn:
            conn.row_factory = __import__('sqlite3').Row
            rows = conn.execute(
                "SELECT * FROM collections ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_collection(self, collection_id: int) -> None:
        """Delete a collection (and its book links)."""
        self._init_collections_tables()
        with self._connection() as conn:
            conn.execute(
                "DELETE FROM collection_books WHERE collection_id = ?",
                (collection_id,),
            )
            conn.execute(
                "DELETE FROM collections WHERE id = ?",
                (collection_id,),
            )

    def rename_collection(self, collection_id: int, new_name: str) -> None:
        """Rename a collection."""
        self._init_collections_tables()
        with self._connection() as conn:
            conn.execute(
                "UPDATE collections SET name = ? WHERE id = ?",
                (new_name, collection_id),
            )

    def add_book_to_collection(self, book_id: int, collection_id: int) -> None:
        """Add a book to a collection (idempotent)."""
        import datetime
        self._init_collections_tables()
        with self._connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO collection_books (collection_id, book_id, added_at)"
                " VALUES (?, ?, ?)",
                (collection_id, book_id, datetime.datetime.now().isoformat()),
            )

    def remove_book_from_collection(self, book_id: int, collection_id: int) -> None:
        """Remove a book from a collection."""
        self._init_collections_tables()
        with self._connection() as conn:
            conn.execute(
                "DELETE FROM collection_books WHERE collection_id = ? AND book_id = ?",
                (collection_id, book_id),
            )

    def get_books_in_collection(self, collection_id: int) -> list[dict]:
        """Return all book rows for a collection."""
        self._init_collections_tables()
        with self._connection() as conn:
            conn.row_factory = __import__('sqlite3').Row
            try:
                rows = conn.execute(
                    """SELECT b.*
                       FROM books b
                       INNER JOIN collection_books cb ON b.id = cb.book_id
                       WHERE cb.collection_id = ?
                       ORDER BY cb.added_at DESC""",
                    (collection_id,),
                ).fetchall()
                return [dict(r) for r in rows]
            except Exception:
                return []

    def get_collection_book_count(self, collection_id: int) -> int:
        """Return number of books in a collection."""
        self._init_collections_tables()
        with self._connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM collection_books WHERE collection_id = ?",
                (collection_id,),
            ).fetchone()
            return row[0] if row else 0

    def is_book_in_collection(self, book_id: int, collection_id: int) -> bool:
        """Return True if book is in the collection."""
        self._init_collections_tables()
        with self._connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM collection_books WHERE collection_id = ? AND book_id = ?",
                (collection_id, book_id),
            ).fetchone()
            return row is not None

    # -- Favorites ----------------------------------------------------

    def add_to_favorites(self, book_id: int) -> None:
        """Add a book to favorites (idempotent)."""
        import datetime
        self._init_collections_tables()
        with self._connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO favorite_books (book_id, added_at) VALUES (?, ?)",
                (book_id, datetime.datetime.now().isoformat()),
            )

    def remove_from_favorites(self, book_id: int) -> None:
        """Remove a book from favorites."""
        self._init_collections_tables()
        with self._connection() as conn:
            conn.execute(
                "DELETE FROM favorite_books WHERE book_id = ?",
                (book_id,),
            )

    def get_favorite_books(self, order: str = "desc") -> list[dict]:
        """Return all favorited book rows sorted by favorite add time."""
        self._init_collections_tables()
        order_text = str(order or "").strip().lower()
        order_sql = "ASC" if order_text == "asc" else "DESC"
        query = f"""SELECT b.*, fb.added_at AS favorite_added_at
                    FROM books b
                    INNER JOIN favorite_books fb ON b.id = fb.book_id
                    ORDER BY fb.added_at {order_sql}"""
        with self._connection() as conn:
            conn.row_factory = __import__('sqlite3').Row
            try:
                rows = conn.execute(query).fetchall()
                return [dict(r) for r in rows]
            except Exception:
                return []

    def get_collections_for_book(self, book_id: int) -> list[dict]:
        """Return all collections that contain the given book."""
        self._init_collections_tables()
        with self._connection() as conn:
            conn.row_factory = __import__("sqlite3").Row
            try:
                rows = conn.execute(
                    """
                    SELECT c.id, c.name, c.description, c.created_at, cb.added_at
                    FROM collections c
                    INNER JOIN collection_books cb ON cb.collection_id = c.id
                    WHERE cb.book_id = ?
                    ORDER BY lower(c.name)
                    """,
                    (int(book_id),),
                ).fetchall()
                return [dict(r) for r in rows]
            except Exception:
                return []

    def is_favorite(self, book_id: int) -> bool:
        """Return True if book is in favorites."""
        self._init_collections_tables()
        with self._connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM favorite_books WHERE book_id = ?",
                (book_id,),
            ).fetchone()
            return row is not None

    # -- Tags ---------------------------------------------------------

    def get_all_tags(self) -> list[str]:
        """Return all unique tags across all books, sorted alphabetically."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT tags_json FROM books WHERE tags_json IS NOT NULL AND tags_json != '[]'"
            ).fetchall()
        tags_set: set[str] = set()
        for row in rows:
            try:
                tags = json.loads(row[0])
                if isinstance(tags, list):
                    for t in tags:
                        if t and isinstance(t, str):
                            tags_set.add(t.strip())
            except Exception:
                pass
        return sorted(tags_set)

    def add_tag_to_book(self, book_id: int, tag: str) -> None:
        """Add a tag to a book's tag list (idempotent)."""
        tag = tag.strip()
        if not tag:
            return
        with self._connection() as conn:
            row = conn.execute(
                "SELECT tags_json FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            if not row:
                return
            try:
                tags: list = json.loads(row[0] or "[]")
            except Exception:
                tags = []
            if not isinstance(tags, list):
                tags = []
            if tag not in tags:
                tags.append(tag)
                conn.execute(
                    "UPDATE books SET tags_json = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(tags, ensure_ascii=False), now_utc_iso(), book_id),
                )

    def remove_tag_from_book(self, book_id: int, tag: str) -> None:
        """Remove a specific tag from a book."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT tags_json FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            if not row:
                return
            try:
                tags: list = json.loads(row[0] or "[]")
            except Exception:
                tags = []
            if not isinstance(tags, list):
                tags = []
            tags = [t for t in tags if t != tag]
            conn.execute(
                "UPDATE books SET tags_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(tags, ensure_ascii=False), now_utc_iso(), book_id),
            )

    def get_book_tags(self, book_id: int) -> list[str]:
        """Return the tags for a specific book."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT tags_json FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        if not row:
            return []
        try:
            tags = json.loads(row[0] or "[]")
            return [str(t) for t in tags if t] if isinstance(tags, list) else []
        except Exception:
            return []
