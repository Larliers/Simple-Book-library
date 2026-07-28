"""Application root and default runtime data paths (dev vs packaged)."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """Return True when running as a packaged executable (Nuitka/PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def dev_project_root() -> Path:
    """Repository root when running from source."""
    return Path(__file__).resolve().parents[2]


def app_root() -> Path:
    """Directory containing the app entrypoint (repo root in dev, exe dir when frozen)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return dev_project_root()


def default_preview_dir() -> Path:
    return (app_root() / "img_preview").resolve(strict=False)


def default_sql_dir() -> Path:
    if is_frozen():
        return (app_root() / "sql").resolve(strict=False)
    return (dev_project_root() / "src" / "sql").resolve(strict=False)


def default_db_path() -> Path:
    return default_sql_dir() / "library.db"


def default_scan_report_path() -> Path:
    return default_sql_dir() / "scan_report.json"


def default_log_dir() -> Path:
    if is_frozen():
        return (app_root() / "Scan_error_logs").resolve(strict=False)
    return (dev_project_root() / "src" / "Scan_error_logs").resolve(strict=False)
