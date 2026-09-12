from __future__ import annotations

import tempfile
import unittest
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.repository import LibraryRepository


class TagManagementRepositoryTests(unittest.TestCase):
    def _repo(self) -> LibraryRepository:
        tmp = tempfile.mkdtemp(prefix="bookhub_tags_")
        return LibraryRepository(db_path=str(Path(tmp) / "library.db"))

    def test_tag_manager_scopes_default_to_all_and_cannot_all_be_disabled(self) -> None:
        repo = self._repo()

        self.assertEqual(
            repo.get_tag_manager_scopes(),
            {"library": True, "text_novel": True, "comic": True},
        )

        saved = repo.set_tag_manager_scopes(
            {"library": False, "text_novel": True, "comic": False}
        )
        rejected = repo.set_tag_manager_scopes(
            {"library": False, "text_novel": False, "comic": False}
        )

        self.assertTrue(saved["ok"])
        self.assertEqual(
            repo.get_tag_manager_scopes(),
            {"library": False, "text_novel": True, "comic": False},
        )
        self.assertFalse(rejected["ok"])
        self.assertEqual(rejected["error"], "empty_scope")
        self.assertEqual(rejected["scopes"], saved["scopes"])

    def _book(
        self,
        repo: LibraryRepository,
        resource_id: str,
        resource_type: str = "book",
    ) -> None:
        repo.upsert_book(
            {
                "resource_id": resource_id,
                "path": rf"C:\library\{resource_id}",
                "title": resource_id,
                "file_name": resource_id,
                "extension": ".txt" if resource_type == "text_novel" else ".pdf",
                "resource_type": resource_type,
                "tags_json": "[]",
            }
        )

    def _comic(self, repo: LibraryRepository, resource_id: str) -> None:
        repo.upsert_comic(
            {
                "resource_id": resource_id,
                "path": rf"C:\comics\{resource_id}",
                "title": resource_id,
                "image_count": 1,
            }
        )

    def test_catalog_groups_and_counts_active_resources_across_selected_scopes(self) -> None:
        repo = self._repo()
        self._book(repo, "book-1")
        self._book(repo, "novel-1", "text_novel")
        self._comic(repo, "comic-1")

        for page, resource_id in (
            ("library", "book-1"),
            ("text_novel", "novel-1"),
            ("comic", "comic-1"),
        ):
            self.assertTrue(repo.add_resource_tag(page, resource_id, "白色"))
        self.assertFalse(repo.add_resource_tag("library", "book-1", "白色"))
        self.assertTrue(repo.add_resource_tag("library", "book-1", "阿拉伯"))
        self.assertTrue(repo.add_resource_tag("library", "book-1", "anatomy"))
        self.assertTrue(repo.add_resource_tag("library", "book-1", "#特殊"))

        ascending = repo.get_tag_catalog("asc")
        descending = repo.get_tag_catalog("desc")
        by_letter = {group["letter"]: group for group in ascending["groups"]}

        self.assertEqual(ascending["tagCount"], 4)
        self.assertEqual([group["letter"] for group in ascending["groups"]], ["A", "B", "#"])
        self.assertEqual([item["name"] for item in by_letter["A"]["items"]], ["阿拉伯", "anatomy"])
        self.assertEqual(by_letter["B"]["items"], [{"name": "白色", "resourceCount": 3}])
        self.assertEqual([group["letter"] for group in descending["groups"]], ["B", "A", "#"])
        self.assertEqual([item["name"] for item in descending["groups"][1]["items"]], ["anatomy", "阿拉伯"])

        scope_combinations = (
            ({"library": True, "text_novel": False, "comic": False}, 1),
            ({"library": False, "text_novel": True, "comic": False}, 1),
            ({"library": False, "text_novel": False, "comic": True}, 1),
            ({"library": True, "text_novel": True, "comic": False}, 2),
            ({"library": True, "text_novel": False, "comic": True}, 2),
            ({"library": False, "text_novel": True, "comic": True}, 2),
            ({"library": True, "text_novel": True, "comic": True}, 3),
        )
        for scopes, expected_count in scope_combinations:
            with self.subTest(scopes=scopes):
                self.assertTrue(repo.set_tag_manager_scopes(scopes)["ok"])
                catalog = repo.get_tag_catalog("asc")
                white = next(
                    item
                    for group in catalog["groups"]
                    for item in group["items"]
                    if item["name"] == "白色"
                )
                self.assertEqual(white["resourceCount"], expected_count)

    def test_tag_resources_keep_source_order_and_comic_tags_survive_rescan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bookhub_tags_reopen_") as tmp:
            db_path = str(Path(tmp) / "library.db")
            repo = LibraryRepository(db_path=db_path)
            self._book(repo, "book-1")
            self._book(repo, "novel-1", "text_novel")
            self._comic(repo, "comic-1")
            for page, resource_id in (
                ("library", "book-1"),
                ("text_novel", "novel-1"),
                ("comic", "comic-1"),
            ):
                repo.add_resource_tag(page, resource_id, "共同标签")

            reopened = LibraryRepository(db_path=db_path)
            reopened.upsert_comic(
                {
                    "resource_id": "comic-1",
                    "path": r"C:\comics\comic-1",
                    "title": "comic-1 rescanned",
                    "image_count": 2,
                }
            )

            resources = reopened.get_resources_by_tag("共同标签")
            self.assertEqual(
                [(row["source_page"], row["resource_id"]) for row in resources],
                [
                    ("library", "book-1"),
                    ("text_novel", "novel-1"),
                    ("comic", "comic-1"),
                ],
            )
            self.assertEqual(resources[-1]["tags"], ["共同标签"])
            self.assertTrue(reopened.remove_resource_tag("comic", "comic-1", "共同标签"))
            self.assertEqual(reopened.get_resources_by_tag("共同标签")[-1]["source_page"], "text_novel")

    def test_existing_comic_table_is_migrated_without_losing_rows(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bookhub_tags_migrate_") as tmp:
            db_path = Path(tmp) / "library.db"
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    """
                    CREATE TABLE comics (
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
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO comics(resource_id, title, path, created_at, updated_at)
                    VALUES('legacy-comic', 'Legacy', 'C:\\comics\\legacy', datetime('now'), datetime('now'))
                    """
                )
                conn.commit()
            finally:
                conn.close()

            repo = LibraryRepository(db_path=str(db_path))

            self.assertTrue(repo.add_resource_tag("comic", "legacy-comic", "迁移标签"))
            self.assertEqual(repo.get_resources_by_tag("迁移标签")[0]["resource_id"], "legacy-comic")

    def test_catalog_ignores_missing_resources_and_invalid_tag_json(self) -> None:
        repo = self._repo()
        self._book(repo, "missing-book")
        self._book(repo, "broken-book")
        repo.add_resource_tag("library", "missing-book", "隐藏标签")
        repo.add_resource_tag("library", "broken-book", "损坏标签")
        with repo._connection() as conn:
            conn.execute("UPDATE books SET is_missing = 1 WHERE resource_id = 'missing-book'")
            conn.execute("UPDATE books SET tags_json = '{broken' WHERE resource_id = 'broken-book'")

        catalog = repo.get_tag_catalog("asc")

        self.assertEqual(catalog["tagCount"], 0)
        self.assertEqual(catalog["groups"], [])

    def test_catalog_and_suggestions_truncate_legacy_field_tags(self) -> None:
        from bookhub.library.metadata import build_metadata_tags
        from bookhub.library.models import ParsedMetadata

        repo = self._repo()
        self._book(repo, "book-1")
        repo.add_resource_tag("library", "book-1", "白色")
        repo.add_resource_tag("library", "book-1", "author: 波多野")
        repo.add_resource_tag("library", "book-1", "language:en")
        repo.add_resource_tag("library", "book-1", "publisher: 某社")
        repo.add_resource_tag("library", "book-1", "series:旧系列")
        repo.add_resource_tag("library", "book-1", "Author：全角")

        catalog = repo.get_tag_catalog("asc")
        names = [item["name"] for group in catalog["groups"] for item in group["items"]]
        suggestions = repo.get_all_tags()

        self.assertEqual(names, ["白色"])
        self.assertEqual(suggestions, ["白色"])
        self.assertEqual(build_metadata_tags(ParsedMetadata(author="波", language="zh")), [])


if __name__ == "__main__":
    unittest.main()
