"""Authoritative UI catalog for Text Rules (sources, steps, templates, help)."""

from __future__ import annotations

from typing import Any

from bookhub.i18n import tr

_SOURCE_IDS = ("filename", "stem", "full_path", "parent_folder", "txt_first_line", "txt_head_text")

FIELDS = ("title", "author", "series", "tag")

STEP_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("clean", ("trim", "normalize_spaces", "remove_all_spaces", "normalize_punctuation")),
    (
        "delete",
        (
            "remove_prefix",
            "remove_suffix",
            "remove_text",
            "remove_regex",
            "remove_bracket_content",
            "remove_brackets_keep_content",
            "replace_text",
        ),
    ),
    (
        "extract",
        (
            "take_after_text",
            "take_before_text",
            "take_before_last_text",
            "take_after_last_text",
            "take_between_texts",
            "take_before_marker",
            "take_after_marker",
        ),
    ),
    ("line", ("take_line", "take_first_lines", "take_line_range", "remove_first_lines", "remove_last_lines", "loop_lines")),
    (
        "bracket",
        (
            "take_bracket_content",
            "take_last_bracket_content",
            "take_all_bracket_contents",
            "remove_nth_bracket",
            "keep_only_bracket_type",
        ),
    ),
    ("split", ("split_and_take", "split_multi_and_take", "split_and_join_range")),
    ("filename", ("remove_extension",)),
    ("regex", ("regex_extract",)),
)

NO_PARAM_STEP_TYPES = frozenset(
    {"trim", "remove_extension", "normalize_spaces", "remove_all_spaces", "normalize_punctuation"}
)

_PARAM_WIDGETS: dict[str, str] = {
    "value": "text",
    "start": "text",
    "end": "text",
    "index": "number",
    "count": "number",
    "scope": "select:all|count",
    "unit": "select:line|char",
    "separator": "text",
    "separators": "textarea",
    "joiner": "text",
    "bracket": "text",
    "bracket_scope": "select:outer|all|inner",
    "text": "text",
    "case_sensitive": "bool",
    "pattern": "text",
    "bracket_type": "select:all|round|square|curly|angle|corner|book",
    "join": "select:newline|comma|semicolon|custom",
    "custom_separator": "text",
    "old": "text",
    "new": "text",
    "group": "number",
    "skip_failed": "bool",
}


