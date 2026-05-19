from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QFontDatabase

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PROJECT_FONTS_DIR = PROJECT_ROOT / "src" / "fonts"
_FONT_SUFFIXES = {".ttf", ".otf", ".ttc"}


@dataclass(slots=True)
class FontScanResult:
    directory: Path
    directory_created: bool
    registered_families: list[str]
    failed_files: list[str]


@dataclass(slots=True)
class ResolvedFont:
    source: str
    family: str
    fallback_reason: str | None


def scan_project_fonts_and_register(fonts_dir: Path | None = None, *, ensure_dir: bool = False) -> FontScanResult:
    target_dir = fonts_dir or DEFAULT_PROJECT_FONTS_DIR
    created = False
    failed: list[str] = []
    if ensure_dir and not target_dir.exists():
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            created = True
        except OSError as exc:
            failed.append(f"{target_dir.name}: {exc}")
            return FontScanResult(
                directory=target_dir,
                directory_created=False,
                registered_families=[],
                failed_files=failed,
            )
    if not target_dir.exists():
        return FontScanResult(directory=target_dir, directory_created=False, registered_families=[], failed_files=[])

    try:
        font_files = sorted(
            [item for item in target_dir.iterdir() if item.is_file() and item.suffix.lower() in _FONT_SUFFIXES],
            key=lambda item: item.name.lower(),
        )
    except OSError as exc:
        failed.append(f"{target_dir.name}: {exc}")
        return FontScanResult(
            directory=target_dir,
            directory_created=created,
            registered_families=[],
            failed_files=failed,
        )
    families: set[str] = set()
    for font_file in font_files:
        font_id = QFontDatabase.addApplicationFont(str(font_file))
        if font_id < 0:
            failed.append(font_file.name)
            continue
        for family in QFontDatabase.applicationFontFamilies(font_id):
            value = str(family).strip()
            if value:
                families.add(value)

    return FontScanResult(
        directory=target_dir,
        directory_created=created,
        registered_families=sorted(families, key=lambda item: item.lower()),
        failed_files=failed,
    )


def resolve_effective_font(
    source: str,
    family: str,
    system_families: list[str],
    project_families: list[str],
) -> ResolvedFont:
    normalized_source = "project" if str(source).strip().lower() == "project" else "system"
    target = str(family or "").strip()
    system_pool = [item for item in system_families if str(item).strip()]
    project_pool = [item for item in project_families if str(item).strip()]

    if normalized_source == "project":
        if target and target in project_pool:
            return ResolvedFont(source="project", family=target, fallback_reason=None)
        if project_pool:
            reason = "missing_selected_project_font" if target else None
            return ResolvedFont(source="project", family=project_pool[0], fallback_reason=reason)
        normalized_source = "system"
        if target and target in system_pool:
            return ResolvedFont(source="system", family=target, fallback_reason="project_empty")
        if system_pool:
            return ResolvedFont(source="system", family=system_pool[0], fallback_reason="project_empty")
        return ResolvedFont(source="system", family="", fallback_reason="project_empty")

    if target and target in system_pool:
        return ResolvedFont(source="system", family=target, fallback_reason=None)
    if system_pool:
        reason = "missing_selected_system_font" if target else None
        return ResolvedFont(source="system", family=system_pool[0], fallback_reason=reason)
    return ResolvedFont(source="system", family="", fallback_reason="system_empty")
