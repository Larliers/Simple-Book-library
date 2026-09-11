from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.models import TextScanRequest, TextScanRoot
from bookhub.library.preview_paths import uri_to_path
from bookhub.library.repository import LibraryRepository
from bookhub.library.scanner import scan_text_roots


class TextScanIncrementalTests(unittest.TestCase):
    def test_adding_sidecar_refreshes_unchanged_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            target = root / "novel.txt"
            target.write_text("第一章\n正文", encoding="utf-8")
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = TextScanRequest(roots=[TextScanRoot(path=str(root))], hash_strategy="size_mtime")

            scan_text_roots(repository, request)
            Image.new("RGB", (24, 36), "green").save(root / "novel.png")
            result = scan_text_roots(repository, request)

            self.assertEqual(result.text_updated_count, 1)
            record = repository.map_text_novels_for_scan([str(root)])[str(target.resolve())]
            self.assertEqual(record["cover_source"], "sidecar")
            self.assertTrue(record["thumbnail_path"])

    def test_scan_uses_preferred_same_stem_cover_and_caches_webp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            target = root / "novel.txt"
            target.write_text("第一章 开场\n正文内容", encoding="utf-8")
            Image.new("RGB", (24, 36), "red").save(root / "novel.jpg")
            Image.new("RGB", (24, 36), "blue").save(root / "novel.webp")

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            result = scan_text_roots(
                repository,
                TextScanRequest(roots=[TextScanRoot(path=str(root))], hash_strategy="size_mtime"),
            )

            self.assertEqual(result.text_added_count, 1)
            record = repository.map_text_novels_for_scan([str(root)])[str(target.resolve())]
            thumbnail_path = str(record["thumbnail_path"] or "")
            self.assertTrue(thumbnail_path.endswith(".webp"))
            cached_path = uri_to_path(thumbnail_path)
            self.assertIsNotNone(cached_path)
            self.assertTrue(cached_path.is_file())
            self.assertEqual(record["cover_source"], "sidecar")
            self.assertIn("novel.webp", record["cover_fingerprint"])

    def test_removing_sidecar_cover_clears_cached_thumbnail_without_touching_txt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            target = root / "novel.txt"
            target.write_text("第一章\n正文", encoding="utf-8")
            sidecar = root / "novel.png"
            Image.new("RGB", (24, 36), "green").save(sidecar)
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = TextScanRequest(
                roots=[TextScanRoot(path=str(root))],
                hash_strategy="size_mtime",
            )

            scan_text_roots(repository, request)
            first_record = repository.map_text_novels_for_scan([str(root)])[str(target.resolve())]
            cached_path = uri_to_path(str(first_record["thumbnail_path"]))
            self.assertIsNotNone(cached_path)
            self.assertTrue(cached_path.is_file())

            sidecar.unlink()
            second = scan_text_roots(repository, request)

            self.assertEqual(second.text_updated_count, 1)
            record = repository.map_text_novels_for_scan([str(root)])[str(target.resolve())]
            self.assertFalse(record["thumbnail_path"])
            self.assertFalse(record["cover_source"])
            self.assertFalse(record["cover_fingerprint"])
            self.assertFalse(cached_path.exists())

    def test_manual_cover_survives_sidecar_changes_and_rescan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            target = root / "novel.txt"
            target.write_text("第一章\n正文", encoding="utf-8")
            sidecar = root / "novel.jpg"
            Image.new("RGB", (24, 36), "green").save(sidecar)
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = TextScanRequest(
                roots=[TextScanRoot(path=str(root))],
                hash_strategy="size_mtime",
            )
            scan_text_roots(repository, request)
            record = repository.list_books()[0]
            manual_path = base / "manual.webp"
            Image.new("RGB", (24, 36), "purple").save(manual_path)
            repository.update_book_thumbnail_state(
                repository.get_book_int_id(str(record["resource_id"])),
                thumbnail_path=manual_path.resolve().as_uri(),
                cover_source="manual",
            )

            Image.new("RGB", (30, 45), "orange").save(sidecar)
            second = scan_text_roots(repository, request)

            self.assertEqual(second.skipped_unchanged_count, 1)
            refreshed = repository.map_text_novels_for_scan([str(root)])[str(target.resolve())]
            self.assertEqual(refreshed["thumbnail_path"], manual_path.resolve().as_uri())
            self.assertEqual(refreshed["cover_source"], "manual")

    def test_missing_manual_cover_falls_back_to_valid_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            target = root / "novel.txt"
            target.write_text("第一章\n正文", encoding="utf-8")
            Image.new("RGB", (24, 36), "green").save(root / "novel.jpg")
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = TextScanRequest(roots=[TextScanRoot(path=str(root))], hash_strategy="size_mtime")
            scan_text_roots(repository, request)
            record = repository.list_books()[0]
            repository.update_book_thumbnail_state(
                repository.get_book_int_id(str(record["resource_id"])),
                thumbnail_path=(base / "missing-manual.webp").resolve().as_uri(),
                cover_source="manual",
            )

            result = scan_text_roots(repository, request)

            self.assertEqual(result.text_updated_count, 1)
            refreshed = repository.map_text_novels_for_scan([str(root)])[str(target.resolve())]
            self.assertEqual(refreshed["cover_source"], "sidecar")
            self.assertTrue(refreshed["thumbnail_path"])

    def test_each_supported_sidecar_extension_is_discovered(self) -> None:
        for extension in (".webp", ".png", ".jpg", ".jpeg"):
            with self.subTest(extension=extension), tempfile.TemporaryDirectory() as tmp_dir:
                base = Path(tmp_dir)
                root = base / "texts"
                root.mkdir(parents=True, exist_ok=True)
                target = root / "novel.txt"
                target.write_text("第一章\n正文", encoding="utf-8")
                Image.new("RGB", (24, 36), "navy").save(root / f"novel{extension}")
                Image.new("RGB", (24, 36), "gray").save(root / "other.png")
                repository = LibraryRepository(base / "library.db", base / "scan_report.json")

                scan_text_roots(
                    repository,
                    TextScanRequest(roots=[TextScanRoot(path=str(root))], hash_strategy="size_mtime"),
                )

                record = repository.map_text_novels_for_scan([str(root)])[str(target.resolve())]
                self.assertTrue(record["thumbnail_path"])
                self.assertIn(f"novel{extension}", record["cover_fingerprint"])

    def test_sidecar_priority_falls_through_in_declared_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            target = root / "novel.txt"
            target.write_text("第一章\n正文", encoding="utf-8")
            for extension, color in zip((".webp", ".png", ".jpg", ".jpeg"), ("red", "green", "blue", "gray")):
                Image.new("RGB", (24, 36), color).save(root / f"novel{extension}")
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = TextScanRequest(roots=[TextScanRoot(path=str(root))], hash_strategy="size_mtime")

            for extension in (".webp", ".png", ".jpg", ".jpeg"):
                scan_text_roots(repository, request)
                record = repository.map_text_novels_for_scan([str(root)])[str(target.resolve())]
                self.assertIn(f"novel{extension}", record["cover_fingerprint"])
                (root / f"novel{extension}").unlink()

    def test_corrupt_sidecar_warns_but_text_is_still_imported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            target = root / "novel.txt"
            target.write_text("第一章\n正文", encoding="utf-8")
            (root / "novel.png").write_bytes(b"not-an-image")
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")

            result = scan_text_roots(
                repository,
                TextScanRequest(roots=[TextScanRoot(path=str(root))], hash_strategy="size_mtime"),
            )

            self.assertEqual(result.text_added_count, 1)
            self.assertTrue(any(item.get("code") == "text_cover_generation_failed" for item in result.warnings))
            record = repository.map_text_novels_for_scan([str(root)])[str(target.resolve())]
            self.assertFalse(record["thumbnail_path"])

    def test_changed_sidecar_refreshes_thumbnail_when_text_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            target = root / "novel.txt"
            target.write_text("第一章\n正文", encoding="utf-8")
            sidecar = root / "novel.jpeg"
            Image.new("RGB", (1000, 1600), "red").save(sidecar)
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = TextScanRequest(
                roots=[TextScanRoot(path=str(root))],
                hash_strategy="size_mtime",
            )
            scan_text_roots(repository, request)
            first = repository.map_text_novels_for_scan([str(root)])[str(target.resolve())]

            Image.new("RGB", (1200, 1800), "blue").save(sidecar)
            os.utime(sidecar, (sidecar.stat().st_atime, sidecar.stat().st_mtime + 10))
            second = scan_text_roots(repository, request)

            self.assertEqual(second.text_updated_count, 1)
            refreshed = repository.map_text_novels_for_scan([str(root)])[str(target.resolve())]
            self.assertNotEqual(refreshed["cover_fingerprint"], first["cover_fingerprint"])
            cached_path = uri_to_path(str(refreshed["thumbnail_path"]))
            self.assertIsNotNone(cached_path)
            with Image.open(cached_path) as cached:
                self.assertLessEqual(cached.width, 360)
                self.assertLessEqual(cached.height, 540)

    def test_same_size_sidecar_change_within_one_second_refreshes_thumbnail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            target = root / "novel.txt"
            target.write_text("第一章\n正文", encoding="utf-8")
            sidecar = root / "novel.png"
            Image.new("RGB", (24, 36), "red").save(sidecar)
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = TextScanRequest(roots=[TextScanRoot(path=str(root))], hash_strategy="size_mtime")
            scan_text_roots(repository, request)
            first = repository.map_text_novels_for_scan([str(root)])[str(target.resolve())]
            original_stat = sidecar.stat()

            sidecar.write_bytes(sidecar.read_bytes())
            original_second_ns = (original_stat.st_mtime_ns // 1_000_000_000) * 1_000_000_000
            shifted_fraction_ns = (original_stat.st_mtime_ns % 1_000_000_000 + 100_000_000) % 1_000_000_000
            os.utime(sidecar, ns=(original_stat.st_atime_ns, original_second_ns + shifted_fraction_ns))
            result = scan_text_roots(repository, request)

            self.assertEqual(result.text_updated_count, 1)
            refreshed = repository.map_text_novels_for_scan([str(root)])[str(target.resolve())]
            self.assertNotEqual(refreshed["cover_fingerprint"], first["cover_fingerprint"])

    def test_existing_text_thumbnail_is_migrated_as_manual_cover(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            db_path = base / "library.db"
            repository = LibraryRepository(db_path, base / "scan_report.json")
            repository.upsert_book(
                {
                    "path": str(base / "legacy.txt"),
                    "file_name": "legacy.txt",
                    "extension": ".txt",
                    "title": "Legacy",
                    "resource_type": "text_novel",
                    "tags_json": "[]",
                    "thumbnail_path": (base / "legacy.webp").resolve().as_uri(),
                }
            )

            reopened = LibraryRepository(db_path, base / "scan_report.json")
            record = reopened.list_books()[0]

            self.assertEqual(record["cover_source"], "manual")

    def test_second_scan_skips_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            target = root / "novel.txt"
            target.write_text("第一章 开场\n正文内容", encoding="utf-8")

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = TextScanRequest(
                roots=[TextScanRoot(path=str(root))],
                hash_strategy="size_mtime",
            )

            first = scan_text_roots(repository, request)
            self.assertEqual(first.text_added_count, 1)
            self.assertEqual(first.skipped_unchanged_count, 0)

            second = scan_text_roots(repository, request)
            self.assertEqual(second.text_added_count, 0)
            self.assertEqual(second.text_updated_count, 0)
            self.assertEqual(second.skipped_unchanged_count, 1)

    def test_touch_forces_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            target = root / "novel.txt"
            target.write_text("旧标题\n正文", encoding="utf-8")

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = TextScanRequest(
                roots=[TextScanRoot(path=str(root))],
                hash_strategy="size_mtime",
            )

            scan_text_roots(repository, request)
            os.utime(target, (target.stat().st_atime, target.stat().st_mtime + 10))
            second = scan_text_roots(repository, request)
            self.assertEqual(second.skipped_unchanged_count, 0)
            self.assertEqual(second.text_updated_count, 1)

    def test_quick_backfills_then_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            target = root / "novel.txt"
            target.write_text("第一章\n正文", encoding="utf-8")

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            first = scan_text_roots(
                repository,
                TextScanRequest(roots=[TextScanRoot(path=str(root))], hash_strategy="size_mtime"),
            )
            self.assertEqual(first.text_added_count, 1)
            mapped = repository.map_text_novels_for_scan([str(root)])
            record = next(iter(mapped.values()))
            self.assertTrue(record["fingerprint_size_mtime"])
            self.assertEqual(record["fingerprint_quick"], "")

            quick_request = TextScanRequest(roots=[TextScanRoot(path=str(root))], hash_strategy="quick")
            backfill = scan_text_roots(repository, quick_request)
            self.assertEqual(backfill.skipped_unchanged_count, 0)
            self.assertEqual(backfill.text_updated_count, 1)
            mapped = repository.map_text_novels_for_scan([str(root)])
            record = next(iter(mapped.values()))
            self.assertTrue(record["fingerprint_quick"])

            second = scan_text_roots(repository, quick_request)
            self.assertEqual(second.skipped_unchanged_count, 1)
            self.assertEqual(second.text_updated_count, 0)

    def test_request_default_hash_strategy_is_quick(self) -> None:
        request = TextScanRequest(roots=[])
        self.assertEqual(request.hash_strategy, "quick")


if __name__ == "__main__":
    unittest.main()
