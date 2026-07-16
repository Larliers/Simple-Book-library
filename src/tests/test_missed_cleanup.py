from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.repository import LibraryRepository


class MissedCleanupTests(unittest.TestCase):
    def test_legacy_is_missing_rows_are_purged_on_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            db_path = base / "library.db"
            report = base / "scan_report.json"
            repo = LibraryRepository(db_path, report)
            timestamp = "2026-01-01T00:00:00+00:00"
            with repo._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO books(
                        resource_id, file_name, extension, title, author, publisher, language, tags_json,
                        status, resource_type, path, thumbnail_path, info_text, is_missing, missing_reason,
                        fingerprint_sha256, fingerprint_size_mtime, fingerprint_quick, created_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, NULL, NULL, NULL, '[]', 'UNREAD', 'pdf', ?, NULL, NULL, 1, 'gone',
                           NULL, NULL, NULL, ?, ?)
                    """,
                    (uuid4().hex, "gone.pdf", ".pdf", "Gone Book", str(base / "gone.pdf"), timestamp, timestamp),
                )
                conn.execute(
                    """
                    INSERT INTO comics(
                        resource_id, title, path, comic_root, cover_image_path, thumbnail_path, cover_fingerprint,
                        folder_size_mtime, folder_mtime, folder_modified_at, image_count, info_text,
                        is_missing, missing_reason, created_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, NULL, NULL, NULL, NULL, 0, 0, 1, NULL, 1, 'gone', ?, ?)
                    """,
                    (uuid4().hex, "Gone Comic", str(base / "gone_comic"), str(base), timestamp, timestamp),
                )

            reopened = LibraryRepository(db_path, report)
            self.assertEqual(reopened.list_books(include_missing=True), [])
            self.assertEqual(reopened.list_comics(include_missing=True), [])
            self.assertFalse(hasattr(reopened, "find_missing_by_fingerprint"))
            self.assertFalse(hasattr(reopened, "restore_missing_book"))


if __name__ == "__main__":
    unittest.main()
