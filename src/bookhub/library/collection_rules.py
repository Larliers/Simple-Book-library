from __future__ import annotations

from pathlib import Path
from typing import Any


COLLECTION_RULE_VERSION = 1
COLLECTION_RULE_MATCH_MODES = frozenset({"all", "any"})
COLLECTION_RULE_OPERATORS = frozenset(
    {"contains", "not_contains", "starts_with", "ends_with", "equals"}
)


def normalize_collection_rule(raw_rule: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw_rule, dict):
        raise ValueError("invalid_rule")
    try:
        version = int(raw_rule.get("version", COLLECTION_RULE_VERSION))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_rule_version") from exc
    if version != COLLECTION_RULE_VERSION:
        raise ValueError("invalid_rule_version")
    match_mode = str(raw_rule.get("matchMode") or "all").strip().lower()
    if match_mode not in COLLECTION_RULE_MATCH_MODES:
        raise ValueError("invalid_match_mode")
    raw_conditions = raw_rule.get("conditions", [])
    if not isinstance(raw_conditions, list):
        raise ValueError("invalid_conditions")
    conditions: list[dict[str, Any]] = []
    for raw_condition in raw_conditions:
        if not isinstance(raw_condition, dict):
            raise ValueError("invalid_condition")
        operator = str(raw_condition.get("operator") or "").strip().lower()
        if operator not in COLLECTION_RULE_OPERATORS:
            raise ValueError("invalid_operator")
        value = str(raw_condition.get("value") or "").strip()
        case_sensitive = raw_condition.get("caseSensitive", False)
        if not isinstance(case_sensitive, bool):
            raise ValueError("invalid_case_sensitive")
        conditions.append(
            {
                "operator": operator,
                "value": value,
                "caseSensitive": case_sensitive,
            }
        )
    return {
        "version": COLLECTION_RULE_VERSION,
        "matchMode": match_mode,
        "conditions": conditions,
    }


def validate_collection_rule(raw_rule: dict[str, Any] | None, *, enabled: bool) -> dict[str, Any]:
    rule = normalize_collection_rule(raw_rule)
    if enabled and not any(condition["value"] for condition in rule["conditions"]):
        raise ValueError("empty_conditions")
    if enabled and any(not condition["value"] for condition in rule["conditions"]):
        raise ValueError("empty_condition")
    return rule


def _matches_condition(source_name: str, condition: dict[str, Any]) -> bool:
    value = str(condition["value"])
    if not value:
        return False
    candidate = str(source_name)
    if not bool(condition["caseSensitive"]):
        candidate = candidate.casefold()
        value = value.casefold()
    operator = str(condition["operator"])
    if operator == "contains":
        return value in candidate
    if operator == "not_contains":
        return value not in candidate
    if operator == "starts_with":
        return candidate.startswith(value)
    if operator == "ends_with":
        return candidate.endswith(value)
    return candidate == value


def matches_collection_rule(source_name: str, rule: dict[str, Any]) -> bool:
    normalized = normalize_collection_rule(rule)
    conditions = normalized["conditions"]
    if not conditions or any(not condition["value"] for condition in conditions):
        return False
    results = [_matches_condition(source_name, condition) for condition in conditions]
    return all(results) if normalized["matchMode"] == "all" else any(results)


def source_name_for_record(record: dict[str, Any], kind: str) -> str:
    """Return the stable source basename used by collection rules."""
    kind_value = str(kind or "").strip().lower()
    path = Path(str(record.get("path") or ""))
    if kind_value == "comic":
        name = path.name or str(record.get("title") or "")
        return name[:-4] if name.casefold().endswith(".cbz") else name

    name = str(record.get("file_name") or path.name)
    extension = str(record.get("extension") or "")
    if extension and extension != ".imgfolder" and name.casefold().endswith(extension.casefold()):
        return name[: -len(extension)]
    return name
