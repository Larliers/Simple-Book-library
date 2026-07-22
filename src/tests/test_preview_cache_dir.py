from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.data_paths import DEFAULT_PREVIEW_DIR, resolve_preview_dir  # noqa: E402
from bookhub.library.preview_cache_migrate import (  # noqa: E402
    apply_preview_cache_change,
    copy_preview_tree,
    rewire_thumbnail_uri,
    safe_unlink_under_preview,
)
from bookhub.library.preview_paths import ensure_preview_structure  # noqa: E402
from bookhub.library.repository import LibraryRepository  # noqa: E402


class ResolvePreviewDirTests(unittest.TestCase):
    def test_empty_uses_default(self) -> None:
        path, used_default = resolve_preview_dir(None, create=False)
        self.assertTrue(used_default)
        self.assertEqual(path, DEFAULT_PREVIEW_DIR.resolve(strict=False))

    def test_relative_falls_back_to_default(self) -> None:
        path, used_default = resolve_preview_dir("relative/cache", create=False)
        self.assertTrue(used_default)

    def test_absolute_custom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "custom_preview"
            path, used_default = resolve_preview_dir(str(target), create=True)
            self.assertFalse(used_default)
            self.assertEqual(path, target.resolve(strict=False))
            self.assertTrue(path.is_dir())


class RepositoryPreviewDirTests(unittest.TestCase):
    def test_default_preview_dir_and_setting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = LibraryRepository(base / "library.db", base / "scan_report.json")
            self.assertEqual(repo.get_preview_cache_dir_setting(), "")
            self.assertEqual(repo.preview_dir, DEFAULT_PREVIEW_DIR.resolve(strict=False))

    def test_setting_overrides_preview_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            custom = base / "thumbs"
            custom.mkdir()
            repo = LibraryRepository(base / "library.db", base / "scan_report.json")
            repo.set_preview_cache_dir(str(custom))
            repo2 = LibraryRepository(base / "library.db", base / "scan_report.json")
            self.assertEqual(repo2.preview_dir, custom.resolve(strict=False))

    def test_preview_dir_constructor_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            custom = base / "forced"
            custom.mkdir()
            repo = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=custom,
            )
            self.assertEqual(repo.preview_dir, custom.resolve(strict=False))


