from __future__ import annotations

from pathlib import Path

from bookhub.library.text_rules.rule_models import RuleContext


_SOURCE_VALUES = {
    "filename",
    "stem",
    "full_path",
    "parent_folder",
    "txt_first_line",
    "txt_head_text",
}


def resolve_source(source: str, context: RuleContext) -> str:
    source_name = str(source or "").strip()
    if source_name not in _SOURCE_VALUES:
        raise ValueError(f"Unsupported source: {source_name}")

    file_path = Path(context.file_path)
    if source_name == "filename":
        return file_path.name
    if source_name == "stem":
        return file_path.stem
    if source_name == "full_path":
        return str(file_path)
    if source_name == "parent_folder":
        return file_path.parent.name
    if source_name == "txt_first_line":
        return context.txt_first_line or ""
    if source_name == "txt_head_text":
        return context.txt_head_text or ""
    return ""
