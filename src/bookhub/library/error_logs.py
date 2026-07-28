from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bookhub.app_paths import default_log_dir


def get_log_dir() -> Path:
    log_dir = default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_today_log_path() -> Path:
    return get_log_dir() / f"{datetime.now().strftime('%Y%m%d')}.txt"


def _is_ymd_txt_name(name: str) -> bool:
    if not name.endswith(".txt"):
        return False
    stem = name[:-4]
    return len(stem) == 8 and stem.isdigit()


def get_latest_log_path() -> Path | None:
    log_dir = get_log_dir()
    files = [p for p in log_dir.iterdir() if p.is_file() and _is_ymd_txt_name(p.name)]
    if not files:
        return None
    files.sort(key=lambda p: p.stem, reverse=True)
    return files[0]


def read_latest_log_text() -> str:
    latest = get_latest_log_path()
    if latest is None:
        return ""
    try:
        return latest.read_text(encoding="utf-8")
    except OSError:
        return ""


def has_conflict_in_latest(conflict_text: str) -> bool:
    needle = str(conflict_text or "").strip()
    if not needle:
        return False
    latest_content = read_latest_log_text()
    return needle in latest_content


def append_conflict_if_new(conflict_text: str) -> bool:
    text = str(conflict_text or "").strip()
    if not text:
        return False

    if has_conflict_in_latest(text):
        return False

    log_path = get_today_log_path()
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}\n"
    try:
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line)
        return True
    except OSError:
        return False


def append_scan_log(text: str, dedupe_latest: bool = False) -> bool:
    line_text = str(text or "").strip()
    if not line_text:
        return False
    if dedupe_latest and has_conflict_in_latest(line_text):
        return False
    log_path = get_today_log_path()
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {line_text}\n"
    try:
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line)
        return True
    except OSError:
        return False
