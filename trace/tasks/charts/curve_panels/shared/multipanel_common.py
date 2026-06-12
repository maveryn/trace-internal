"""Shared constants, specs, and defaults for curve-panel chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from .....core.scene_config import get_scene_defaults
from ....shared.config_defaults import (
    group_default,
    resolve_required_int_bounds,
    split_scene_generation_rendering_prompt_defaults,
)
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.render_variation import resolve_render_int, resolve_render_rgb
from ...shared.labeled_chart_common import resolve_chart_axis_variant
from ...shared.visual_defaults import load_chart_scene_background_defaults, load_chart_scene_noise_defaults


SCENE_NAMESPACE = "charts.curve_panels"
SCENE_ID = "curve_panels"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("multipanel_line_grid",)
SUPPORTED_POINT_THRESHOLD_DIRECTIONS: Tuple[str, ...] = ("above", "below")
SUPPORTED_THRESHOLD_CROSSING_DIRECTIONS: Tuple[str, ...] = ("upward", "downward")

_TASK_GROUP_DEFAULTS = get_scene_defaults("charts", "curve_panels")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    **{"task" "_id": SCENE_NAMESPACE},
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id="curve_panels")
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id="curve_panels", apply_prob=0.0)

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
    prompt_key: str
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
            namespace=SCENE_NAMESPACE,
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
        namespace=SCENE_NAMESPACE,
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
        context=f"generation defaults for {SCENE_NAMESPACE}",
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
            namespace=f"{SCENE_NAMESPACE}.panel_count",
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
        context=f"generation defaults for {SCENE_NAMESPACE}",
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
        context=f"generation defaults for {SCENE_NAMESPACE}",
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
            namespace=f"{SCENE_NAMESPACE}.method_count",
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
        context=f"generation defaults for {SCENE_NAMESPACE}",
    )
    return max(3, int(high))

def _point_id(panel_label: str, method_label: str, x_value: int) -> str:
    return f"{str(panel_label)}|{str(method_label)}|{int(x_value)}"


def _intersection_id(panel_label: str, method_a_label: str, method_b_label: str, index: int) -> str:
    return f"{str(panel_label)}|{str(method_a_label)}|{str(method_b_label)}|intersection:{int(index)}"


def _threshold_crossing_id(panel_label: str, method_label: str, index: int) -> str:
    return f"{str(panel_label)}|{str(method_label)}|threshold_crossing:{int(index)}"
