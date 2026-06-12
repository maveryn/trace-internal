"""Identity-free dominoes scene state for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .rendering import DominoTileInstance


SCENE_ID = "dominoes"
DOMINOES_NAMESPACE = "games.dominoes"
SUPPORTED_DOMINO_SCENE_VARIANTS: Tuple[str, ...] = ("single_row", "two_row")
DOMINO_QUERY_IDS: Tuple[str, ...] = (
    "higher_sum_than_reference_count",
    "sum_to_target_count",
    "double_count",
    "matching_end_count",
    "second_play_candidate_count",
    "extendable_first_play_count",
)
OPTION_LABELS: Tuple[str, ...] = tuple("ABCDEFGHIJKL")
PIP_VALUES: Tuple[int, ...] = tuple(range(7))
CANONICAL_DOMINOES: Tuple[Tuple[int, int], ...] = tuple(
    (int(left_value), int(right_value))
    for left_value in range(7)
    for right_value in range(left_value, 7)
)


@dataclass(frozen=True)
class DominoSceneDefaults:
    """Stable fallback defaults for visible domino chain scenes."""

    matching_end_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    higher_sum_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    sum_to_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    double_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    second_play_candidate_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    extendable_first_play_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    single_row_candidate_count_support: Tuple[int, ...] = (7, 8, 9)
    two_row_candidate_count_support: Tuple[int, ...] = (10, 11, 12)
    sum_target_total_support: Tuple[int, ...] = (2, 3, 4, 5, 6, 7, 8, 9, 10)
    chain_length: int = 3
    canvas_width: int = 1180
    canvas_height: int = 760
    panel_margin_px: int = 56
    chain_top_px: int = 104
    tile_width_px: int = 138
    tile_height_px: int = 76
    chain_gap_px: int = 18
    candidate_gap_px: int = 18
    row_gap_px: int = 34
    tile_corner_radius_px: int = 12
    pip_radius_px: int = 5
    divider_width_px: int = 4
    reference_tag_font_size_px: int = 16
    reference_tag_gap_px: int = 14
    section_label_font_size_px: int = 18
    section_separator_width_px: int = 2


@dataclass(frozen=True)
class DominoSceneAxes:
    """Resolved scene/style axes shared by dominoes tasks."""

    scene_variant: str
    style_variant: str
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class DominoIntegerAxis:
    """Resolved integer sampling axis with trace metadata."""

    value: int
    support: Tuple[int, ...]
    probabilities: Dict[str, float]


@dataclass(frozen=True)
class SampledDominoScene:
    """One sampled domino chain scene with task-specific witness metadata."""

    chain_tiles: Tuple[DominoTileInstance, ...]
    candidate_tiles: Tuple[DominoTileInstance, ...]
    annotation_tile_ids: Tuple[str, ...]
    answer_value: int | str
    reference_tile_id: str | None
    open_end_value: int | None
    reference_sum: int | None
    target_total: int | None
    first_step_tile_id: str | None
    second_step_tile_id: str | None
    bridge_value: int | None
    chain_tile_specs: Tuple[Dict[str, Any], ...]
    candidate_tile_specs: Tuple[Dict[str, Any], ...]


@dataclass(frozen=True)
class DominoGeneratedComponents:
    """Generated scene components for public task files to wrap in TaskOutput."""

    prompt: str
    prompt_variants: Dict[str, Any]
    answer_type: str
    answer_value: int | str
    annotation_type: str
    annotation_value: Any
    image: Any
    trace_payload: Dict[str, Any]
    query_id: str


DEFAULTS = DominoSceneDefaults()


__all__ = [
    "CANONICAL_DOMINOES",
    "DEFAULTS",
    "DOMINOES_NAMESPACE",
    "DOMINO_QUERY_IDS",
    "OPTION_LABELS",
    "PIP_VALUES",
    "SCENE_ID",
    "SUPPORTED_DOMINO_SCENE_VARIANTS",
    "DominoGeneratedComponents",
    "DominoIntegerAxis",
    "DominoSceneAxes",
    "DominoSceneDefaults",
    "SampledDominoScene",
]
