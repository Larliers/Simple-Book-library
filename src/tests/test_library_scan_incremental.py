from __future__ import annotations

import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.metadata import compute_fingerprints
from bookhub.library.models import LibraryScanRoot, ParsedMetadata, ScanRequest
from bookhub.library.preview_paths import uri_to_path
from bookhub.library.repository import LibraryRepository
from bookhub.library.scanner import scan_roots


def _write_mock_pdf(path: Path, payload: bytes = b"%PDF-1.4\nmock\n") -> None:
    path.write_bytes(payload)


def _fake_thumbnail(
    file_path: Path,
    extension: str,
    output_path: Path,
    title_fallback: str,
) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"RIFF....WEBP")
    return output_path.resolve(strict=False).as_uri()


@contextmanager
def _patched_library_scan(metadata: ParsedMetadata):
    with (
        mock.patch("bookhub.library.scanner._probe_pdf_backend", return_value=(True, None)),
        mock.patch("bookhub.library.scanner._extract_metadata_by_extension", return_value=metadata),
        mock.patch("bookhub.library.scanner._build_thumbnail_by_extension", side_effect=_fake_thumbnail),
    ):
        yield


class ComputeFingerprintsStrategyTests(unittest.TestCase):
    def test_size_mtime_does_not_open_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "big.bin"
            target.write_bytes(b"x" * (8 * 1024 * 1024))
            with mock.patch.object(Path, "open", side_effect=AssertionError("should not open")):
                bundle = compute_fingerprints(target, strategy="size_mtime")
            self.assertTrue(bundle.size_mtime)
            self.assertEqual(bundle.sha256, "")
            self.assertEqual(bundle.quick, "")

    def test_quick_reads_prefix_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "data.bin"
            target.write_bytes(b"a" * (6 * 1024 * 1024))
            bundle = compute_fingerprints(target, strategy="quick")
            self.assertTrue(bundle.quick)
            self.assertEqual(bundle.sha256, "")
            full = compute_fingerprints(target, strategy="sha256")
            self.assertTrue(full.sha256)
            self.assertEqual(bundle.quick, full.quick)


