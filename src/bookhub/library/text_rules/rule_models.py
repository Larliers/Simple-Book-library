from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class RuleStep:
    type: str
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuleStep":
        raw_type = str(data.get("type") or "").strip()
        params = {str(key): value for key, value in data.items() if key != "type"}
        return cls(type=raw_type, params=params)

    def to_dict(self) -> dict[str, Any]:
        payload = {"type": self.type}
        payload.update(self.params)
        return payload


@dataclass(slots=True)
class ImportRule:
    field: str
    source: str
    steps: list[RuleStep] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImportRule":
        steps_data = data.get("steps")
        steps: list[RuleStep] = []
        if isinstance(steps_data, list):
            for item in steps_data:
                if isinstance(item, dict):
                    steps.append(RuleStep.from_dict(item))
        return cls(
            field=str(data.get("field") or "").strip(),
            source=str(data.get("source") or "").strip(),
            steps=steps,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "source": self.source,
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(slots=True)
class RuleContext:
    file_path: str
    txt_first_line: str = ""
    txt_head_text: str = ""


@dataclass(slots=True)
class RuleResult:
    success: bool
    value: str
    failed_step: str | None = None
    error_message: str | None = None


def load_rules_from_json(value: Any) -> dict[str, list[ImportRule]]:
    if not isinstance(value, dict):
        return {}
    rules: dict[str, list[ImportRule]] = {}
    for field_name, items in value.items():
        if not isinstance(items, list):
            continue
        parsed_items: list[ImportRule] = []
        for item in items:
            if isinstance(item, dict):
                parsed_items.append(ImportRule.from_dict(item))
        if parsed_items:
            rules[str(field_name)] = parsed_items
    return rules


def dump_rules_to_json(value: dict[str, list[ImportRule]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field_name, rules in value.items():
        payload[str(field_name)] = [rule.to_dict() for rule in rules]
    return payload


def to_plain_dict(rule: ImportRule | RuleStep) -> dict[str, Any]:
    data = asdict(rule)
    if isinstance(rule, RuleStep):
        data = rule.to_dict()
    return data
