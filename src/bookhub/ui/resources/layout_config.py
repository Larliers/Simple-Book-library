from __future__ import annotations

from dataclasses import dataclass

CARD_SPACING_MIN = 6
CARD_SPACING_MAX = 40
DEFAULT_CARD_SPACING = 14
TOPBAR_SEARCH_FONT_SIZE_MIN = 12
TOPBAR_SEARCH_FONT_SIZE_MAX = 20
DEFAULT_TOPBAR_SEARCH_FONT_SIZE = 15


def normalize_card_spacing(value: int | str | None) -> int:
    try:
        spacing = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        spacing = DEFAULT_CARD_SPACING
    return min(CARD_SPACING_MAX, max(CARD_SPACING_MIN, spacing))


def normalize_topbar_search_font_size(value: int | str | None) -> int:
    try:
        size = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        size = DEFAULT_TOPBAR_SEARCH_FONT_SIZE
    return min(TOPBAR_SEARCH_FONT_SIZE_MAX, max(TOPBAR_SEARCH_FONT_SIZE_MIN, size))


@dataclass
class UiLayoutConfig:
    sidebar_width: int = 240
    topbar_height: int = 52
    card_width: int = 176
    card_inner_padding: int = 8
    card_spacing: int = DEFAULT_CARD_SPACING
    cover_aspect_width: int = 2
    cover_aspect_height: int = 3
    add_card_height: int = 264
    grid_left_inset: int = 12
    topbar_search_font_size: int = DEFAULT_TOPBAR_SEARCH_FONT_SIZE

    def cover_size(self) -> tuple[int, int]:
        cover_width = self.card_width - self.card_inner_padding * 2
        cover_height = int(cover_width * self.cover_aspect_height / self.cover_aspect_width)
        return cover_width, cover_height

    def set_card_spacing(self, spacing: int | str | None) -> None:
        self.card_spacing = normalize_card_spacing(spacing)

    def set_topbar_search_font_size(self, size: int | str | None) -> None:
        self.topbar_search_font_size = normalize_topbar_search_font_size(size)


UI_LAYOUT = UiLayoutConfig()
