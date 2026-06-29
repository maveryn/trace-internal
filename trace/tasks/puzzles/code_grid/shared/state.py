"""State records for code-grid puzzle tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trace.tasks.puzzles.shared.word_grid import Cell

DOMAIN = "puzzles"
SCENE_ID = "code_grid"

COORDINATE_FORMATS: tuple[str, ...] = ("compact", "spaced")
SCENE_VARIANTS: tuple[str, ...] = (
    "code_grid_classic",
    "code_grid_notebook",
    "code_grid_card",
)


@dataclass(frozen=True)
class CodeGridRenderParams:
    """Resolved rendering knobs for one code-grid instance."""

    canvas_width: int
    canvas_height: int
    cell_size_px: int
    header_size_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    grid_line_width_px: int
    letter_font_size_px: int
    index_font_size_px: int
    panel_fill_rgb: tuple[int, int, int]
    grid_fill_rgb: tuple[int, int, int]
    header_fill_rgb: tuple[int, int, int]
    grid_line_rgb: tuple[int, int, int]
    text_rgb: tuple[int, int, int]
    text_stroke_rgb: tuple[int, int, int]
    unit_size_jitter: dict[str, Any]


@dataclass(frozen=True)
class CodeGridDataset:
    """Generated code-grid state before rendering."""

    rows: int
    cols: int
    grid_size_range: tuple[int, int]
    grid: tuple[tuple[str, ...], ...]
    target_word: str
    answer_value: str
    coordinate_tokens: tuple[str, ...]
    coordinate_sequence: str
    coordinate_format: str
    target_cells: tuple[Cell, ...]
    scene_variant: str
    answer_support: tuple[str, ...]
    coordinate_format_probabilities: dict[str, float]
    scene_variant_probabilities: dict[str, float]


@dataclass(frozen=True)
class RenderedCodeGrid:
    """Rendered code-grid image and pixel maps."""

    image: Any
    entities: tuple[dict[str, Any], ...]
    scene_bbox_px: list[float]
    item_bbox_map: dict[str, list[float]]
    cell_bbox_map: dict[str, list[float]]
    layout_jitter: dict[str, Any]


__all__ = [
    "COORDINATE_FORMATS",
    "DOMAIN",
    "SCENE_ID",
    "SCENE_VARIANTS",
    "CodeGridDataset",
    "CodeGridRenderParams",
    "RenderedCodeGrid",
]
