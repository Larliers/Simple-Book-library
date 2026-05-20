from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from bookhub.library.models import (
    HASH_STRATEGIES,
    HASH_STRATEGY_SIZE_MTIME,
    DEFAULT_TEXT_PREVIEW_CHARS,
    TEXT_PREVIEW_CHAR_OPTIONS,
    HashStrategy,
)
from bookhub.library.preview_paths import ensure_preview_structure

DEFAULT_CARD_SPACING = 14
CARD_SPACING_MIN = 6
CARD_SPACING_MAX = 40
DEFAULT_TOPBAR_SEARCH_FONT_SIZE = 15
TOPBAR_SEARCH_FONT_SIZE_MIN = 12
TOPBAR_SEARCH_FONT_SIZE_MAX = 20

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_DB_PATH = SRC_ROOT / "sql" / "library.db"
DEFAULT_SCAN_REPORT_PATH = SRC_ROOT / "sql" / "scan_report.json"
DEFAULT_PREVIEW_DIR = PROJECT_ROOT / "img_preview"


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


class LibraryRepository:
    def __init__(self, db_path: str | Path | None = None, scan_report_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.scan_report_path = Path(scan_report_path) if scan_report_path else DEFAULT_SCAN_REPORT_PATH
        self.preview_dir = DEFAULT_PREVIEW_DIR
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.scan_report_path.parent.mkdir(parents=True, exist_ok=True)
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        ensure_preview_structure(self.preview_dir)
        self._init_db()
        self._ensure_defaults()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

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
            self.set_setting("hash_strategy", HASH_STRATEGY_SIZE_MTIME)
        if self.get_setting("card_spacing", None) is None:
            self.set_setting("card_spacing", DEFAULT_CARD_SPACING)
        if self.get_setting("topbar_search_font_size", None) is None:
            self.set_setting("topbar_search_font_size", DEFAULT_TOPBAR_SEARCH_FONT_SIZE)
        if self.get_setting("text_preview_chars", None) is None:
            self.set_setting("text_preview_chars", DEFAULT_TEXT_PREVIEW_CHARS)
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
        strategy = str(self.get_setting("hash_strategy", HASH_STRATEGY_SIZE_MTIME))
        if strategy not in HASH_STRATEGIES:
            strategy = HASH_STRATEGY_SIZE_MTIME
        return strategy  # type: ignore[return-value]

    def set_hash_strategy(self, strategy: str) -> None:
        normalized = strategy if strategy in HASH_STRATEGIES else HASH_STRATEGY_SIZE_MTIME
        self.set_setting("hash_strategy", normalized)

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

    def list_roots(self) -> list[str]:
        with self._connection() as conn:
            rows = conn.execute("SELECT path FROM library_roots ORDER BY lower(path)").fetchall()
        return [str(row["path"]) for row in rows]

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
            cursor = conn.execute(
                """
                DELETE FROM books
                WHERE 1=1
                AND resource_type != 'text_novel'
                AND (path = ? OR path LIKE ?)
                """,
                (normalized, root_prefix),
            )
            moved_to_missed = cursor.rowcount if cursor.rowcount is not None else 0
        return max(0, int(moved_to_missed))

    def list_comic_roots(self) -> list[str]:
        with self._connection() as conn:
            rows = conn.execute("SELECT path FROM comic_roots ORDER BY lower(path)").fetchall()
        return [str(row["path"]) for row in rows]

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
            cursor = conn.execute(
                """
                DELETE FROM comics
                WHERE 1=1
                AND (path = ? OR path LIKE ?)
                """,
                (normalized, root_prefix),
            )
            moved_to_missed = cursor.rowcount if cursor.rowcount is not None else 0
        return max(0, int(moved_to_missed))

    def list_text_roots(self) -> list[str]:
        with self._connection() as conn:
            rows = conn.execute("SELECT path FROM text_roots ORDER BY lower(path)").fetchall()
        return [str(row["path"]) for row in rows]

    def list_text_roots_with_rules(self) -> list[dict[str, str]]:
        with self._connection() as conn:
            rows = conn.execute("SELECT path, rules_json FROM text_roots ORDER BY lower(path)").fetchall()
        return [{"path": str(row["path"]), "rules_json": str(row["rules_json"] or "{}")} for row in rows]

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
            cursor = conn.execute(
                """
                DELETE FROM books
                WHERE 1=1
                AND resource_type = 'text_novel'
                AND (path = ? OR path LIKE ?)
                """,
                (normalized, root_prefix),
            )
            moved_to_missed = cursor.rowcount if cursor.rowcount is not None else 0
        return max(0, int(moved_to_missed))

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

    def find_missing_by_fingerprint(self, strategy: HashStrategy, value: str) -> dict[str, Any] | None:
        if not value:
            return None
        column_map = {
            "sha256": "fingerprint_sha256",
            "size_mtime": "fingerprint_size_mtime",
            "quick": "fingerprint_quick",
        }
        column = column_map[strategy]
        with self._connection() as conn:
            row = conn.execute(
                f"SELECT * FROM books WHERE is_missing = 1 AND {column} = ? LIMIT 1",  # noqa: S608
                (value,),
            ).fetchone()
        return dict(row) if row else None

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

    def delete_book_by_id(self, book_id: int) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM books WHERE id = ?", (int(book_id),))

    def delete_books_by_ids(self, book_ids: list[int]) -> int:
        ids = [int(item) for item in book_ids if int(item) > 0]
        if not ids:
            return 0
        placeholders = ",".join(["?"] * len(ids))
        with self._connection() as conn:
            cursor = conn.execute(f"DELETE FROM books WHERE id IN ({placeholders})", tuple(ids))  # noqa: S608
            deleted = cursor.rowcount if cursor.rowcount is not None else 0
        return max(0, int(deleted))

    def delete_comics_by_ids(self, comic_ids: list[int]) -> int:
        ids = [int(item) for item in comic_ids if int(item) > 0]
        if not ids:
            return 0
        placeholders = ",".join(["?"] * len(ids))
        with self._connection() as conn:
            cursor = conn.execute(f"DELETE FROM comics WHERE id IN ({placeholders})", tuple(ids))  # noqa: S608
            deleted = cursor.rowcount if cursor.rowcount is not None else 0
        return max(0, int(deleted))

    def upsert_book(self, payload: dict[str, Any]) -> bool:
        path = payload["path"]
        timestamp = now_utc_iso()
        with self._connection() as conn:
            existing = conn.execute("SELECT id, resource_id FROM books WHERE path = ?", (path,)).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE books
                    SET file_name = ?, extension = ?, title = ?, author = ?, publisher = ?, language = ?,
                        tags_json = ?, status = ?, resource_type = ?, thumbnail_path = ?, info_text = ?,
                        is_missing = 0, missing_reason = NULL,
                        fingerprint_sha256 = ?, fingerprint_size_mtime = ?, fingerprint_quick = ?, updated_at = ?
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
                        payload.get("fingerprint_sha256"),
                        payload.get("fingerprint_size_mtime"),
                        payload.get("fingerprint_quick"),
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
                    payload.get("fingerprint_sha256"),
                    payload.get("fingerprint_size_mtime"),
                    payload.get("fingerprint_quick"),
                    timestamp,
                    timestamp,
                ),
            )
            return True

    def restore_missing_book(self, missing_id: int, payload: dict[str, Any]) -> None:
        timestamp = now_utc_iso()
        with self._connection() as conn:
            conn.execute("DELETE FROM books WHERE path = ? AND id != ?", (payload["path"], missing_id))
            conn.execute(
                """
                UPDATE books
                SET file_name = ?, extension = ?, title = ?, author = ?, publisher = ?, language = ?,
                    tags_json = ?, status = ?, resource_type = ?, path = ?, thumbnail_path = ?, info_text = ?,
                    is_missing = 0, missing_reason = NULL,
                    fingerprint_sha256 = ?, fingerprint_size_mtime = ?, fingerprint_quick = ?, updated_at = ?
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
                    payload["path"],
                    payload.get("thumbnail_path"),
                    payload.get("info_text"),
                    payload.get("fingerprint_sha256"),
                    payload.get("fingerprint_size_mtime"),
                    payload.get("fingerprint_quick"),
                    timestamp,
                    missing_id,
                ),
            )

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
                        cover_fingerprint = ?, image_count = ?, info_text = ?, is_missing = 0, missing_reason = NULL, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        payload["title"],
                        payload.get("comic_root"),
                        payload.get("cover_image_path"),
                        payload.get("thumbnail_path"),
                        payload.get("cover_fingerprint"),
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
                    image_count, info_text, is_missing, missing_reason, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
                """,
                (
                    resource_id,
                    payload["title"],
                    path,
                    payload.get("comic_root"),
                    payload.get("cover_image_path"),
                    payload.get("thumbnail_path"),
                    payload.get("cover_fingerprint"),
                    int(payload.get("image_count") or 0),
                    payload.get("info_text"),
                    timestamp,
                    timestamp,
                ),
            )
            return True

    def list_comics(self, include_missing: bool | None = None) -> list[dict[str, Any]]:
        where_clause = ""
        if include_missing is True:
            where_clause = "WHERE is_missing = 1"
        elif include_missing is False:
            where_clause = "WHERE is_missing = 0"

        query = f"""
            SELECT resource_id, title, path, comic_root, cover_image_path, thumbnail_path,
                   cover_fingerprint, image_count, info_text, is_missing, missing_reason
            FROM comics
            {where_clause}
            ORDER BY lower(title)
        """
        with self._connection() as conn:
            rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]

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

    def get_favorite_comics(self, order: str = "desc") -> list[dict[str, Any]]:
        order_text = str(order or "").strip().lower()
        order_sql = "ASC" if order_text == "asc" else "DESC"
        query = f"""SELECT c.*, fc.added_at AS favorite_added_at
                    FROM comics c
                    INNER JOIN favorite_comics fc ON c.id = fc.comic_id
                    ORDER BY fc.added_at {order_sql}"""
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
