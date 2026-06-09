"""Shared constants, specs, and defaults for curve-panel chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ....core.task_group_config import get_task_group_defaults
from ...shared.config_defaults import (
    group_default,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.render_variation import resolve_render_int, resolve_render_rgb
from ..shared.complexity import resolve_chart_complexity_weights
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_curve_panels_subplot_query_base"
SCENE_ID = "curve_panels"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "curve_at_x_extremum_label",
    "threshold_series_count",
    "panel_point_threshold_count",
    "panel_curve_threshold_crossing_count",
    "cross_panel_delta_extremum_label",
    "cross_panel_threshold_earliest_label",
    "curve_intersection_count",
    "earliest_maximum_panel_label",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("multipanel_line_grid",)
SUPPORTED_POINT_THRESHOLD_DIRECTIONS: Tuple[str, ...] = ("above", "below")
SUPPORTED_THRESHOLD_CROSSING_DIRECTIONS: Tuple[str, ...] = ("upward", "downward")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "scientific")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="scientific")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="scientific", apply_prob=0.0)

_PANEL_LABELS: Tuple[str, ...] = tuple("ABCDEFGHI")
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "curve_at_x_extremum_label": 0.54,
    "threshold_series_count": 0.58,
    "panel_point_threshold_count": 0.62,
    "panel_curve_threshold_crossing_count": 0.68,
    "cross_panel_delta_extremum_label": 0.78,
    "cross_panel_threshold_earliest_label": 0.80,
    "curve_intersection_count": 0.72,
    "earliest_maximum_panel_label": 0.76,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {"multipanel_line_grid": 0.82}

RGB = Tuple[int, int, int]
BBox = Tuple[float, float, float, float]


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
class _Curve:
    method_label: str
    values: Tuple[int, ...]
    color_rgb: RGB


@dataclass(frozen=True)
class _Panel:
    panel_label: str
    curves: Tuple[_Curve, ...]


@dataclass(frozen=True)
class _Intersection:
    intersection_id: str
    panel_label: str
    method_a_label: str
    method_b_label: str
    x_value: float
    y_value: float


@dataclass(frozen=True)
class _ThresholdCrossing:
    crossing_id: str
    panel_label: str
    method_label: str
    x_value: float
    y_value: float
    direction: str


@dataclass(frozen=True)
class _Query:
    query_id: str
    scene_variant: str
    answer: str | int
    answer_type: str
    panel_label: str
    method_label: str
    method_a_label: str
    method_b_label: str
    x_value: int
    start_x_value: int
    end_x_value: int
    threshold_value: int
    threshold_direction: str
    annotation_panel_labels: Tuple[str, ...]
    annotation_point_ids: Tuple[str, ...]
    annotation_intersection_ids: Tuple[str, ...]
    annotation_threshold_crossing_ids: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    scene_variant: str
    x_values: Tuple[int, ...]
    y_min: int
    y_max: int
    panels: Tuple[_Panel, ...]
    query: _Query
    intersections: Tuple[_Intersection, ...]
    threshold_crossings: Tuple[_ThresholdCrossing, ...]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: List[float]
    panel_bboxes: Dict[str, List[float]]
    panel_plot_bboxes: Dict[str, List[float]]
    point_bboxes: Dict[str, List[float]]
    intersection_bboxes: Dict[str, List[float]]
    threshold_crossing_bboxes: Dict[str, List[float]]
    legend_bboxes: Dict[str, List[float]]
    render_meta: Dict[str, Any]

def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(
        resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            str(key),
            int(fallback),
            instance_seed=_render_style_seed(params),
            namespace=TASK_ID,
        )
    )


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _resolve_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _without_sample_cursor(params: Mapping[str, Any]) -> Dict[str, Any]:
    copied = dict(params)
    copied.pop("_sample_cursor", None)
    return copied


def _choice_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    return int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))


def _balanced_choice(values: Sequence[Any], params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> Any:
    support = list(values)
    if not support:
        raise ValueError(f"empty support for {namespace}")
    index = _choice_index(params, instance_seed=int(instance_seed), namespace=str(namespace))
    return support[int(index) % len(support)]


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _uses_uniform_query_id_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> bool:
    if params.get("query_id") is not None or params.get("query_id_weights") is not None:
        return False
    positives = [float(value) for value in query_id_probabilities.values() if float(value) > 0.0]
    if len(positives) != len(SUPPORTED_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _support_sampling_params(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    support_params = dict(params)
    sampling_index = support_params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_query_id_cycle(params, query_id_probabilities=query_id_probabilities):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return support_params


def _palette(params: Mapping[str, Any]) -> Tuple[RGB, ...]:
    raw = params.get("method_palette_rgb", _RENDER_DEFAULTS.get("method_palette_rgb", ()))
    colors: List[RGB] = []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            if isinstance(item, Sequence) and not isinstance(item, (str, bytes)) and len(item) >= 3:
                colors.append(_as_rgb(item, (0, 0, 0)))
    return tuple(colors) if colors else (
        (39, 105, 176),
        (203, 79, 72),
        (52, 145, 98),
        (138, 91, 184),
        (211, 139, 44),
        (48, 147, 168),
    )


def _panel_count(params: Mapping[str, Any], *, instance_seed: int, min_required: int = 4) -> int:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="panel_count_min",
        max_key="panel_count_max",
        fallback_min=6,
        fallback_max=8,
        context=f"generation defaults for {TASK_ID}",
    )
    low = max(4, int(min_required), int(low))
    high = min(len(_PANEL_LABELS), int(high))
    if int(low) > int(high):
        raise ValueError("panel_count support is empty")
    return int(
        _balanced_choice(
            list(range(int(low), int(high) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.panel_count",
        )
    )


def _panel_answer_index_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    _low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="panel_count_min",
        max_key="panel_count_max",
        fallback_min=6,
        fallback_max=8,
        context=f"generation defaults for {TASK_ID}",
    )
    high = min(len(_PANEL_LABELS), max(4, int(high)))
    return tuple(range(int(high)))


def _method_count(params: Mapping[str, Any], *, instance_seed: int, min_required: int = 3) -> int:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="method_count_min",
        max_key="method_count_max",
        fallback_min=5,
        fallback_max=5,
        context=f"generation defaults for {TASK_ID}",
    )
    low = max(3, int(min_required), int(low))
    high = int(high)
    if int(low) > int(high):
        raise ValueError("method_count support is empty")
    return int(
        _balanced_choice(
            list(range(int(low), int(high) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.method_count",
        )
    )


def _method_count_max(params: Mapping[str, Any]) -> int:
    _low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="method_count_min",
        max_key="method_count_max",
        fallback_min=5,
        fallback_max=5,
        context=f"generation defaults for {TASK_ID}",
    )
    return max(3, int(high))

def _point_id(panel_label: str, method_label: str, x_value: int) -> str:
    return f"{str(panel_label)}|{str(method_label)}|{int(x_value)}"


def _intersection_id(panel_label: str, method_a_label: str, method_b_label: str, index: int) -> str:
    return f"{str(panel_label)}|{str(method_a_label)}|{str(method_b_label)}|intersection:{int(index)}"


def _threshold_crossing_id(panel_label: str, method_label: str, index: int) -> str:
    return f"{str(panel_label)}|{str(method_label)}|threshold_crossing:{int(index)}"
