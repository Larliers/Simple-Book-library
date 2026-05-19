from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = (PROJECT_ROOT / "src" / "bookhub" / "ui", PROJECT_ROOT / "src" / "bookhub" / "library")

PATTERNS = [
    r'QLabel\(\s*"',
    r'QPushButton\(\s*"',
    r'QCheckBox\(\s*"',
    r'QMessageBox\.\w+\(.*?"',
    r'setWindowTitle\(\s*"',
    r'addItem\(\s*"',
    r'addItems\(\s*\[',
]


def scan_file(path: Path) -> list[tuple[int, str]]:
    results: list[tuple[int, str]] = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        if "tr(" in line:
            continue
        if any(re.search(pattern, line) for pattern in PATTERNS):
            results.append((index, line.strip()))
    return results


def main() -> int:
    report_rows: list[str] = []
    total_hits = 0
    for base in SCAN_DIRS:
        if not base.exists():
            continue
        for file_path in sorted(base.rglob("*.py")):
            hits = scan_file(file_path)
            if not hits:
                continue
            report_rows.append(f"\n## {file_path.relative_to(PROJECT_ROOT).as_posix()}")
            for line_no, content in hits:
                total_hits += 1
                report_rows.append(f"- L{line_no}: {content}")

    print(f"[i18n-scan] hardcoded_candidates={total_hits}")
    if report_rows:
        print("\n".join(report_rows))
    else:
        print("[i18n-scan] no candidates found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

