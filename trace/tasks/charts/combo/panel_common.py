"""Shared constants and specs for combo chart panel tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ..shared.complexity import resolve_chart_complexity_weights
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults

SCENE_ID = "combo_mark"
TASK_ID = "charts_combo_panel_query_base"

_SCENE_VARIANTS: Tuple[str, ...] = (
    "bar_line_shared_axis",
    "bar_line_dual_axis",
    "stacked_bar_line",
    "area_line_overlay",
)
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "bar_line_shared_axis": 0.10,
    "bar_line_dual_axis": 0.30,
    "stacked_bar_line": 0.54,
    "area_line_overlay": 0.36,
}
_QUERY_REASONING_LOAD: Dict[str, float] = {
    "primary_minus_line_at_label": 0.20,
    "line_minus_primary_at_label": 0.20,
    "absolute_gap_at_label": 0.18,
    "larger_minus_smaller_at_label": 0.22,
    "max_line_where_primary_above_threshold": 0.54,
    "min_line_where_primary_above_threshold": 0.54,
    "max_primary_where_line_below_threshold": 0.56,
    "min_primary_where_line_below_threshold": 0.56,
    "primary_above_and_line_above": 0.42,
    "primary_above_and_line_below": 0.46,
    "primary_below_and_line_above": 0.46,
    "primary_between_and_line_above": 0.58,
    "line_between_and_primary_above": 0.58,
    "largest_absolute_gap_label": 0.50,
    "smallest_nonzero_absolute_gap_label": 0.54,
    "largest_primary_over_line_gap_label": 0.58,
    "largest_line_over_primary_gap_label": 0.58,
    "primary_first_above_threshold_label": 0.44,
    "primary_first_below_threshold_label": 0.44,
    "line_first_above_threshold_label": 0.48,
    "line_first_below_threshold_label": 0.48,
}

_THRESHOLD_CROSSING_QUERY_IDS: Tuple[str, ...] = (
    "primary_first_above_threshold_label",
    "primary_first_below_threshold_label",
    "line_first_above_threshold_label",
    "line_first_below_threshold_label",
)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "combo")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="combo")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="combo", apply_prob=0.0)


def _public_task_param_overrides(task_id: str) -> Dict[str, Any]:
    """Return task-id-specific generation/rendering params for public wrappers."""

    overrides: Dict[str, Any] = {}
    if not isinstance(_TASK_GROUP_DEFAULTS, Mapping):
        return overrides
    for section in ("generation", "rendering"):
        section_cfg = _TASK_GROUP_DEFAULTS.get(section)
        if not isinstance(section_cfg, Mapping):
            continue
        task_overrides = section_cfg.get("task_overrides")
        if not isinstance(task_overrides, Mapping):
            continue
        task_values = task_overrides.get(str(task_id))
        if isinstance(task_values, Mapping):
            overrides.update(dict(task_values))
    return overrides


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    plot_left: int
    plot_right: int
    plot_top: int
    plot_bottom: int
    axis_width: int
    grid_width: int
    line_width: int
    point_radius: int
    tick_font_size: int
    label_font_size: int
    value_font_size: int
    legend_font_size: int
    primary_rgb: Tuple[int, int, int]
    primary_alt_rgb: Tuple[int, int, int]
    line_rgb: Tuple[int, int, int]
    area_rgb: Tuple[int, int, int]
    axis_rgb: Tuple[int, int, int]
    grid_rgb: Tuple[int, int, int]
    text_rgb: Tuple[int, int, int]
    panel_rgb: Tuple[int, int, int]
    layout_jitter_meta: Mapping[str, Any]


@dataclass(frozen=True)
class _ComboScene:
    image: Image.Image
    labels: Tuple[str, ...]
    primary_values: Tuple[int, ...]
    line_values: Tuple[int, ...]
    primary_points: Tuple[Tuple[float, float], ...]
    line_points: Tuple[Tuple[float, float], ...]
    entities: Tuple[Dict[str, Any], ...]
    scene_variant: str
    primary_name: str
    line_name: str
    primary_axis_max: int
    line_axis_max: int
    plot_bbox: Tuple[int, int, int, int]
    legend_bbox: Tuple[float, float, float, float]


def _as_int_bounds(params: Mapping[str, Any], low_key: str, high_key: str, fallback: Tuple[int, int]) -> Tuple[int, int]:
    low = int(params.get(low_key, group_default(_GEN_DEFAULTS, low_key, int(fallback[0]))))
    high = int(params.get(high_key, group_default(_GEN_DEFAULTS, high_key, int(fallback[1]))))
    if low > high:
        raise ValueError(f"{low_key} must be <= {high_key}")
    return low, high


def _axis_choice(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    supported: Sequence[str],
    explicit_keys: Sequence[str],
    weights_key: str,
    balance_key: str,
    namespace: str,
    sampling_divisor: int = 1,
) -> Tuple[str, Dict[str, float]]:
    for key in explicit_keys:
        value = params.get(str(key))
        if value is not None and str(value).strip():
            text = str(value)
            if text not in set(supported):
                raise ValueError(f"unsupported {key}: {text}")
            return text, {str(item): 1.0 if str(item) == text else 0.0 for item in supported}
    raw_weights = params.get(str(weights_key), group_default(_GEN_DEFAULTS, str(weights_key), None))
    if isinstance(raw_weights, Mapping):
        probabilities = normalize_positive_weights({str(k): float(v) for k, v in raw_weights.items()}, default_keys=supported)
    else:
        probabilities = normalize_positive_weights({}, default_keys=supported)
    if bool(params.get(str(balance_key), group_default(_GEN_DEFAULTS, str(balance_key), True))) and params.get("_sample_cursor") is not None:
        positives = [key for key in supported if float(probabilities.get(str(key), 0.0)) > 0.0]
        index = abs(int(params.get("_sample_cursor", 0))) // max(1, int(sampling_divisor))
        return str(positives[int(index) % len(positives)]), dict(probabilities)
    rng = spawn_rng(int(instance_seed), str(namespace))
    return weighted_choice(rng, probabilities, sort_keys=True), dict(probabilities)


def _explicit_axis_selected(params: Mapping[str, Any], keys: Sequence[str], supported: Sequence[str]) -> bool:
    supported_values = {str(value) for value in supported}
    return any(str(params.get(str(key))) in supported_values for key in keys if params.get(str(key)) is not None)
