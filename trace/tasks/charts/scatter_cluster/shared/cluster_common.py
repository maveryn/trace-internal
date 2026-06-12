"""Shared scatter cluster task constants, records, and render defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from .....core.scene_config import get_scene_defaults
from ....shared.config_defaults import group_default, split_scene_generation_rendering_prompt_defaults
from ....shared.font_assets import sample_font_family
from ....shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ...shared.visual_defaults import load_chart_scene_background_defaults, load_chart_scene_noise_defaults


TASK_ID = "charts_scatter_cluster_query_base"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "cluster_trend_direction_label",
    "cluster_separation_extremum_label",
    "cluster_spread_extremum_label",
    "largest_cluster_area_label",
    "second_largest_cluster_area_label",
    "smallest_cluster_area_label",
    "centroid_option_selection_label",
)
_SUPPORTED_TREND_DIRECTIONS: Tuple[str, ...] = ("upward", "downward")
_SUPPORTED_SEPARATION_EXTREMA: Tuple[str, ...] = ("closest", "farthest")
_SUPPORTED_SPREAD_AXES: Tuple[str, ...] = ("horizontal", "vertical", "overall")
_SUPPORTED_SPREAD_EXTREMA: Tuple[str, ...] = ("largest", "smallest")
_SUPPORTED_AREA_RANK_QUERY_IDS: Tuple[str, ...] = (
    "largest_cluster_area_label",
    "second_largest_cluster_area_label",
    "smallest_cluster_area_label",
)
_AREA_RANK_BY_QUERY_ID: Dict[str, str] = {
    "largest_cluster_area_label": "largest",
    "second_largest_cluster_area_label": "second_largest",
    "smallest_cluster_area_label": "smallest",
}
_AREA_RANK_PHRASE_BY_QUERY_ID: Dict[str, str] = {
    "largest_cluster_area_label": "largest",
    "second_largest_cluster_area_label": "second-largest",
    "smallest_cluster_area_label": "smallest",
}
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("single_scatter", "area_envelope_scatter")
_OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

_TASK_GROUP_DEFAULTS = get_scene_defaults("charts", "scatter_cluster")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id="scatter_cluster")
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id="scatter_cluster", apply_prob=0.0)

_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "cluster_trend_direction_label": 0.62,
    "cluster_separation_extremum_label": 0.68,
    "cluster_spread_extremum_label": 0.72,
    "largest_cluster_area_label": 0.70,
    "second_largest_cluster_area_label": 0.76,
    "smallest_cluster_area_label": 0.70,
    "centroid_option_selection_label": 0.66,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {"single_scatter": 0.58, "area_envelope_scatter": 0.64}

RGB = Tuple[int, int, int]
BBox = Tuple[float, float, float, float]



@dataclass(frozen=True)
class _Point:
    point_id: str
    cluster_label: str
    x_value: float
    y_value: float


@dataclass(frozen=True)
class _AreaEnvelope:
    center_x: float
    center_y: float
    radius_x: float
    radius_y: float
    angle_degrees: float
    area_value: float


@dataclass(frozen=True)
class _Cluster:
    cluster_label: str
    color_rgb: RGB
    center_x: float
    center_y: float
    slope: float
    spread_x: float
    spread_y: float
    points: Tuple[_Point, ...]
    area_envelope: _AreaEnvelope | None = None


@dataclass(frozen=True)
class _OptionMarker:
    option_label: str
    x_value: float
    y_value: float


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer_label: str
    answer_type: str
    annotation_cluster_labels: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    scene_variant: str
    clusters: Tuple[_Cluster, ...]
    query: _Query
    option_markers: Tuple[_OptionMarker, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    plot_margin_left_px: int
    plot_margin_right_px: int
    plot_margin_top_px: int
    plot_margin_bottom_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    tick_length_px: int
    point_radius_px: int
    tick_font_size_px: int
    legend_font_size_px: int
    title_font_size_px: int
    cluster_hull_padding_px: int
    axis_color_rgb: RGB
    grid_color_rgb: RGB
    text_color_rgb: RGB
    text_stroke_rgb: RGB
    plot_fill_rgb: RGB
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: List[float]
    point_bboxes: Dict[str, List[float]]
    cluster_bboxes: Dict[str, List[float]]
    cluster_envelope_bboxes: Dict[str, List[float]]
    cluster_label_bboxes: Dict[str, List[float]]
    legend_bboxes: Dict[str, List[float]]
    option_bboxes: Dict[str, List[float]]
    option_centers_px: Dict[str, List[float]]


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


def _gen_float(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), float(fallback))))


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def _is_area_rank_query(query_id: str) -> bool:
    return str(query_id) in set(_SUPPORTED_AREA_RANK_QUERY_IDS)


def _sample_chart_font_family(instance_seed: int, params: Mapping[str, Any]) -> str:
    return str(
        sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            exclude_tags=("display",),
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
    )


def _palette(params: Mapping[str, Any]) -> Tuple[RGB, ...]:
    raw = params.get("cluster_palette_rgb", _RENDER_DEFAULTS.get("cluster_palette_rgb", ()))
    colors: List[RGB] = []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            colors.append(_as_rgb(item, (60, 110, 180)))
    if len(colors) >= 8:
        return tuple(colors[:8])
    return (
        (38, 101, 176),
        (218, 91, 75),
        (56, 150, 96),
        (142, 92, 188),
        (218, 145, 46),
        (78, 159, 191),
        (188, 87, 132),
        (109, 125, 55),
    )


def _resolve_render_params(params: Mapping[str, Any]) -> _RenderParams:
    margin_left = _resolve_int(params, "plot_margin_left_px", 110)
    margin_right = _resolve_int(params, "plot_margin_right_px", 260)
    margin_top = _resolve_int(params, "plot_margin_top_px", 72)
    margin_bottom = _resolve_int(params, "plot_margin_bottom_px", 112)
    margin_left, margin_right, margin_top, margin_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=_render_style_seed(params),
        namespace=f"{TASK_ID}.layout",
    )
    return _RenderParams(
        canvas_width=_resolve_int(params, "canvas_width", 1280),
        canvas_height=_resolve_int(params, "canvas_height", 820),
        plot_margin_left_px=int(margin_left),
        plot_margin_right_px=int(margin_right),
        plot_margin_top_px=int(margin_top),
        plot_margin_bottom_px=int(margin_bottom),
        axis_line_width_px=_resolve_int(params, "axis_line_width_px", 2),
        grid_line_width_px=_resolve_int(params, "grid_line_width_px", 1),
        tick_length_px=_resolve_int(params, "tick_length_px", 8),
        point_radius_px=_resolve_int(params, "point_radius_px", 7),
        tick_font_size_px=_resolve_int(params, "tick_font_size_px", 17),
        legend_font_size_px=_resolve_int(params, "legend_font_size_px", 22),
        title_font_size_px=_resolve_int(params, "title_font_size_px", 26),
        cluster_hull_padding_px=_resolve_int(params, "cluster_hull_padding_px", 14),
        axis_color_rgb=_resolve_rgb(params, "axis_color_rgb", (74, 78, 86)),
        grid_color_rgb=_resolve_rgb(params, "grid_color_rgb", (225, 228, 234)),
        text_color_rgb=_resolve_rgb(params, "text_color_rgb", (38, 41, 48)),
        text_stroke_rgb=_resolve_rgb(params, "text_stroke_rgb", (255, 255, 255)),
        plot_fill_rgb=_resolve_rgb(params, "plot_fill_rgb", (255, 255, 255)),
        panel_fill_rgb=_resolve_rgb(params, "panel_fill_rgb", (252, 253, 255)),
        panel_border_rgb=_resolve_rgb(params, "panel_border_rgb", (204, 210, 220)),
        layout_jitter_meta=dict(layout_jitter_meta),
    )
