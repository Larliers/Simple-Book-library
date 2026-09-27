from __future__ import annotations

import sqlite3
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bookhub.library.repository import LibraryRepository


class AuthorArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.repo = LibraryRepository(root / "library.db", root / "scan_report.json")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def novel(self, path: str, author: str) -> int:
        self.repo.upsert_book({"path": path, "file_name": Path(path).name, "extension": ".txt",
                               "title": Path(path).stem, "resource_type": "text_novel", "author": author,
                               "tags_json": "[]"})
        with self.repo._connection() as conn:
            return int(conn.execute("SELECT id FROM books WHERE path = ?", (path,)).fetchone()[0])

    def save(self, enabled: bool, mode: str = "") -> dict:
        preview = self.repo.preview_archive_preset(enabled=enabled, disable_mode=mode)
        return self.repo.save_archive_preset(enabled=enabled, disable_mode=mode, fingerprint=preview["fingerprint"])

    def collection(self, name: str) -> dict:
        return next(row for row in self.repo.get_all_collections("text_novel") if row["name"] == name)

    def test_cross_path_grouping_singleton_missing_and_reuse(self) -> None:
        a = self.novel("C:/one/a.txt", " Alice ")
        b = self.novel("D:/two/b.txt", "alice")
        self.novel("D:/two/c.txt", "Bob & Carol")
        self.novel("D:/two/d.txt", " ")
        self.repo.upsert_book({"path": "C:/books/book.pdf", "file_name": "book.pdf", "extension": ".pdf",
                               "title": "Book", "resource_type": "book", "author": "Alice", "tags_json": "[]"})
        reused = self.repo.create_collection("ALICE", "keep", kind="text_novel")
        self.repo.add_book_to_collection(a, reused)
        preview = self.repo.preview_archive_preset(enabled=True)
        self.assertEqual(preview["summary"]["create"], 1)
        self.assertEqual(preview["summary"]["reuse"], 1)
        self.assertEqual(preview["summary"]["missingAuthorCount"], 1)
        self.save(True)
        alice = self.collection("ALICE")
        self.assertEqual(alice["description"], "keep")
        self.assertEqual(alice["archive_key"], "alice")
        with self.repo._connection() as conn:
            links = conn.execute("SELECT book_id, manual_source, rule_source FROM collection_books WHERE collection_id = ? ORDER BY book_id", (reused,)).fetchall()
            self.assertEqual([(r[0], r[1], r[2]) for r in links], [(a, 1, 1), (b, 0, 1)])
        self.assertEqual(self.repo.get_collection_item_count(int(self.collection("Bob & Carol")["id"])), 1)

    def test_conflicts_skip_only_their_author(self) -> None:
        self.novel("C:/a.txt", "A")
        self.novel("C:/b.txt", "B")
        self.novel("C:/c.txt", "C")
        cid = self.repo.create_collection("A", kind="text_novel")
        self.repo.save_collection_rule(cid, enabled=True, rule={"version": 2, "conditions": [
            {"field": "author", "operator": "equals", "value": "A", "caseSensitive": False}]})
        self.repo.create_collection("B", kind="text_novel")
        self.repo.create_collection("b", kind="text_novel")
        preview = self.repo.preview_archive_preset(enabled=True)
        self.assertEqual(preview["summary"]["conflict"], 2)
        self.save(True)
        self.assertEqual(self.collection("C")["archive_key"], "c")
        self.assertEqual(self.collection("A")["archive_preset"], "")

    def test_author_change_scan_exclusion_disable_reenable(self) -> None:
        book = self.novel("C:/a.txt", "Alice")
        self.save(True)
        alice = int(self.collection("Alice")["id"])
        self.repo.remove_book_from_collection(book, alice)
        with self.repo._connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM collection_rule_book_exclusions WHERE collection_id = ?", (alice,)).fetchone()[0], 1)
        self.save(False, "remove")
        self.save(True)
        self.assertEqual(self.repo.get_collection_item_count(alice), 0)
        with self.repo._connection() as conn:
            conn.execute("UPDATE books SET author = 'Bob' WHERE id = ?", (book,))
        self.repo.apply_enabled_collection_rules({"text_novel"})
        self.assertEqual(self.repo.get_collection_item_count(alice), 0)
        self.assertEqual(self.repo.get_collection_item_count(int(self.collection("Bob")["id"])), 1)
        self.assertIsNotNone(self.repo.get_collection(alice))
        self.novel("C:/new.txt", "Bob")
        self.repo.apply_enabled_collection_rules({"text_novel"})
        self.assertEqual(self.repo.get_collection_item_count(int(self.collection("Bob")["id"])), 2)

    def test_manual_member_survives_author_change_and_other_scope_does_not_archive(self) -> None:
        book = self.novel("C:/manual.txt", "Alice")
        self.save(True)
        alice = int(self.collection("Alice")["id"])
        self.repo.add_book_to_collection(book, alice)
        with self.repo._connection() as conn:
            conn.execute("UPDATE books SET author = 'Bob' WHERE id = ?", (book,))
        self.repo.apply_enabled_collection_rules({"book"})
        self.assertFalse(any(row["name"] == "Bob" for row in self.repo.get_all_collections("text_novel")))
        self.repo.apply_enabled_collection_rules({"text_novel"})
        with self.repo._connection() as conn:
            link = conn.execute("SELECT manual_source, rule_source FROM collection_books WHERE collection_id = ? AND book_id = ?", (alice, book)).fetchone()
            self.assertEqual(tuple(link), (1, 0))

    def test_direct_author_metadata_update_reconciles_immediately(self) -> None:
        self.novel("C:/change.txt", "Alice")
        self.save(True)
        changed = self.repo.update_text_novel_metadata(
            "C:/change.txt", title="Change", author="Bob", series=None, tags=[], info_text=None)
        self.assertTrue(changed)
        self.assertEqual(self.repo.get_collection_item_count(int(self.collection("Alice")["id"])), 0)
        self.assertEqual(self.repo.get_collection_item_count(int(self.collection("Bob")["id"])), 1)

    def test_bridge_preview_token_and_targeted_page(self) -> None:
        from bookhub.ui.web_bridge import UiBridge
        self.novel("C:/one.txt", "Alice")
        bridge = UiBridge(self.repo, set())
        self.assertFalse(json.loads(bridge.getArchivePresets())["presets"][0]["enabled"])
        request = {"id": "text_novel_author", "enabled": True, "page": 1, "pageSize": 1}
        self.assertEqual(json.loads(bridge.saveArchivePreset(json.dumps(request)))["error"], "preview_required")
        preview = json.loads(bridge.previewArchivePreset(json.dumps(request)))
        self.assertTrue(preview["ok"])
        request["previewToken"] = preview["previewToken"]
        result = json.loads(bridge.saveArchivePreset(json.dumps(request)))
        self.assertTrue(result["ok"])
        self.assertEqual(result["collectionPage"], "novel_collections")
        self.assertEqual(len(result["collectionPageData"]["items"]), 1)
        self.assertEqual(json.loads(bridge.saveArchivePreset(json.dumps(request)))["error"], "preview_required")

    def test_convert_locks_and_detaches_after_disable(self) -> None:
        self.novel("C:/a.txt", "Alice")
        self.save(True)
        cid = int(self.collection("Alice")["id"])
        with self.assertRaisesRegex(ValueError, "archive_preset_managed"):
            self.repo.rename_collection(cid, "Different")
        with self.assertRaisesRegex(ValueError, "archive_preset_managed"):
            self.repo.delete_collection(cid)
        with self.assertRaisesRegex(ValueError, "archive_preset_managed"):
            self.repo.save_collection_rule(cid, enabled=False, rule={"version": 2, "conditions": []}, disable_mode="remove")
        self.save(False, "convert")
        with self.repo._connection() as conn:
            row = conn.execute("SELECT manual_source, rule_source FROM collection_books WHERE collection_id = ?", (cid,)).fetchone()
            self.assertEqual(tuple(row), (1, 0))
        self.repo.rename_collection(cid, "Different")
        self.assertEqual(self.repo.get_collection(cid)["archive_preset"], "")

    def test_stale_preview_and_sqlite_failure_roll_back(self) -> None:
        self.novel("C:/a.txt", "Alice")
        preview = self.repo.preview_archive_preset(enabled=True)
        self.novel("C:/b.txt", "Bob")
        with self.assertRaisesRegex(ValueError, "stale_preview"):
            self.repo.save_archive_preset(enabled=True, disable_mode="", fingerprint=preview["fingerprint"])
        preview = self.repo.preview_archive_preset(enabled=True)
        original = self.repo._author_archive_rule
        with patch.object(self.repo, "_author_archive_rule", side_effect=[original("Alice"), sqlite3.OperationalError("failed")]):
            with self.assertRaises(sqlite3.OperationalError):
                self.repo.save_archive_preset(enabled=True, disable_mode="", fingerprint=preview["fingerprint"])
        self.assertEqual(self.repo.get_all_collections("text_novel"), [])
        self.assertFalse(self.repo.get_setting("text_novel_author_archive_enabled", False))

    def test_existing_collection_schema_is_migrated_incrementally(self) -> None:
        root = Path(self.temp.name)
        old_db = root / "old.db"
        with sqlite3.connect(old_db) as conn:
            conn.execute("CREATE TABLE collections(id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', "
                         "kind TEXT NOT NULL DEFAULT 'book', created_at TEXT NOT NULL DEFAULT '', rule_enabled INTEGER NOT NULL DEFAULT 0, "
                         "rule_json TEXT NOT NULL DEFAULT '{}', rule_updated_at TEXT)")
            conn.execute("INSERT INTO collections(id, name, kind, rule_json) VALUES (7, 'Old', 'text_novel', ?)",
                         (json.dumps({"version": 2, "matchMode": "all", "conditions": []}),))
        repo = LibraryRepository(old_db, root / "old_scan.json")
        collection = repo.get_collection(7)
        self.assertEqual(collection["name"], "Old")
        self.assertEqual(collection["archive_preset"], "")
        self.assertEqual(collection["archive_key"], "")


if __name__ == "__main__":
    unittest.main()
