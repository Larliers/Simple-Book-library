from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GridDensityConfig:
    # Main tuning knobs for different resolutions.
    card_width: int = 176
    min_grid_spacing: int = 14

    # Card internals.
    card_inner_padding: int = 8
    cover_aspect_width: int = 2
    cover_aspect_height: int = 3
    add_card_height: int = 264

    def cover_size(self) -> tuple[int, int]:
        cover_width = self.card_width - self.card_inner_padding * 2
        cover_height = int(cover_width * self.cover_aspect_height / self.cover_aspect_width)
        return cover_width, cover_height

    def apply(self, *, card_width: int | None = None, min_grid_spacing: int | None = None) -> None:
        if card_width is not None:
            self.card_width = max(120, min(360, int(card_width)))
        if min_grid_spacing is not None:
            self.min_grid_spacing = max(4, min(48, int(min_grid_spacing)))


GRID_DENSITY = GridDensityConfig()
