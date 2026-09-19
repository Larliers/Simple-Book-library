from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.formats.zip_safety import ZipBombError, open_zip_safely  # noqa: E402
from bookhub.library.formats.cbz import _safe_archive_member_path, prepare_cbz_for_external_viewer  # noqa: E402
from bookhub.library.metadata import (  # noqa: E402
    build_thumbnail_by_extension,
    extract_metadata_by_extension,
    extension_lower,
)
from bookhub.library.models import (  # noqa: E402
    HASH_STRATEGY_QUICK,
    ComicScanRequest,
    ComicScanRoot,
    LibraryScanRoot,
    ScanRequest,
    is_supported_library_file,
)
from bookhub.library.preview_paths import uri_to_path  # noqa: E402
from bookhub.library.repository import LibraryRepository  # noqa: E402
from bookhub.library.scanner import scan_comic_roots, scan_roots  # noqa: E402


def _write_png(path: Path, color: tuple[int, int, int] = (200, 80, 80)) -> None:
    Image.new("RGB", (80, 120), color=color).save(path, format="PNG")


class ExtensionHelpersTests(unittest.TestCase):
    def test_fb2_zip_extension(self) -> None:
        path = Path("novel.fb2.zip")
        self.assertEqual(extension_lower(path), ".fb2.zip")
        self.assertTrue(is_supported_library_file(path))


class LibraryFormatExtractTests(unittest.TestCase):
    def test_html_metadata_and_thumbnail_from_local_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cover = base / "cover.png"
            _write_png(cover)
            html = base / "book.html"
            html.write_text(
                "<html><head><title>HTML Title</title></head>"
                '<body><img src="cover.png"/></body></html>',
                encoding="utf-8",
            )
            meta = extract_metadata_by_extension(html, ".html")
            self.assertEqual(meta.title, "HTML Title")
            out = base / "thumb.webp"
            uri = build_thumbnail_by_extension(html, ".html", out, "fallback")
            self.assertTrue(uri.startswith("file://"))
            generated = uri_to_path(uri)
            self.assertIsNotNone(generated)
            assert generated is not None
            self.assertTrue(generated.exists())
            self.assertTrue(generated.is_file())

    def test_markdown_heading_and_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            md = base / "note.md"
            md.write_text("# Markdown Title\n\nHello\n", encoding="utf-8")
            meta = extract_metadata_by_extension(md, ".md")
            self.assertEqual(meta.title, "Markdown Title")
            uri = build_thumbnail_by_extension(md, ".md", base / "out.webp", "fallback")
            self.assertTrue(uri.startswith("file://"))

    def test_fb2_title_and_cover_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            png = base / "c.png"
            _write_png(png)
            import base64

            encoded = base64.b64encode(png.read_bytes()).decode("ascii")
            fb2 = base / "story.fb2"
            fb2.write_text(
                f"""<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0"
 xmlns:l="http://www.w3.org/1999/xlink">
  <description>
    <title-info>
      <book-title>FB2 Book</book-title>
      <author><first-name>Ann</first-name><last-name>Lee</last-name></author>
      <coverpage><image l:href="#cover.jpg"/></coverpage>
    </title-info>
  </description>
  <body><section><p>Hi</p></section></body>
  <binary id="cover.jpg" content-type="image/png">{encoded}</binary>
</FictionBook>
""",
                encoding="utf-8",
            )
            meta = extract_metadata_by_extension(fb2, ".fb2")
            self.assertEqual(meta.title, "FB2 Book")
            self.assertIn("Ann", meta.author or "")
            uri = build_thumbnail_by_extension(fb2, ".fb2", base / "fb2.webp", "fallback")
            self.assertTrue(uri.startswith("file://"))

    def test_docx_metadata_and_media_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            docx_path = base / "doc.docx"
            from docx import Document

            document = Document()
            document.core_properties.title = "Docx Title"
            document.core_properties.author = "Doc Author"
            document.add_paragraph("Hello")
            document.save(str(docx_path))

            # Inject a media image into the docx zip for cover extraction.
            png = base / "m.png"
            _write_png(png)
            with zipfile.ZipFile(docx_path, "a") as zf:
                zf.write(png, "word/media/image1.png")

            meta = extract_metadata_by_extension(docx_path, ".docx")
            self.assertEqual(meta.title, "Docx Title")
            uri = build_thumbnail_by_extension(docx_path, ".docx", base / "docx.webp", "fallback")
            self.assertTrue(uri.startswith("file://"))

    def test_zip_bomb_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bomb = base / "bomb.zip"
            with zipfile.ZipFile(bomb, "w", compression=zipfile.ZIP_STORED) as zf:
                for index in range(5_001):
                    zf.writestr(f"pad/{index:05d}.txt", b"x")
            with self.assertRaises(ZipBombError):
                open_zip_safely(bomb)


