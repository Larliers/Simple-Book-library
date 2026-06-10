from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.text_rules import ImportRule, RuleStep
from bookhub.library.text_rules.rule_preview import (
    build_preview_context,
    find_first_txt_file,
    preview_rule_chain,
    read_txt_preview_sample,
)


class RulePreviewTests(unittest.TestCase):
    def test_find_and_read_first_txt_sample(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            nested = root / "nested"
            nested.mkdir()
            sample_path = nested / "novel.txt"
            sample_path.write_text("T 雪中悍刀行\n第二行", encoding="utf-8")

            found = find_first_txt_file(str(root))
            self.assertEqual(found, str(sample_path.resolve(strict=False)))

            sample = read_txt_preview_sample(found or "")
            self.assertIsNotNone(sample)
            assert sample is not None
            self.assertEqual(sample.file_path, str(sample_path.resolve(strict=False)))
            self.assertEqual(sample.txt_first_line, "T 雪中悍刀行")
            self.assertIn("第二行", sample.txt_head_text)

    def test_preview_rule_chain_uses_fallback_rule(self) -> None:
        rules = [
            ImportRule(
                field="title",
                source="txt_first_line",
                steps=[RuleStep(type="take_after_text", params={"value": "标题："})],
            ),
            ImportRule(field="title", source="stem", steps=[RuleStep(type="trim", params={})]),
        ]
        context = build_preview_context(r"F:\books\FallbackTitle.txt", "No marker", "")

        result = preview_rule_chain(rules, context)

        self.assertTrue(result.success)
        self.assertEqual(result.value, "FallbackTitle")

    def test_preview_invalid_regex_returns_failure(self) -> None:
        rules = [
            ImportRule(
                field="title",
                source="filename",
                steps=[RuleStep(type="regex_extract", params={"pattern": "(", "group": 1})],
            )
        ]
        context = build_preview_context(r"F:\books\demo.txt", "", "")

        result = preview_rule_chain(rules, context)

        self.assertFalse(result.success)
        self.assertEqual(result.failed_step, "regex_extract")
        self.assertIsInstance(result.error_message, str)
        self.assertTrue(result.error_message)

    def test_empty_directory_has_no_sample(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.assertIsNone(find_first_txt_file(tmp_dir))
            self.assertIsNone(read_txt_preview_sample(str(Path(tmp_dir) / "missing.txt")))


if __name__ == "__main__":
    unittest.main()
