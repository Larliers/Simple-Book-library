from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.repository import LibraryRepository
from bookhub.ui.resources.layout_config import (
    DEFAULT_COVER_SELECTED_BORDER_COLOR,
    DEFAULT_COVER_SELECTED_BORDER_WIDTH,
    normalize_cover_selected_border_color,
    normalize_cover_selected_border_width,
)


class CoverGridSettingsTests(unittest.TestCase):
    def test_cover_border_normalizers(self) -> None:
        self.assertEqual(normalize_cover_selected_border_width(None), DEFAULT_COVER_SELECTED_BORDER_WIDTH)
        self.assertEqual(normalize_cover_selected_border_width(-1), 1)
        self.assertEqual(normalize_cover_selected_border_width(100), 6)
        self.assertEqual(normalize_cover_selected_border_width("3"), 3)

        self.assertEqual(
            normalize_cover_selected_border_color(None),
            DEFAULT_COVER_SELECTED_BORDER_COLOR,
        )
        self.assertEqual(
            normalize_cover_selected_border_color("#zzzzzz"),
            DEFAULT_COVER_SELECTED_BORDER_COLOR,
        )
        self.assertEqual(normalize_cover_selected_border_color("00ff7a"), "#00FF7A")

    def test_repository_cover_border_settings_persist_and_normalize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = LibraryRepository(
                db_path=root / "library.db",
                scan_report_path=root / "scan_report.json",
            )
            self.assertEqual(repo.get_cover_selected_border_width(), DEFAULT_COVER_SELECTED_BORDER_WIDTH)
            self.assertEqual(repo.get_cover_selected_border_color(), DEFAULT_COVER_SELECTED_BORDER_COLOR)

            repo.set_cover_selected_border_width(999)
            repo.set_cover_selected_border_color("invalid")
            self.assertEqual(repo.get_cover_selected_border_width(), 6)
            self.assertEqual(repo.get_cover_selected_border_color(), DEFAULT_COVER_SELECTED_BORDER_COLOR)

            repo.set_cover_selected_border_width(4)
            repo.set_cover_selected_border_color("#11aaee")

            repo_reload = LibraryRepository(
                db_path=root / "library.db",
                scan_report_path=root / "scan_report.json",
            )
            self.assertEqual(repo_reload.get_cover_selected_border_width(), 4)
            self.assertEqual(repo_reload.get_cover_selected_border_color(), "#11AAEE")

    def test_repository_text_rule_preview_result_height_persists_and_clamps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = LibraryRepository(
                db_path=root / "library.db",
                scan_report_path=root / "scan_report.json",
            )
            self.assertEqual(repo.get_text_rule_preview_result_height(), 180)

            repo.set_text_rule_preview_result_height(999)
            self.assertEqual(repo.get_text_rule_preview_result_height(), 420)
            repo.set_text_rule_preview_result_height(12)
            self.assertEqual(repo.get_text_rule_preview_result_height(), 96)
            repo.set_text_rule_preview_result_height(260)

            repo_reload = LibraryRepository(
                db_path=root / "library.db",
                scan_report_path=root / "scan_report.json",
            )
            self.assertEqual(repo_reload.get_text_rule_preview_result_height(), 260)

    def test_repository_text_rule_dialog_size_persists_and_clamps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = LibraryRepository(
                db_path=root / "library.db",
                scan_report_path=root / "scan_report.json",
            )
            self.assertEqual(repo.get_text_rule_dialog_size(), (1320, 820))

            repo.set_text_rule_dialog_size(5000, 100)
            self.assertEqual(repo.get_text_rule_dialog_size(), (1920, 700))
            repo.set_text_rule_dialog_size(1440, 900)

            repo_reload = LibraryRepository(
                db_path=root / "library.db",
                scan_report_path=root / "scan_report.json",
            )
            self.assertEqual(repo_reload.get_text_rule_dialog_size(), (1440, 900))

    def test_repository_text_rule_presets_persist_and_normalize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = LibraryRepository(
                db_path=root / "library.db",
                scan_report_path=root / "scan_report.json",
            )
            self.assertEqual(repo.get_text_rule_presets(), [])

            repo.set_text_rule_presets(
                [
                    {
                        "id": "preset-1",
                        "kind": "rule",
                        "name": "Title rule",
                        "source": "txt_head_text",
                        "steps": [{"type": "take_line", "index": 2}, {"bad": "ignored"}],
                    },
                    {"id": "preset-2", "kind": "steps", "name": "", "steps": [{"type": "trim"}]},
                    {"id": "", "kind": "rule", "name": "bad", "steps": []},
                    {"id": "bad-kind", "kind": "unknown", "name": "bad", "steps": []},
                ]
            )

            repo_reload = LibraryRepository(
                db_path=root / "library.db",
                scan_report_path=root / "scan_report.json",
            )
            presets = repo_reload.get_text_rule_presets()

            self.assertEqual(len(presets), 2)
            self.assertEqual(presets[0]["id"], "preset-1")
            self.assertEqual(presets[0]["kind"], "rule")
            self.assertEqual(presets[0]["source"], "txt_head_text")
            self.assertEqual(presets[0]["steps"], [{"type": "take_line", "index": 2}])
            self.assertEqual(presets[1]["kind"], "steps")
            self.assertEqual(presets[1]["name"], "Preset")
            self.assertNotIn("source", presets[1])


if __name__ == "__main__":
    unittest.main()
