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

from PIL import Image

from bookhub.library.models import ComicScanRequest, ComicScanRoot
from bookhub.library.preview_paths import ensure_preview_structure
from bookhub.library.repository import LibraryRepository
from bookhub.library.scanner import scan_comic_roots


def _make_comic_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 120), color=(90, 40, 40)).save(path / "001.png")
    Image.new("RGB", (80, 120), color=(40, 90, 40)).save(path / "002.png")


class ComicTitleConflictTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.repo = LibraryRepository(self.base / "library.db", self.base / "scan_report.json")
        self.repo.preview_dir = self.base / "img_preview"
        ensure_preview_structure(self.repo.preview_dir)
        self.comic_root = self.base / "comic_root"
        self.comic_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_skip_incoming_keeps_first_only(self) -> None:
        first = self.comic_root / "series_a" / "Vol01"
        second = self.comic_root / "series_b" / "Vol01"
        _make_comic_folder(first)
        scan_comic_roots(
            self.repo,
            ComicScanRequest(roots=[ComicScanRoot(path=str(self.comic_root))], title_conflict_policy="skip_incoming"),
        )
        _make_comic_folder(second)
        result = scan_comic_roots(
            self.repo,
            ComicScanRequest(roots=[ComicScanRoot(path=str(self.comic_root))], title_conflict_policy="skip_incoming"),
        )
        comics = self.repo.list_comics(include_missing=False)
        self.assertEqual(len(comics), 1)
        self.assertTrue(str(comics[0]["path"]).endswith("series_a" + os.sep + "Vol01") or "series_a" in str(comics[0]["path"]))
        self.assertEqual(len(result.name_conflicts), 1)
        self.assertTrue(any("skipped" in err.lower() or "conflict" in err.lower() for err in result.comic_errors))

    def test_keep_both_allows_duplicate_titles(self) -> None:
        first = self.comic_root / "series_a" / "Vol01"
        second = self.comic_root / "series_b" / "Vol01"
        _make_comic_folder(first)
        scan_comic_roots(
            self.repo,
            ComicScanRequest(roots=[ComicScanRoot(path=str(self.comic_root))], title_conflict_policy="keep_both"),
        )
        _make_comic_folder(second)
        result = scan_comic_roots(
            self.repo,
            ComicScanRequest(roots=[ComicScanRoot(path=str(self.comic_root))], title_conflict_policy="keep_both"),
        )
        comics = self.repo.list_comics(include_missing=False)
        self.assertEqual(len(comics), 2)
        self.assertEqual(len(result.name_conflicts), 1)

    def test_prefer_newer_replaces_older(self) -> None:
        older = self.comic_root / "series_a" / "Vol01"
        newer = self.comic_root / "series_b" / "Vol01"
        _make_comic_folder(older)
        os.utime(older, (1_000_000, 1_000_000))
        for child in older.iterdir():
            os.utime(child, (1_000_000, 1_000_000))
        scan_comic_roots(
            self.repo,
            ComicScanRequest(roots=[ComicScanRoot(path=str(self.comic_root))], title_conflict_policy="prefer_newer"),
        )
        _make_comic_folder(newer)
        newer_mtime = 2_000_000
        os.utime(newer, (newer_mtime, newer_mtime))
        for child in newer.iterdir():
            os.utime(child, (newer_mtime, newer_mtime))
        result = scan_comic_roots(
            self.repo,
            ComicScanRequest(roots=[ComicScanRoot(path=str(self.comic_root))], title_conflict_policy="prefer_newer"),
        )
        comics = self.repo.list_comics(include_missing=False)
        self.assertEqual(len(comics), 1)
        self.assertIn("series_b", str(comics[0]["path"]))
        self.assertEqual(len(result.name_conflicts), 1)

    def test_cross_root_same_title_allowed(self) -> None:
        root_a = self.base / "root_a"
        root_b = self.base / "root_b"
        _make_comic_folder(root_a / "Vol01")
        _make_comic_folder(root_b / "Vol01")
        result = scan_comic_roots(
            self.repo,
            ComicScanRequest(
                roots=[ComicScanRoot(path=str(root_a)), ComicScanRoot(path=str(root_b))],
                title_conflict_policy="skip_incoming",
            ),
        )
        comics = self.repo.list_comics(include_missing=False)
        self.assertEqual(len(comics), 2)
        self.assertEqual(len(result.name_conflicts), 0)


if __name__ == "__main__":
    unittest.main()
