from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.models import ParsedMetadata, ScanRequest
from bookhub.library.repository import LibraryRepository
from bookhub.library.scanner import scan_roots


class ScanPdfDegradeTests(unittest.TestCase):
    def test_pdf_backend_unavailable_degrades_without_error_storm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "pdfs"
            root.mkdir(parents=True, exist_ok=True)
            for index in range(10):
                (root / f"book_{index}.pdf").write_bytes(b"%PDF-1.4\nmock\n")

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = ScanRequest(roots=[str(root)], scan_depth=2, hash_strategy="size_mtime")

            with mock.patch(
                "bookhub.library.scanner._probe_pdf_backend",
                return_value=(False, "ImportError: No module named fitz"),
            ):
                result = scan_roots(repository, request)

            self.assertEqual(result.added_count, 10)
            self.assertEqual(result.updated_count, 0)
            self.assertEqual(result.errors, [])
            self.assertEqual(len(result.warnings), 1)
            warning = result.warnings[0]
            self.assertEqual(warning.get("code"), "pdf_backend_unavailable")
            self.assertEqual(int(warning.get("count", 0) or 0), 10)
            self.assertIn("fitz", str(warning.get("reason") or ""))

            records = repository.list_books(include_missing=False)
            self.assertEqual(len(records), 10)
            for record in records:
                expected_title = Path(str(record["file_name"])).stem
                self.assertEqual(record["title"], expected_title)
                self.assertIsNone(record["thumbnail_path"])

    def test_pdf_backend_available_keeps_normal_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "pdfs"
            root.mkdir(parents=True, exist_ok=True)
            pdf_path = root / "normal.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\nmock\n")

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = ScanRequest(roots=[str(root)], scan_depth=2, hash_strategy="size_mtime")

            with (
                mock.patch("bookhub.library.scanner._probe_pdf_backend", return_value=(True, None)),
                mock.patch(
                    "bookhub.library.scanner._extract_metadata_by_extension",
                    return_value=ParsedMetadata(title="Mock Title", author="Mock Author"),
                ) as metadata_mock,
                mock.patch(
                    "bookhub.library.scanner._build_thumbnail_by_extension",
                    return_value="file:///mock-thumb.webp",
                ) as thumb_mock,
            ):
                result = scan_roots(repository, request)

            self.assertEqual(result.added_count, 1)
            self.assertEqual(result.errors, [])
            self.assertEqual(result.warnings, [])
            metadata_mock.assert_called_once()
            thumb_mock.assert_called_once()

            records = repository.list_books(include_missing=False)
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record["title"], "Mock Title")
            self.assertEqual(record["author"], "Mock Author")
            self.assertEqual(record["thumbnail_path"], "file:///mock-thumb.webp")


if __name__ == "__main__":
    unittest.main()
