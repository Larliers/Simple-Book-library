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

    def test_take_line_from_head_text(self) -> None:
        rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="take_line", params={"index": 3})],
        )
        context = RuleContext(
            file_path=r"F:\books\x.txt",
            txt_head_text="第一行\n第二行\n第三行\n第四行",
        )
        result = apply_rule(rule, context)
        self.assertTrue(result.success)
        self.assertEqual(result.value, "第三行")

    def test_take_first_lines_from_head_text(self) -> None:
        rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="take_first_lines", params={"count": 2})],
        )
        context = RuleContext(
            file_path=r"F:\books\x.txt",
            txt_head_text="第一行\n第二行\n第三行",
        )
        result = apply_rule(rule, context)
        self.assertTrue(result.success)
        self.assertEqual(result.value, "第一行\n第二行")

    def test_remove_last_lines_from_head_text(self) -> None:
        rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="remove_last_lines", params={"count": 2})],
        )
        context = RuleContext(
            file_path=r"F:\books\x.txt",
            txt_head_text="第一行\n第二行\n第三行\n第四行",
        )

        result = apply_rule(rule, context)

        self.assertTrue(result.success)
        self.assertEqual(result.value, "第一行\n第二行")

    def test_remove_last_lines_can_remove_all_lines(self) -> None:
        rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="remove_last_lines", params={"count": 9})],
        )
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="第一行\n第二行")

        result = apply_rule(rule, context)

        self.assertTrue(result.success)
        self.assertEqual(result.value, "")

    def test_remove_first_lines_from_head_text(self) -> None:
        rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="remove_first_lines", params={"count": 2})],
        )
        context = RuleContext(
            file_path=r"F:\books\x.txt",
            txt_head_text="第一行\n第二行\n第三行\n第四行",
        )

        result = apply_rule(rule, context)

        self.assertTrue(result.success)
        self.assertEqual(result.value, "第三行\n第四行")

    def test_remove_first_lines_can_remove_all_lines(self) -> None:
        rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="remove_first_lines", params={"count": 9})],
        )
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="第一行\n第二行")

        result = apply_rule(rule, context)

        self.assertTrue(result.success)
        self.assertEqual(result.value, "")

    def test_cleanup_steps_normalize_and_remove_spaces(self) -> None:
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text=" 作者　\t 张三 \n 第 001 话 ")
        cases = [
            ("normalize_spaces", {}, "作者 张三 第 001 话"),
            ("remove_all_spaces", {}, "作者张三第001话"),
            ("normalize_punctuation", {}, " 作者　\t 张三 \n 第 001 话 "),
        ]

        for step_type, params, expected in cases:
            with self.subTest(step_type=step_type):
                rule = ImportRule(field="title", source="txt_head_text", steps=[RuleStep(type=step_type, params=params)])
                result = apply_rule(rule, context)
                self.assertTrue(result.success)
                self.assertEqual(result.value, expected)

    def test_normalize_punctuation_converts_common_full_width_marks(self) -> None:
        rule = ImportRule(field="title", source="txt_head_text", steps=[RuleStep(type="normalize_punctuation")])
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="【甲】（乙），丙：丁；戊／己")

        result = apply_rule(rule, context)

        self.assertTrue(result.success)
        self.assertEqual(result.value, "[甲](乙),丙:丁;戊/己")

    def test_remove_text_and_remove_regex(self) -> None:
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="[汉化组] 标题 (DL版)")
        fixed_rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="remove_text", params={"text": "(dl版)", "case_sensitive": False})],
        )
        regex_rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="remove_regex", params={"pattern": r"\[.*?\]\s*"})],
        )

        fixed = apply_rule(fixed_rule, context)
        regex = apply_rule(regex_rule, context)

        self.assertTrue(fixed.success)
        self.assertEqual(fixed.value, "[汉化组] 标题 ")
        self.assertTrue(regex.success)
        self.assertEqual(regex.value, "标题 (DL版)")

    def test_remove_regex_invalid_pattern_returns_failure(self) -> None:
        rule = ImportRule(field="title", source="txt_head_text", steps=[RuleStep(type="remove_regex", params={"pattern": "("})])
        result = apply_rule(rule, RuleContext(file_path=r"F:\books\x.txt", txt_head_text="abc"))

        self.assertFalse(result.success)
        self.assertEqual(result.failed_step, "remove_regex")
        self.assertIn("Invalid regex pattern", str(result.error_message))

    def test_remove_bracket_steps(self) -> None:
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="[汉化组]【作者】标题（DL版）《副题》")
        remove_rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="remove_bracket_content", params={"bracket_type": "all"}), RuleStep(type="trim")],
        )
        keep_rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="remove_brackets_keep_content", params={"bracket_type": "chinese_square"})],
        )

        removed = apply_rule(remove_rule, context)
        kept = apply_rule(keep_rule, context)

        self.assertTrue(removed.success)
        self.assertEqual(removed.value, "标题")
        self.assertTrue(kept.success)
        self.assertEqual(kept.value, "[汉化组]作者标题（DL版）《副题》")

    def test_take_before_and_after_last_text(self) -> None:
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="作者 - 系列 - 标题")
        before_rule = ImportRule(field="title", source="txt_head_text", steps=[RuleStep(type="take_before_last_text", params={"value": " - "})])
        after_rule = ImportRule(field="title", source="txt_head_text", steps=[RuleStep(type="take_after_last_text", params={"value": " - "})])

        before = apply_rule(before_rule, context)
        after = apply_rule(after_rule, context)

        self.assertTrue(before.success)
        self.assertEqual(before.value, "作者 - 系列")
        self.assertTrue(after.success)
        self.assertEqual(after.value, "标题")

    def test_take_line_range_from_head_text(self) -> None:
        rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="take_line_range", params={"start": 2, "end": 4})],
        )
        context = RuleContext(
            file_path=r"F:\books\x.txt",
            txt_head_text="第一行\n第二行\n第三行\n第四行\n第五行",
        )

        result = apply_rule(rule, context)

        self.assertTrue(result.success)
        self.assertEqual(result.value, "第二行\n第三行\n第四行")
        self.assertIsNone(result.warning_message)

    def test_take_line_range_truncates_end_with_warning(self) -> None:
        rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="take_line_range", params={"start": 2, "end": 5})],
        )
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="第一行\n第二行\n第三行")

        result = apply_rule(rule, context)

        self.assertTrue(result.success)
        self.assertEqual(result.value, "第二行\n第三行")
        self.assertIn("truncated to line 3", str(result.warning_message))

    def test_take_line_range_invalid_params_return_failure(self) -> None:
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="一\n二")
        cases = [
            ({"start": 3, "end": 4}, "out of range"),
            ({"start": 2, "end": 1}, "start must be <= end"),
            ({"start": "x", "end": 2}, "start must be an integer"),
        ]

        for params, expected in cases:
            with self.subTest(expected=expected):
                rule = ImportRule(
                    field="title",
                    source="txt_head_text",
                    steps=[RuleStep(type="take_line_range", params=params)],
                )
                result = apply_rule(rule, context)
                self.assertFalse(result.success)
                self.assertEqual(result.failed_step, "take_line_range")
                self.assertIn(expected, str(result.error_message))

    def test_take_before_and_after_marker_all_lines(self) -> None:
        context = RuleContext(
            file_path=r"F:\books\x.txt",
            txt_head_text="标题\n作者\n---简介---\n第一段\n第二段",
        )

        before_rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="take_before_marker", params={"value": "---简介---", "scope": "all", "unit": "line"})],
        )
        after_rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="take_after_marker", params={"value": "---简介---", "scope": "all", "unit": "line"})],
        )

        before = apply_rule(before_rule, context)
        after = apply_rule(after_rule, context)

        self.assertTrue(before.success)
        self.assertEqual(before.value, "标题\n作者")
        self.assertTrue(after.success)
        self.assertEqual(after.value, "第一段\n第二段")

    def test_take_before_and_after_marker_count_lines(self) -> None:
        context = RuleContext(
            file_path=r"F:\books\x.txt",
            txt_head_text="一\n二\n三\n分界\n四\n五\n六",
        )
        before_rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[
                RuleStep(
                    type="take_before_marker",
                    params={"value": "分界", "scope": "count", "unit": "line", "count": 2},
                )
            ],
        )
        after_rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[
                RuleStep(
                    type="take_after_marker",
                    params={"value": "分界", "scope": "count", "unit": "line", "count": 2},
                )
            ],
        )

        before = apply_rule(before_rule, context)
        after = apply_rule(after_rule, context)

        self.assertTrue(before.success)
        self.assertEqual(before.value, "二\n三")
        self.assertTrue(after.success)
        self.assertEqual(after.value, "四\n五")

    def test_take_before_and_after_marker_count_chars(self) -> None:
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="abcMARKdefghi")
        before_rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="take_before_marker", params={"value": "MARK", "scope": "count", "unit": "char", "count": 2})],
        )
        after_rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="take_after_marker", params={"value": "MARK", "scope": "count", "unit": "char", "count": 3})],
        )

        before = apply_rule(before_rule, context)
        after = apply_rule(after_rule, context)

        self.assertTrue(before.success)
        self.assertEqual(before.value, "bc")
        self.assertTrue(after.success)
        self.assertEqual(after.value, "def")

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

    def test_line_index_out_of_range_returns_failure(self) -> None:
        rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="take_line", params={"index": 4})],
        )
        result = apply_rule(rule, RuleContext(file_path=r"F:\books\x.txt", txt_head_text="一\n二"))

        self.assertFalse(result.success)
        self.assertEqual(result.failed_step, "take_line")
        self.assertIn("out of range", str(result.error_message))

    def test_marker_not_found_returns_failure(self) -> None:
        rule = ImportRule(
            field="title",
            source="txt_head_text",
            steps=[RuleStep(type="take_after_marker", params={"value": "不存在", "scope": "all", "unit": "line"})],
        )
        result = apply_rule(rule, RuleContext(file_path=r"F:\books\x.txt", txt_head_text="一\n二"))

        self.assertFalse(result.success)
        self.assertEqual(result.failed_step, "take_after_marker")
        self.assertIn("Text not found", str(result.error_message))

    def test_invalid_line_count_returns_failure(self) -> None:
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="一\n二")
        for step_type in ("take_first_lines", "remove_last_lines", "remove_first_lines"):
            with self.subTest(step_type=step_type):
                rule = ImportRule(
                    field="title",
                    source="txt_head_text",
                    steps=[RuleStep(type=step_type, params={"count": 0})],
                )
                result = apply_rule(rule, context)

                self.assertFalse(result.success)
                self.assertEqual(result.failed_step, step_type)
                self.assertIn("count must be >= 1", str(result.error_message))

    def test_loop_lines_extracts_tags_with_newline_join(self) -> None:
        rule = ImportRule(
            field="tag",
            source="txt_head_text",
            steps=[RuleStep(type="loop_lines", params={"pattern": r"#\[(.+?)\]", "group": 1})],
        )
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="#[fantasy]\n#[completed]")

        result = apply_rule(rule, context)

        self.assertTrue(result.success)
        self.assertEqual(result.value, "fantasy\ncompleted")

    def test_loop_lines_skips_unmatched_lines_by_default(self) -> None:
        rule = ImportRule(
            field="tag",
            source="txt_head_text",
            steps=[RuleStep(type="loop_lines", params={"pattern": r"#\[(.+?)\]", "group": 1})],
        )
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="#[fantasy]\n普通文本\n#[completed]")

        result = apply_rule(rule, context)

        self.assertTrue(result.success)
        self.assertEqual(result.value, "fantasy\ncompleted")

    def test_loop_lines_can_fail_on_unmatched_line(self) -> None:
        rule = ImportRule(
            field="tag",
            source="txt_head_text",
            steps=[
                RuleStep(
                    type="loop_lines",
                    params={"pattern": r"#\[(.+?)\]", "group": 1, "skip_failed": False},
                )
            ],
        )
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="#[fantasy]\n普通文本")

        result = apply_rule(rule, context)

        self.assertFalse(result.success)
        self.assertEqual(result.failed_step, "loop_lines")
        self.assertIn("Line 2 did not match", str(result.error_message))

    def test_loop_lines_validates_regex_group_and_empty_result(self) -> None:
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="#[fantasy]")
        cases = [
            ({"pattern": "(", "group": 1}, "Invalid regex pattern"),
            ({"pattern": r"#\[(.+?)\]", "group": 2}, "out of range"),
            ({"pattern": r"@(.+)", "group": 1}, "No lines matched"),
        ]

        for params, expected in cases:
            with self.subTest(expected=expected):
                rule = ImportRule(field="tag", source="txt_head_text", steps=[RuleStep(type="loop_lines", params=params)])
                result = apply_rule(rule, context)
                self.assertFalse(result.success)
                self.assertEqual(result.failed_step, "loop_lines")
                self.assertIn(expected, str(result.error_message))

    def test_loop_lines_join_options(self) -> None:
        context = RuleContext(file_path=r"F:\books\x.txt", txt_head_text="#[a]\n#[b]")
        cases = [
            ("newline", "", "a\nb"),
            ("comma", "", "a,b"),
            ("semicolon", "", "a;b"),
            ("custom", " / ", "a / b"),
        ]

        for join, custom_separator, expected in cases:
            with self.subTest(join=join):
                rule = ImportRule(
                    field="tag",
                    source="txt_head_text",
                    steps=[
                        RuleStep(
                            type="loop_lines",
                            params={
                                "pattern": r"#\[(.+?)\]",
                                "group": 1,
                                "join": join,
                                "custom_separator": custom_separator,
                            },
                        )
                    ],
                )
                result = apply_rule(rule, context)
                self.assertTrue(result.success)
                self.assertEqual(result.value, expected)

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
