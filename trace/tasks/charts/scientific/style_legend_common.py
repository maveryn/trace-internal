"""Shared constants and specs for scientific style-legend chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
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

TASK_ID = "charts_style_legend_binding_base"
SCENE_ID = "style_legend"

EXTREMUM_QUERY_IDS: Tuple[str, ...] = (
    "x_position_highest_series_label",
    "x_position_lowest_series_label",
)
GAP_QUERY_IDS: Tuple[str, ...] = ("pairwise_gap_value",)
THRESHOLD_QUERY_IDS: Tuple[str, ...] = (
    "above_threshold_series_count",
    "below_threshold_series_count",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = EXTREMUM_QUERY_IDS + GAP_QUERY_IDS + THRESHOLD_QUERY_IDS
SUPPORTED_STYLE_PALETTE_MODES: Tuple[str, ...] = ("grayscale", "muted_color", "colorblind_safe")
SUPPORTED_LEGEND_POSITIONS: Tuple[str, ...] = ("right", "inside_top_right", "top")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "scientific")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="scientific")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="scientific", apply_prob=0.0)

_REASONING_LOAD_BY_QUERY: Dict[str, float] = {
    "x_position_highest_series_label": 0.58,
    "x_position_lowest_series_label": 0.58,
    "pairwise_gap_value": 0.64,
    "above_threshold_series_count": 0.62,
    "below_threshold_series_count": 0.62,
}
_PALETTE_MODE_LOAD: Dict[str, float] = {
    "grayscale": 0.78,
    "muted_color": 0.64,
    "colorblind_safe": 0.56,
}

RGB = Tuple[int, int, int]
Point = List[float]
BBox = List[float]

_LINE_STYLES: Tuple[str, ...] = ("solid", "dashed", "dotted", "dashdot", "long_dash", "short_dash")
_MARKER_SHAPES: Tuple[str, ...] = ("circle", "square", "diamond", "triangle", "ring", "cross")
_MARKER_FILLS: Tuple[str, ...] = ("filled", "open")


@dataclass(frozen=True)
class _SeriesStyle:
    color_rgb: RGB
    line_style: str
    marker_shape: str
    marker_fill: str
    line_width_px: int


@dataclass(frozen=True)
class _Series:
    series_id: str
    label: str
    values: Tuple[int, ...]
    style: _SeriesStyle


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int | str
    answer_type: str
    annotation_point_ids: Tuple[str, ...]
    params: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    x_labels: Tuple[str, ...]
    x_label_meta: Dict[str, Any]
    series: Tuple[_Series, ...]
    series_label_meta: Dict[str, Any]
    query: _Query
    target_x_index: int
    threshold_value: int | None
    pair_series_ids: Tuple[str, str]
    palette_mode: str
    palette_mode_probabilities: Dict[str, float]
    legend_position: str
    legend_position_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    margin_left_px: int
    margin_right_px: int
    margin_top_px: int
    margin_bottom_px: int
    title_font_size_px: int
    tick_font_size_px: int
    label_font_size_px: int
    legend_font_size_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    point_radius_px: int
    text_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    axis_rgb: RGB
    grid_rgb: RGB
    panel_fill_rgb: RGB
    panel_outline_rgb: RGB
    threshold_rgb: RGB
    font_family: str
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: BBox
    legend_bbox_px: BBox
    legend_item_bboxes_px: Dict[str, BBox]
    point_map_px: Dict[str, Dict[str, Point]]
    point_bboxes_px: Dict[str, BBox]
    threshold_bbox_px: BBox | None
    render_meta: Dict[str, Any]


def _bbox(values: Sequence[float]) -> BBox:
    return [round(float(value), 3) for value in values]


def _point(x: float, y: float) -> Point:
    return [round(float(x), 3), round(float(y), 3)]


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


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


def _resolve_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _selection_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    return abs(int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))))


def _balanced_choice(values: Sequence[Any], params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> Any:
    support = tuple(values)
    if not support:
        raise ValueError(f"empty support for {namespace}")
    index = _selection_index(params, instance_seed=int(instance_seed), namespace=str(namespace))
    return support[int(index) % len(support)]


def _normalize_weights(raw: Mapping[str, float]) -> Dict[str, float]:
    clean = {str(key): float(value) for key, value in raw.items() if float(value) > 0.0}
    total = float(sum(clean.values()))
    if total <= 0.0:
        return {}
    return {str(key): float(value) / total for key, value in sorted(clean.items())}


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


def _resolve_axis_variant(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    supported: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_key: str,
    namespace: str,
    fallback_weights: Mapping[str, float],
) -> Tuple[str, Dict[str, float]]:
    explicit = params.get(str(explicit_key), group_default(_GEN_DEFAULTS, str(explicit_key), None))
    supported_values = tuple(str(value) for value in supported)
    if explicit is not None:
        value = str(explicit)
        if value not in set(supported_values):
            raise ValueError(f"unsupported {explicit_key}: {value}")
        return value, {value: 1.0}
    raw_weights = params.get(str(weights_key), group_default(_GEN_DEFAULTS, str(weights_key), fallback_weights))
    weights = _normalize_weights(raw_weights if isinstance(raw_weights, Mapping) else fallback_weights)
    candidates = tuple(value for value in supported_values if float(weights.get(value, 0.0)) > 0.0)
    if not candidates:
        candidates = supported_values
        weights = {str(value): 1.0 / float(len(candidates)) for value in candidates}
    if bool(params.get(str(balance_key), group_default(_GEN_DEFAULTS, str(balance_key), False))):
        return str(_balanced_choice(candidates, params, instance_seed=int(instance_seed), namespace=str(namespace))), dict(weights)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace}")
    total = sum(float(weights.get(value, 0.0)) for value in candidates)
    pick = rng.random() * float(total)
    running = 0.0
    for value in candidates:
        running += float(weights.get(value, 0.0))
        if pick <= running:
            return str(value), dict(weights)
    return str(candidates[-1]), dict(weights)


def _resolve_palette_mode(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return _resolve_axis_variant(
        params,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_STYLE_PALETTE_MODES,
        explicit_key="style_palette_mode",
        weights_key="style_palette_mode_weights",
        balance_key="balanced_style_palette_mode_sampling",
        namespace="style_palette_mode",
        fallback_weights={"grayscale": 7.0, "muted_color": 2.0, "colorblind_safe": 1.0},
    )


def _resolve_legend_position(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return _resolve_axis_variant(
        params,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_LEGEND_POSITIONS,
        explicit_key="legend_position",
        weights_key="legend_position_weights",
        balance_key="balanced_legend_position_sampling",
        namespace="legend_position",
        fallback_weights={"right": 2.0, "inside_top_right": 1.0, "top": 1.0},
    )


def _count_from_range(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    instance_seed: int,
    namespace: str,
) -> int:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"generation defaults for {TASK_ID}",
    )
    if int(low) > int(high):
        raise ValueError(f"empty count range for {namespace}")
    return int(
        _balanced_choice(
            tuple(range(int(low), int(high) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{namespace}",
        )
    )



def _point_id(series_id: str, x_index: int) -> str:
    return f"{str(series_id)}|x{int(x_index)}"
