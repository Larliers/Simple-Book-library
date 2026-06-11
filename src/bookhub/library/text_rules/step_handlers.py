from __future__ import annotations

import re
from dataclasses import dataclass
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


@dataclass(slots=True)
class StepOutput:
    value: str
    warning_message: str | None = None


def _index_from_step(params: dict[str, Any], key: str = "index") -> int:
    try:
        raw = int(params.get(key, 1))
    except (TypeError, ValueError) as exc:
        raise StepError(f"{key} must be an integer") from exc
    if raw <= 0:
        raise StepError(f"{key} must be >= 1")
    return raw


def _positive_int_from_step(params: dict[str, Any], key: str, default: int = 1) -> int:
    try:
        raw = int(params.get(key, default))
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


def _take_line(value: str, step: RuleStep) -> str:
    index = _index_from_step(step.params)
    lines = value.splitlines()
    if index > len(lines):
        raise StepError(f"Line index {index} out of range")
    return lines[index - 1]


def _take_first_lines(value: str, step: RuleStep) -> str:
    count = _positive_int_from_step(step.params, "count")
    return "\n".join(value.splitlines()[:count])


def _remove_last_lines(value: str, step: RuleStep) -> str:
    count = _positive_int_from_step(step.params, "count")
    lines = value.splitlines()
    if count >= len(lines):
        return ""
    return "\n".join(lines[:-count])


def _take_line_range(value: str, step: RuleStep) -> StepOutput:
    start = _positive_int_from_step(step.params, "start")
    end = _positive_int_from_step(step.params, "end")
    if start > end:
        raise StepError("start must be <= end")

    lines = value.splitlines()
    total = len(lines)
    if start > total:
        raise StepError(f"Line start {start} out of range")

    effective_end = min(end, total)
    selected = "\n".join(lines[start - 1 : effective_end])
    warning = None
    if end > total:
        warning = f"Line end {end} out of range; truncated to line {total}"
    return StepOutput(value=selected, warning_message=warning)


def _line_index_at_position(value: str, position: int) -> int:
    return value[:position].count("\n")


def _take_around_marker(value: str, step: RuleStep, *, after: bool) -> str:
    marker = str(step.params.get("value") or "")
    if not marker:
        raise StepError("value is required")
    marker_pos = value.find(marker)
    if marker_pos < 0:
        raise StepError(f"Text not found: {marker}")

    scope = str(step.params.get("scope") or "all").strip()
    if scope not in {"all", "count"}:
        raise StepError(f"Unsupported scope: {scope}")
    unit = str(step.params.get("unit") or "line").strip()
    if unit not in {"line", "char"}:
        raise StepError(f"Unsupported unit: {unit}")

    if unit == "char":
        text = value[marker_pos + len(marker) :] if after else value[:marker_pos]
        if scope == "all":
            return text
        count = _positive_int_from_step(step.params, "count")
        return text[:count] if after else text[-count:]

    lines = value.splitlines()
    marker_line_index = _line_index_at_position(value, marker_pos)
    if after:
        selected = lines[marker_line_index + 1 :]
        if scope == "count":
            selected = selected[: _positive_int_from_step(step.params, "count")]
        return "\n".join(selected)

    selected = lines[:marker_line_index]
    if scope == "count":
        selected = selected[-_positive_int_from_step(step.params, "count") :]
    return "\n".join(selected)


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


def _bool_from_step(params: dict[str, Any], key: str, default: bool = False) -> bool:
    value = params.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _join_separator(params: dict[str, Any]) -> str:
    join = str(params.get("join") or "newline").strip()
    if join == "newline":
        return "\n"
    if join == "comma":
        return ","
    if join == "semicolon":
        return ";"
    if join == "custom":
        return str(params.get("custom_separator") or "")
    raise StepError(f"Unsupported join: {join}")


def _loop_lines(value: str, step: RuleStep) -> str:
    pattern = str(step.params.get("pattern") or "")
    if not pattern:
        raise StepError("pattern is required")
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise StepError(f"Invalid regex pattern: {exc}") from exc

    try:
        group = int(step.params.get("group", 1))
    except (TypeError, ValueError) as exc:
        raise StepError("group must be an integer") from exc

    skip_failed = _bool_from_step(step.params, "skip_failed", True)
    extracted: list[str] = []
    for line_number, raw_line in enumerate(value.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        match = compiled.search(line)
        if not match:
            if skip_failed:
                continue
            raise StepError(f"Line {line_number} did not match")
        try:
            item = match.group(group)
        except IndexError as exc:
            raise StepError(f"Regex group {group} out of range") from exc
        item = item.strip()
        if item:
            extracted.append(item)

    if not extracted:
        raise StepError("No lines matched")
    return _join_separator(step.params).join(extracted)


def apply_step(value: str, step: RuleStep) -> str | StepOutput:
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
    if step_type == "take_line":
        return _take_line(value, step)
    if step_type == "take_first_lines":
        return _take_first_lines(value, step)
    if step_type == "remove_last_lines":
        return _remove_last_lines(value, step)
    if step_type == "take_line_range":
        return _take_line_range(value, step)
    if step_type == "take_before_marker":
        return _take_around_marker(value, step, after=False)
    if step_type == "take_after_marker":
        return _take_around_marker(value, step, after=True)
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
    if step_type == "loop_lines":
        return _loop_lines(value, step)

    raise StepError(f"Unsupported step type: {step_type}")
