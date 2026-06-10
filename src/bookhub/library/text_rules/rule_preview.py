from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from bookhub.library.models import DEFAULT_TEXT_PREVIEW_CHARS, TEXT_FILE_EXTENSION
from bookhub.library.text_rules.rule_models import ImportRule, RuleContext, RuleResult
from bookhub.library.text_rules.rule_engine import apply_rule_chain


@dataclass(slots=True)
class RulePreviewSample:
    file_path: str
    txt_first_line: str
    txt_head_text: str


def find_first_txt_file(root_path: str) -> str | None:
    root = Path(str(root_path or ""))
    if not root.exists() or not root.is_dir():
        return None

    for current_dir, dir_names, file_names in os.walk(root):
        dir_names[:] = sorted(dir_names)
        for name in sorted(file_names):
            candidate = Path(current_dir) / name
            if candidate.suffix.lower() == TEXT_FILE_EXTENSION:
                return str(candidate.resolve(strict=False))
    return None


def read_txt_preview_sample(file_path: str, preview_chars: int = DEFAULT_TEXT_PREVIEW_CHARS) -> RulePreviewSample | None:
    path = Path(str(file_path or ""))
    if not path.exists() or not path.is_file():
        return None

    safe_limit = max(100, int(preview_chars or DEFAULT_TEXT_PREVIEW_CHARS))
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            first_line = (handle.readline() or "").strip()
            handle.seek(0)
            head_text = handle.read(safe_limit + 1)[:safe_limit].strip()
    except OSError:
        return None

    return RulePreviewSample(
        file_path=str(path.resolve(strict=False)),
        txt_first_line=first_line,
        txt_head_text=head_text,
    )


def build_preview_context(file_path: str, txt_first_line: str, txt_head_text: str) -> RuleContext:
    return RuleContext(
        file_path=str(file_path or ""),
        txt_first_line=str(txt_first_line or ""),
        txt_head_text=str(txt_head_text or ""),
    )


def preview_rule_chain(rules: list[ImportRule], context: RuleContext) -> RuleResult:
    return apply_rule_chain(rules, context)