class MigrateAndRewireTests(unittest.TestCase):
    def test_rewire_uri_under_old_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_root = Path(tmp) / "old"
            new_root = Path(tmp) / "new"
            old_file = old_root / "book" / "compressed" / "a.webp"
            old_file.parent.mkdir(parents=True)
            old_file.write_bytes(b"x")
            new_uri = rewire_thumbnail_uri(old_file.as_uri(), old_root, new_root)
            self.assertIsNotNone(new_uri)
            assert new_uri is not None
            self.assertTrue(new_uri.endswith("book/compressed/a.webp") or "book" in new_uri)

    def test_rewire_skips_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_root = Path(tmp) / "old"
            new_root = Path(tmp) / "new"
            outside = Path(tmp) / "other" / "x.webp"
            outside.parent.mkdir(parents=True)
            outside.write_bytes(b"x")
            self.assertIsNone(rewire_thumbnail_uri(outside.as_uri(), old_root, new_root))

    def test_migrate_copies_and_rewrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            old_preview = base / "old_preview"
            new_preview = base / "new_preview"
            ensure_preview_structure(old_preview)
            sample = old_preview / "book" / "compressed" / "sample.webp"
            sample.write_bytes(b"webp")

            repo = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=old_preview,
            )
            timestamp = "2026-01-01T00:00:00+00:00"
            with repo._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO books(
                        resource_id, file_name, extension, title, tags_json, status, resource_type,
                        path, thumbnail_path, created_at, updated_at
                    ) VALUES (?, 't.pdf', '.pdf', 'T', '[]', 'UNREAD', 'book', ?, ?, ?, ?)
                    """,
                    ("res-1", str(base / "book.pdf"), sample.as_uri(), timestamp, timestamp),
                )

            result = apply_preview_cache_change(repo, str(new_preview), "migrate")
            self.assertTrue(result.ok, result.errors)
            self.assertGreaterEqual(result.copied_files, 1)
            self.assertEqual(result.rewritten_uris, 1)
            self.assertTrue((new_preview / "book" / "compressed" / "sample.webp").exists())
            self.assertEqual(repo.preview_dir, new_preview.resolve(strict=False))
            self.assertEqual(repo.get_preview_cache_dir_setting(), str(new_preview.resolve(strict=False)))

            rows = repo.iter_thumbnail_uris()
            self.assertEqual(len(rows), 1)
            self.assertIn("new_preview", rows[0].replace("\\", "/"))

    def test_rewire_only_updates_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            old_preview = base / "old_preview"
            new_preview = base / "new_preview"
            ensure_preview_structure(old_preview)
            ensure_preview_structure(new_preview)
            sample = old_preview / "comic" / "compressed" / "c.webp"
            sample.parent.mkdir(parents=True, exist_ok=True)
            sample.write_bytes(b"webp")
            moved = new_preview / "comic" / "compressed" / "c.webp"
            moved.parent.mkdir(parents=True, exist_ok=True)
            moved.write_bytes(b"webp")

            repo = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=old_preview,
            )
            timestamp = "2026-01-01T00:00:00+00:00"
            with repo._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO comics(
                        resource_id, title, path, thumbnail_path, image_count,
                        is_missing, created_at, updated_at
                    ) VALUES (?, 'C', ?, ?, 1, 0, ?, ?)
                    """,
                    ("comic-1", str(base / "comic_folder"), sample.as_uri(), timestamp, timestamp),
                )

            result = apply_preview_cache_change(repo, str(new_preview), "rewire_only")
            self.assertTrue(result.ok, result.errors)
            self.assertEqual(result.copied_files, 0)
            self.assertEqual(result.rewritten_uris, 1)

    def test_switch_only_does_not_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            old_preview = base / "old_preview"
            new_preview = base / "new_preview"
            ensure_preview_structure(old_preview)
            sample = old_preview / "book" / "compressed" / "s.webp"
            sample.write_bytes(b"x")
            repo = LibraryRepository(
                base / "library.db",
                base / "scan_report.json",
                preview_dir=old_preview,
            )
            timestamp = "2026-01-01T00:00:00+00:00"
            with repo._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO books(
                        resource_id, file_name, extension, title, tags_json, status, resource_type,
                        path, thumbnail_path, created_at, updated_at
                    ) VALUES (?, 'b.pdf', '.pdf', 'T', '[]', 'UNREAD', 'book', ?, ?, ?, ?)
                    """,
                    ("res-2", str(base / "b.pdf"), sample.as_uri(), timestamp, timestamp),
                )
            old_uri = sample.as_uri()
            result = apply_preview_cache_change(repo, str(new_preview), "switch_only")
            self.assertTrue(result.ok)
            self.assertEqual(result.rewritten_uris, 0)
            self.assertEqual(repo.iter_thumbnail_uris()[0], old_uri)

    def test_safe_unlink_refuses_outside_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            preview = Path(tmp) / "preview"
            outside = Path(tmp) / "book.pdf"
            preview.mkdir()
            outside.write_bytes(b"pdf")
            refused = safe_unlink_under_preview(outside, preview)
            self.assertFalse(refused)
            self.assertTrue(outside.exists())

    def test_copy_preview_tree_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_root = Path(tmp) / "old"
            new_root = Path(tmp) / "new"
            src = old_root / "book" / "original" / "a.png"
            src.parent.mkdir(parents=True)
            src.write_bytes(b"png")
            copied, errors = copy_preview_tree(old_root, new_root)
            self.assertEqual(errors, [])
            self.assertEqual(copied, 1)
            self.assertTrue((new_root / "book" / "original" / "a.png").exists())

    def test_migrate_rejects_destination_nested_in_old_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            old_preview = base / "old_preview"
            old_preview.mkdir()
            (old_preview / "cover.webp").write_bytes(b"cover")
            repo = LibraryRepository(base / "library.db", base / "scan_report.json", preview_dir=old_preview)

            result = apply_preview_cache_change(repo, str(old_preview / "nested"), "migrate")

            self.assertFalse(result.ok)
            self.assertTrue(any("inside" in error for error in result.errors))
            self.assertEqual(repo.preview_dir, old_preview.resolve(strict=False))

    def test_copy_preview_tree_refuses_different_destination_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            old_root = base / "old"
            new_root = base / "new"
            source = old_root / "book" / "compressed" / "a.webp"
            destination = new_root / "book" / "compressed" / "a.webp"
            source.parent.mkdir(parents=True)
            destination.parent.mkdir(parents=True)
            source.write_bytes(b"source")
            destination.write_bytes(b"existing")

            copied, errors = copy_preview_tree(old_root, new_root)

            self.assertEqual(copied, 0)
            self.assertTrue(any("collision" in error.lower() for error in errors))
            self.assertEqual(destination.read_bytes(), b"existing")

    def test_migrate_keeps_current_setting_when_uri_rewrite_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            old_preview = base / "old"
            new_preview = base / "new"
            old_preview.mkdir()
            (old_preview / "cover.webp").write_bytes(b"cover")
            repo = LibraryRepository(base / "library.db", base / "scan_report.json", preview_dir=old_preview)

            with patch.object(repo, "rewrite_thumbnail_uris_for_root_move", side_effect=RuntimeError("db unavailable")):
                result = apply_preview_cache_change(repo, str(new_preview), "migrate")

            self.assertFalse(result.ok)
            self.assertTrue(any("rewrite failed" in error.lower() for error in result.errors))
            self.assertEqual(repo.preview_dir, old_preview.resolve(strict=False))
            self.assertEqual(repo.get_preview_cache_dir_setting(), "")


if __name__ == "__main__":
    unittest.main()
