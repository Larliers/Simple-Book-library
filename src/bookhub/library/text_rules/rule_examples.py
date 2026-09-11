from __future__ import annotations

from bookhub.library.text_rules.rule_models import ImportRule, RuleStep


def default_text_title_rule_chain() -> list[ImportRule]:
    prefix_rules = [
        ImportRule(
            field="title",
            source="txt_first_line",
            steps=[RuleStep(type="take_after_text", params={"value": prefix}), RuleStep(type="trim")],
        )
        for prefix in ("Title:", "Title：", "标题：", "标题:")
    ]
    return [
        *prefix_rules,
        ImportRule(field="title", source="txt_first_line", steps=[RuleStep(type="trim")]),
        ImportRule(
            field="title",
            source="filename",
            steps=[RuleStep(type="take_bracket_content", params={"bracket": "《》", "index": 1}), RuleStep(type="trim")],
        ),
        ImportRule(field="title", source="stem", steps=[RuleStep(type="trim")]),
    ]
