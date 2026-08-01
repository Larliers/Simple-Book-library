from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bookhub.library import LibraryRepository


class RepositoryOrphanCleanupTests(unittest.TestCase):
    def _repo(self) -> LibraryRepository:
        tmp = tempfile.mkdtemp(prefix="bookhub_orphan_")
        return LibraryRepository(db_path=str(Path(tmp) / "library.db"))

    def test_delete_books_clears_favorite_and_collection_links(self) -> None:
        repo = self._repo()
        self.assertTrue(
            repo.upsert_book(
                {
                    "path": r"C:\lib\a.pdf",
                    "title": "A",
                    "file_name": "a.pdf",
                    "extension": ".pdf",
                    "resource_type": "book",
                    "tags_json": "[]",
                }
            )
        )
        with repo._connection() as conn:
            bid = int(conn.execute("SELECT id FROM books WHERE path = ?", (r"C:\lib\a.pdf",)).fetchone()["id"])
        repo.add_to_favorites(bid)
        cid = repo.create_collection("List")
        repo.add_book_to_collection(bid, cid)
        deleted = repo.delete_books_by_ids([bid])
        self.assertEqual(deleted, 1)
        with repo._connection() as conn:
            fav = conn.execute("SELECT COUNT(*) AS c FROM favorite_books WHERE book_id = ?", (bid,)).fetchone()["c"]
            col = conn.execute("SELECT COUNT(*) AS c FROM collection_books WHERE book_id = ?", (bid,)).fetchone()["c"]
        self.assertEqual(fav, 0)
        self.assertEqual(col, 0)

    def test_delete_comics_clears_favorite_links(self) -> None:
        repo = self._repo()
        with repo._connection() as conn:
            conn.execute(
                """
                INSERT INTO comics(
                    resource_id, path, title, image_count, is_missing,
                    created_at, updated_at
                )
                VALUES('comic-1', ?, 'Comic', 1, 0, datetime('now'), datetime('now'))
                """,
                (r"C:\comics\one",),
            )
            comic_id = int(conn.execute("SELECT id FROM comics WHERE resource_id = 'comic-1'").fetchone()["id"])
            conn.execute(
                "INSERT INTO favorite_comics(comic_id, added_at) VALUES(?, datetime('now'))",
                (comic_id,),
            )
        deleted = repo.delete_comics_by_ids([comic_id])
        self.assertEqual(deleted, 1)
        with repo._connection() as conn:
            fav = conn.execute("SELECT COUNT(*) AS c FROM favorite_comics WHERE comic_id = ?", (comic_id,)).fetchone()["c"]
        self.assertEqual(fav, 0)

    def test_foreign_keys_pragma_enabled(self) -> None:
        repo = self._repo()
        with repo._connection() as conn:
            enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(int(enabled), 1)


class RepositoryRootRemovalSafetyTests(unittest.TestCase):
    """BUG-2 regression: root dirs containing LIKE wildcards (% / _) must not
    delete sibling-directory records when a root is removed."""

    def _repo(self) -> LibraryRepository:
        tmp = tempfile.mkdtemp(prefix="bookhub_root_removal_")
        return LibraryRepository(db_path=str(Path(tmp) / "library.db"))

    def test_remove_root_keeps_sibling_with_like_wildcards(self) -> None:
        repo = self._repo()
        base = Path(repo.normalize_path(str(Path(tempfile.mkdtemp(prefix="lib_base_")))))
        target = repo.normalize_path(str(base / "100%_Special"))
        sibling = repo.normalize_path(str(base / "1000XSpecial"))
        for path in (target, sibling):
            repo.upsert_book(
                {
                    "path": path + "\\a.pdf",
                    "title": Path(path).name,
                    "file_name": "a.pdf",
                    "extension": ".pdf",
                    "resource_type": "book",
                    "tags_json": "[]",
                }
            )
        repo.add_root(target)
        # Sibling must not be affected by removing target root.
        deleted = repo.remove_root(target)
        self.assertEqual(deleted, 1)
        remaining = repo.list_books(include_missing=False)
        self.assertEqual([b["title"] for b in remaining], ["1000XSpecial"])

    def test_remove_comic_root_keeps_sibling_with_like_wildcards(self) -> None:
        repo = self._repo()
        base = Path(repo.normalize_path(str(Path(tempfile.mkdtemp(prefix="comic_base_")))))
        target = repo.normalize_path(str(base / "100%_Special"))
        sibling = repo.normalize_path(str(base / "1000XSpecial"))
        for path in (target, sibling):
            repo.upsert_comic(
                {
                    "path": path + "\\mycomic",
                    "title": Path(path).name,
                    "image_count": 1,
                }
            )
        repo.add_comic_root(target)
        deleted = repo.remove_comic_root(target)
        self.assertEqual(deleted, 1)
        remaining = repo.list_comics(include_missing=False)
        self.assertEqual([c["title"] for c in remaining], ["1000XSpecial"])

    def test_remove_text_root_keeps_sibling_with_like_wildcards(self) -> None:
        repo = self._repo()
        base = Path(repo.normalize_path(str(Path(tempfile.mkdtemp(prefix="text_base_")))))
        target = repo.normalize_path(str(base / "100%_Special"))
        sibling = repo.normalize_path(str(base / "1000XSpecial"))
        for path in (target, sibling):
            repo.upsert_book(
                {
                    "path": path + "\\novel.txt",
                    "title": Path(path).name,
                    "file_name": "novel.txt",
                    "extension": ".txt",
                    "resource_type": "text_novel",
                    "tags_json": "[]",
                }
            )
        repo.add_text_root(target)
        deleted = repo.remove_text_root(target)
        self.assertEqual(deleted, 1)
        remaining = repo.list_books(include_missing=False)
        self.assertEqual([b["title"] for b in remaining], ["1000XSpecial"])


if __name__ == "__main__":
    unittest.main()
