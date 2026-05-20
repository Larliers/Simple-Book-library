from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PIL import Image

from bookhub.library.models import ComicScanRequest
from bookhub.library.preview_paths import ensure_preview_structure, is_preview_variant_uri
from bookhub.library.repository import LibraryRepository
from bookhub.library.scanner import scan_comic_roots
from bookhub.library.thumbnail_tasks import regenerate_comic_thumbnails


class ComicPreviewPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.db_path = self.tmp_path / "library.db"
        self.scan_report = self.tmp_path / "scan_report.json"
        self.repo = LibraryRepository(db_path=self.db_path, scan_report_path=self.scan_report)
        self.repo.preview_dir = self.tmp_path / "img_preview"
        ensure_preview_structure(self.repo.preview_dir)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_comic_placeholder_copy_and_regenerate_missing(self) -> None:
        comic_root = self.tmp_path / "comic_root"
        chapter = comic_root / "series_a" / "ch_001"
        chapter.mkdir(parents=True, exist_ok=True)
        cover = chapter / "001.png"
        Image.new("RGB", (120, 180), color=(120, 80, 200)).save(cover)
        Image.new("RGB", (120, 180), color=(120, 80, 200)).save(chapter / "002.png")

        result = scan_comic_roots(
            self.repo,
            ComicScanRequest(
                roots=[str(comic_root)],
                max_depth=5,
                placeholder_copy_enabled=True,
            ),
        )
        self.assertEqual(result.comic_detected_folders, 1)
        self.assertEqual(result.comic_placeholder_copied_count, 1)
        self.assertEqual(result.comic_thumbnail_enqueued_count, 1)

        records = self.repo.list_comics(include_missing=False)
        self.assertEqual(len(records), 1)
        placeholder_uri = str(records[0].get("thumbnail_path") or "")
        self.assertTrue(is_preview_variant_uri(placeholder_uri, resource_type="comic", variant="original"))

        regen = regenerate_comic_thumbnails(self.repo, only_missing=True, workers=2)
        self.assertEqual(regen.succeeded, 1)
        records = self.repo.list_comics(include_missing=False)
        compressed_uri = str(records[0].get("thumbnail_path") or "")
        self.assertTrue(is_preview_variant_uri(compressed_uri, resource_type="comic", variant="compressed"))
        self.assertFalse(is_preview_variant_uri(compressed_uri, resource_type="comic", variant="original"))


if __name__ == "__main__":
    unittest.main()
