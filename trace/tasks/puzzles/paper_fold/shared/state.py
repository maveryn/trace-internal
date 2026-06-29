"""Passive state and ids for paper-fold result puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

DOMAIN = "puzzles"
SCENE_ID = "paper_fold"

SUPPORTED_SCENE_VARIANTS: tuple[str, ...] = (
    "fold_strip",
    "fold_card",
    "fold_outline",
)
SUPPORTED_FOLD_AXES: tuple[str, ...] = ("vertical", "horizontal")
FOLD_MARK_TYPES: tuple[str, ...] = (
    "circle",
    "diamond",
    "square",
    "hexagon",
    "star",
)
Cells = Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class PaperFoldDataset:
    """Sampled fold-result puzzle data before rendering and prompt assembly."""

    grid_size: int
    result_grid_cols: int
    result_grid_rows: int
    option_count: int
    option_count_range: tuple[int, int]
    mark_count: int
    mark_count_range: tuple[int, int]
    fold_axis: str
    fold_direction: str
    original_mark_specs: tuple[Dict[str, Any], ...]
    folded_result_mark_specs: tuple[Dict[str, Any], ...]
    option_specs: tuple[Dict[str, Any], ...]
    answer_option_label: str
    correct_option_index: int
    correct_option_choice_id: str
    folded_mark_count: int
    kept_mark_count: int
    option_count_probabilities: Dict[str, float]
    correct_option_index_probabilities: Dict[str, float]


__all__ = [
    "Cells",
    "DOMAIN",
    "FOLD_MARK_TYPES",
    "PaperFoldDataset",
    "SCENE_ID",
    "SUPPORTED_FOLD_AXES",
    "SUPPORTED_SCENE_VARIANTS",
]
