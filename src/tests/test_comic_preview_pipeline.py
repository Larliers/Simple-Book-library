from __future__ import annotations

import os
import tempfile
import unittest
import zipfile
from pathlib import Path
import sys
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PIL import Image

from bookhub.library.models import ComicScanRequest, ComicScanRoot
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
                roots=[ComicScanRoot(path=str(comic_root))],
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
                roots=[ComicScanRoot(path=str(comic_root))],
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
        os.utime(alpha, (1_700_000_000, 1_700_000_000))
        os.utime(beta, (1_800_000_000, 1_800_000_000))

        scan_comic_roots(
            self.repo,
            ComicScanRequest(
                roots=[ComicScanRoot(path=str(comic_root))],
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
        self.assertGreater(int(by_mtime_desc[0].get("folder_modified_at") or 0), int(by_mtime_desc[1].get("folder_modified_at") or 0))

    def test_gif_bmp_tiff_leaf_folder_and_gif_first_frame_cover(self) -> None:
        comic_root = self.tmp_path / "comic_root"
        chapter = comic_root / "gif_vol"
        chapter.mkdir(parents=True, exist_ok=True)
        frame0 = Image.new("RGB", (80, 100), color=(255, 0, 0))
        frame1 = Image.new("RGB", (80, 100), color=(0, 255, 0))
        cover = chapter / "000.gif"
        frame0.save(
            cover,
            save_all=True,
            append_images=[frame1],
            duration=100,
            loop=0,
            format="GIF",
        )
        Image.new("RGB", (80, 100), color=(0, 0, 255)).save(chapter / "001.bmp")
        Image.new("RGB", (80, 100), color=(10, 20, 30)).save(chapter / "002.tiff")

        result = scan_comic_roots(
            self.repo,
            ComicScanRequest(
                roots=[ComicScanRoot(path=str(comic_root))],
                max_depth=5,
                placeholder_copy_enabled=True,
            ),
        )
        self.assertEqual(result.comic_detected_folders, 1)
        self.assertEqual(result.comic_added_count, 1)
        self.assertEqual(result.comic_placeholder_copied_count, 1)

        records = self.repo.list_comics(include_missing=False)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "gif_vol")
        self.assertEqual(int(records[0]["image_count"]), 3)
        placeholder_uri = str(records[0].get("thumbnail_path") or "")
        from bookhub.library.preview_paths import uri_to_path

        thumb = uri_to_path(placeholder_uri)
        self.assertIsNotNone(thumb)
        assert thumb is not None
        self.assertTrue(thumb.exists())
        self.assertEqual(thumb.suffix.lower(), ".png")
        with Image.open(thumb) as img:
            self.assertEqual(img.mode, "RGB")
            # First GIF frame is red.
            self.assertEqual(img.getpixel((40, 50))[:3], (255, 0, 0))

    def test_unchanged_cbz_reuses_cached_cover_without_opening_archive(self) -> None:
        comic_root = self.tmp_path / "comic_root"
        comic_root.mkdir()
        page = self.tmp_path / "001.png"
        Image.new("RGB", (80, 120), color=(40, 70, 100)).save(page)
        archive = comic_root / "cached.cbz"
        with zipfile.ZipFile(archive, "w") as zip_file:
            zip_file.write(page, "001.png")
        request = ComicScanRequest(roots=[ComicScanRoot(path=str(comic_root))], placeholder_copy_enabled=True)
        first = scan_comic_roots(self.repo, request)
        self.assertEqual(first.comic_added_count, 1)

        with patch("bookhub.library.scanner.read_cbz_cover_bytes", side_effect=AssertionError("archive should not reopen")):
            second = scan_comic_roots(self.repo, request)

        self.assertEqual(second.comic_errors, [])
        self.assertEqual(second.comic_thumbnail_enqueued_count, 0)

    def test_regeneration_never_deletes_worker_path_outside_preview(self) -> None:
        comic_root = self.tmp_path / "comic_root"
        chapter = comic_root / "chapter"
        chapter.mkdir(parents=True)
        Image.new("RGB", (80, 120), color=(20, 60, 90)).save(chapter / "001.png")
        scan_comic_roots(
            self.repo,
            ComicScanRequest(roots=[ComicScanRoot(path=str(comic_root))], placeholder_copy_enabled=False),
        )
        outside = self.tmp_path / "outside.png"
        outside.write_bytes(b"must remain")
        safe_thumbnail = (self.repo.preview_dir / "comic" / "compressed" / "safe.webp").as_uri()
        payload = {
            "status": "ok",
            "thumbnail_uri": safe_thumbnail,
            "cover_fingerprint": "test",
            "original_path": str(outside),
        }

        with patch("bookhub.library.thumbnail_tasks._render_comic_thumbnail", return_value=payload):
            result = regenerate_comic_thumbnails(self.repo, workers=1)

        self.assertEqual(result.succeeded, 1)
        self.assertTrue(outside.exists())


if __name__ == "__main__":
    unittest.main()
