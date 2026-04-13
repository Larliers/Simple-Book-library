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
    HashStrategy,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_DB_PATH = SRC_ROOT / "sql" / "library.db"
DEFAULT_SCAN_REPORT_PATH = SRC_ROOT / "sql" / "scan_report.json"
DEFAULT_PREVIEW_DIR = PROJECT_ROOT / "img_preview"


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LibraryRepository:
    def __init__(self, db_path: str | Path | None = None, scan_report_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.scan_report_path = Path(scan_report_path) if scan_report_path else DEFAULT_SCAN_REPORT_PATH
        self.preview_dir = DEFAULT_PREVIEW_DIR
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.scan_report_path.parent.mkdir(parents=True, exist_ok=True)
        self.preview_dir.mkdir(parents=True, exist_ok=True)
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

                CREATE TABLE IF NOT EXISTS scan_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    summary_json TEXT NOT NULL
                );
                """
            )

    def _ensure_defaults(self) -> None:
        if self.get_setting("scan_depth", None) is None:
            self.set_setting("scan_depth", 2)
        if self.get_setting("hash_strategy", None) is None:
            self.set_setting("hash_strategy", HASH_STRATEGY_SIZE_MTIME)

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
        timestamp = now_utc_iso()
        with self._connection() as conn:
            conn.execute("DELETE FROM library_roots WHERE path = ?", (normalized,))
            cursor = conn.execute(
                """
                UPDATE books
                SET is_missing = 1, missing_reason = ?, updated_at = ?
                WHERE is_missing = 0
                AND (path = ? OR path LIKE ?)
                """,
                ("root_removed", timestamp, normalized, root_prefix),
            )
            moved_to_missed = cursor.rowcount if cursor.rowcount is not None else 0
        return max(0, int(moved_to_missed))

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
                SELECT path, title, file_name
                FROM books
                WHERE lower(file_name) = lower(?)
                AND lower(extension) = lower(?)
                AND path != ?
                LIMIT 1
                """,
                (file_name, extension, incoming_path),
            ).fetchone()
        return dict(row) if row else None

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
                        tags_json = ?, status = ?, resource_type = ?, thumbnail_path = ?,
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
                    status, resource_type, path, thumbnail_path, is_missing, missing_reason,
                    fingerprint_sha256, fingerprint_size_mtime, fingerprint_quick, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?, ?, ?, ?)
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
                    tags_json = ?, status = ?, resource_type = ?, path = ?, thumbnail_path = ?,
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
                   resource_type, path, thumbnail_path, is_missing, missing_reason
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
                    "is_missing": bool(row["is_missing"]),
                    "missing_reason": row["missing_reason"],
                }
            )
        return records

    def read_scan_report(self) -> dict[str, Any]:
        default: dict[str, Any] = {
            "added_count": 0,
            "updated_count": 0,
            "ignored_unsupported": 0,
            "name_conflicts": [],
            "restored_from_missed": 0,
            "moved_to_missed_count": 0,
            "errors": [],
            "unsupported_files": [],
            "scanned_files": 0,
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

    def list_active_books_for_thumbnail_task(self) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, resource_id, file_name, extension, title, path, thumbnail_path
                FROM books
                WHERE is_missing = 0
                ORDER BY lower(COALESCE(title, file_name))
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def clear_all_thumbnail_paths(self) -> int:
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

    def get_book_int_id(self, resource_id: str) -> int | None:
        """Return the integer primary key for a given resource_id (UUID hex)."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id FROM books WHERE resource_id = ?",
                (resource_id,),
            ).fetchone()
        return int(row["id"]) if row else None


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

    def get_favorite_books(self) -> list[dict]:
        """Return all favorited book rows."""
        self._init_collections_tables()
        with self._connection() as conn:
            conn.row_factory = __import__('sqlite3').Row
            try:
                rows = conn.execute(
                    """SELECT b.*
                       FROM books b
                       INNER JOIN favorite_books fb ON b.id = fb.book_id
                       ORDER BY fb.added_at DESC""",
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
