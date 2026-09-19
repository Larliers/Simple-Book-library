from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from bookhub.library import LibraryRepository
from bookhub.ui.web_window import WebAppWindow


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


class RepositorySettingNormalizeTests(unittest.TestCase):
    """BUG-6 regression: int settings must tolerate malformed values from the
    web layer, falling back to defaults and clamping to allowed ranges."""

    def _repo(self) -> LibraryRepository:
        tmp = tempfile.mkdtemp(prefix="bookhub_setting_")
        return LibraryRepository(db_path=str(Path(tmp) / "library.db"))

    def _window(self, repo: LibraryRepository) -> tuple[SimpleNamespace, SimpleNamespace]:
        bridge = SimpleNamespace(push_resources_calls=0)
        bridge.push_resources = lambda: setattr(
            bridge,
            "push_resources_calls",
            bridge.push_resources_calls + 1,
        )
        return SimpleNamespace(_repository=repo, _bridge=bridge), bridge

    def test_scan_depth_invalid_falls_back_to_default(self) -> None:
        repo = self._repo()
        repo.set_scan_depth("abc")
        self.assertEqual(repo.get_scan_depth(), 2)
        repo.set_scan_depth(None)
        self.assertEqual(repo.get_scan_depth(), 2)

    def test_scan_depth_out_of_range_is_clamped(self) -> None:
        repo = self._repo()
        repo.set_scan_depth("5")
        self.assertEqual(repo.get_scan_depth(), 3)
        repo.set_scan_depth("0")
        self.assertEqual(repo.get_scan_depth(), 1)

    def test_text_preview_chars_invalid_falls_back_to_default(self) -> None:
        repo = self._repo()
        repo.set_text_preview_chars("abc")
        self.assertEqual(repo.get_text_preview_chars(), 1200)
        repo.set_text_preview_chars(None)
        self.assertEqual(repo.get_text_preview_chars(), 1200)

    def test_text_preview_chars_outside_whitelist_falls_back(self) -> None:
        repo = self._repo()
        repo.set_text_preview_chars("1500")
        self.assertEqual(repo.get_text_preview_chars(), 1200)

    def test_comic_page_size_invalid_falls_back_to_default(self) -> None:
        repo = self._repo()
        repo.set_comic_page_size("abc")
        self.assertEqual(repo.get_comic_page_size(), 48)

    def test_viewport_buffer_screens_invalid_falls_back_to_default(self) -> None:
        repo = self._repo()
        repo.set_viewport_buffer_screens(None)
        self.assertEqual(repo.get_viewport_buffer_screens(), 3)

    def test_grid_columns_invalid_and_outside_whitelist_fall_back(self) -> None:
        repo = self._repo()
        repo.set_grid_columns("abc")
        self.assertEqual(repo.get_grid_columns(), 6)
        repo.set_grid_columns("9")
        self.assertEqual(repo.get_grid_columns(), 6)

    def test_apply_setting_routes_invalid_integer_values_through_repository_normalizers(self) -> None:
        repo = self._repo()
        window, bridge = self._window(repo)

        for key in ("comicPageSize", "viewportBufferScreens", "gridColumns"):
            with self.subTest(key=key):
                WebAppWindow.apply_setting(window, key, "abc")

        self.assertEqual(repo.get_comic_page_size(), 48)
        self.assertEqual(repo.get_viewport_buffer_screens(), 3)
        self.assertEqual(repo.get_grid_columns(), 6)
        self.assertEqual(bridge.push_resources_calls, 1)

    def test_apply_setting_normalizes_none_allowed_and_outside_values(self) -> None:
        repo = self._repo()
        window, bridge = self._window(repo)

        for key in ("comicPageSize", "viewportBufferScreens", "gridColumns"):
            with self.subTest(key=key, value=None):
                WebAppWindow.apply_setting(window, key, None)
        self.assertEqual(
            (repo.get_comic_page_size(), repo.get_viewport_buffer_screens(), repo.get_grid_columns()),
            (48, 3, 6),
        )

        for key, value in (
            ("comicPageSize", "96"),
            ("viewportBufferScreens", "6"),
            ("gridColumns", "12"),
        ):
            WebAppWindow.apply_setting(window, key, value)
        self.assertEqual(
            (repo.get_comic_page_size(), repo.get_viewport_buffer_screens(), repo.get_grid_columns()),
            (96, 6, 12),
        )

        for key, value in (
            ("comicPageSize", "95"),
            ("viewportBufferScreens", "7"),
            ("gridColumns", "9"),
        ):
            WebAppWindow.apply_setting(window, key, value)
        self.assertEqual(
            (repo.get_comic_page_size(), repo.get_viewport_buffer_screens(), repo.get_grid_columns()),
            (48, 3, 6),
        )
        self.assertEqual(bridge.push_resources_calls, 3)


if __name__ == "__main__":
    unittest.main()
