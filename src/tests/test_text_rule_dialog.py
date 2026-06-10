from __future__ import annotations

import json
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

try:
    from PySide6.QtWidgets import QApplication

    from bookhub.ui.dialogs.text_rule_dialog import TextRuleDialog

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - optional UI dependency
    QApplication = None  # type: ignore[assignment]
    TextRuleDialog = None  # type: ignore[assignment]
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, "PySide6 is not available")
class TextRuleDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_dialog_loads_legacy_json_and_contextual_step_params(self) -> None:
        rules = {
            "title": [
                {
                    "field": "title",
                    "source": "filename",
                    "steps": [{"type": "regex_extract", "pattern": "(", "group": 1}],
                }
            ],
            "author": [
                {
                    "field": "author",
                    "source": "filename",
                    "steps": [{"type": "take_bracket_content", "bracket": "【】", "index": 1}],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            dialog = TextRuleDialog(tmp_dir, json.dumps(rules), preview_chars=120)
            self.addCleanup(dialog.close)

            self.assertEqual(dialog.rule_list.count(), 1)
            self.assertEqual(dialog._visible_step_param_keys[0], ("pattern", "group"))

            dialog._set_current_field("author")
            self.assertEqual(dialog.rule_list.count(), 1)
            self.assertEqual(dialog._visible_step_param_keys[0], ("bracket", "index"))

            dialog._set_current_field("title")
            dialog.preview_path_edit.setText(str(Path(tmp_dir) / "demo.txt"))
            dialog.preview_first_line_edit.setText("demo")
            dialog.preview_head_text_edit.setPlainText("demo")
            dialog._refresh_preview()

            self.assertEqual(dialog.preview_result_box.property("state"), "failed")
            self.assertIn("regex_extract", dialog.preview_result_label.text())

            payload = json.loads(dialog.rules_json())
            self.assertEqual(payload["title"][0]["source"], "filename")
            self.assertEqual(payload["title"][0]["steps"][0]["type"], "regex_extract")
            self.assertIn("pattern", payload["title"][0]["steps"][0])


if __name__ == "__main__":
    unittest.main()
