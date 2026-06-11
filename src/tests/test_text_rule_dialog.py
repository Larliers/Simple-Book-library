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
    from PySide6.QtWidgets import QApplication, QComboBox, QSplitter
    from PySide6.QtWidgets import QLineEdit
    from PySide6.QtWidgets import QTextBrowser, QTextEdit

    from bookhub.ui.dialogs.text_rule_help_dialog import TextRuleHelpDialog
    from bookhub.ui.dialogs.text_rule_dialog import TextRuleDialog
    from bookhub.ui.dialogs.text_rule_regex_dialog import TextRuleRegexDialog

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - optional UI dependency
    QApplication = None  # type: ignore[assignment]
    QLineEdit = None  # type: ignore[assignment]
    QComboBox = None  # type: ignore[assignment]
    QSplitter = None  # type: ignore[assignment]
    QTextBrowser = None  # type: ignore[assignment]
    QTextEdit = None  # type: ignore[assignment]
    TextRuleHelpDialog = None  # type: ignore[assignment]
    TextRuleDialog = None  # type: ignore[assignment]
    TextRuleRegexDialog = None  # type: ignore[assignment]
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
            self.assertIn(dialog.regex_help_btn.text(), {"常用正则", "Common Regex"})
            self.assertIn(dialog.help_btn.text(), {"使用文档", "Usage Guide"})

            dialog._set_current_field("author")
            self.assertEqual(dialog.rule_list.count(), 1)
            self.assertEqual(dialog._visible_step_param_keys[0], ("bracket", "index"))

            dialog._set_current_field("title")
            dialog.preview_path_edit.setText(str(Path(tmp_dir) / "demo.txt"))
            dialog.preview_first_line_edit.setText("demo")
            dialog.preview_head_text_edit.setPlainText("demo")
            dialog._refresh_preview()

            self.assertEqual(dialog.preview_result_box.property("state"), "failed")
            self.assertIn("regex_extract", dialog.preview_result_label.toPlainText())

            payload = json.loads(dialog.rules_json())
            self.assertEqual(payload["title"][0]["source"], "filename")
            self.assertEqual(payload["title"][0]["steps"][0]["type"], "regex_extract")
            self.assertIn("pattern", payload["title"][0]["steps"][0])

    def test_dialog_exposes_new_line_and_marker_step_params(self) -> None:
        rules = {
            "title": [
                {
                    "field": "title",
                    "source": "txt_head_text",
                    "steps": [
                        {"type": "take_line", "index": 2},
                        {
                            "type": "take_after_marker",
                            "value": "简介",
                            "scope": "count",
                            "unit": "line",
                            "count": 2,
                        },
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            dialog = TextRuleDialog(tmp_dir, json.dumps(rules), preview_chars=120)
            self.addCleanup(dialog.close)

            self.assertEqual(dialog._visible_step_param_keys[0], ("index",))
            self.assertEqual(dialog._visible_step_param_keys[1], ("value", "scope", "unit", "count"))

            dialog._set_step_param(1, "scope", "all")
            dialog._set_step_param(1, "unit", "char")
            dialog._set_step_param(1, "count", 5)

            payload = json.loads(dialog.rules_json())
            marker_step = payload["title"][0]["steps"][1]
            self.assertEqual(marker_step["type"], "take_after_marker")
            self.assertEqual(marker_step["scope"], "all")
            self.assertEqual(marker_step["unit"], "char")
            self.assertEqual(marker_step["count"], 5)

    def test_dialog_exposes_line_range_params_and_warning_preview(self) -> None:
        rules = {
            "title": [
                {
                    "field": "title",
                    "source": "txt_head_text",
                    "steps": [{"type": "take_line_range", "start": 2, "end": 5}],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            dialog = TextRuleDialog(tmp_dir, json.dumps(rules), preview_chars=120)
            self.addCleanup(dialog.close)

            self.assertEqual(dialog._visible_step_param_keys[0], ("start", "end"))
            self.assertIsInstance(dialog.preview_result_label, QTextEdit)
            self.assertEqual(dialog.preview_result_label.frameShape(), QTextEdit.NoFrame)
            self.assertEqual(dialog.preview_result_box.minimumHeight(), 96)
            self.assertEqual(dialog.preview_result_box.maximumHeight(), 420)
            self.assertIsInstance(dialog.preview_splitter, QSplitter)

            dialog.preview_path_edit.setText(str(Path(tmp_dir) / "demo.txt"))
            dialog.preview_head_text_edit.setPlainText("一\n二\n三")
            dialog._refresh_preview()

            self.assertEqual(dialog.preview_result_box.property("state"), "warning")
            self.assertIn("二\n三", dialog.preview_result_label.toPlainText())
            self.assertIn("truncated", dialog.preview_result_label.toPlainText())

    def test_dialog_exposes_remove_last_lines_param_and_json(self) -> None:
        rules = {
            "title": [
                {
                    "field": "title",
                    "source": "txt_head_text",
                    "steps": [{"type": "remove_last_lines", "count": 2}],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            dialog = TextRuleDialog(tmp_dir, json.dumps(rules), preview_chars=120)
            self.addCleanup(dialog.close)

            self.assertEqual(dialog._visible_step_param_keys[0], ("count",))
            dialog._set_step_param(0, "count", 3)

            payload = json.loads(dialog.rules_json())
            step = payload["title"][0]["steps"][0]
            self.assertEqual(step["type"], "remove_last_lines")
            self.assertEqual(step["count"], 3)

    def test_dialog_exposes_remove_first_lines_param_and_json(self) -> None:
        rules = {
            "title": [
                {
                    "field": "title",
                    "source": "txt_head_text",
                    "steps": [{"type": "remove_first_lines", "count": 2}],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            dialog = TextRuleDialog(tmp_dir, json.dumps(rules), preview_chars=120)
            self.addCleanup(dialog.close)

            category_combos = dialog.steps_container.findChildren(QComboBox, "TextRuleStepCategoryCombo")
            type_combos = dialog.steps_container.findChildren(QComboBox, "TextRuleStepTypeCombo")
            self.assertEqual(category_combos[0].currentData(), "line")
            self.assertEqual(type_combos[0].currentData(), "remove_first_lines")
            self.assertEqual(dialog._visible_step_param_keys[0], ("count",))

            dialog._set_step_param(0, "count", 4)

            payload = json.loads(dialog.rules_json())
            step = payload["title"][0]["steps"][0]
            self.assertEqual(step["type"], "remove_first_lines")
            self.assertEqual(step["count"], 4)

    def test_dialog_groups_step_types_and_exposes_new_cleanup_params(self) -> None:
        rules = {
            "title": [
                {
                    "field": "title",
                    "source": "txt_head_text",
                    "steps": [
                        {"type": "remove_text", "text": "[汉化组]", "case_sensitive": False},
                        {"type": "take_after_last_text", "value": " - "},
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            dialog = TextRuleDialog(tmp_dir, json.dumps(rules), preview_chars=120)
            self.addCleanup(dialog.close)

            category_combos = dialog.steps_container.findChildren(QComboBox, "TextRuleStepCategoryCombo")
            type_combos = dialog.steps_container.findChildren(QComboBox, "TextRuleStepTypeCombo")
            self.assertEqual(len(category_combos), 2)
            self.assertEqual(len(type_combos), 2)
            self.assertEqual(category_combos[0].currentData(), "delete")
            self.assertEqual(type_combos[0].currentData(), "remove_text")
            self.assertEqual(dialog._visible_step_param_keys[0], ("text", "case_sensitive"))
            self.assertEqual(category_combos[1].currentData(), "extract")
            self.assertEqual(type_combos[1].currentData(), "take_after_last_text")
            self.assertEqual(dialog._visible_step_param_keys[1], ("value",))

            dialog._set_step_param(0, "text", "[翻译]")
            dialog._set_step_param(0, "case_sensitive", True)
            payload = json.loads(dialog.rules_json())
            step = payload["title"][0]["steps"][0]
            self.assertEqual(step["type"], "remove_text")
            self.assertEqual(step["text"], "[翻译]")
            self.assertIs(step["case_sensitive"], True)

    def test_preview_result_height_callback_tracks_splitter(self) -> None:
        rules = {
            "title": [
                {
                    "field": "title",
                    "source": "txt_head_text",
                    "steps": [{"type": "take_first_lines", "count": 1}],
                }
            ]
        }
        saved: list[int] = []

        with tempfile.TemporaryDirectory() as tmp_dir:
            dialog = TextRuleDialog(
                tmp_dir,
                json.dumps(rules),
                preview_chars=120,
                preview_result_height=260,
                preview_result_height_changed=saved.append,
            )
            self.addCleanup(dialog.close)

            self.assertEqual(dialog._preview_result_height, 260)
            dialog.preview_splitter.setSizes([280, 320])
            dialog._on_preview_splitter_moved(0, 1)
            expected_height = dialog._normalize_preview_result_height(dialog.preview_splitter.sizes()[1])
            dialog.reject()

            self.assertTrue(saved)
            self.assertEqual(saved[-1], expected_height)
            self.assertNotEqual(saved[-1], 260)

    def test_dialog_saves_rule_and_steps_presets(self) -> None:
        rules = {
            "title": [
                {
                    "field": "title",
                    "source": "txt_head_text",
                    "steps": [{"type": "take_line", "index": 2}, {"type": "trim"}],
                }
            ]
        }
        saved: list[list[dict[str, object]]] = []

        with tempfile.TemporaryDirectory() as tmp_dir:
            dialog = TextRuleDialog(
                tmp_dir,
                json.dumps(rules),
                preview_chars=120,
                rule_presets_changed=saved.append,
            )
            self.addCleanup(dialog.close)

            rule = dialog._selected_rule()
            self.assertIsNotNone(rule)
            rule_preset = dialog._add_rule_preset("Title rule", "rule", rule)  # type: ignore[arg-type]
            steps_preset = dialog._add_rule_preset("Cleanup", "steps", rule)  # type: ignore[arg-type]

            self.assertTrue(saved)
            self.assertEqual(dialog.preset_combo.count(), 2)
            self.assertEqual(rule_preset["kind"], "rule")
            self.assertEqual(rule_preset["source"], "txt_head_text")
            self.assertEqual(rule_preset["steps"][0]["type"], "take_line")
            self.assertEqual(steps_preset["kind"], "steps")
            self.assertNotIn("source", steps_preset)
            self.assertEqual(saved[-1][-1]["name"], "Cleanup")

    def test_dialog_imports_rule_and_steps_presets(self) -> None:
        rules = {
            "title": [
                {
                    "field": "title",
                    "source": "filename",
                    "steps": [{"type": "trim"}],
                }
            ]
        }
        presets = [
            {
                "id": "preset-rule",
                "kind": "rule",
                "name": "Title line",
                "source": "txt_head_text",
                "steps": [{"type": "take_line", "index": 2}],
            },
            {
                "id": "preset-steps",
                "kind": "steps",
                "name": "Cleanup",
                "steps": [{"type": "remove_first_lines", "count": 1}, {"type": "trim"}],
            },
        ]
        saved: list[list[dict[str, object]]] = []

        with tempfile.TemporaryDirectory() as tmp_dir:
            dialog = TextRuleDialog(
                tmp_dir,
                json.dumps(rules),
                preview_chars=120,
                rule_presets=presets,
                rule_presets_changed=saved.append,
            )
            self.addCleanup(dialog.close)

            dialog.preset_combo.setCurrentIndex(dialog.preset_combo.findData("preset-rule"))
            dialog._import_selected_preset()
            self.assertEqual(dialog.rule_list.count(), 2)
            payload = json.loads(dialog.rules_json())
            imported_rule = payload["title"][1]
            self.assertEqual(imported_rule["source"], "txt_head_text")
            self.assertEqual(imported_rule["steps"][0]["type"], "take_line")

            dialog.rule_list.setCurrentRow(0)
            dialog.preset_combo.setCurrentIndex(dialog.preset_combo.findData("preset-steps"))
            dialog._import_selected_preset()
            payload = json.loads(dialog.rules_json())
            original_steps = payload["title"][0]["steps"]
            self.assertEqual([step["type"] for step in original_steps], ["trim", "remove_first_lines", "trim"])

            dialog._remove_rule_preset_by_id("preset-rule")
            self.assertEqual(dialog.preset_combo.count(), 1)
            self.assertEqual(dialog.preset_combo.currentData(), "preset-steps")
            self.assertTrue(saved)
            self.assertEqual(saved[-1][0]["id"], "preset-steps")

    def test_dialog_exposes_loop_lines_params_and_json(self) -> None:
        rules = {
            "tag": [
                {
                    "field": "tag",
                    "source": "txt_head_text",
                    "steps": [
                        {
                            "type": "loop_lines",
                            "pattern": r"#\[(.+?)\]",
                            "group": 1,
                            "join": "newline",
                            "custom_separator": " / ",
                            "skip_failed": True,
                        }
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            dialog = TextRuleDialog(tmp_dir, json.dumps(rules), preview_chars=120)
            self.addCleanup(dialog.close)
            dialog._set_current_field("tag")

            self.assertEqual(
                dialog._visible_step_param_keys[0],
                ("pattern", "group", "join", "custom_separator", "skip_failed"),
            )
            separator_edits = [
                item
                for item in dialog.steps_container.findChildren(QLineEdit)
                if item.text() == " / "
            ]
            self.assertEqual(len(separator_edits), 1)
            self.assertFalse(separator_edits[0].isEnabled())

            dialog._set_step_param(0, "join", "custom")
            dialog._set_step_param(0, "skip_failed", False)
            dialog._render_steps(dialog._selected_steps())

            separator_edits = [
                item
                for item in dialog.steps_container.findChildren(QLineEdit)
                if item.text() == " / " and item.isEnabled()
            ]
            self.assertEqual(len(separator_edits), 1)

            payload = json.loads(dialog.rules_json())
            loop_step = payload["tag"][0]["steps"][0]
            self.assertEqual(loop_step["type"], "loop_lines")
            self.assertEqual(loop_step["pattern"], r"#\[(.+?)\]")
            self.assertEqual(loop_step["join"], "custom")
            self.assertEqual(loop_step["custom_separator"], " / ")
            self.assertIs(loop_step["skip_failed"], False)

    def test_help_dialog_is_single_guide_column(self) -> None:
        dialog = TextRuleHelpDialog()
        self.addCleanup(dialog.close)

        browsers = dialog.findChildren(QTextBrowser)

        self.assertEqual(len(browsers), 1)
        self.assertIn("Quick Start", browsers[0].toPlainText())
        self.assertNotIn("Common Regex", browsers[0].toPlainText())

    def test_regex_dialog_uses_plain_examples(self) -> None:
        dialog = TextRuleRegexDialog()
        self.addCleanup(dialog.close)

        browsers = dialog.findChildren(QTextBrowser)

        self.assertEqual(len(browsers), 1)
        text = browsers[0].toPlainText()
        self.assertIn("Purpose: Extract date", text)
        self.assertIn("Sample text: 2026年06月11日", text)
        self.assertIn(r"Regex: (\d{4})年(\d{1,2})月(\d{1,2})日", text)
        self.assertIn("Extract result: 分组1=2026", text)
        self.assertIn(r"Regex: #\[(.+?)\]", text)
        self.assertNotIn("- ", text)
        self.assertNotIn(" | ", text)


if __name__ == "__main__":
    unittest.main()
