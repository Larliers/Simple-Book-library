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
from bookhub.library.repository import LibraryRepository
from bookhub.library.scanner import scan_text_roots


class TextScanIncrementalTests(unittest.TestCase):
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
