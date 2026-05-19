from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.text_rules import ImportRule, RuleContext, RuleStep, apply_rule, apply_rule_chain


class RuleEngineTests(unittest.TestCase):
    def test_take_second_square_bracket_content(self) -> None:
        rule = ImportRule(
            field="tag",
            source="filename",
            steps=[RuleStep(type="take_bracket_content", params={"bracket": "[]", "index": 2})],
        )
        context = RuleContext(file_path=r"F:\books\[完结][玄幻]斗破苍穹.txt")
        result = apply_rule(rule, context)
        self.assertTrue(result.success)
        self.assertEqual(result.value, "玄幻")

    def test_take_title_from_first_line_after_t(self) -> None:
        rule = ImportRule(
            field="title",
            source="txt_first_line",
            steps=[
                RuleStep(type="take_after_text", params={"value": "T"}),
                RuleStep(type="trim"),
            ],
        )
        context = RuleContext(
            file_path=r"F:\books\novel.txt",
            txt_first_line="T 我的青春恋爱物语果然有问题",
        )
        result = apply_rule(rule, context)
        self.assertTrue(result.success)
        self.assertEqual(result.value, "我的青春恋爱物语果然有问题")

    def test_split_and_take_second_piece(self) -> None:
        rule = ImportRule(
            field="title",
            source="filename",
            steps=[
                RuleStep(type="remove_extension"),
                RuleStep(type="split_and_take", params={"separator": "_", "index": 2}),
            ],
        )
        context = RuleContext(file_path=r"F:\books\刘慈欣_三体_全集.txt")
        result = apply_rule(rule, context)
        self.assertTrue(result.success)
        self.assertEqual(result.value, "三体")

    def test_take_between_texts(self) -> None:
        rule = ImportRule(
            field="title",
            source="txt_first_line",
            steps=[
                RuleStep(type="take_between_texts", params={"start": "标题：", "end": " 作者："}),
                RuleStep(type="trim"),
            ],
        )
        context = RuleContext(
            file_path=r"F:\books\x.txt",
            txt_first_line="标题：雪中悍刀行 作者：烽火戏诸侯",
        )
        result = apply_rule(rule, context)
        self.assertTrue(result.success)
        self.assertEqual(result.value, "雪中悍刀行")

    def test_take_chinese_bracket_content(self) -> None:
        rule = ImportRule(
            field="author",
            source="filename",
            steps=[RuleStep(type="take_bracket_content", params={"bracket": "【】", "index": 1})],
        )
        context = RuleContext(file_path=r"F:\books\【作者】诡秘之主.txt")
        result = apply_rule(rule, context)
        self.assertTrue(result.success)
        self.assertEqual(result.value, "作者")

    def test_invalid_regex_does_not_crash(self) -> None:
        rule = ImportRule(
            field="title",
            source="filename",
            steps=[RuleStep(type="regex_extract", params={"pattern": "(", "group": 1})],
        )
        context = RuleContext(file_path=r"F:\books\demo.txt")
        result = apply_rule(rule, context)
        self.assertFalse(result.success)
        self.assertEqual(result.failed_step, "regex_extract")
        self.assertIsInstance(result.error_message, str)
        self.assertTrue(result.error_message)

    def test_rule_chain_fallback(self) -> None:
        chain = [
            ImportRule(
                field="title",
                source="txt_first_line",
                steps=[RuleStep(type="take_after_text", params={"value": "T"}), RuleStep(type="trim")],
            ),
            ImportRule(
                field="title",
                source="filename",
                steps=[RuleStep(type="take_bracket_content", params={"bracket": "《》", "index": 1})],
            ),
            ImportRule(field="title", source="stem", steps=[RuleStep(type="trim")]),
        ]
        context = RuleContext(file_path=r"F:\books\BookName.txt", txt_first_line="No prefix")
        result = apply_rule_chain(chain, context)
        self.assertTrue(result.success)
        self.assertEqual(result.value, "BookName")


if __name__ == "__main__":
    unittest.main()
