from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.models import ScanConflict, ScanResult


class ScanSummaryFieldAlignmentTests(unittest.TestCase):
    def test_to_summary_includes_canonical_and_alias_keys(self) -> None:
        result = ScanResult(
            added_count=1,
            ignored_unsupported=3,
            skipped_unchanged_count=5,
            comic_added_count=7,
            comic_updated_count=2,
            comic_large_image_downscaled_count=4,
            text_added_count=8,
            text_scanned_files=9,
            name_conflicts=[
                ScanConflict(
                    file_name="a.pdf",
                    incoming_path="/in/a.pdf",
                    existing_path="/old/a.pdf",
                )
            ],
        )
        summary = result.to_summary()
        self.assertEqual(summary["ignored_unsupported"], 3)
        self.assertEqual(summary["ignored_unsupported_count"], 3)
        self.assertEqual(summary["text_scanned_files"], 9)
        self.assertEqual(summary["text_scanned_count"], 9)
        self.assertEqual(summary["comic_large_image_downscaled_count"], 4)
        self.assertEqual(summary["comic_thumbnail_downscaled_count"], 4)
        self.assertEqual(summary["comic_added_count"], 7)
        self.assertEqual(summary["skipped_unchanged_count"], 5)
        conflict = summary["name_conflicts"][0]
        assert isinstance(conflict, dict)
        self.assertEqual(conflict["incoming_path"], "/in/a.pdf")
        self.assertNotIn("source_path", conflict)

    def test_added_total_matches_toast_formula(self) -> None:
        summary = ScanResult(
            added_count=1,
            text_added_count=2,
            comic_added_count=3,
        ).to_summary()
        added = (
            int(summary.get("added_count", 0) or 0)
            + int(summary.get("text_added_count", 0) or 0)
            + int(summary.get("comic_added_count", 0) or 0)
        )
        self.assertEqual(added, 6)


if __name__ == "__main__":
    unittest.main()
