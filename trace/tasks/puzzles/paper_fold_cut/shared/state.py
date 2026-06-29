"""Passive state and ids for paper fold-cut puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

DOMAIN = "puzzles"
SCENE_ID = "paper_fold_cut"

SUPPORTED_SCENE_VARIANTS: tuple[str, ...] = (
    "fold_strip",
    "fold_card",
    "fold_outline",
)
SUPPORTED_FOLD_COUNTS: tuple[int, ...] = (1, 2)
SUPPORTED_FOLD_AXES: tuple[str, ...] = ("vertical", "horizontal")
SUPPORTED_CUT_HOLE_SHAPES: tuple[str, ...] = (
    "circle",
    "square",
    "diamond",
    "rounded_square",
)

Cells = Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class PaperFoldCutDataset:
    """Sampled fold-cut puzzle data before rendering and prompt assembly."""

    internal_grammar_id: str
    grid_size: int
    folded_grid_cols: int
    folded_grid_rows: int
    fold_sequence: tuple[Dict[str, Any], ...]
    fold_count: int
    folded_dimensions_by_step: tuple[tuple[int, int], ...]
    cut_count: int
    cut_count_range: tuple[int, int]
    cut_cells: tuple[tuple[int, int], ...]
    cut_specs: tuple[Dict[str, Any], ...]
    unfolded_hole_cells: tuple[tuple[int, int], ...]
    unfolded_hole_specs: tuple[Dict[str, Any], ...]
    unfolded_hole_count: int
    option_count: int
    option_count_range: tuple[int, int]
    option_specs: tuple[Dict[str, Any], ...]
    answer_option_label: str
    correct_option_index: int
    correct_option_choice_id: str
    valid_option_choice_ids: tuple[str, ...]
    option_count_probabilities: Dict[str, float]
    fold_count_probabilities: Dict[str, float]
    fold_axis_probabilities: Dict[str, float]
    cut_count_probabilities: Dict[str, float]
    correct_option_index_probabilities: Dict[str, float]


__all__ = [
    "Cells",
    "DOMAIN",
    "PaperFoldCutDataset",
    "SCENE_ID",
    "SUPPORTED_CUT_HOLE_SHAPES",
    "SUPPORTED_FOLD_AXES",
    "SUPPORTED_FOLD_COUNTS",
    "SUPPORTED_SCENE_VARIANTS",
]
