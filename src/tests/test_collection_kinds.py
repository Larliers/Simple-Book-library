from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.repository import (
    COLLECTION_KIND_BOOK,
    COLLECTION_KIND_COMIC,
    COLLECTION_KIND_TEXT_NOVEL,
    DEFAULT_FAVORITES_COLLECTION_NAME,
    FAVORITES_MIGRATED_SETTING,
    LibraryRepository,
)


class CollectionKindIsolationTests(unittest.TestCase):
    def _repo(self) -> LibraryRepository:
        tmp = tempfile.mkdtemp(prefix="bookhub_colkind_")
        return LibraryRepository(db_path=str(Path(tmp) / "library.db"))

    def _book(self, repo: LibraryRepository, name: str, resource_type: str = "book") -> int:
        path = rf"C:\lib\{name}"
        self.assertTrue(
            repo.upsert_book(
                {
                    "path": path,
                    "title": name,
                    "file_name": name,
                    "extension": ".pdf" if resource_type != "text_novel" else ".txt",
                    "resource_type": resource_type,
                    "tags_json": "[]",
                }
            )
        )
        with repo._connection() as conn:
            return int(conn.execute("SELECT id FROM books WHERE path = ?", (path,)).fetchone()["id"])

    def _comic(self, repo: LibraryRepository, name: str) -> int:
        path = rf"C:\comics\{name}"
        with repo._connection() as conn:
            conn.execute(
                """
                INSERT INTO comics(
                    resource_id, path, title, image_count, is_missing,
                    created_at, updated_at
                )
                VALUES(?, ?, ?, 1, 0, datetime('now'), datetime('now'))
                """,
                (f"comic-{name}", path, name),
            )
            return int(conn.execute("SELECT id FROM comics WHERE path = ?", (path,)).fetchone()["id"])

    def test_cross_kind_membership_rejected(self) -> None:
        repo = self._repo()
        book_id = self._book(repo, "a.pdf")
        novel_id = self._book(repo, "n.txt", "text_novel")
        comic_id = self._comic(repo, "c1")
        book_cid = repo.create_collection("Books", kind=COLLECTION_KIND_BOOK)
        novel_cid = repo.create_collection("Novels", kind=COLLECTION_KIND_TEXT_NOVEL)
        comic_cid = repo.create_collection("Comics", kind=COLLECTION_KIND_COMIC)

        repo.add_book_to_collection(novel_id, book_cid)
        repo.add_book_to_collection(book_id, novel_cid)
        repo.add_comic_to_collection(comic_id, book_cid)
        repo.add_book_to_collection(book_id, comic_cid)

        self.assertFalse(repo.is_book_in_collection(novel_id, book_cid))
        self.assertFalse(repo.is_book_in_collection(book_id, novel_cid))
        self.assertEqual(repo.get_books_in_collection(book_cid), [])
        self.assertEqual(repo.get_comics_in_collection(book_cid), [])
        self.assertEqual(repo.get_comics_in_collection(comic_cid), [])

        repo.add_book_to_collection(book_id, book_cid)
        repo.add_book_to_collection(novel_id, novel_cid)
        repo.add_comic_to_collection(comic_id, comic_cid)
        self.assertTrue(repo.is_book_in_collection(book_id, book_cid))
        self.assertEqual(len(repo.get_books_in_collection(novel_cid)), 1)
        self.assertEqual(len(repo.get_comics_in_collection(comic_cid)), 1)

    def test_get_all_collections_filters_kind(self) -> None:
        repo = self._repo()
        repo.create_collection("B", kind=COLLECTION_KIND_BOOK)
        repo.create_collection("N", kind=COLLECTION_KIND_TEXT_NOVEL)
        names = {c["name"] for c in repo.get_all_collections(COLLECTION_KIND_BOOK)}
        self.assertEqual(names, {"B"})

    def test_apply_collection_membership_changes_creates_and_updates_atomically(self) -> None:
        repo = self._repo()
        book_id = self._book(repo, "a.pdf")
        keep_id = repo.create_collection("Keep", kind=COLLECTION_KIND_BOOK)
        remove_id = repo.create_collection("Remove", kind=COLLECTION_KIND_BOOK)
        repo.add_book_to_collection(book_id, remove_id)

        result = repo.apply_collection_membership_changes(
            resource_db_id=book_id,
            kind=COLLECTION_KIND_BOOK,
            add_collection_ids=[keep_id],
            remove_collection_ids=[remove_id],
            create_name="  New Shelf  ",
        )

        self.assertEqual(result["created_collection"]["name"], "New Shelf")
        self.assertEqual(
            set(result["member_ids"]),
            {keep_id, result["created_collection"]["id"]},
        )
        self.assertFalse(repo.is_book_in_collection(book_id, remove_id))
        self.assertTrue(repo.is_book_in_collection(book_id, keep_id))

    def test_apply_collection_membership_changes_reuses_casefolded_name(self) -> None:
        repo = self._repo()
        book_id = self._book(repo, "a.pdf")
        existing_id = repo.create_collection("Reading List", kind=COLLECTION_KIND_BOOK)

        result = repo.apply_collection_membership_changes(
            resource_db_id=book_id,
            kind=COLLECTION_KIND_BOOK,
            create_name=" reading list ",
        )

        self.assertEqual(result["created_collection"]["id"], existing_id)
        self.assertEqual(result["member_ids"], [existing_id])
        self.assertEqual(len(repo.get_all_collections(COLLECTION_KIND_BOOK)), 1)

    def test_apply_collection_membership_changes_rejects_invalid_ids_without_partial_write(self) -> None:
        repo = self._repo()
        book_id = self._book(repo, "a.pdf")
        existing_id = repo.create_collection("Existing", kind=COLLECTION_KIND_BOOK)
        repo.add_book_to_collection(book_id, existing_id)

        with self.assertRaisesRegex(ValueError, "invalid_collection"):
            repo.apply_collection_membership_changes(
                resource_db_id=book_id,
                kind=COLLECTION_KIND_BOOK,
                add_collection_ids=[999999],
                remove_collection_ids=[existing_id],
                create_name="Must Not Exist",
            )

        self.assertTrue(repo.is_book_in_collection(book_id, existing_id))
        self.assertFalse(
            any(
                collection["name"] == "Must Not Exist"
                for collection in repo.get_all_collections(COLLECTION_KIND_BOOK)
            )
        )

    def test_strips_novels_from_book_collections(self) -> None:
        repo = self._repo()
        book_id = self._book(repo, "a.pdf")
        novel_id = self._book(repo, "n.txt", "text_novel")
        cid = repo.create_collection("Mix", kind=COLLECTION_KIND_BOOK)
        with repo._connection() as conn:
            conn.execute(
                "INSERT INTO collection_books (collection_id, book_id, added_at) VALUES (?, ?, datetime('now'))",
                (cid, novel_id),
            )
            conn.execute(
                "INSERT INTO collection_books (collection_id, book_id, added_at) VALUES (?, ?, datetime('now'))",
                (cid, book_id),
            )
        repo._migrate_typed_collections()
        members = repo.get_books_in_collection(cid)
        self.assertEqual([row["id"] for row in members], [book_id])

    def test_migrates_favorites_into_default_collections(self) -> None:
        repo = self._repo()
        book_id = self._book(repo, "a.pdf")
        novel_id = self._book(repo, "n.txt", "text_novel")
        comic_id = self._comic(repo, "c1")
        repo.add_to_favorites(book_id)
        repo.add_to_favorites(novel_id)
        repo.add_comic_to_favorites(comic_id)
        repo.set_setting(FAVORITES_MIGRATED_SETTING, False)
        repo._migrate_typed_collections()

        book_cols = repo.get_all_collections(COLLECTION_KIND_BOOK)
        novel_cols = repo.get_all_collections(COLLECTION_KIND_TEXT_NOVEL)
        comic_cols = repo.get_all_collections(COLLECTION_KIND_COMIC)
        self.assertTrue(any(c["name"] == DEFAULT_FAVORITES_COLLECTION_NAME for c in book_cols))
        self.assertTrue(any(c["name"] == DEFAULT_FAVORITES_COLLECTION_NAME for c in novel_cols))
        self.assertTrue(any(c["name"] == DEFAULT_FAVORITES_COLLECTION_NAME for c in comic_cols))
        book_cid = next(c["id"] for c in book_cols if c["name"] == DEFAULT_FAVORITES_COLLECTION_NAME)
        novel_cid = next(c["id"] for c in novel_cols if c["name"] == DEFAULT_FAVORITES_COLLECTION_NAME)
        comic_cid = next(c["id"] for c in comic_cols if c["name"] == DEFAULT_FAVORITES_COLLECTION_NAME)
        self.assertTrue(repo.is_book_in_collection(book_id, book_cid))
        self.assertTrue(repo.is_book_in_collection(novel_id, novel_cid))
        self.assertEqual([row["id"] for row in repo.get_comics_in_collection(comic_cid)], [comic_id])

    def test_delete_comics_clears_collection_links(self) -> None:
        repo = self._repo()
        comic_id = self._comic(repo, "c1")
        cid = repo.create_collection("Comics", kind=COLLECTION_KIND_COMIC)
        repo.add_comic_to_collection(comic_id, cid)
        self.assertEqual(repo.get_collection_item_count(cid), 1)
        deleted = repo.delete_comics_by_ids([comic_id])
        self.assertEqual(deleted, 1)
        self.assertEqual(repo.get_comics_in_collection(cid), [])
        self.assertEqual(repo.get_collection_item_count(cid), 0)


if __name__ == "__main__":
    unittest.main()
