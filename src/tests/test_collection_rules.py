from __future__ import annotations

import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from bookhub.library.collection_rules import matches_collection_rule, normalize_collection_rule, source_name_for_record
from bookhub.library.repository import COLLECTION_KIND_BOOK, LibraryRepository
from bookhub.library.worker import ScanWorker


class CollectionRuleMatchingTests(unittest.TestCase):
    def test_source_name_uses_original_file_or_folder_name(self) -> None:
        self.assertEqual(
            source_name_for_record(
                {"file_name": "[作者]-书名-出版社.fb2.zip", "extension": ".fb2.zip", "path": r"C:\books\changed.fb2.zip"},
                "book",
            ),
            "[作者]-书名-出版社",
        )
        self.assertEqual(
            source_name_for_record(
                {"file_name": "图片书", "extension": ".imgfolder", "path": r"C:\books\图片书"},
                "book",
            ),
            "图片书",
        )
        self.assertEqual(
            source_name_for_record({"path": r"C:\comics\短篇合集", "title": "改名"}, "comic"),
            "短篇合集",
        )
        self.assertEqual(
            source_name_for_record({"path": r"C:\comics\Archive.part.cbz", "title": "改名"}, "comic"),
            "Archive.part",
        )

    def test_match_modes_operators_and_case_sensitivity(self) -> None:
        rule = normalize_collection_rule(
            {
                "version": 1,
                "matchMode": "all",
                "conditions": [
                    {"operator": "starts_with", "value": " [作者] ", "caseSensitive": False},
                    {"operator": "contains", "value": "Book", "caseSensitive": True},
                    {"operator": "not_contains", "value": "试读", "caseSensitive": False},
                    {"operator": "ends_with", "value": "出版社", "caseSensitive": False},
                ],
            }
        )
        self.assertEqual(rule["conditions"][0]["value"], "[作者]")
        self.assertTrue(matches_collection_rule("[作者]-Book-出版社", rule))
        self.assertFalse(matches_collection_rule("[作者]-book-出版社", rule))

        equals_any = normalize_collection_rule(
            {
                "version": 1,
                "matchMode": "any",
                "conditions": [
                    {"operator": "equals", "value": "完全名称", "caseSensitive": False},
                    {"operator": "contains", "value": "备用", "caseSensitive": False},
                ],
            }
        )
        self.assertTrue(matches_collection_rule("完全名称", equals_any))
        self.assertTrue(matches_collection_rule("这是备用名称", equals_any))
        self.assertFalse(matches_collection_rule("完全名称-增补", equals_any))

    def test_metadata_conditions_use_selected_fields_and_preserve_v1_names(self) -> None:
        record = {
            "file_name": "Old Filename.txt", "extension": ".txt", "path": r"C:\novels\Old Filename.txt",
            "title": "新标题", "author": "Alice", "series": "银月系列", "tags_json": '["科幻", "长篇"]',
        }
        rule = normalize_collection_rule({
            "version": 2, "matchMode": "all", "conditions": [
                {"field": "author", "operator": "equals", "value": "alice", "caseSensitive": False},
                {"field": "series", "operator": "contains", "value": "银月", "caseSensitive": False},
                {"field": "tags", "operator": "equals", "value": "科幻", "caseSensitive": False},
            ],
        })
        self.assertTrue(matches_collection_rule(record, rule, kind="text_novel"))
        self.assertFalse(matches_collection_rule({**record, "author": "Bob"}, rule, kind="text_novel"))
        legacy = normalize_collection_rule({"version": 1, "conditions": [
            {"operator": "contains", "value": "Old Filename", "caseSensitive": False},
        ]})
        self.assertEqual(legacy["conditions"][0]["field"], "source_name")
        self.assertTrue(matches_collection_rule(record, legacy, kind="text_novel"))

    def test_empty_fields_and_individual_tags_do_not_match_accidentally(self) -> None:
        rule = {"version": 2, "conditions": [
            {"field": "tags", "operator": "not_contains", "value": "试读", "caseSensitive": False},
        ]}
        self.assertFalse(matches_collection_rule({"tags_json": "[]"}, rule, kind="comic"))
        self.assertFalse(matches_collection_rule({"tags_json": '["科幻", "试读版"]'}, rule, kind="comic"))
        self.assertTrue(matches_collection_rule({"tags_json": '["科幻", "长篇"]'}, rule, kind="comic"))
        no_author = {"version": 2, "conditions": [
            {"field": "author", "operator": "not_contains", "value": "Alice", "caseSensitive": False},
        ]}
        self.assertFalse(matches_collection_rule({"author": ""}, no_author, kind="book"))
        self.assertTrue(matches_collection_rule({"author": "Bob"}, no_author, kind="book"))