class LibraryScanIntegrationTests(unittest.TestCase):
    def test_scan_roots_imports_html_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "lib"
            root.mkdir()
            (root / "a.html").write_text("<html><head><title>A</title></head><body>x</body></html>", encoding="utf-8")
            (root / "b.md").write_text("# B\n", encoding="utf-8")
            preview = base / "preview"
            repo = LibraryRepository(base / "library.db", base / "scan_report.json", preview_dir=preview)
            repo.add_root(root)
            result = scan_roots(
                repo,
                ScanRequest(roots=[LibraryScanRoot(path=str(root))], hash_strategy=HASH_STRATEGY_QUICK, scan_depth=2),
            )
            self.assertGreaterEqual(result.added_count, 2)
            books = repo.list_books(include_missing=False)
            titles = {str(item.get("title") or "") for item in books}
            self.assertIn("A", titles)
            self.assertIn("B", titles)


class ComicCbzTests(unittest.TestCase):
    def test_scan_cbz_and_missing_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "comics"
            root.mkdir()
            page = base / "001.png"
            _write_png(page)
            cbz = root / "MyComic.cbz"
            with zipfile.ZipFile(cbz, "w") as zf:
                zf.write(page, "001.png")
            preview = base / "preview"
            repo = LibraryRepository(base / "library.db", base / "scan_report.json", preview_dir=preview)
            repo.add_comic_root(root)
            result = scan_comic_roots(
                repo,
                ComicScanRequest(roots=[ComicScanRoot(path=str(root))], max_depth=3, placeholder_copy_enabled=True),
            )
            self.assertEqual(result.comic_added_count, 1)
            comics = repo.list_comics(include_missing=False)
            self.assertEqual(len(comics), 1)
            self.assertEqual(comics[0]["title"], "MyComic")
            self.assertTrue(str(comics[0]["path"]).lower().endswith(".cbz"))

            cbz.unlink()
            removed = scan_comic_roots(
                repo,
                ComicScanRequest(roots=[ComicScanRoot(path=str(root))], max_depth=3),
            )
            self.assertGreaterEqual(removed.removed_missing_comic_count, 1)
            self.assertEqual(repo.list_comics(include_missing=False), [])

    def test_prepare_cbz_for_external_viewer_extracts_pages_for_viewer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            page_one = base / "001.png"
            page_two = base / "002.png"
            _write_png(page_one, color=(200, 80, 80))
            _write_png(page_two, color=(80, 200, 80))
            cbz = base / "MyComic.cbz"
            with zipfile.ZipFile(cbz, "w") as zf:
                zf.write(page_one, "001.png")
                zf.write(page_two, "002.png")
            preview = base / "preview"
            first_page = prepare_cbz_for_external_viewer(cbz, preview)
            self.assertIsNotNone(first_page)
            assert first_page is not None
            self.assertTrue(first_page.exists())
            self.assertEqual(first_page.name, "001.png")
            normalized = str(first_page).replace("\\", "/").lower()
            self.assertIn("/comic/read/", normalized)
            cache_dir = first_page.parent
            self.assertTrue((cache_dir / "002.png").is_file())
            self.assertTrue((cache_dir / ".cbz_source").is_file())

    def test_prepare_cbz_for_external_viewer_removes_previous_revision_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cbz = base / "Changing.cbz"
            preview = base / "preview"
            with zipfile.ZipFile(cbz, "w") as zf:
                zf.writestr("001.png", b"first-version")

            first_page = prepare_cbz_for_external_viewer(cbz, preview)
            self.assertIsNotNone(first_page)
            assert first_page is not None
            first_cache_dir = first_page.parent
            first_mtime_ns = cbz.stat().st_mtime_ns
            previous_cache_dir = first_cache_dir
            current_page = first_page
            for revision in (2, 3):
                with zipfile.ZipFile(cbz, "w") as zf:
                    zf.writestr("001.png", f"version-{revision}".encode("utf-8"))
                revision_mtime_ns = first_mtime_ns + (revision * 1_000_000_000)
                os.utime(cbz, ns=(revision_mtime_ns, revision_mtime_ns))

                current_page = prepare_cbz_for_external_viewer(cbz, preview)

                self.assertIsNotNone(current_page)
                assert current_page is not None
                self.assertNotEqual(current_page.parent, previous_cache_dir)
                self.assertFalse(previous_cache_dir.exists())
                previous_cache_dir = current_page.parent
            self.assertEqual(
                [path for path in (preview / "comic" / "read").iterdir() if path.is_dir()],
                [current_page.parent],
            )

    def test_prepare_cbz_for_external_viewer_removes_expired_but_keeps_recent_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            preview = base / "preview"

            def prepare(name: str) -> Path:
                cbz = base / f"{name}.cbz"
                with zipfile.ZipFile(cbz, "w") as zf:
                    zf.writestr("001.png", name.encode("utf-8"))
                page = prepare_cbz_for_external_viewer(cbz, preview)
                self.assertIsNotNone(page)
                assert page is not None
                return page.parent

            stale_cache = prepare("stale")
            recent_cache = prepare("recent")
            current_cache = prepare("current")
            expired_at = time.time() - (31 * 24 * 60 * 60)
            os.utime(stale_cache / ".cbz_source", (expired_at, expired_at))

            current_page = prepare_cbz_for_external_viewer(base / "current.cbz", preview)

            self.assertIsNotNone(current_page)
            self.assertFalse(stale_cache.exists())
            self.assertTrue(recent_cache.exists())
            self.assertTrue(current_cache.exists())

    def test_prepare_cbz_for_external_viewer_upgrades_legacy_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cbz = base / "Legacy.cbz"
            with zipfile.ZipFile(cbz, "w") as zf:
                zf.writestr("001.png", b"legacy")
            preview = base / "preview"
            first_page = prepare_cbz_for_external_viewer(cbz, preview)
            self.assertIsNotNone(first_page)
            assert first_page is not None
            marker = first_page.parent / ".cbz_source"
            marker.write_text(str(cbz.stat().st_mtime_ns), encoding="utf-8")

            reopened_page = prepare_cbz_for_external_viewer(cbz, preview)

            self.assertEqual(reopened_page, first_page)
            payload = json.loads(marker.read_text(encoding="utf-8"))
            self.assertEqual(payload["version"], 2)
            self.assertEqual(payload["mtime_ns"], cbz.stat().st_mtime_ns)
            self.assertNotIn(str(cbz.resolve()), marker.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["source_hash"]), 40)

    def test_prepare_cbz_for_external_viewer_recovers_from_damaged_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cbz = base / "DamagedMarker.cbz"
            with zipfile.ZipFile(cbz, "w") as zf:
                zf.writestr("001.png", b"page")
            preview = base / "preview"
            first_page = prepare_cbz_for_external_viewer(cbz, preview)
            self.assertIsNotNone(first_page)
            assert first_page is not None
            marker = first_page.parent / ".cbz_source"
            marker.write_text("not-json-or-mtime", encoding="utf-8")

            reopened_page = prepare_cbz_for_external_viewer(cbz, preview)

            self.assertEqual(reopened_page, first_page)
            self.assertEqual(json.loads(marker.read_text(encoding="utf-8"))["version"], 2)

    def test_prepare_cbz_for_external_viewer_ignores_cleanup_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            preview = base / "preview"
            old_cbz = base / "old.cbz"
            current_cbz = base / "current.cbz"
            for cbz in (old_cbz, current_cbz):
                with zipfile.ZipFile(cbz, "w") as zf:
                    zf.writestr("001.png", cbz.stem.encode("utf-8"))
            old_page = prepare_cbz_for_external_viewer(old_cbz, preview)
            current_page = prepare_cbz_for_external_viewer(current_cbz, preview)
            self.assertIsNotNone(old_page)
            self.assertIsNotNone(current_page)
            assert old_page is not None
            expired_at = time.time() - (31 * 24 * 60 * 60)
            os.utime(old_page.parent / ".cbz_source", (expired_at, expired_at))

            with mock.patch("bookhub.library.formats.cbz.shutil.rmtree", side_effect=OSError("denied")):
                reopened_page = prepare_cbz_for_external_viewer(current_cbz, preview)

            self.assertEqual(reopened_page, current_page)
            self.assertTrue(old_page.parent.exists())

    def test_prepare_cbz_for_external_viewer_ignores_marker_refresh_permission_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cbz = base / "PermissionFailure.cbz"
            with zipfile.ZipFile(cbz, "w") as zf:
                zf.writestr("001.png", b"page")
            preview = base / "preview"
            first_page = prepare_cbz_for_external_viewer(cbz, preview)
            self.assertIsNotNone(first_page)

            with mock.patch.object(Path, "write_text", side_effect=PermissionError("denied")):
                reopened_page = prepare_cbz_for_external_viewer(cbz, preview)

            self.assertEqual(reopened_page, first_page)

    def test_safe_archive_member_path_rejects_escape_vectors(self) -> None:
        for evil in (
            "/evil.png",
            "\\evil.png",
            "C:/evil.png",
            "C:\\evil.png",
            "../evil.png",
            "pages/../../evil.png",
        ):
            with self.subTest(member=evil):
                self.assertIsNone(_safe_archive_member_path(evil))
        normal = _safe_archive_member_path("pages/001.png")
        self.assertIsNotNone(normal)
        assert normal is not None
        self.assertEqual(normal.parts, ("pages", "001.png"))
        # "a//b.png" is normalized by Path and stays inside the cache dir; it is not an escape vector.
        self.assertIsNotNone(_safe_archive_member_path("a//b.png"))

    def test_malicious_cbz_never_writes_outside_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cbz = base / "Evil.cbz"
            with zipfile.ZipFile(cbz, "w") as zf:
                zf.writestr("/evil.png", b"fake-png-bytes")
            preview = base / "preview"
            first_page = prepare_cbz_for_external_viewer(cbz, preview)
            self.assertIsNone(first_page)
            self.assertFalse((base / "evil.png").exists(), "escaped file must not be written")
            escape_target = Path(Path(tmp).anchor) / "evil.png"
            self.assertFalse(escape_target.exists())


if __name__ == "__main__":
    unittest.main()
