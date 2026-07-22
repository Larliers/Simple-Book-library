from __future__ import annotations

import shutil
import sqlite3
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

from PIL import Image

from bookhub.library.models import (
    COMIC_SCAN_STRATEGY_FULL,
    COMIC_SCAN_STRATEGY_SNAPSHOT,
    ComicScanRequest,
    ComicScanRoot,
    LibraryScanRoot,
    ParsedMetadata,
    ScanRequest,
    TextScanRequest,
    TextScanRoot,
)
from bookhub.library.repository import LibraryRepository, now_utc_iso
from bookhub.library.scanner import scan_comic_roots, scan_roots, scan_text_roots


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
        mock.patch("bookhub.library.scanner.extract_metadata_by_extension", return_value=metadata),
        mock.patch("bookhub.library.scanner.build_thumbnail_by_extension", side_effect=_fake_thumbnail),
    ):
        yield


def _make_comic_folder(path: Path, *, info_text: str | None = None) -> None:
    path.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 120), color=(90, 40, 40)).save(path / "001.png")
    Image.new("RGB", (80, 120), color=(40, 90, 40)).save(path / "002.png")
    if info_text is not None:
        (path / "info.txt").write_text(info_text, encoding="utf-8")


def _create_legacy_db(db_path: Path) -> str:
    timestamp = now_utc_iso()
    root_path = str((db_path.parent / "legacy_books").resolve())
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE library_roots (
                path TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE comic_roots (
                path TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE text_roots (
                path TEXT PRIMARY KEY,
                rules_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO library_roots(path, created_at, updated_at) VALUES(?, ?, ?)",
            (root_path, timestamp, timestamp),
        )
    return root_path


class ScanStrategyMigrationTests(unittest.TestCase):
    def test_legacy_db_gains_scan_strategy_columns(self) -> None:
        tmp_dir = tempfile.mkdtemp()
        try:
            base = Path(tmp_dir)
            db_path = base / "legacy.db"
            root_path = _create_legacy_db(db_path)

            repository = LibraryRepository(db_path, base / "scan_report.json")
            with repository._connection() as conn:  # noqa: SLF001
                library_columns = {
                    str(row["name"]) for row in conn.execute("PRAGMA table_info(library_roots)").fetchall()
                }
                comic_columns = {
                    str(row["name"]) for row in conn.execute("PRAGMA table_info(comic_roots)").fetchall()
                }
                text_columns = {
                    str(row["name"]) for row in conn.execute("PRAGMA table_info(text_roots)").fetchall()
                }
            self.assertIn("scan_strategy", library_columns)
            self.assertIn("scan_strategy", comic_columns)
            self.assertIn("scan_strategy", text_columns)

            roots = repository.list_roots_with_strategy()
            self.assertEqual(len(roots), 1)
            self.assertEqual(roots[0]["path"], repository.normalize_path(root_path))
            self.assertIsNone(roots[0]["scan_strategy"])
            del repository
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class LibraryPerRootStrategyTests(unittest.TestCase):
    def test_per_root_overrides_skip_independently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root_a = base / "books_a"
            root_b = base / "books_b"
            root_a.mkdir(parents=True, exist_ok=True)
            root_b.mkdir(parents=True, exist_ok=True)
            _write_mock_pdf(root_a / "alpha.pdf")
            _write_mock_pdf(root_b / "beta.pdf")

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            repository.set_per_root_scan_strategy_enabled(True)
            request = ScanRequest(
                roots=[
                    LibraryScanRoot(path=str(root_a), scan_strategy="quick"),
                    LibraryScanRoot(path=str(root_b), scan_strategy="size_mtime"),
                ],
                scan_depth=2,
                hash_strategy="quick",
            )
            metadata = ParsedMetadata(title="Book", author="Author")

            with _patched_library_scan(metadata):
                first = scan_roots(repository, request)
                self.assertEqual(first.added_count, 2)
                second = scan_roots(repository, request)
                self.assertEqual(second.skipped_unchanged_count, 2)
                self.assertEqual(second.updated_count, 0)

    def test_disable_per_root_uses_global_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "books"
            root.mkdir(parents=True, exist_ok=True)
            _write_mock_pdf(root / "only.pdf")

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            repository.set_per_root_scan_strategy_enabled(True)
            request = ScanRequest(
                roots=[LibraryScanRoot(path=str(root), scan_strategy="size_mtime")],
                scan_depth=2,
                hash_strategy="quick",
            )
            metadata = ParsedMetadata(title="Only", author="Author")
            strategies: list[str] = []
            original = __import__("bookhub.library.scanner", fromlist=["compute_fingerprints"]).compute_fingerprints

            def _track_strategy(file_path: Path, *, strategy: str = "quick"):
                strategies.append(strategy)
                return original(file_path, strategy=strategy)

            with _patched_library_scan(metadata):
                with mock.patch("bookhub.library.scanner.compute_fingerprints", side_effect=_track_strategy):
                    scan_roots(repository, request)
                    self.assertEqual(strategies, ["size_mtime"])

                    strategies.clear()
                    repository.set_per_root_scan_strategy_enabled(False)
                    scan_roots(repository, request)
                    self.assertEqual(strategies, ["quick"])


class TextPerRootStrategyTests(unittest.TestCase):
    def test_per_root_text_roots_use_different_hash_strategies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root_a = base / "texts_a"
            root_b = base / "texts_b"
            root_a.mkdir(parents=True, exist_ok=True)
            root_b.mkdir(parents=True, exist_ok=True)
            (root_a / "a.txt").write_text("第一章 A", encoding="utf-8")
            (root_b / "b.txt").write_text("第一章 B", encoding="utf-8")

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            repository.set_per_root_scan_strategy_enabled(True)
            request = TextScanRequest(
                roots=[
                    TextScanRoot(path=str(root_a), scan_strategy="quick"),
                    TextScanRoot(path=str(root_b), scan_strategy="size_mtime"),
                ],
                hash_strategy="quick",
            )

            first = scan_text_roots(repository, request)
            self.assertEqual(first.text_added_count, 2)
            second = scan_text_roots(repository, request)
            self.assertEqual(second.skipped_unchanged_count, 2)
            self.assertEqual(second.text_updated_count, 0)

    def test_disable_per_root_text_uses_global_hash_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "texts"
            root.mkdir(parents=True, exist_ok=True)
            (root / "novel.txt").write_text("第一章", encoding="utf-8")

            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            repository.set_per_root_scan_strategy_enabled(True)
            request = TextScanRequest(
                roots=[TextScanRoot(path=str(root), scan_strategy="size_mtime")],
                hash_strategy="quick",
            )
            strategies: list[str] = []
            original = __import__("bookhub.library.scanner", fromlist=["compute_fingerprints"]).compute_fingerprints

            def _track_strategy(file_path: Path, *, strategy: str = "quick"):
                strategies.append(strategy)
                return original(file_path, strategy=strategy)

            with mock.patch("bookhub.library.scanner.compute_fingerprints", side_effect=_track_strategy):
                scan_text_roots(repository, request)
                self.assertEqual(strategies, ["size_mtime"])

                strategies.clear()
                repository.set_per_root_scan_strategy_enabled(False)
                scan_text_roots(repository, request)
                self.assertEqual(strategies, ["quick"])


class ComicFullVsSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.repo = LibraryRepository(self.base / "library.db", self.base / "scan_report.json")
        self.repo.preview_dir = self.base / "img_preview"
        self.comic_root = self.base / "comic_root"
        self.chapter = self.comic_root / "series" / "ch01"
        _make_comic_folder(self.chapter, info_text="original info")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_snapshot_skips_info_refresh_when_folder_snapshot_unchanged(self) -> None:
        first = scan_comic_roots(
            self.repo,
            ComicScanRequest(
                roots=[ComicScanRoot(path=str(self.comic_root))],
                scan_strategy=COMIC_SCAN_STRATEGY_SNAPSHOT,
                placeholder_copy_enabled=False,
            ),
        )
        self.assertEqual(first.comic_detected_folders, 1)
        records = self.repo.list_comics(include_missing=False)
        self.assertEqual(records[0]["info_text"], "original info")

        (self.chapter / "info.txt").write_text("updated info", encoding="utf-8")
        second = scan_comic_roots(
            self.repo,
            ComicScanRequest(
                roots=[ComicScanRoot(path=str(self.comic_root))],
                scan_strategy=COMIC_SCAN_STRATEGY_SNAPSHOT,
                placeholder_copy_enabled=False,
            ),
        )
        self.assertEqual(second.comic_detected_folders, 1)
        records = self.repo.list_comics(include_missing=False)
        self.assertEqual(records[0]["info_text"], "original info")

    def test_full_strategy_refreshes_info_even_when_snapshot_unchanged(self) -> None:
        scan_comic_roots(
            self.repo,
            ComicScanRequest(
                roots=[ComicScanRoot(path=str(self.comic_root))],
                scan_strategy=COMIC_SCAN_STRATEGY_SNAPSHOT,
                placeholder_copy_enabled=False,
            ),
        )
        (self.chapter / "info.txt").write_text("updated info", encoding="utf-8")

        result = scan_comic_roots(
            self.repo,
            ComicScanRequest(
                roots=[ComicScanRoot(path=str(self.comic_root))],
                scan_strategy=COMIC_SCAN_STRATEGY_FULL,
                placeholder_copy_enabled=False,
            ),
        )
        self.assertEqual(result.comic_detected_folders, 1)
        records = self.repo.list_comics(include_missing=False)
        self.assertEqual(records[0]["info_text"], "updated info")


class SetRootScanStrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.repo = LibraryRepository(self.base / "library.db", self.base / "scan_report.json")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_set_valid_and_clear_strategies(self) -> None:
        library_path = self.repo.add_root(self.base / "library")
        comic_path = self.repo.add_comic_root(self.base / "comic")
        text_path = self.repo.add_text_root(self.base / "text")

        self.repo.set_root_scan_strategy("library", library_path, "quick")
        self.repo.set_root_scan_strategy("comic", comic_path, "full")
        self.repo.set_root_scan_strategy("text", text_path, "size_mtime")

        self.assertEqual(self.repo.list_roots_with_strategy()[0]["scan_strategy"], "quick")
        self.assertEqual(self.repo.list_comic_roots_with_strategy()[0]["scan_strategy"], "full")
        self.assertEqual(self.repo.list_text_roots_with_rules()[0]["scan_strategy"], "size_mtime")

        self.repo.set_root_scan_strategy("library", library_path, "")
        self.assertIsNone(self.repo.list_roots_with_strategy()[0]["scan_strategy"])

    def test_invalid_kind_or_strategy_raises(self) -> None:
        path = self.repo.add_root(self.base / "library")
        with self.assertRaises(ValueError):
            self.repo.set_root_scan_strategy("audio", path, "quick")
        with self.assertRaises(ValueError):
            self.repo.set_root_scan_strategy("library", path, "not-a-strategy")
        with self.assertRaises(ValueError):
            self.repo.set_root_scan_strategy("comic", path, "quick")
        with self.assertRaises(ValueError):
            self.repo.set_root_scan_strategy("library", self.base / "missing-root", "quick")


class RepositoryScanStrategyDefaultsTests(unittest.TestCase):
    def test_new_db_has_scan_strategy_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            self.assertFalse(repository.get_per_root_scan_strategy_enabled())
            self.assertEqual(repository.get_comic_scan_strategy(), COMIC_SCAN_STRATEGY_SNAPSHOT)

    def test_set_comic_scan_strategy_normalizes_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            repository = LibraryRepository(base / "library.db", base / "scan_report.json")
            repository.set_comic_scan_strategy("invalid")
            self.assertEqual(repository.get_comic_scan_strategy(), COMIC_SCAN_STRATEGY_SNAPSHOT)
            repository.set_comic_scan_strategy(COMIC_SCAN_STRATEGY_FULL)
            self.assertEqual(repository.get_comic_scan_strategy(), COMIC_SCAN_STRATEGY_FULL)


if __name__ == "__main__":
    unittest.main()
