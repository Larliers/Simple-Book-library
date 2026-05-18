from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bookhub.library.text_rules.rule_models import RuleStep

_BRACKET_PAIRS = {
    "[]": ("[", "]"),
    "【】": ("【", "】"),
    "()": ("(", ")"),
    "（）": ("（", "）"),
    "<>": ("<", ">"),
    "《》": ("《", "》"),
}


class StepError(ValueError):
    pass


def _index_from_step(params: dict[str, Any], key: str = "index") -> int:
    try:
        raw = int(params.get(key, 1))
    except (TypeError, ValueError) as exc:
        raise StepError(f"{key} must be an integer") from exc
    if raw <= 0:
        raise StepError(f"{key} must be >= 1")
    return raw


def _take_bracket_content(value: str, step: RuleStep) -> str:
    bracket = str(step.params.get("bracket") or "[]")
    pair = _BRACKET_PAIRS.get(bracket)
    if pair is None:
        raise StepError(f"Unsupported bracket pair: {bracket}")
    start, end = pair
    index = _index_from_step(step.params)
    pattern = rf"{re.escape(start)}(.*?){re.escape(end)}"
    matches = re.findall(pattern, value, flags=re.DOTALL)
    if index > len(matches):
        raise StepError(f"Bracket content index {index} out of range")
    return matches[index - 1]


def _take_after_text(value: str, step: RuleStep) -> str:
    needle = str(step.params.get("value") or "")
    if not needle:
        raise StepError("value is required")
    pos = value.find(needle)
    if pos < 0:
        raise StepError(f"Text not found: {needle}")
    line = value.splitlines()[0] if "\n" in value else value
    line_pos = line.find(needle)
    if line_pos < 0:
        return value[pos + len(needle) :]
    return line[line_pos + len(needle) :]


def _take_before_text(value: str, step: RuleStep) -> str:
    needle = str(step.params.get("value") or "")
    if not needle:
        raise StepError("value is required")
    pos = value.find(needle)
    if pos < 0:
        raise StepError(f"Text not found: {needle}")
    return value[:pos]


def _take_between_texts(value: str, step: RuleStep) -> str:
    start = str(step.params.get("start") or "")
    end = str(step.params.get("end") or "")
    if not start or not end:
        raise StepError("start and end are required")
    start_pos = value.find(start)
    if start_pos < 0:
        raise StepError(f"Start text not found: {start}")
    content_pos = start_pos + len(start)
    end_pos = value.find(end, content_pos)
    if end_pos < 0:
        raise StepError(f"End text not found: {end}")
    return value[content_pos:end_pos]


def _split_and_take(value: str, step: RuleStep) -> str:
    separator = str(step.params.get("separator") or "")
    if not separator:
        raise StepError("separator is required")
    index = _index_from_step(step.params)
    parts = value.split(separator)
    if index > len(parts):
        raise StepError(f"Split index {index} out of range")
    return parts[index - 1]


def _remove_prefix(value: str, step: RuleStep) -> str:
    prefix = str(step.params.get("value") or "")
    if not prefix:
        return value
    return value[len(prefix) :] if value.startswith(prefix) else value


def _remove_suffix(value: str, step: RuleStep) -> str:
    suffix = str(step.params.get("value") or "")
    if not suffix:
        return value
    return value[: -len(suffix)] if value.endswith(suffix) else value


def _replace_text(value: str, step: RuleStep) -> str:
    old = str(step.params.get("old") or "")
    new = str(step.params.get("new") or "")
    if not old:
        raise StepError("old is required")
    return value.replace(old, new)


def _regex_extract(value: str, step: RuleStep) -> str:
    pattern = str(step.params.get("pattern") or "")
    if not pattern:
        raise StepError("pattern is required")
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise StepError(f"Invalid regex pattern: {exc}") from exc

    match = compiled.search(value)
    if not match:
        raise StepError("Regex did not match")

    try:
        group = int(step.params.get("group", 1))
    except (TypeError, ValueError) as exc:
        raise StepError("group must be an integer") from exc

    try:
        return match.group(group)
    except IndexError as exc:
        raise StepError(f"Regex group {group} out of range") from exc


def apply_step(value: str, step: RuleStep) -> str:
    step_type = str(step.type or "").strip()

    if step_type == "trim":
        return value.strip()
    if step_type == "remove_extension":
        return Path(value).stem
    if step_type == "take_bracket_content":
        return _take_bracket_content(value, step)
    if step_type == "take_after_text":
        return _take_after_text(value, step)
    if step_type == "take_before_text":
        return _take_before_text(value, step)
    if step_type == "take_between_texts":
        return _take_between_texts(value, step)
    if step_type == "split_and_take":
        return _split_and_take(value, step)
    if step_type == "remove_prefix":
        return _remove_prefix(value, step)
    if step_type == "remove_suffix":
        return _remove_suffix(value, step)
    if step_type == "replace_text":
        return _replace_text(value, step)
    if step_type == "regex_extract":
        return _regex_extract(value, step)

    raise StepError(f"Unsupported step type: {step_type}")
