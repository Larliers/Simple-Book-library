from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UiLayoutConfig:
    sidebar_width: int = 240
    topbar_height: int = 52
    card_width: int = 176
    card_inner_padding: int = 8
    card_spacing: int = 14
    cover_aspect_width: int = 2
    cover_aspect_height: int = 3
    add_card_height: int = 264

    def cover_size(self) -> tuple[int, int]:
        cover_width = self.card_width - self.card_inner_padding * 2
        cover_height = int(cover_width * self.cover_aspect_height / self.cover_aspect_width)
        return cover_width, cover_height


UI_LAYOUT = UiLayoutConfig()
