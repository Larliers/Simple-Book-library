from __future__ import annotations

import sys
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.models import LibraryScanRoot, ScanRequest
from bookhub.library.preview_paths import uri_to_path
from bookhub.library.repository import LibraryRepository
from bookhub.library.scanner import scan_roots
from bookhub.library.thumbnail_tasks import cleanup_library_thumbnails, regenerate_library_thumbnails


def _write_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (24, 36), color).save(path)


class ImageFolderBookImportTests(unittest.TestCase):
    def test_depth_two_image_folder_is_imported_with_natural_first_image_cover(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            book = root / "artbooks" / "Sample Book"
            _write_image(book / "0010.jpg", (10, 10, 10))
            _write_image(book / "0002.jpg", (20, 20, 20))
            _write_image(book / "0001.jpg", (30, 30, 30))

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            result = scan_roots(
                repository,
                ScanRequest(
                    roots=[LibraryScanRoot(path=str(root))],
                    scan_depth=2,
                    hash_strategy="size_mtime",
                ),
            )

            records = repository.list_books(include_missing=False)
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record["title"], "Sample Book")
            self.assertEqual(record["file_name"], "Sample Book")
            self.assertEqual(record["extension"], ".imgfolder")
            self.assertEqual(record["path"], repository.normalize_path(book))
            self.assertEqual(record["cover_image_path"], repository.normalize_path(book / "0001.jpg"))
            thumbnail = uri_to_path(record["thumbnail_path"])
            self.assertIsNotNone(thumbnail)
            self.assertTrue(thumbnail and thumbnail.is_file())
            self.assertEqual(result.added_count, 1)
            self.assertEqual(result.image_book_added_count, 1)
            self.assertEqual(result.image_book_detected_folders, 1)
            self.assertEqual(result.to_summary()["image_book_added_count"], 1)
            self.assertEqual(result.to_summary()["removed_ineligible_image_book_count"], 0)

    def test_existing_books_table_gains_cover_image_path_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            db_path = base / "legacy.db"
            with closing(sqlite3.connect(db_path)) as connection:
                connection.execute(
                    """
                    CREATE TABLE books (
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
                        cover_source TEXT,
                        cover_fingerprint TEXT,
                        info_text TEXT,
                        is_missing INTEGER NOT NULL DEFAULT 0,
                        missing_reason TEXT,
                        fingerprint_sha256 TEXT,
                        fingerprint_size_mtime TEXT,
                        fingerprint_quick TEXT,
                        file_mtime INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                connection.commit()

            repository = LibraryRepository(db_path, base / "scan_report.json", preview_dir=base / "preview")

            with closing(sqlite3.connect(db_path)) as connection:
                columns = {row[1] for row in connection.execute("PRAGMA table_info(books)")}
            self.assertIn("cover_image_path", columns)
            del repository

    def test_only_direct_child_folders_meeting_all_qualification_rules_are_imported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            root.mkdir(parents=True)
            for index in range(3):
                _write_image(root / f"root-{index}.jpg", (index, 0, 0))

            two_images = root / "two-images"
            for index in range(2):
                _write_image(two_images / f"{index}.jpg", (index, 1, 0))

            one_image = root / "one-image"
            _write_image(one_image / "0.jpg", (0, 1, 1))

            tied = root / "tied"
            for index in range(3):
                _write_image(tied / f"{index}.png", (index, 2, 0))
                (tied / f"{index}.txt").write_text("note", encoding="utf-8")

            fewer_images = root / "fewer-images"
            for index in range(3):
                _write_image(fewer_images / f"{index}.png", (index, 2, 1))
            for index in range(4):
                (fewer_images / f"{index}.txt").write_text("note", encoding="utf-8")

            has_child = root / "has-child"
            for index in range(3):
                _write_image(has_child / f"{index}.webp", (index, 3, 0))
            (has_child / "nested").mkdir()

            valid = root / "valid"
            for index, suffix in enumerate((".JPG", ".JPEG", ".PNG", ".WEBP")):
                _write_image(valid / f"{index}{suffix}", (index, 4, 0))
            (valid / "note.txt").write_text("note", encoding="utf-8")

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            result = scan_roots(
                repository,
                ScanRequest(
                    roots=[LibraryScanRoot(path=str(root))],
                    scan_depth=2,
                    hash_strategy="size_mtime",
                ),
            )

            records = repository.list_books(include_missing=False)
            self.assertEqual([record["title"] for record in records], ["valid"])
            self.assertEqual(result.image_book_detected_folders, 1)

    def test_all_comic_image_extensions_are_accepted_case_insensitively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            book = root / "all-image-formats"
            suffixes = (".JPG", ".jpeg", ".PNG", ".webp", ".GIF", ".bmp", ".TIF", ".tiff")
            for index, suffix in enumerate(suffixes):
                _write_image(book / f"{index:04}{suffix}", (index, 13, 0))

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            result = scan_roots(
                repository,
                ScanRequest(
                    roots=[LibraryScanRoot(path=str(root))],
                    scan_depth=1,
                    hash_strategy="size_mtime",
                ),
            )

            records = repository.list_books(include_missing=False)
            self.assertEqual([(record["title"], record["extension"]) for record in records], [
                ("all-image-formats", ".imgfolder")
            ])
            self.assertEqual(result.image_book_detected_folders, 1)

    def test_supported_book_files_inside_a_qualified_folder_are_not_imported_separately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            book = root / "mixed-book"
            for index in range(4):
                _write_image(book / f"{index:04}.jpg", (index, 5, 0))
            (book / "duplicate.pdf").write_bytes(b"%PDF-1.4\nmock\n")

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            result = scan_roots(
                repository,
                ScanRequest(
                    roots=[LibraryScanRoot(path=str(root))],
                    scan_depth=2,
                    hash_strategy="size_mtime",
                ),
            )

            records = repository.list_books(include_missing=False)
            self.assertEqual([(record["title"], record["extension"]) for record in records], [("mixed-book", ".imgfolder")])
            self.assertEqual(result.scanned_files, 0)

    def test_same_named_image_folders_use_existing_library_conflict_handling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            for parent_name in ("first", "second"):
                book = root / parent_name / "Same Name"
                for index in range(3):
                    _write_image(book / f"{index:04}.jpg", (index, 15, 0))

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            result = scan_roots(
                repository,
                ScanRequest(
                    roots=[LibraryScanRoot(path=str(root))],
                    scan_depth=2,
                    hash_strategy="size_mtime",
                ),
            )

            records = repository.list_books(include_missing=False)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["extension"], ".imgfolder")
            self.assertEqual(len(result.name_conflicts), 1)

    def test_second_scan_skips_unchanged_image_folder_book(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            book = root / "stable-book"
            for index in range(3):
                _write_image(book / f"{index:04}.jpg", (index, 6, 0))

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            request = ScanRequest(
                roots=[LibraryScanRoot(path=str(root))],
                scan_depth=2,
                hash_strategy="quick",
            )
            first = scan_roots(repository, request)
            second = scan_roots(repository, request)

            self.assertEqual(first.image_book_added_count, 1)
            self.assertEqual(second.image_book_added_count, 0)
            self.assertEqual(second.image_book_updated_count, 0)
            self.assertEqual(second.skipped_unchanged_count, 1)
            self.assertEqual(len(repository.list_books(include_missing=False)), 1)

    def test_rescan_removes_an_image_folder_book_that_is_no_longer_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            book = root / "temporary-book"
            for index in range(3):
                _write_image(book / f"{index:04}.jpg", (index, 7, 0))

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            request = ScanRequest(
                roots=[LibraryScanRoot(path=str(root))],
                scan_depth=2,
                hash_strategy="size_mtime",
            )
            scan_roots(repository, request)
            record = repository.list_books(include_missing=False)[0]
            book_id = repository.get_book_int_id(record["resource_id"])
            self.assertIsNotNone(book_id)
            collection_id = repository.create_collection("Shelf")
            repository.add_to_favorites(int(book_id))
            repository.add_book_to_collection(int(book_id), collection_id)

            (book / "nested").mkdir()
            result = scan_roots(repository, request)

            self.assertEqual(repository.list_books(include_missing=False), [])
            self.assertEqual(repository.get_favorite_books(), [])
            self.assertEqual(repository.get_books_in_collection(collection_id), [])
            self.assertEqual(result.removed_ineligible_image_book_count, 1)

    def test_unavailable_root_does_not_remove_an_existing_image_folder_book(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            book = root / "kept-book"
            for index in range(3):
                _write_image(book / f"{index:04}.jpg", (index, 8, 0))

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            scan_roots(
                repository,
                ScanRequest(
                    roots=[LibraryScanRoot(path=str(root))],
                    scan_depth=2,
                    hash_strategy="size_mtime",
                ),
            )

            offline_root = base / "offline"
            root.rename(offline_root)
            result = scan_roots(
                repository,
                ScanRequest(
                    roots=[LibraryScanRoot(path=str(root))],
                    scan_depth=2,
                    hash_strategy="size_mtime",
                ),
            )

            self.assertEqual(len(repository.list_books(include_missing=False)), 1)
            self.assertEqual(result.removed_ineligible_image_book_count, 0)
            self.assertEqual(len(result.errors), 1)

    def test_unreadable_root_does_not_remove_an_existing_image_folder_book(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            book = root / "kept-book"
            for index in range(3):
                _write_image(book / f"{index:04}.jpg", (index, 14, 0))

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            request = ScanRequest(
                roots=[LibraryScanRoot(path=str(root))],
                scan_depth=2,
                hash_strategy="size_mtime",
            )
            scan_roots(repository, request)

            with patch("bookhub.library.scanner.os.walk", side_effect=OSError("access denied")):
                result = scan_roots(repository, request)

            self.assertEqual(len(repository.list_books(include_missing=False)), 1)
            self.assertEqual(result.removed_ineligible_image_book_count, 0)
            self.assertTrue(any("access denied" in message for message in result.errors))

    def test_new_natural_first_image_updates_cover_and_open_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            book = root / "changing-cover"
            for index in (1, 2, 3):
                _write_image(book / f"{index:04}.jpg", (index, 9, 0))

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            request = ScanRequest(
                roots=[LibraryScanRoot(path=str(root))],
                scan_depth=2,
                hash_strategy="size_mtime",
            )
            scan_roots(repository, request)
            first_record = repository.list_books(include_missing=False)[0]
            self.assertTrue(str(first_record["cover_image_path"]).endswith("0001.jpg"))

            _write_image(book / "0000.jpg", (0, 9, 0))
            result = scan_roots(repository, request)
            updated = repository.list_books(include_missing=False)[0]

            self.assertTrue(str(updated["cover_image_path"]).endswith("0000.jpg"))
            self.assertEqual(result.image_book_updated_count, 1)

    def test_valid_manual_cover_survives_rescan_but_open_target_tracks_first_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            book = root / "manual-cover"
            for index in (1, 2, 3):
                _write_image(book / f"{index:04}.jpg", (index, 10, 0))

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            request = ScanRequest(
                roots=[LibraryScanRoot(path=str(root))],
                scan_depth=2,
                hash_strategy="size_mtime",
            )
            scan_roots(repository, request)
            record = repository.list_books(include_missing=False)[0]
            book_id = repository.get_book_int_id(record["resource_id"])
            self.assertIsNotNone(book_id)
            manual_cover = base / "preview" / "manual.webp"
            _write_image(manual_cover, (200, 100, 50))
            manual_uri = manual_cover.resolve().as_uri()
            repository.update_book_thumbnail_state(
                int(book_id),
                thumbnail_path=manual_uri,
                cover_source="manual",
            )

            _write_image(book / "0000.jpg", (0, 10, 0))
            scan_roots(repository, request)
            updated = repository.list_books(include_missing=False)[0]

            self.assertEqual(updated["thumbnail_path"], manual_uri)
            self.assertEqual(updated["cover_source"], "manual")
            self.assertTrue(str(updated["cover_image_path"]).endswith("0000.jpg"))

    def test_missing_manual_cover_falls_back_to_automatic_first_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            book = root / "missing-manual-cover"
            for index in (1, 2, 3):
                _write_image(book / f"{index:04}.jpg", (index, 16, 0))

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            request = ScanRequest(
                roots=[LibraryScanRoot(path=str(root))],
                scan_depth=2,
                hash_strategy="size_mtime",
            )
            scan_roots(repository, request)
            record = repository.list_books(include_missing=False)[0]
            book_id = repository.get_book_int_id(record["resource_id"])
            self.assertIsNotNone(book_id)
            repository.update_book_thumbnail_state(
                int(book_id),
                thumbnail_path=(base / "preview" / "deleted-manual.webp").resolve().as_uri(),
                cover_source="manual",
            )

            result = scan_roots(repository, request)
            updated = repository.list_books(include_missing=False)[0]

            self.assertEqual(result.image_book_updated_count, 1)
            self.assertIsNone(updated["cover_source"])
            self.assertTrue(uri_to_path(updated["thumbnail_path"]).is_file())
            self.assertTrue(str(updated["cover_image_path"]).endswith("0001.jpg"))

    def test_broken_first_image_warns_but_still_imports_the_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            book = root / "broken-cover"
            book.mkdir(parents=True)
            (book / "0000.jpg").write_bytes(b"not-an-image")
            _write_image(book / "0001.jpg", (1, 11, 0))
            _write_image(book / "0002.jpg", (2, 11, 0))

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            result = scan_roots(
                repository,
                ScanRequest(
                    roots=[LibraryScanRoot(path=str(root))],
                    scan_depth=2,
                    hash_strategy="size_mtime",
                ),
            )

            record = repository.list_books(include_missing=False)[0]
            self.assertIsNone(record["thumbnail_path"])
            self.assertTrue(str(record["cover_image_path"]).endswith("0000.jpg"))
            self.assertEqual([warning["code"] for warning in result.warnings], ["image_book_cover_generation_failed"])

    def test_library_thumbnail_cleanup_and_regenerate_support_image_folder_books(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "library"
            book = root / "thumbnail-book"
            for index in range(3):
                _write_image(book / f"{index:04}.jpg", (index, 12, 0))

            repository = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=base / "preview",
            )
            scan_roots(
                repository,
                ScanRequest(
                    roots=[LibraryScanRoot(path=str(root))],
                    scan_depth=2,
                    hash_strategy="size_mtime",
                ),
            )

            cleanup = cleanup_library_thumbnails(repository)
            regenerate = regenerate_library_thumbnails(repository)
            record = repository.list_books(include_missing=False)[0]
            thumbnail = uri_to_path(record["thumbnail_path"])

            self.assertEqual(cleanup.succeeded, 1)
            self.assertEqual(regenerate.succeeded, 1)
            self.assertEqual(regenerate.skipped, 0)
            self.assertTrue(thumbnail and thumbnail.is_file())


if __name__ == "__main__":
    unittest.main()
