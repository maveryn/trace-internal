"""Shared constants and semantic helpers for heatmap chart tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from .....core.scene_config import get_scene_defaults
from ....shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from ...shared.visual_defaults import load_chart_scene_background_defaults, load_chart_scene_noise_defaults


SCENE_ID = "heatmap"
SCENE_NAMESPACE = "charts_heatmap_query_base"
_SUPPORTED_PROMPT_KEYS: Tuple[str, ...] = (
    "axis_condition_extremum_label",
    "axis_cell_extremum_label",
    "condition_run_extremum_label",
    "colorbar_above_threshold_cell_count",
    "colorbar_below_threshold_cell_count",
    "colorbar_interval_cell_count",
)
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "intensity_heatmap",
    "signed_change_heatmap",
    "calendar_heatmap",
    "continuous_colorbar_heatmap",
)
_CONTINUOUS_COLORBAR_PROMPT_KEYS: Tuple[str, ...] = (
    "colorbar_above_threshold_cell_count",
    "colorbar_below_threshold_cell_count",
    "colorbar_interval_cell_count",
)
_COLORBAR_THRESHOLD_PROMPT_KEYS: Tuple[str, ...] = (
    "colorbar_above_threshold_cell_count",
    "colorbar_below_threshold_cell_count",
)
_SUPPORTED_EXTREMUM_DIRECTIONS: Tuple[str, ...] = ("hottest", "coolest")
_SUPPORTED_PROMPT_AXES: Tuple[str, ...] = ("row", "column")
_INTENSITY_CONDITIONS: Tuple[str, ...] = ("hot", "cool")
_SIGNED_CONDITIONS: Tuple[str, ...] = ("increase", "decrease")
SUPPORTED_PROMPT_KEYS = _SUPPORTED_PROMPT_KEYS
SUPPORTED_SCENE_VARIANTS = _SUPPORTED_SCENE_VARIANTS

_TASK_GROUP_DEFAULTS = get_scene_defaults("charts", "heatmap")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    **{"task" "_id": SCENE_NAMESPACE},
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id="heatmap")
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id="heatmap", apply_prob=0.0)

_MISSING_CONDITION_PHRASES: Tuple[str, ...] = (
    "purple-coded",
    "black-striped",
    "teal-outlined",
    "orange-dotted",
)
_WEEKDAY_LABELS: Tuple[str, ...] = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
_TITLE_OPTIONS: Tuple[str, ...] = (
    "Activity Heatmap",
    "Change Intensity Grid",
    "Category Heat Matrix",
    "Weekly Signal Heatmap",
    "Response Pattern Grid",
)
_INTENSITY_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (247, 252, 245),
    (199, 233, 192),
    (116, 196, 118),
    (49, 163, 84),
    (0, 109, 44),
)
_SIGNED_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (49, 117, 182),
    (171, 217, 233),
    (244, 244, 244),
    (253, 174, 97),
    (215, 48, 39),
)
_CALENDAR_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (246, 245, 252),
    (218, 218, 235),
    (188, 189, 220),
    (128, 125, 186),
    (84, 39, 143),
)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "axis_condition_extremum_label": 0.70,
    "axis_cell_extremum_label": 0.60,
    "condition_run_extremum_label": 0.82,
    "colorbar_above_threshold_cell_count": 0.72,
    "colorbar_below_threshold_cell_count": 0.72,
    "colorbar_interval_cell_count": 0.78,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {
    "intensity_heatmap": 0.44,
    "signed_change_heatmap": 0.56,
    "calendar_heatmap": 0.50,
    "continuous_colorbar_heatmap": 0.62,
}


BBox = Tuple[float, float, float, float]


def _is_continuous_colorbar_prompt_key(prompt_key: str) -> bool:
    return str(prompt_key) in set(_CONTINUOUS_COLORBAR_PROMPT_KEYS)


def _condition_support(scene_variant: str) -> Tuple[str, ...]:
    if str(scene_variant) == "signed_change_heatmap":
        return _SIGNED_CONDITIONS
    return _INTENSITY_CONDITIONS

def _condition_matches(value: int, *, condition_kind: str, bin_count: int) -> bool:
    midpoint = int(bin_count) // 2
    if str(condition_kind) == "hot":
        return int(value) >= max(0, int(bin_count) - 2)
    if str(condition_kind) == "cool":
        return int(value) <= 1
    if str(condition_kind) == "increase":
        return int(value) > int(midpoint)
    if str(condition_kind) == "decrease":
        return int(value) < int(midpoint)
    raise ValueError(f"unsupported condition_kind: {condition_kind}")


def _condition_phrase(condition_kind: str, *, scene_variant: str) -> str:
    if str(scene_variant) == "calendar_heatmap":
        phrases = {
            "hot": "high-activity (one of the two darkest color levels)",
            "cool": "low-activity (one of the two lightest color levels)",
        }
    else:
        phrases = {
            "hot": "high-intensity (one of the two darkest color levels)",
            "cool": "low-intensity (one of the two lightest color levels)",
            "increase": "increase-colored (one of the two strongest increase color levels)",
            "decrease": "decrease-colored (one of the two strongest decrease color levels)",
        }
    return str(phrases[str(condition_kind)])


def _extremum_phrase(extremum_direction: str, *, scene_variant: str) -> str:
    if str(scene_variant) == "signed_change_heatmap":
        if str(extremum_direction) == "hottest":
            return "strongest increase-colored"
        if str(extremum_direction) == "coolest":
            return "strongest decrease-colored"
    if str(scene_variant) == "calendar_heatmap":
        if str(extremum_direction) == "hottest":
            return "highest-activity"
        if str(extremum_direction) == "coolest":
            return "lowest-activity"
    if str(extremum_direction) == "hottest":
        return "highest-intensity"
    if str(extremum_direction) == "coolest":
        return "lowest-intensity"
    raise ValueError(f"unsupported extremum_direction: {extremum_direction}")