class CollectionRuleRepositoryTests(unittest.TestCase):
    def _repo(self) -> LibraryRepository:
        temp_dir = Path(tempfile.mkdtemp(prefix="bookhub_collection_rules_"))
        return LibraryRepository(temp_dir / "library.db", temp_dir / "scan_report.json")

    def _book(self, repo: LibraryRepository, file_name: str, resource_type: str = "book") -> int:
        extension = ".txt" if resource_type == "text_novel" else ".pdf"
        path = rf"C:\books\{file_name}"
        repo.upsert_book(
            {
                "path": path,
                "file_name": file_name,
                "extension": extension,
                "title": f"Display {file_name}",
                "resource_type": resource_type,
                "tags_json": "[]",
            }
        )
        with repo._connection() as conn:
            return int(conn.execute("SELECT id FROM books WHERE path = ?", (path,)).fetchone()["id"])

    def _comic(self, repo: LibraryRepository, source_name: str, *, cbz: bool = False) -> int:
        suffix = ".cbz" if cbz else ""
        path = rf"C:\comics\{source_name}{suffix}"
        repo.upsert_comic(
            {
                "path": path,
                "title": "Display title",
                "comic_root": r"C:\comics",
                "image_count": 3,
            }
        )
        with repo._connection() as conn:
            return int(conn.execute("SELECT id FROM comics WHERE path = ?", (path,)).fetchone()["id"])

    def test_preview_uses_metadata_fields_and_rejects_wrong_kind(self) -> None:
        repo = self._repo()
        repo.upsert_book({
            "path": r"C:\books\Opaque.pdf", "file_name": "Opaque.pdf", "extension": ".pdf",
            "title": "显示名称", "author": "Alice", "publisher": "青山社", "language": "zh",
            "tags_json": '["科幻", "长篇"]', "resource_type": "book",
        })
        book_collection = repo.create_collection("科幻", kind="book")
        rule = {"version": 2, "matchMode": "all", "conditions": [
            {"field": "author", "operator": "equals", "value": "Alice", "caseSensitive": True},
            {"field": "tags", "operator": "not_contains", "value": "试读", "caseSensitive": False},
        ]}
        self.assertEqual(repo.preview_collection_rule(book_collection, enabled=True, rule=rule)["summary"]["matched"], 1)
        self.assertEqual(repo.get_collection_rule(book_collection)["availableFields"],
                         ["source_name", "title", "author", "publisher", "language", "tags"])
        invalid = {"version": 2, "conditions": [
            {"field": "series", "operator": "contains", "value": "某系列", "caseSensitive": False},
        ]}
        with self.assertRaisesRegex(ValueError, "invalid_field"):
            repo.preview_collection_rule(book_collection, enabled=True, rule=invalid)

    def test_comic_title_and_tags_match_without_book_only_fields(self) -> None:
        repo = self._repo()
        repo.upsert_comic({"path": r"C:\comics\Opaque.cbz", "title": "夜航",
                           "comic_root": r"C:\comics", "image_count": 3})
        with repo._connection() as conn:
            resource_id = conn.execute("SELECT resource_id FROM comics WHERE path = ?", (r"C:\comics\Opaque.cbz",)).fetchone()[0]
        repo.add_resource_tag("comic", resource_id, "短篇")
        collection_id = repo.create_collection("短篇", kind="comic")
        detail = repo.get_collection_rule(collection_id)
        self.assertEqual(detail["availableFields"], ["source_name", "title", "tags"])
        rule = {"version": 2, "matchMode": "all", "conditions": [
            {"field": "title", "operator": "equals", "value": "夜航", "caseSensitive": False},
            {"field": "tags", "operator": "contains", "value": "短", "caseSensitive": False},
        ]}
        self.assertEqual(repo.preview_collection_rule(collection_id, enabled=True, rule=rule)["summary"]["matched"], 1)
        with self.assertRaisesRegex(ValueError, "invalid_field"):
            repo.save_collection_rule(collection_id, enabled=True, rule={"version": 2, "conditions": [
                {"field": "author", "operator": "contains", "value": "某人", "caseSensitive": False},
            ]})

    def test_text_tag_manual_changes_reconcile_immediately_and_survive_rescan(self) -> None:
        repo = self._repo()
        payload = {
            "path": r"C:\novels\Opaque.txt", "file_name": "Opaque.txt", "extension": ".txt",
            "title": "一部小说", "resource_type": "text_novel", "tags_json": '["科幻"]',
        }
        repo.upsert_book(payload)
        with repo._connection() as conn:
            row = conn.execute("SELECT id, resource_id FROM books WHERE path = ?", (payload["path"],)).fetchone()
        collection_id = repo.create_collection("科幻", kind="text_novel")
        rule = {"version": 2, "conditions": [
            {"field": "tags", "operator": "equals", "value": "科幻", "caseSensitive": False},
        ]}
        repo.save_collection_rule(collection_id, enabled=True, rule=rule)
        self.assertTrue(repo.is_book_in_collection(row["id"], collection_id))
        self.assertTrue(repo.remove_resource_tag("text_novel", row["resource_id"], "科幻"))
        self.assertFalse(repo.is_book_in_collection(row["id"], collection_id))
        repo.upsert_book(payload)
        self.assertEqual(repo.get_book_tags(row["id"]), [])
        self.assertTrue(repo.add_resource_tag("text_novel", row["resource_id"], "科幻"))
        self.assertTrue(repo.is_book_in_collection(row["id"], collection_id))

    def test_batch_added_tag_reconciles_rule_and_remains_after_text_rescan(self) -> None:
        repo = self._repo()
        payload = {
            "path": r"C:\novels\Batch.txt", "file_name": "Batch.txt", "extension": ".txt",
            "title": "批量", "resource_type": "text_novel", "tags_json": "[]",
        }
        repo.upsert_book(payload)
        with repo._connection() as conn:
            row = conn.execute("SELECT id, resource_id FROM books WHERE path = ?", (payload["path"],)).fetchone()
        collection_id = repo.create_collection("科幻", kind="text_novel")
        repo.save_collection_rule(collection_id, enabled=True, rule={"version": 2, "conditions": [
            {"field": "tags", "operator": "equals", "value": "科幻", "caseSensitive": False},
        ]})
        repo.apply_batch_quick_add(resources=[{"source_page": "text_novel", "resource_id": row["resource_id"]}],
                                   tags=["科幻"])
        self.assertTrue(repo.is_book_in_collection(row["id"], collection_id))
        repo.upsert_book(payload)
        self.assertEqual(repo.get_book_tags(row["id"]), ["科幻"])

    def test_tag_change_rolls_back_when_rule_membership_write_fails(self) -> None:
        repo = self._repo()
        repo.upsert_book({"path": r"C:\books\Atomic.pdf", "file_name": "Atomic.pdf",
                          "extension": ".pdf", "title": "原子", "resource_type": "book", "tags_json": "[]"})
        with repo._connection() as conn:
            row = conn.execute("SELECT id, resource_id FROM books WHERE file_name = 'Atomic.pdf'").fetchone()
        collection_id = repo.create_collection("原子", kind="book")
        repo.save_collection_rule(collection_id, enabled=True, rule={"version": 2, "conditions": [
            {"field": "tags", "operator": "equals", "value": "科幻", "caseSensitive": False},
        ]})
        with repo._connection() as conn:
            conn.execute("CREATE TRIGGER fail_tag_rule BEFORE INSERT ON collection_books "
                         "BEGIN SELECT RAISE(ABORT, 'blocked'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            repo.add_resource_tag("library", row["resource_id"], "科幻")
        self.assertEqual(repo.get_book_tags(row["id"]), [])
        self.assertFalse(repo.is_book_in_collection(row["id"], collection_id))

    def test_tag_mismatch_clears_exclusion_before_future_rematch(self) -> None:
        repo = self._repo()
        repo.upsert_book({"path": r"C:\books\Excluded.pdf", "file_name": "Excluded.pdf",
                          "extension": ".pdf", "title": "测试", "resource_type": "book",
                          "tags_json": '["科幻"]'})
        with repo._connection() as conn:
            row = conn.execute("SELECT id, resource_id FROM books WHERE file_name = 'Excluded.pdf'").fetchone()
        collection_id = repo.create_collection("科幻", kind="book")
        repo.save_collection_rule(collection_id, enabled=True, rule={"version": 2, "conditions": [
            {"field": "tags", "operator": "equals", "value": "科幻", "caseSensitive": False},
        ]})
        repo.remove_book_from_collection(row["id"], collection_id)
        self.assertEqual(repo.get_collection_rule(collection_id)["excludedCount"], 1)
        repo.remove_resource_tag("library", row["resource_id"], "科幻")
        self.assertEqual(repo.get_collection_rule(collection_id)["excludedCount"], 0)
        repo.add_resource_tag("library", row["resource_id"], "科幻")
        self.assertTrue(repo.is_book_in_collection(row["id"], collection_id))

    def test_legacy_text_tags_become_preserved_baseline_without_series_backfill(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="bookhub_legacy_text_rule_"))
        db_path = base / "library.db"
        with sqlite3.connect(db_path) as conn:
            conn.executescript("""
                CREATE TABLE books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, resource_id TEXT NOT NULL UNIQUE,
                    file_name TEXT NOT NULL, extension TEXT NOT NULL, title TEXT, author TEXT,
                    publisher TEXT, language TEXT, tags_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'UNREAD', resource_type TEXT NOT NULL DEFAULT 'book',
                    path TEXT NOT NULL UNIQUE, thumbnail_path TEXT, cover_image_path TEXT,
                    cover_source TEXT, cover_fingerprint TEXT, info_text TEXT,
                    is_missing INTEGER NOT NULL DEFAULT 0, missing_reason TEXT,
                    fingerprint_sha256 TEXT, fingerprint_size_mtime TEXT, fingerprint_quick TEXT,
                    file_mtime INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
            """)
            conn.execute(
                "INSERT INTO books(resource_id,file_name,extension,title,tags_json,resource_type,path,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                ("old-novel", "Old.txt", ".txt", "旧小说", '["旧标签"]', "text_novel", r"C:\novels\Old.txt", "", ""),
            )
        repo = LibraryRepository(db_path, base / "scan_report.json")
        self.assertEqual(repo.list_books(resource_type="text_novel")[0]["series"], "")
        repo.update_text_novel_metadata(r"C:\novels\Old.txt", title="旧小说", author=None,
                                        series="新系列", tags=[], info_text=None)
        record = repo.list_books(resource_type="text_novel")[0]
        self.assertEqual(record["series"], "新系列")
        self.assertEqual(record["tags"], ["旧标签"])

    def test_new_collections_are_disabled_and_manual_members_are_marked(self) -> None:
        repo = self._repo()
        repo.upsert_book(
            {
                "path": r"C:\books\Manual.pdf",
                "file_name": "Manual.pdf",
                "extension": ".pdf",
                "title": "Manual",
                "resource_type": "book",
                "tags_json": "[]",
            }
        )
        with repo._connection() as conn:
            book_id = int(conn.execute("SELECT id FROM books").fetchone()["id"])
        collection_id = repo.create_collection("Manual shelf", kind=COLLECTION_KIND_BOOK)
        repo.add_book_to_collection(book_id, collection_id)

        collection = repo.get_collection(collection_id)
        self.assertEqual(collection["rule_enabled"], 0)
        self.assertEqual(
            collection["rule_json"],
            '{"version":2,"matchMode":"all","conditions":[]}',
        )
        with repo._connection() as conn:
            link = conn.execute(
                "SELECT manual_source, rule_source FROM collection_books WHERE collection_id = ? AND book_id = ?",
                (collection_id, book_id),
            ).fetchone()
        self.assertEqual(dict(link), {"manual_source": 1, "rule_source": 0})

    def test_preview_and_save_rule_reconcile_manual_and_automatic_sources(self) -> None:
        repo = self._repo()
        manual_id = self._book(repo, "Python Manual.pdf")
        automatic_id = self._book(repo, "Python Cookbook.pdf")
        self._book(repo, "Rust Book.pdf")
        collection_id = repo.create_collection("Python", kind=COLLECTION_KIND_BOOK)
        repo.add_book_to_collection(manual_id, collection_id)
        with repo._connection() as conn:
            added_at = conn.execute(
                "SELECT added_at FROM collection_books WHERE collection_id = ? AND book_id = ?",
                (collection_id, manual_id),
            ).fetchone()["added_at"]

        rule = {
            "version": 1,
            "matchMode": "all",
            "conditions": [{"operator": "contains", "value": "Python", "caseSensitive": False}],
        }
        preview = repo.preview_collection_rule(collection_id, enabled=True, rule=rule)
        self.assertEqual(
            preview["summary"],
            {"matched": 2, "add": 1, "remove": 0, "manual_kept": 1, "excluded": 0},
        )
        self.assertEqual(repo.get_collection_item_count(collection_id), 1)

        applied = repo.save_collection_rule(collection_id, enabled=True, rule=rule)
        self.assertEqual(applied["summary"], preview["summary"])
        with repo._connection() as conn:
            links = {
                int(row["book_id"]): (int(row["manual_source"]), int(row["rule_source"]), row["added_at"])
                for row in conn.execute(
                    "SELECT book_id, manual_source, rule_source, added_at FROM collection_books WHERE collection_id = ?",
                    (collection_id,),
                ).fetchall()
            }
        self.assertEqual(links[manual_id], (1, 1, added_at))
        self.assertEqual(links[automatic_id][:2], (0, 1))

    def test_manual_removal_excludes_rule_member_until_exclusion_is_cleared(self) -> None:
        repo = self._repo()
        book_id = self._book(repo, "Python Patterns.pdf")
        collection_id = repo.create_collection("Python", kind=COLLECTION_KIND_BOOK)
        rule = {
            "version": 1,
            "matchMode": "all",
            "conditions": [{"operator": "contains", "value": "Python", "caseSensitive": False}],
        }
        repo.save_collection_rule(collection_id, enabled=True, rule=rule)
        self.assertTrue(repo.is_book_in_collection(book_id, collection_id))

        repo.remove_book_from_collection(book_id, collection_id)
        self.assertFalse(repo.is_book_in_collection(book_id, collection_id))
        detail = repo.get_collection_rule(collection_id)
        self.assertEqual([item["id"] for item in detail["exclusions"]], [book_id])

        repo.save_collection_rule(collection_id, enabled=True, rule=rule)
        self.assertFalse(repo.is_book_in_collection(book_id, collection_id))
        result = repo.clear_collection_rule_exclusion(collection_id, book_id)
        self.assertTrue(result["memberRestored"])
        self.assertTrue(repo.is_book_in_collection(book_id, collection_id))

    def test_exclusion_is_cleared_after_resource_stops_matching(self) -> None:
        repo = self._repo()
        book_id = self._book(repo, "Python Patterns.pdf")
        collection_id = repo.create_collection("Language", kind=COLLECTION_KIND_BOOK)

        def rule(value: str) -> dict[str, object]:
            return {
                "version": 1,
                "matchMode": "all",
                "conditions": [{"operator": "contains", "value": value, "caseSensitive": False}],
            }

        repo.save_collection_rule(collection_id, enabled=True, rule=rule("Python"))
        repo.remove_book_from_collection(book_id, collection_id)
        self.assertEqual(repo.get_collection_rule(collection_id)["excludedCount"], 1)

        repo.save_collection_rule(collection_id, enabled=True, rule=rule("Rust"))
        self.assertEqual(repo.get_collection_rule(collection_id)["excludedCount"], 0)
        repo.save_collection_rule(collection_id, enabled=True, rule=rule("Python"))
        self.assertTrue(repo.is_book_in_collection(book_id, collection_id))

    def test_manual_readd_clears_exclusion_and_marks_manual_source(self) -> None:
        repo = self._repo()
        book_id = self._book(repo, "Python Readd.pdf")
        collection_id = repo.create_collection("Python", kind="book")
        rule = {
            "version": 1,
            "matchMode": "all",
            "conditions": [{"operator": "contains", "value": "Python", "caseSensitive": False}],
        }
        repo.save_collection_rule(collection_id, enabled=True, rule=rule)
        repo.remove_book_from_collection(book_id, collection_id)

        repo.apply_collection_membership_changes(
            resource_db_id=book_id,
            kind="book",
            add_collection_ids=[collection_id],
        )

        self.assertEqual(repo.get_collection_rule(collection_id)["excludedCount"], 0)
        with repo._connection() as conn:
            link = conn.execute(
                "SELECT manual_source, rule_source FROM collection_books WHERE collection_id = ? AND book_id = ?",
                (collection_id, book_id),
            ).fetchone()
        self.assertEqual(dict(link), {"manual_source": 1, "rule_source": 0})

    def test_disabling_rule_requires_mode_and_supports_remove_or_convert(self) -> None:
        repo = self._repo()
        book_id = self._book(repo, "Python Patterns.pdf")
        rule = {
            "version": 1,
            "matchMode": "all",
            "conditions": [{"operator": "contains", "value": "Python", "caseSensitive": False}],
        }

        remove_collection = repo.create_collection("Remove", kind=COLLECTION_KIND_BOOK)
        repo.save_collection_rule(remove_collection, enabled=True, rule=rule)
        with self.assertRaisesRegex(ValueError, "disable_mode_required"):
            repo.save_collection_rule(remove_collection, enabled=False, rule=rule)
        self.assertTrue(repo.get_collection_rule(remove_collection)["enabled"])
        repo.save_collection_rule(remove_collection, enabled=False, rule=rule, disable_mode="remove")
        self.assertFalse(repo.is_book_in_collection(book_id, remove_collection))
        self.assertEqual(repo.get_collection_rule(remove_collection)["rule"], normalize_collection_rule(rule))

        convert_collection = repo.create_collection("Convert", kind=COLLECTION_KIND_BOOK)
        repo.save_collection_rule(convert_collection, enabled=True, rule=rule)
        repo.save_collection_rule(convert_collection, enabled=False, rule=rule, disable_mode="convert")
        self.assertTrue(repo.is_book_in_collection(book_id, convert_collection))
        with repo._connection() as conn:
            link = conn.execute(
                "SELECT manual_source, rule_source FROM collection_books WHERE collection_id = ? AND book_id = ?",
                (convert_collection, book_id),
            ).fetchone()
        self.assertEqual(dict(link), {"manual_source": 1, "rule_source": 0})

        zero_collection = repo.create_collection("No automatic members", kind=COLLECTION_KIND_BOOK)
        zero_rule = {
            "version": 1,
            "matchMode": "all",
            "conditions": [{"operator": "contains", "value": "Never matches", "caseSensitive": False}],
        }
        repo.save_collection_rule(zero_collection, enabled=True, rule=zero_rule)
        self.assertEqual(repo.get_collection_rule(zero_collection)["autoMemberCount"], 0)
        with self.assertRaisesRegex(ValueError, "disable_mode_required"):
            repo.preview_collection_rule(zero_collection, enabled=False, rule=zero_rule)
        with self.assertRaisesRegex(ValueError, "disable_mode_required"):
            repo.save_collection_rule(zero_collection, enabled=False, rule=zero_rule)
        repo.save_collection_rule(zero_collection, enabled=False, rule=zero_rule, disable_mode="remove")

    def test_rules_are_kind_isolated_and_resource_can_match_multiple_collections(self) -> None:
        repo = self._repo()
        book_id = self._book(repo, "Shared Keyword.pdf")
        novel_id = self._book(repo, "Shared Keyword.txt", "text_novel")
        comic_id = self._comic(repo, "Shared Keyword", cbz=True)
        rule = {
            "version": 1,
            "matchMode": "all",
            "conditions": [{"operator": "contains", "value": "Shared", "caseSensitive": False}],
        }
        book_collection_a = repo.create_collection("Book A", kind="book")
        book_collection_b = repo.create_collection("Book B", kind="book")
        novel_collection = repo.create_collection("Novel", kind="text_novel")
        comic_collection = repo.create_collection("Comic", kind="comic")

        for collection_id in (book_collection_a, book_collection_b, novel_collection, comic_collection):
            repo.save_collection_rule(collection_id, enabled=True, rule=rule)

        self.assertTrue(repo.is_book_in_collection(book_id, book_collection_a))
        self.assertTrue(repo.is_book_in_collection(book_id, book_collection_b))
        self.assertFalse(repo.is_book_in_collection(novel_id, book_collection_a))
        self.assertTrue(repo.is_book_in_collection(novel_id, novel_collection))
        self.assertEqual([item["id"] for item in repo.get_comics_in_collection(comic_collection)], [comic_id])

    def test_rule_save_rolls_back_configuration_and_membership_together(self) -> None:
        repo = self._repo()
        book_id = self._book(repo, "Python Atomic.pdf")
        collection_id = repo.create_collection("Atomic", kind="book")
        rule = {
            "version": 1,
            "matchMode": "all",
            "conditions": [{"operator": "contains", "value": "Python", "caseSensitive": False}],
        }
        with repo._connection() as conn:
            conn.execute(
                """
                CREATE TRIGGER fail_collection_rule_insert
                BEFORE INSERT ON collection_books
                BEGIN
                    SELECT RAISE(ABORT, 'forced collection rule failure');
                END
                """
            )

        with self.assertRaises(sqlite3.IntegrityError):
            repo.save_collection_rule(collection_id, enabled=True, rule=rule)

        self.assertFalse(repo.get_collection_rule(collection_id)["enabled"])
        self.assertFalse(repo.is_book_in_collection(book_id, collection_id))

    def test_legacy_collection_schema_migrates_members_as_manual_and_rules_off(self) -> None:
        repo = self._repo()
        book_id = self._book(repo, "Legacy.pdf")
        with repo._connection() as conn:
            conn.executescript(
                """
                DROP TABLE collection_rule_book_exclusions;
                DROP TABLE collection_rule_comic_exclusions;
                DROP TABLE collection_books;
                DROP TABLE collection_comics;
                DROP TABLE collections;
                CREATE TABLE collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    kind TEXT NOT NULL DEFAULT 'book',
                    created_at TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE collection_books (
                    collection_id INTEGER NOT NULL,
                    book_id INTEGER NOT NULL,
                    added_at TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (collection_id, book_id)
                );
                CREATE TABLE collection_comics (
                    collection_id INTEGER NOT NULL,
                    comic_id INTEGER NOT NULL,
                    added_at TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (collection_id, comic_id)
                );
                """
            )
            conn.execute(
                "INSERT INTO collections(id, name, description, kind, created_at) VALUES (7, 'Legacy', '', 'book', 'old')"
            )
            conn.execute(
                "INSERT INTO collection_books(collection_id, book_id, added_at) VALUES (7, ?, 'old')",
                (book_id,),
            )

        migrated = LibraryRepository(repo.db_path, repo.scan_report_path)
        self.assertFalse(migrated.get_collection_rule(7)["enabled"])
        with migrated._connection() as conn:
            link = conn.execute(
                "SELECT manual_source, rule_source FROM collection_books WHERE collection_id = 7 AND book_id = ?",
                (book_id,),
            ).fetchone()
        self.assertEqual(dict(link), {"manual_source": 1, "rule_source": 0})

    def test_scan_reconciliation_applies_all_enabled_rules_for_selected_kinds(self) -> None:
        repo = self._repo()
        collection_id = repo.create_collection("Python", kind="book")
        rule = {
            "version": 1,
            "matchMode": "all",
            "conditions": [{"operator": "contains", "value": "Python", "caseSensitive": False}],
        }
        repo.save_collection_rule(collection_id, enabled=True, rule=rule)
        book_id = self._book(repo, "Python After Scan.pdf")

        summary = repo.apply_enabled_collection_rules({"book"})

        self.assertEqual(
            summary,
            {
                "collectionsEvaluated": 1,
                "matched": 1,
                "added": 1,
                "removed": 0,
                "manualKept": 0,
                "excluded": 0,
            },
        )
        self.assertTrue(repo.is_book_in_collection(book_id, collection_id))