def _safe_int(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _safe_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def param_keys_for_step_type(step_type: str) -> tuple[str, ...]:
    if step_type in NO_PARAM_STEP_TYPES:
        return ()
    if step_type in {
        "take_after_text",
        "take_before_text",
        "take_before_last_text",
        "take_after_last_text",
        "remove_prefix",
        "remove_suffix",
    }:
        return ("value",)
    if step_type == "take_between_texts":
        return ("start", "end")
    if step_type == "take_line":
        return ("index",)
    if step_type in {"take_first_lines", "remove_last_lines", "remove_first_lines"}:
        return ("count",)
    if step_type == "take_line_range":
        return ("start", "end")
    if step_type in {"take_before_marker", "take_after_marker"}:
        return ("value", "scope", "unit", "count")
    if step_type == "split_and_take":
        return ("separator", "index")
    if step_type == "split_multi_and_take":
        return ("separators", "index")
    if step_type == "split_and_join_range":
        return ("separator", "start", "end", "joiner")
    if step_type == "take_bracket_content":
        return ("bracket", "bracket_scope", "index")
    if step_type == "remove_text":
        return ("text", "case_sensitive")
    if step_type == "remove_regex":
        return ("pattern",)
    if step_type in {"remove_bracket_content", "remove_brackets_keep_content", "take_last_bracket_content"}:
        return ("bracket_type", "bracket_scope")
    if step_type in {"take_all_bracket_contents", "keep_only_bracket_type"}:
        return ("bracket_type", "bracket_scope", "join", "custom_separator")
    if step_type == "remove_nth_bracket":
        return ("bracket_type", "bracket_scope", "index")
    if step_type == "replace_text":
        return ("old", "new")
    if step_type == "regex_extract":
        return ("pattern", "group")
    if step_type == "loop_lines":
        return ("pattern", "group", "join", "custom_separator", "skip_failed")
    return ()


def default_params_for_step_type(step_type: str, old_params: dict[str, Any] | None = None) -> dict[str, Any]:
    old = old_params or {}
    keys = param_keys_for_step_type(step_type)
    if not keys:
        return {}
    seeded = _seed_defaults(step_type, old)
    return {k: seeded[k] for k in keys if k in seeded}


def _seed_defaults(step_type: str, old: dict[str, Any]) -> dict[str, Any]:
    if step_type in {
        "take_after_text",
        "take_before_text",
        "take_before_last_text",
        "take_after_last_text",
        "remove_prefix",
        "remove_suffix",
    }:
        return {"value": str(old.get("value") or "")}
    if step_type == "take_between_texts":
        return {"start": str(old.get("start") or ""), "end": str(old.get("end") or "")}
    if step_type == "take_line":
        return {"index": _safe_int(old.get("index"), 1)}
    if step_type in {"take_first_lines", "remove_last_lines", "remove_first_lines"}:
        return {"count": _safe_int(old.get("count"), 1)}
    if step_type == "take_line_range":
        return {"start": _safe_int(old.get("start"), 1), "end": _safe_int(old.get("end"), 1)}
    if step_type in {"take_before_marker", "take_after_marker"}:
        return {
            "value": str(old.get("value") or ""),
            "scope": str(old.get("scope") or "all"),
            "unit": str(old.get("unit") or "line"),
            "count": _safe_int(old.get("count"), 1),
        }
    if step_type == "split_and_take":
        return {"separator": str(old.get("separator") or ""), "index": _safe_int(old.get("index"), 1)}
    if step_type == "split_multi_and_take":
        return {
            "separators": str(old.get("separators") or "-\n_\n／\n/"),
            "index": _safe_int(old.get("index"), 1),
        }
    if step_type == "split_and_join_range":
        separator = str(old.get("separator") or "")
        return {
            "separator": separator,
            "start": _safe_int(old.get("start"), 1),
            "end": _safe_int(old.get("end"), 1),
            "joiner": str(old.get("joiner") if old.get("joiner") is not None else separator),
        }
    if step_type == "take_bracket_content":
        return {
            "bracket": str(old.get("bracket") or "[]"),
            "bracket_scope": str(old.get("bracket_scope") or "outer"),
            "index": _safe_int(old.get("index"), 1),
        }
    if step_type == "remove_text":
        return {
            "text": str(old.get("text") or old.get("value") or ""),
            "case_sensitive": _safe_bool(old.get("case_sensitive"), True),
        }
    if step_type == "remove_regex":
        return {"pattern": str(old.get("pattern") or "")}
    if step_type in {"remove_bracket_content", "remove_brackets_keep_content", "take_last_bracket_content"}:
        return {
            "bracket_type": str(old.get("bracket_type") or "all"),
            "bracket_scope": str(old.get("bracket_scope") or "outer"),
        }
    if step_type in {"take_all_bracket_contents", "keep_only_bracket_type"}:
        return {
            "bracket_type": str(old.get("bracket_type") or "all"),
            "bracket_scope": str(old.get("bracket_scope") or "outer"),
            "join": str(old.get("join") or "newline"),
            "custom_separator": str(old.get("custom_separator") or ""),
        }
    if step_type == "remove_nth_bracket":
        return {
            "bracket_type": str(old.get("bracket_type") or "all"),
            "bracket_scope": str(old.get("bracket_scope") or "outer"),
            "index": _safe_int(old.get("index"), 1),
        }
    if step_type == "replace_text":
        return {"old": str(old.get("old") or ""), "new": str(old.get("new") or "")}
    if step_type == "regex_extract":
        return {"pattern": str(old.get("pattern") or ""), "group": _safe_int(old.get("group"), 1)}
    if step_type == "loop_lines":
        return {
            "pattern": str(old.get("pattern") or r"#\[(.+?)\]"),
            "group": _safe_int(old.get("group"), 1),
            "join": str(old.get("join") or "newline"),
            "custom_separator": str(old.get("custom_separator") or ""),
            "skip_failed": _safe_bool(old.get("skip_failed"), True),
        }
    return {}


def category_for_step_type(step_type: str) -> str:
    for category, steps in STEP_CATEGORIES:
        if step_type in steps:
            return category
    return STEP_CATEGORIES[0][0]


def field_label(code: str) -> str:
    mapping = {
        "title": tr("text.rules.field.title", "Title"),
        "author": tr("text.rules.field.author", "Author"),
        "series": tr("text.rules.field.series", "Series"),
        "tag": tr("text.rules.field.tag", "Tag"),
    }
    return mapping.get(code, code)


def source_label(code: str) -> str:
    mapping = {
        "filename": tr("text.rules.source.filename", "File name"),
        "stem": tr("text.rules.source.stem", "Stem (without extension)"),
        "full_path": tr("text.rules.source.full_path", "Full path"),
        "parent_folder": tr("text.rules.source.parent_folder", "Parent folder"),
        "txt_first_line": tr("text.rules.source.txt_first_line", "TXT first line"),
        "txt_head_text": tr("text.rules.source.txt_head_text", "TXT head text"),
    }
    return mapping.get(code, code)


def step_type_label(code: str) -> str:
    mapping = {
        "trim": tr("text.rules.step.trim", "Trim"),
        "normalize_spaces": tr("text.rules.step.normalize_spaces", "Normalize spaces"),
        "remove_all_spaces": tr("text.rules.step.remove_all_spaces", "Remove all spaces"),
        "normalize_punctuation": tr("text.rules.step.normalize_punctuation", "Normalize punctuation"),
        "remove_extension": tr("text.rules.step.remove_extension", "Remove extension"),
        "take_bracket_content": tr("text.rules.step.take_bracket_content", "Take bracket content"),
        "take_after_text": tr("text.rules.step.take_after_text", "Take after text"),
        "take_before_text": tr("text.rules.step.take_before_text", "Take before text"),
        "take_before_last_text": tr("text.rules.step.take_before_last_text", "Take before last text"),
        "take_after_last_text": tr("text.rules.step.take_after_last_text", "Take after last text"),
        "take_between_texts": tr("text.rules.step.take_between_texts", "Take between texts"),
        "take_line": tr("text.rules.step.take_line", "Take line N"),
        "take_first_lines": tr("text.rules.step.take_first_lines", "Take first N lines"),
        "remove_last_lines": tr("text.rules.step.remove_last_lines", "Remove last N lines"),
        "remove_first_lines": tr("text.rules.step.remove_first_lines", "Remove first N lines"),
        "take_line_range": tr("text.rules.step.take_line_range", "Take line N-M"),
        "take_before_marker": tr("text.rules.step.take_before_marker", "Take before marker"),
        "take_after_marker": tr("text.rules.step.take_after_marker", "Take after marker"),
        "split_and_take": tr("text.rules.step.split_and_take", "Split and take"),
        "split_multi_and_take": tr("text.rules.step.split_multi_and_take", "Split multi and take"),
        "split_and_join_range": tr("text.rules.step.split_and_join_range", "Split and join range"),
        "remove_prefix": tr("text.rules.step.remove_prefix", "Remove prefix"),
        "remove_suffix": tr("text.rules.step.remove_suffix", "Remove suffix"),
        "remove_text": tr("text.rules.step.remove_text", "Remove text"),
        "remove_regex": tr("text.rules.step.remove_regex", "Remove regex"),
        "remove_bracket_content": tr("text.rules.step.remove_bracket_content", "Remove bracket content"),
        "remove_brackets_keep_content": tr(
            "text.rules.step.remove_brackets_keep_content", "Remove brackets keep content"
        ),
        "take_last_bracket_content": tr("text.rules.step.take_last_bracket_content", "Take last bracket content"),
        "take_all_bracket_contents": tr("text.rules.step.take_all_bracket_contents", "Take all bracket contents"),
        "remove_nth_bracket": tr("text.rules.step.remove_nth_bracket", "Remove Nth bracket"),
        "keep_only_bracket_type": tr("text.rules.step.keep_only_bracket_type", "Keep only bracket type"),
        "replace_text": tr("text.rules.step.replace_text", "Replace text"),
        "regex_extract": tr("text.rules.step.regex_extract", "Regex extract"),
        "loop_lines": tr("text.rules.step.loop_lines", "Loop lines"),
    }
    return mapping.get(code, code)


def category_label(code: str) -> str:
    mapping = {
        "clean": tr("text.rules.category.clean", "Text cleanup"),
        "delete": tr("text.rules.category.delete", "Text delete"),
        "extract": tr("text.rules.category.extract", "Text extract"),
        "line": tr("text.rules.category.line", "Line processing"),
        "bracket": tr("text.rules.category.bracket", "Bracket processing"),
        "split": tr("text.rules.category.split", "Split processing"),
        "filename": tr("text.rules.category.filename", "File name"),
        "regex": tr("text.rules.category.regex", "Advanced regex"),
    }
    return mapping.get(code, code)


def builtin_templates() -> list[dict[str, Any]]:
    return [
        {
            "id": "title_t_marker",
            "label": tr("text.rules.template.title_t", "Title after T"),
            "field": "title",
            "rule": {
                "field": "title",
                "source": "txt_first_line",
                "steps": [{"type": "take_after_text", "value": "T"}, {"type": "trim"}],
            },
        },
        {
            "id": "author_corner_bracket",
            "label": tr("text.rules.template.author_bracket", "Author from 【】"),
            "field": "author",
            "rule": {
                "field": "author",
                "source": "filename",
                "steps": [
                    {"type": "take_bracket_content", "bracket": "【】", "bracket_scope": "outer", "index": 1},
                    {"type": "trim"},
                ],
            },
        },
        {
            "id": "fallback_stem",
            "label": tr("text.rules.template.fallback_stem", "Fallback stem"),
            "field": "title",
            "rule": {"field": "title", "source": "stem", "steps": [{"type": "trim"}]},
        },
    ]


def regex_examples() -> list[dict[str, str]]:
    return [
        {"id": "date", "purpose": "Extract date", "sample": "2026年06月11日", "regex": r"(\d{4})年(\d{1,2})月(\d{1,2})日", "result": "g1=2026 g2=06 g3=11"},
        {"id": "year", "purpose": "Extract year", "sample": "发布于 2026", "regex": r"(\d{4})", "result": "g1=2026"},
        {"id": "book_title", "purpose": "Book title 《》", "sample": "《异世界勇者物语》", "regex": r"《(.+?)》", "result": "g1=异世界勇者物语"},
        {"id": "square_tag", "purpose": "Square bracket", "sample": "[奇幻]", "regex": r"\[(.+?)\]", "result": "g1=奇幻"},
        {"id": "hash_tag", "purpose": "#[tag]", "sample": "#[奇幻]", "regex": r"#\[(.+?)\]", "result": "g1=奇幻"},
        {"id": "author", "purpose": "Author label", "sample": "作者：山田", "regex": r"作者[:：]\s*(.+)", "result": "g1=山田"},
        {"id": "dash_parts", "purpose": "Dash parts", "sample": "标题 - 作者 - 完结", "regex": r"^(.+?)\s*-\s*(.+?)\s*-\s*(.+)$", "result": "g1/g2/g3"},
        {"id": "volume", "purpose": "Chapter number", "sample": "第12章", "regex": r"[第卷章]\s*(\d+)", "result": "g1=12"},
    ]


def help_sections() -> list[dict[str, Any]]:
    return [
        {
            "title": tr("text.rules.help.section.quick_start", "Quick Start"),
            "lines": [
                tr("text.rules.help.quick.1", "1. Select target field (title / author / series / tag)."),
                tr("text.rules.help.quick.2", "2. Add a rule and pick a source."),
                tr("text.rules.help.quick.3", "3. Add steps from top to bottom, then save."),
            ],
        },
        {
            "title": tr("text.rules.help.section.sources", "Source Definitions"),
            "lines": [
                tr("text.rules.help.source.filename", "- filename: file name without directory"),
                tr("text.rules.help.source.stem", "- stem: file name without extension"),
                tr("text.rules.help.source.full_path", "- full_path: full path string"),
                tr("text.rules.help.source.parent_folder", "- parent_folder: direct parent folder name"),
                tr("text.rules.help.source.txt_first_line", "- txt_first_line: first line of TXT"),
                tr("text.rules.help.source.txt_head_text", "- txt_head_text: head text snippet of TXT"),
            ],
        },
        {
            "title": tr("text.rules.help.section.steps", "Common Steps"),
            "lines": [
                tr("text.rules.help.step.trim", "- trim: remove leading/trailing spaces"),
                tr("text.rules.help.step.take_after_text", "- take_after_text: keep content after marker"),
                tr("text.rules.help.step.take_bracket_content", "- take_bracket_content: extract Nth bracket content"),
                tr("text.rules.help.step.regex_extract", "- regex_extract: capture group from regex"),
            ],
        },
    ]


def describe_step_catalog() -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for category, codes in STEP_CATEGORIES:
        for code in codes:
            keys = param_keys_for_step_type(code)
            steps.append(
                {
                    "type": code,
                    "label": step_type_label(code),
                    "category": category,
                    "categoryLabel": category_label(category),
                    "params": [
                        {
                            "key": key,
                            "widget": _PARAM_WIDGETS.get(key, "text"),
                        }
                        for key in keys
                    ],
                    "defaults": default_params_for_step_type(code, {}),
                }
            )
    sources = [{"id": sid, "label": source_label(sid)} for sid in _SOURCE_IDS]
    fields = [{"id": fid, "label": field_label(fid)} for fid in FIELDS]
    categories = [{"id": cid, "label": category_label(cid)} for cid, _ in STEP_CATEGORIES]
    return {
        "fields": fields,
        "sources": sources,
        "categories": categories,
        "steps": steps,
        "templates": builtin_templates(),
        "regexExamples": regex_examples(),
        "helpSections": help_sections(),
    }
