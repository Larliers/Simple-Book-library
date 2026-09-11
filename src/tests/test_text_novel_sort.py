from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.models import TextScanRequest, TextScanRoot
from bookhub.library.repository import COLLECTION_KIND_BOOK, COLLECTION_KIND_TEXT_NOVEL, LibraryRepository
from bookhub.library.scanner import scan_text_roots


class TextNovelSortTests(unittest.TestCase):
    def _titles(self, rows: list[dict]) -> list[str]:
        return [str(item.get("title") or item.get("file_name") or "") for item in rows]

    def test_text_novel_sort_order_by_file_mtime_and_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            alpha = root / "A_alpha.txt"
            beta = root / "B_beta.txt"
            alpha.write_text("A_alpha\nbody", encoding="utf-8")
            beta.write_text("B_beta\nbody", encoding="utf-8")
            os.utime(alpha, (1_700_000_000, 1_700_000_000))
            os.utime(beta, (1_800_000_000, 1_800_000_000))

            repo = LibraryRepository(base / "library.db", base / "scan_report.json")
            scan_text_roots(
                repo,
                TextScanRequest(roots=[TextScanRoot(path=str(root))], hash_strategy="size_mtime"),
            )

            by_mtime_asc = repo.list_books(
                include_missing=False,
                resource_type="text_novel",
                order_by="file_mtime_asc",
            )
            by_mtime_desc = repo.list_books(
                include_missing=False,
                resource_type="text_novel",
                order_by="file_mtime_desc",
            )
            by_title_asc = repo.list_books(
                include_missing=False,
                resource_type="text_novel",
                order_by="title_asc",
            )
            by_title_desc = repo.list_books(
                include_missing=False,
                resource_type="text_novel",
                order_by="title_desc",
            )

            self.assertEqual(self._titles(by_mtime_asc), ["A_alpha", "B_beta"])
            self.assertEqual(self._titles(by_mtime_desc), ["B_beta", "A_alpha"])
            self.assertEqual(self._titles(by_title_asc), ["A_alpha", "B_beta"])
            self.assertEqual(self._titles(by_title_desc), ["B_beta", "A_alpha"])
            self.assertGreater(int(by_mtime_desc[0].get("file_mtime") or 0), int(by_mtime_desc[1].get("file_mtime") or 0))

    def test_collection_members_follow_requested_order_not_added_at(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            alpha = root / "A_alpha.txt"
            beta = root / "B_beta.txt"
            alpha.write_text("A_alpha\nbody", encoding="utf-8")
            beta.write_text("B_beta\nbody", encoding="utf-8")
            os.utime(alpha, (1_700_000_000, 1_700_000_000))
            os.utime(beta, (1_800_000_000, 1_800_000_000))

            repo = LibraryRepository(base / "library.db", base / "scan_report.json")
            scan_text_roots(
                repo,
                TextScanRequest(roots=[TextScanRoot(path=str(root))], hash_strategy="size_mtime"),
            )
            novels = {
                item["title"]: item
                for item in repo.list_books(include_missing=False, resource_type="text_novel")
            }
            alpha_id = repo.get_book_int_id(str(novels["A_alpha"]["resource_id"]))
            beta_id = repo.get_book_int_id(str(novels["B_beta"]["resource_id"]))
            self.assertIsNotNone(alpha_id)
            self.assertIsNotNone(beta_id)
            assert alpha_id is not None
            assert beta_id is not None

            cid = repo.create_collection("Novels", kind=COLLECTION_KIND_TEXT_NOVEL)
            repo.add_book_to_collection(alpha_id, cid)
            repo.add_book_to_collection(beta_id, cid)
            with repo._connection() as conn:
                conn.execute(
                    "UPDATE collection_books SET added_at = ? WHERE collection_id = ? AND book_id = ?",
                    ("2026-01-01T00:00:00+00:00", cid, alpha_id),
                )
                conn.execute(
                    "UPDATE collection_books SET added_at = ? WHERE collection_id = ? AND book_id = ?",
                    ("2026-01-02T00:00:00+00:00", cid, beta_id),
                )

            by_added = repo.get_books_in_collection(cid)
            by_title = repo.get_books_in_collection(cid, order_by="title_asc")
            by_mtime = repo.get_books_in_collection(cid, order_by="file_mtime_desc")
            self.assertEqual(self._titles(by_added), ["B_beta", "A_alpha"])
            self.assertEqual(self._titles(by_title), ["A_alpha", "B_beta"])
            self.assertEqual(self._titles(by_mtime), ["B_beta", "A_alpha"])

    def test_invalid_sort_setting_falls_back_and_library_stays_title_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            repo = LibraryRepository(base / "library.db", base / "scan_report.json")
            repo.upsert_book(
                {
                    "path": str(base / "z-lib.pdf"),
                    "file_name": "z-lib.pdf",
                    "extension": ".pdf",
                    "title": "Z Library",
                    "resource_type": "book",
                    "tags_json": "[]",
                    "file_mtime": 1_900_000_000,
                }
            )
            repo.upsert_book(
                {
                    "path": str(base / "a-lib.pdf"),
                    "file_name": "a-lib.pdf",
                    "extension": ".pdf",
                    "title": "A Library",
                    "resource_type": "book",
                    "tags_json": "[]",
                    "file_mtime": 1_600_000_000,
                }
            )
            repo.upsert_book(
                {
                    "path": str(base / "z-novel.txt"),
                    "file_name": "z-novel.txt",
                    "extension": ".txt",
                    "title": "Z Novel",
                    "resource_type": "text_novel",
                    "tags_json": "[]",
                    "file_mtime": 1_900_000_000,
                }
            )
            repo.upsert_book(
                {
                    "path": str(base / "a-novel.txt"),
                    "file_name": "a-novel.txt",
                    "extension": ".txt",
                    "title": "A Novel",
                    "resource_type": "text_novel",
                    "tags_json": "[]",
                    "file_mtime": 1_600_000_000,
                }
            )

            repo.set_text_novel_sort_order_main("not-a-real-order")
            self.assertEqual(repo.get_text_novel_sort_order_main(), "file_mtime_desc")

            library = repo.list_books(include_missing=False, exclude_resource_type="text_novel")
            self.assertEqual(self._titles(library), ["A Library", "Z Library"])

            novels_default = repo.list_books(include_missing=False, resource_type="text_novel")
            self.assertEqual(self._titles(novels_default), ["A Novel", "Z Novel"])

            novels_sorted = repo.list_books(
                include_missing=False,
                resource_type="text_novel",
                order_by=repo.get_text_novel_sort_order_main(),
            )
            self.assertEqual(self._titles(novels_sorted), ["Z Novel", "A Novel"])

            book_cid = repo.create_collection("Books", kind=COLLECTION_KIND_BOOK)
            book_rows = repo.list_books(include_missing=False, exclude_resource_type="text_novel")
            for row in book_rows:
                book_id = repo.get_book_int_id(str(row["resource_id"]))
                self.assertIsNotNone(book_id)
                assert book_id is not None
                repo.add_book_to_collection(book_id, book_cid)
            members = repo.get_books_in_collection(book_cid, order_by="title_asc")
            self.assertEqual(len(members), 2)

    def test_backfill_file_mtime_from_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            db_path = base / "library.db"
            report = base / "scan_report.json"
            repo = LibraryRepository(db_path, report)
            timestamp = "2026-01-01T00:00:00+00:00"
            with repo._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO books(
                        resource_id, file_name, extension, title, author, publisher, language, tags_json,
                        status, resource_type, path, thumbnail_path, info_text, is_missing, missing_reason,
                        fingerprint_sha256, fingerprint_size_mtime, fingerprint_quick, file_mtime, created_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, NULL, NULL, NULL, '[]', 'UNREAD', 'text_novel', ?, NULL, NULL, 0, NULL,
                           NULL, ?, NULL, 0, ?, ?)
                    """,
                    ("rid-mtime", "old.txt", ".txt", "Old Novel", str(base / "old.txt"), "12:1700000123", timestamp, timestamp),
                )
            reopened = LibraryRepository(db_path, report)
            rows = reopened.list_books(include_missing=False, resource_type="text_novel")
            self.assertEqual(len(rows), 1)
            self.assertEqual(int(rows[0].get("file_mtime") or 0), 1700000123)


if __name__ == "__main__":
    unittest.main()