class CollectionRuleScanTests(unittest.TestCase):
    def test_scan_applies_enabled_rules_before_writing_summary(self) -> None:
        temp_dir = Path(tempfile.mkdtemp(prefix="bookhub_collection_rule_scan_"))
        root = temp_dir / "library"
        root.mkdir()
        (root / "Python Scan.md").write_text("# Python", encoding="utf-8")
        db_path = temp_dir / "library.db"
        report_path = temp_dir / "scan_report.json"
        preview_dir = temp_dir / "previews"
        repo = LibraryRepository(db_path, report_path, preview_dir=preview_dir)
        collection_id = repo.create_collection("Python", kind="book")
        repo.save_collection_rule(
            collection_id,
            enabled=True,
            rule={
                "version": 1,
                "matchMode": "all",
                "conditions": [{"operator": "contains", "value": "Python", "caseSensitive": False}],
            },
        )
        completed: list[dict[str, object]] = []
        worker = ScanWorker(
            db_path=db_path,
            scan_report_path=report_path,
            roots=[str(root)],
            comic_roots=[],
            text_roots=[],
            text_preview_chars=1200,
            scan_depth=2,
            hash_strategy="quick",
            comic_placeholder_copy_enabled=False,
            comic_thumbnail_workers_used=1,
            trigger="test",
            scope="library",
            preview_dir=preview_dir,
        )
        worker.scan_completed.connect(completed.append)

        worker.run()

        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]["collection_rules"]["added"], 1)
        refreshed = LibraryRepository(db_path, report_path, preview_dir=preview_dir)
        members = refreshed.get_books_in_collection(collection_id)
        self.assertEqual([item["file_name"] for item in members], ["Python Scan.md"])
        stored_report = refreshed.read_scan_report()
        self.assertEqual(stored_report["collection_rules"]["collectionsEvaluated"], 1)

    def test_rule_failure_keeps_scan_results_and_rolls_back_rule_members(self) -> None:
        temp_dir = Path(tempfile.mkdtemp(prefix="bookhub_collection_rule_scan_failure_"))
        root = temp_dir / "library"
        root.mkdir()
        (root / "Python Durable.md").write_text("# Python", encoding="utf-8")
        db_path = temp_dir / "library.db"
        report_path = temp_dir / "scan_report.json"
        preview_dir = temp_dir / "previews"
        repo = LibraryRepository(db_path, report_path, preview_dir=preview_dir)
        collection_id = repo.create_collection("Python", kind="book")
        repo.save_collection_rule(
            collection_id,
            enabled=True,
            rule={
                "version": 1,
                "matchMode": "all",
                "conditions": [{"operator": "contains", "value": "Python", "caseSensitive": False}],
            },
        )
        with repo._connection() as conn:
            conn.execute(
                """
                CREATE TRIGGER fail_scan_rule_insert
                BEFORE INSERT ON collection_books
                BEGIN
                    SELECT RAISE(ABORT, 'forced scan rule failure');
                END
                """
            )
        completed: list[dict[str, object]] = []
        worker = ScanWorker(
            db_path=db_path,
            scan_report_path=report_path,
            roots=[str(root)],
            comic_roots=[],
            text_roots=[],
            text_preview_chars=1200,
            scan_depth=2,
            hash_strategy="quick",
            comic_placeholder_copy_enabled=False,
            comic_thumbnail_workers_used=1,
            trigger="test",
            scope="library",
            preview_dir=preview_dir,
        )
        worker.scan_completed.connect(completed.append)

        worker.run()

        self.assertEqual(completed[0]["collection_rules"]["status"], "failed")
        self.assertTrue(any(item.get("code") == "collection_rules_failed" for item in completed[0]["warnings"]))
        refreshed = LibraryRepository(db_path, report_path, preview_dir=preview_dir)
        scanned = refreshed.list_books(include_missing=False)
        self.assertEqual([item["file_name"] for item in scanned], ["Python Durable.md"])
        self.assertEqual(refreshed.get_books_in_collection(collection_id), [])


if __name__ == "__main__":
    unittest.main()