class LibraryScanIncrementalTests(unittest.TestCase):
    def test_second_scan_skips_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "books"
            root.mkdir(parents=True, exist_ok=True)
            _write_mock_pdf(root / "alpha.pdf")

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = ScanRequest(roots=[LibraryScanRoot(path=str(root))], scan_depth=2, hash_strategy="size_mtime")
            metadata = ParsedMetadata(title="Alpha", author="A")

            with _patched_library_scan(metadata):
                first = scan_roots(repository, request)
                self.assertEqual(first.added_count, 1)
                self.assertEqual(first.skipped_unchanged_count, 0)

                second = scan_roots(repository, request)
                self.assertEqual(second.added_count, 0)
                self.assertEqual(second.updated_count, 0)
                self.assertEqual(second.skipped_unchanged_count, 1)

    def test_touch_forces_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "books"
            root.mkdir(parents=True, exist_ok=True)
            pdf_path = root / "beta.pdf"
            _write_mock_pdf(pdf_path)

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = ScanRequest(roots=[LibraryScanRoot(path=str(root))], scan_depth=2, hash_strategy="size_mtime")
            metadata = ParsedMetadata(title="Beta", author="B")

            with _patched_library_scan(metadata):
                scan_roots(repository, request)
                os.utime(pdf_path, (pdf_path.stat().st_atime, pdf_path.stat().st_mtime + 10))
                second = scan_roots(repository, request)
                self.assertEqual(second.skipped_unchanged_count, 0)
                self.assertEqual(second.updated_count, 1)

    def test_missing_thumbnail_forces_reprocess(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "books"
            root.mkdir(parents=True, exist_ok=True)
            _write_mock_pdf(root / "gamma.pdf")

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            request = ScanRequest(roots=[LibraryScanRoot(path=str(root))], scan_depth=2, hash_strategy="size_mtime")
            metadata = ParsedMetadata(title="Gamma", author="C")

            with _patched_library_scan(metadata):
                first = scan_roots(repository, request)
                self.assertEqual(first.added_count, 1)
                books = repository.map_library_books_for_scan([str(root)])
                self.assertEqual(len(books), 1)
                thumb_uri = str(next(iter(books.values())).get("thumbnail_path") or "")
                thumb_file = uri_to_path(thumb_uri)
                assert thumb_file is not None
                thumb_file.unlink()

                second = scan_roots(repository, request)
                self.assertEqual(second.skipped_unchanged_count, 0)
                self.assertEqual(second.updated_count, 1)

    def test_upsert_preserves_uncomputed_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            payload = {
                "path": str(base / "keep.pdf"),
                "file_name": "keep.pdf",
                "extension": ".pdf",
                "title": "Keep",
                "author": None,
                "publisher": None,
                "language": None,
                "tags_json": "[]",
                "status": "UNREAD",
                "resource_type": "pdf",
                "thumbnail_path": None,
                "fingerprint_sha256": "abc123",
                "fingerprint_size_mtime": "1:2",
                "fingerprint_quick": "quick1",
            }
            repository.upsert_book(payload)
            repository.upsert_book(
                {
                    **payload,
                    "title": "Keep2",
                    "fingerprint_sha256": "",
                    "fingerprint_size_mtime": "3:4",
                    "fingerprint_quick": "",
                }
            )
            mapped = repository.map_library_books_for_scan([str(base)])
            record = mapped[repository.normalize_path(base / "keep.pdf")]
            self.assertEqual(record["fingerprint_sha256"], "abc123")
            self.assertEqual(record["fingerprint_size_mtime"], "3:4")
            self.assertEqual(record["fingerprint_quick"], "quick1")

    def test_quick_backfills_then_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "books"
            root.mkdir(parents=True, exist_ok=True)
            pdf_path = root / "delta.pdf"
            _write_mock_pdf(pdf_path)

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            metadata = ParsedMetadata(title="Delta", author="D")
            with _patched_library_scan(metadata):
                first = scan_roots(
                    repository,
                    ScanRequest(roots=[LibraryScanRoot(path=str(root))], scan_depth=2, hash_strategy="size_mtime"),
                )
                self.assertEqual(first.added_count, 1)
                mapped = repository.map_library_books_for_scan([str(root)])
                record = next(iter(mapped.values()))
                self.assertTrue(record["fingerprint_size_mtime"])
                self.assertEqual(record["fingerprint_quick"], "")

                quick_request = ScanRequest(roots=[LibraryScanRoot(path=str(root))], scan_depth=2, hash_strategy="quick")
                backfill = scan_roots(repository, quick_request)
                self.assertEqual(backfill.skipped_unchanged_count, 0)
                self.assertEqual(backfill.updated_count, 1)
                mapped = repository.map_library_books_for_scan([str(root)])
                record = next(iter(mapped.values()))
                self.assertTrue(record["fingerprint_quick"])

                second = scan_roots(repository, quick_request)
                self.assertEqual(second.skipped_unchanged_count, 1)
                self.assertEqual(second.updated_count, 0)


class HashStrategyDefaultTests(unittest.TestCase):
    def test_new_db_defaults_to_quick(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            self.assertEqual(repository.get_hash_strategy(), "quick")
            self.assertEqual(repository.get_setting("hash_strategy"), "quick")

    def test_existing_size_mtime_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            repository.set_hash_strategy("size_mtime")
            reopened = LibraryRepository(base / "library.db", base / "scan_report.json")
            self.assertEqual(reopened.get_hash_strategy(), "size_mtime")

    def test_invalid_strategy_falls_back_to_quick(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            repository.set_setting("hash_strategy", "not-a-strategy")
            self.assertEqual(repository.get_hash_strategy(), "quick")
            repository.set_hash_strategy("also-invalid")
            self.assertEqual(repository.get_hash_strategy(), "quick")


if __name__ == "__main__":
    unittest.main()
