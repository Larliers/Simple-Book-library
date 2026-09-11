from __future__ import annotations

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
from bookhub.library.thumbnail_tasks import (
    cleanup_text_novel_thumbnails,
    regenerate_text_novel_thumbnails,
)


class TextNovelThumbnailTaskTests(unittest.TestCase):
    def _seed_sidecar(self, base: Path) -> tuple[LibraryRepository, Path, Path]:
        root = base / "texts"
        preview = base / "preview"
        root.mkdir(parents=True, exist_ok=True)
        target = root / "novel.txt"
        target.write_text("第一章\n正文", encoding="utf-8")
        sidecar = root / "novel.png"
        Image.new("RGB", (720, 1080), "green").save(sidecar)
        repository = LibraryRepository(base / "library.db", base / "scan-report.json", preview_dir=preview)
        scan_text_roots(
            repository,
            TextScanRequest(roots=[TextScanRoot(path=str(root))], hash_strategy="size_mtime"),
        )
        return repository, target, sidecar

    def test_cleanup_then_regenerate_text_novel_sidecar_thumbnail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            repository, target, _sidecar = self._seed_sidecar(base)
            before = repository.map_text_novels_for_scan([str(target.parent)])[str(target.resolve())]
            cached_path = uri_to_path(str(before["thumbnail_path"]))
            self.assertIsNotNone(cached_path)
            self.assertTrue(cached_path.is_file())

            cleanup = cleanup_text_novel_thumbnails(repository)

            self.assertEqual(cleanup.task_scope, "text_novel")
            self.assertEqual(cleanup.succeeded, 1)
            self.assertFalse(cached_path.exists())
            cleared = repository.map_text_novels_for_scan([str(target.parent)])[str(target.resolve())]
            self.assertFalse(cleared["thumbnail_path"])
            self.assertFalse(cleared["cover_source"])
            self.assertFalse(cleared["cover_fingerprint"])

            rebuilt = regenerate_text_novel_thumbnails(repository)

            self.assertEqual(rebuilt.task_scope, "text_novel")
            self.assertEqual(rebuilt.succeeded, 1)
            refreshed = repository.map_text_novels_for_scan([str(target.parent)])[str(target.resolve())]
            self.assertEqual(refreshed["cover_source"], "sidecar")
            rebuilt_path = uri_to_path(str(refreshed["thumbnail_path"]))
            self.assertIsNotNone(rebuilt_path)
            self.assertTrue(rebuilt_path.is_file())

    def test_regenerate_preserves_valid_manual_cover(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            repository, _target, sidecar = self._seed_sidecar(base)
            record = next(
                item for item in repository.list_books(include_missing=False)
                if item["resource_type"] == "text_novel"
            )
            manual_path = repository.preview_dir / "text_novel" / "compressed" / "manual.webp"
            manual_path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (360, 540), "purple").save(manual_path)
            repository.update_book_thumbnail_state(
                repository.get_book_int_id(str(record["resource_id"])),
                thumbnail_path=manual_path.resolve().as_uri(),
                cover_source="manual",
            )
            Image.new("RGB", (720, 1080), "orange").save(sidecar)

            rebuilt = regenerate_text_novel_thumbnails(repository)

            self.assertEqual(rebuilt.skipped, 1)
            refreshed = next(
                item for item in repository.list_books(include_missing=False)
                if item["resource_type"] == "text_novel"
            )
            self.assertEqual(refreshed["thumbnail_path"], manual_path.resolve().as_uri())
            self.assertEqual(refreshed["cover_source"], "manual")


if __name__ == "__main__":
    unittest.main()
