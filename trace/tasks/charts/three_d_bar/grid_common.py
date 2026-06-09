"""Shared constants, defaults, and types for 3D bar-grid chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ..shared.complexity import resolve_chart_complexity_weights
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_three_d_bar_grid_query_base"
SCENE_ID = "bar_3d"
AXIS_TOTAL_QUERY_IDS: Tuple[str, ...] = (
    "series_total_value",
    "category_total_value",
    "series_interval_total_value",
)
AXIS_GAP_QUERY_IDS: Tuple[str, ...] = (
    "series_total_gap_value",
    "category_total_gap_value",
    "category_extremum_gap_value",
)
CONDITION_COUNT_QUERY_IDS: Tuple[str, ...] = (
    "series_threshold_count",
    "category_threshold_count",
    "series_comparison_count",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = AXIS_TOTAL_QUERY_IDS + AXIS_GAP_QUERY_IDS + CONDITION_COUNT_QUERY_IDS

RGB = Tuple[int, int, int]
BBox = List[float]

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "three_d_bar")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="three_d_bar")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="three_d_bar", apply_prob=0.0)

_DEFAULT_PALETTE: Tuple[RGB, ...] = (
    (62, 121, 190),
    (219, 117, 68),
    (73, 157, 99),
    (151, 100, 186),
    (206, 166, 63),
    (73, 158, 176),
)
_QUERY_REASONING_LOAD: Dict[str, float] = {
    "series_total_value": 0.62,
    "category_total_value": 0.60,
    "series_interval_total_value": 0.66,
    "series_total_gap_value": 0.72,
    "category_total_gap_value": 0.70,
    "category_extremum_gap_value": 0.74,
    "series_threshold_count": 0.68,
    "category_threshold_count": 0.66,
    "series_comparison_count": 0.72,
}



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
class _BarCell:
    bar_id: str
    x_label: str
    series_label: str
    x_index: int
    series_index: int
    value: int
    color_rgb: RGB


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int
    annotation_bar_ids: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    x_labels: Tuple[str, ...]
    series_labels: Tuple[str, ...]
    bars: Tuple[_BarCell, ...]
    query: _Query


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
    bar_edge_width_px: int
    tick_length_px: int
    tick_font_size_px: int
    label_font_size_px: int
    value_font_size_px: int
    legend_font_size_px: int
    label_stroke_width_px: int
    axis_color_rgb: RGB
    grid_color_rgb: RGB
    plot_fill_rgb: RGB
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    text_color_rgb: RGB
    text_stroke_rgb: RGB
    legend_border_rgb: RGB
    bar_edge_rgb: RGB
    depth_axis_dx_px: int
    depth_axis_dy_px: int
    bar_face_dx_px: int
    bar_face_dy_px: int
    bar_width_px: int
    bar_style_variant: str
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedBarGrid:
    image: Image.Image
    plot_bbox_px: BBox
    y_axis_max: int
    y_ticks: Tuple[int, ...]
    entities: Tuple[Dict[str, Any], ...]
    bar_traces: Tuple[Dict[str, Any], ...]
    legend_traces: Tuple[Dict[str, Any], ...]
    layout_jitter_meta: Dict[str, Any]
    bar_style_meta: Dict[str, Any]


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _int_default(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _sample_bar_style_variant(params: Mapping[str, Any], *, instance_seed: int) -> str:
    explicit = params.get("bar_style_variant", group_default(_RENDER_DEFAULTS, "bar_style_variant", None))
    if explicit is not None:
        return str(explicit)
    raw_variants = params.get("bar_style_variants", group_default(_RENDER_DEFAULTS, "bar_style_variants", None))
    variants = (
        [str(value) for value in raw_variants if str(value)]
        if isinstance(raw_variants, Sequence) and not isinstance(raw_variants, (str, bytes))
        else []
    )
    if not variants:
        variants = ["solid", "front_highlight", "side_stripes", "top_ridge"]
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.bar_style")
    return str(variants[int(rng.randrange(len(variants)))])


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1120)))
    canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 760)))
    margin_left = int(params.get("plot_margin_left_px", group_default(_RENDER_DEFAULTS, "plot_margin_left_px", 104)))
    margin_right = int(params.get("plot_margin_right_px", group_default(_RENDER_DEFAULTS, "plot_margin_right_px", 190)))
    margin_top = int(params.get("plot_margin_top_px", group_default(_RENDER_DEFAULTS, "plot_margin_top_px", 68)))
    margin_bottom = int(params.get("plot_margin_bottom_px", group_default(_RENDER_DEFAULTS, "plot_margin_bottom_px", 124)))
    margin_left, margin_right, margin_top, margin_bottom, jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="charts.three_d_bar.layout",
    )
    return _RenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        plot_margin_left_px=int(margin_left),
        plot_margin_right_px=int(margin_right),
        plot_margin_top_px=int(margin_top),
        plot_margin_bottom_px=int(margin_bottom),
        axis_line_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "axis_line_width_px", 2, instance_seed=int(instance_seed), namespace=TASK_ID)),
        grid_line_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "grid_line_width_px", 1, instance_seed=int(instance_seed), namespace=TASK_ID)),
        bar_edge_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "bar_edge_width_px", 2, instance_seed=int(instance_seed), namespace=TASK_ID)),
        tick_length_px=int(params.get("tick_length_px", group_default(_RENDER_DEFAULTS, "tick_length_px", 8))),
        tick_font_size_px=int(params.get("tick_font_size_px", group_default(_RENDER_DEFAULTS, "tick_font_size_px", 15))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", 17))),
        value_font_size_px=int(params.get("value_font_size_px", group_default(_RENDER_DEFAULTS, "value_font_size_px", 14))),
        legend_font_size_px=int(params.get("legend_font_size_px", group_default(_RENDER_DEFAULTS, "legend_font_size_px", 17))),
        label_stroke_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "label_stroke_width_px", 2, instance_seed=int(instance_seed), namespace=TASK_ID)),
        axis_color_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "axis_color_rgb", (61, 65, 74), instance_seed=int(instance_seed), namespace=TASK_ID),
        grid_color_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "grid_color_rgb", (212, 218, 226), instance_seed=int(instance_seed), namespace=TASK_ID),
        plot_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "plot_fill_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID),
        panel_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_fill_rgb", (250, 252, 255), instance_seed=int(instance_seed), namespace=TASK_ID),
        panel_border_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_border_rgb", (181, 190, 204), instance_seed=int(instance_seed), namespace=TASK_ID),
        text_color_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_color_rgb", (35, 39, 46), instance_seed=int(instance_seed), namespace=TASK_ID),
        text_stroke_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_stroke_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID),
        legend_border_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "legend_border_rgb", (185, 193, 206), instance_seed=int(instance_seed), namespace=TASK_ID),
        bar_edge_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "bar_edge_rgb", (64, 68, 78), instance_seed=int(instance_seed), namespace=TASK_ID),
        depth_axis_dx_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "depth_axis_dx_px", 34, instance_seed=int(instance_seed), namespace=TASK_ID)),
        depth_axis_dy_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "depth_axis_dy_px", 24, instance_seed=int(instance_seed), namespace=TASK_ID)),
        bar_face_dx_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "bar_face_dx_px", 16, instance_seed=int(instance_seed), namespace=TASK_ID)),
        bar_face_dy_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "bar_face_dy_px", 12, instance_seed=int(instance_seed), namespace=TASK_ID)),
        bar_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "bar_width_px", 42, instance_seed=int(instance_seed), namespace=TASK_ID)),
        bar_style_variant=_sample_bar_style_variant(params, instance_seed=int(instance_seed)),
        layout_jitter_meta=dict(jitter_meta),
    )
