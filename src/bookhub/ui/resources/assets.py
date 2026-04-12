from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap


ASSETS_DIR = Path(__file__).resolve().parents[3] / "assets"
ICONS_DIR = ASSETS_DIR / "icons"


def icon_path(name: str) -> Path:
    return ICONS_DIR / name


def load_icon(name: str) -> QIcon:
    path = icon_path(name)
    if path.exists():
        return QIcon(str(path))
    return QIcon()


def load_pixmap(name: str, width: int, height: int) -> QPixmap:
    path = icon_path(name)
    if path.exists():
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            return pixmap.scaled(width, height)
    return QPixmap()
