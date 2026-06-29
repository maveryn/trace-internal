"""Passive state and ids for transparent-sheet overlay puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

DOMAIN = "puzzles"
SCENE_ID = "overlay"

Cells = Tuple[Tuple[int, int], ...]

SUPPORTED_SCENE_VARIANTS: tuple[str, ...] = (
    "overlay_strip",
    "overlay_card",
    "overlay_outline",
)
SUPPORTED_MARK_SHAPES: tuple[str, ...] = (
    "circle",
    "square",
    "diamond",
    "rounded_square",
)


@dataclass(frozen=True)
class OverlayDataset:
    """Sampled overlay puzzle data before rendering and prompt assembly."""

    grid_size: int
    grid_size_range: tuple[int, int]
    option_count: int
    option_count_range: tuple[int, int]
    sheet_mark_count_range: tuple[int, int]
    overlap_count_range: tuple[int, int]
    left_cells: Cells
    right_cells: Cells
    overlap_cells: Cells
    union_cells: Cells
    left_mark_specs: tuple[Dict[str, Any], ...]
    right_mark_specs: tuple[Dict[str, Any], ...]
    left_mark_count: int
    right_mark_count: int
    overlap_count: int
    union_mark_count: int
    option_specs: tuple[Dict[str, Any], ...]
    answer_option_label: str
    correct_option_index: int
    correct_option_choice_id: str
    option_count_probabilities: Dict[str, float]
    grid_size_probabilities: Dict[str, float]
    correct_option_index_probabilities: Dict[str, float]


__all__ = [
    "Cells",
    "DOMAIN",
    "INTERNAL_QUERY_ID",
    "OverlayDataset",
    "SCENE_ID",
    "SUPPORTED_MARK_SHAPES",
    "SUPPORTED_SCENE_VARIANTS",
]
