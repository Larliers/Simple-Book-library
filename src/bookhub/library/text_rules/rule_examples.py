from __future__ import annotations

from bookhub.library.text_rules.rule_models import ImportRule, RuleStep


def default_text_title_rule_chain() -> list[ImportRule]:
    return [
        ImportRule(
            field="title",
            source="txt_first_line",
            steps=[RuleStep(type="take_after_text", params={"value": "T"}), RuleStep(type="trim")],
        ),
        ImportRule(
            field="title",
            source="filename",
            steps=[RuleStep(type="take_bracket_content", params={"bracket": "《》", "index": 1}), RuleStep(type="trim")],
        ),
        ImportRule(field="title", source="stem", steps=[RuleStep(type="trim")]),
    ]
