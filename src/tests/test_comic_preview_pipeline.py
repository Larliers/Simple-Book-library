from __future__ import annotations

import os
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

    def test_large_cover_is_downscaled_for_placeholder(self) -> None:
        comic_root = self.tmp_path / "comic_root"
        chapter = comic_root / "series_b" / "ch_001"
        chapter.mkdir(parents=True, exist_ok=True)
        cover = chapter / "001.png"
        Image.new("RGB", (120, 180), color=(40, 60, 80)).save(cover)

        result = scan_comic_roots(
            self.repo,
            ComicScanRequest(
                roots=[str(comic_root)],
                max_depth=5,
                placeholder_copy_enabled=True,
                max_image_decode_bytes=1,
            ),
        )
        self.assertEqual(result.comic_large_image_downscaled_count, 1)
        self.assertTrue(any(str(item.get("code") or "") == "comic_large_image_downscaled" for item in result.warnings))

    def test_comic_sort_order_by_folder_mtime_and_name(self) -> None:
        comic_root = self.tmp_path / "comic_root"
        alpha = comic_root / "A_alpha"
        beta = comic_root / "B_beta"
        alpha.mkdir(parents=True, exist_ok=True)
        beta.mkdir(parents=True, exist_ok=True)
        alpha_cover = alpha / "001.png"
        beta_cover = beta / "001.png"
        Image.new("RGB", (100, 120), color=(100, 100, 100)).save(alpha_cover)
        Image.new("RGB", (100, 120), color=(120, 120, 120)).save(beta_cover)
        os.utime(alpha_cover, (1_700_000_000, 1_700_000_000))
        os.utime(beta_cover, (1_800_000_000, 1_800_000_000))

        scan_comic_roots(
            self.repo,
            ComicScanRequest(
                roots=[str(comic_root)],
                max_depth=5,
                placeholder_copy_enabled=False,
            ),
        )
        by_mtime_asc = self.repo.list_comics(include_missing=False, order_by="folder_mtime_asc")
        by_mtime_desc = self.repo.list_comics(include_missing=False, order_by="folder_mtime_desc")
        by_name_asc = self.repo.list_comics(include_missing=False, order_by="folder_name_asc")
        by_name_desc = self.repo.list_comics(include_missing=False, order_by="folder_name_desc")

        self.assertEqual([item["title"] for item in by_mtime_asc], ["A_alpha", "B_beta"])
        self.assertEqual([item["title"] for item in by_mtime_desc], ["B_beta", "A_alpha"])
        self.assertEqual([item["title"] for item in by_name_asc], ["A_alpha", "B_beta"])
        self.assertEqual([item["title"] for item in by_name_desc], ["B_beta", "A_alpha"])


if __name__ == "__main__":
    unittest.main()
