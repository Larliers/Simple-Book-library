from __future__ import annotations

import json
from pathlib import Path
from typing import Any


COLLECTION_RULE_VERSION = 2
COLLECTION_RULE_MATCH_MODES = frozenset({"all", "any"})
COLLECTION_RULE_OPERATORS = frozenset(
    {"contains", "not_contains", "starts_with", "ends_with", "equals"}
)
COLLECTION_RULE_FIELDS = {
    "book": ("source_name", "title", "author", "publisher", "language", "tags"),
    "text_novel": ("source_name", "title", "author", "publisher", "language", "tags", "series"),
    "comic": ("source_name", "title", "tags"),
}


def available_collection_rule_fields(kind: str) -> tuple[str, ...]:
    try:
        return COLLECTION_RULE_FIELDS[kind]
    except KeyError as exc:
        raise ValueError("invalid_collection_kind") from exc


def normalize_collection_rule(raw_rule: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw_rule, dict):
        raise ValueError("invalid_rule")
    try:
        version = int(raw_rule.get("version", COLLECTION_RULE_VERSION))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_rule_version") from exc
    if version not in {1, COLLECTION_RULE_VERSION}:
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
        field = "source_name" if version == 1 else str(raw_condition.get("field") or "").strip().lower()
        if field not in {item for fields in COLLECTION_RULE_FIELDS.values() for item in fields}:
            raise ValueError("invalid_field")
        value = str(raw_condition.get("value") or "").strip()
        case_sensitive = raw_condition.get("caseSensitive", False)
        if not isinstance(case_sensitive, bool):
            raise ValueError("invalid_case_sensitive")
        conditions.append(
            {
                "field": field,
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


def validate_collection_rule(
    raw_rule: dict[str, Any] | None, *, enabled: bool, kind: str | None = None,
) -> dict[str, Any]:
    rule = normalize_collection_rule(raw_rule)
    if kind is not None:
        allowed = available_collection_rule_fields(kind)
        if any(condition["field"] not in allowed for condition in rule["conditions"]):
            raise ValueError("invalid_field")
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
    if not candidate:
        return False
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


def _condition_values(record: dict[str, Any], kind: str, field: str) -> list[str]:
    if field == "source_name":
        return [source_name_for_record(record, kind)]
    if field != "tags":
        return [str(record.get(field) or "")]
    raw_tags = record.get("tags", record.get("tags_json", []))
    if isinstance(raw_tags, str):
        try:
            raw_tags = json.loads(raw_tags)
        except (TypeError, ValueError):
            raw_tags = []
    return [str(tag) for tag in raw_tags if isinstance(tag, str) and tag] if isinstance(raw_tags, list) else []


def matches_collection_rule(
    source_name: str | dict[str, Any], rule: dict[str, Any], *, kind: str = "book",
) -> bool:
    normalized = normalize_collection_rule(rule)
    conditions = normalized["conditions"]
    if not conditions or any(not condition["value"] for condition in conditions):
        return False
    record = source_name if isinstance(source_name, dict) else {"file_name": source_name}
    results = []
    for condition in conditions:
        values = [value for value in _condition_values(record, kind, condition["field"]) if value]
        if not values:
            results.append(False)
        elif condition["field"] == "tags" and condition["operator"] == "not_contains":
            results.append(all(_matches_condition(value, condition) for value in values))
        else:
            results.append(any(_matches_condition(value, condition) for value in values))
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
