"""Synthetic 3D chart panel query tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_raw as _bbox_union
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import load_font, temporary_default_font_family
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import build_chart_complexity, clamp_unit_interval, normalize_int_with_bounds, resolve_chart_complexity_weights
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin
from ..shared.label_assets import resolve_chart_entity_labels
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import (
    chart_font_asset_metadata,
    load_chart_background_defaults,
    load_chart_noise_defaults,
    sample_chart_font_family,
)


TASK_ID = "charts_three_d_panel_query_base"
SCENE_ID = "surface_3d"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "reference_nearest_label",
    "surface_extremum_label",
    "series_trend_label",
    "panel_variation_label",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "three_d_scatter",
    "three_d_surface",
    "three_d_small_multiples",
)
_SUPPORTED_EXTREMA: Tuple[str, ...] = ("highest", "lowest")
_SUPPORTED_TRENDS: Tuple[str, ...] = ("increase", "decrease")
_TIME_POOL: Tuple[int, ...] = (2018, 2019, 2020, 2021, 2022, 2023, 2024)
_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (42, 104, 178),
    (216, 92, 74),
    (54, 148, 96),
    (139, 91, 183),
    (218, 143, 43),
    (75, 156, 190),
    (186, 85, 130),
    (108, 123, 60),
)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "reference_nearest_label": 0.62,
    "surface_extremum_label": 0.70,
    "series_trend_label": 0.74,
    "panel_variation_label": 0.76,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {
    "three_d_scatter": 0.72,
    "three_d_surface": 0.78,
    "three_d_small_multiples": 0.84,
}

RGB = Tuple[int, int, int]
BBox = List[float]

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "three_d")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="three_d")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="three_d", apply_prob=0.0)


@dataclass(frozen=True)
class _Point3D:
    point_id: str
    label: str
    x_value: float
    y_value: float
    z_value: float
    color_rgb: RGB
    shape: str = "circle"


@dataclass(frozen=True)
class _SurfaceCell:
    cell_id: str
    x_label: str
    y_label: str
    x_index: int
    y_index: int
    value: int


@dataclass(frozen=True)
class _Panel3D:
    panel_label: str
    values: Tuple[int, ...]
    color_rgb: RGB


@dataclass(frozen=True)
class _Query:
    query_id: str
    scene_variant: str
    answer: int | str
    answer_type: str
    evidence_point_ids: Tuple[str, ...] = ()
    evidence_cell_ids: Tuple[str, ...] = ()
    evidence_panel_labels: Tuple[str, ...] = ()
    trace: Dict[str, Any] | None = None


@dataclass(frozen=True)
class _Dataset:
    scene_variant: str
    points: Tuple[_Point3D, ...]
    surface_cells: Tuple[_SurfaceCell, ...]
    panels: Tuple[_Panel3D, ...]
    x_axis_label: str
    y_axis_label: str
    z_axis_label: str
    x_range: Tuple[float, float]
    y_range: Tuple[float, float]
    z_range: Tuple[float, float]
    x_labels: Tuple[str, ...]
    y_labels: Tuple[str, ...]
    query: _Query


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    plot_margin_left_px: int
    plot_margin_right_px: int
    plot_margin_top_px: int
    plot_margin_bottom_px: int
    panel_gap_px: int
    point_radius_px: int
    line_width_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    tick_font_size_px: int
    label_font_size_px: int
    title_font_size_px: int
    panel_title_font_size_px: int
    plot_fill_rgb: RGB
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    axis_color_rgb: RGB
    grid_color_rgb: RGB
    text_color_rgb: RGB
    text_stroke_rgb: RGB
    surface_low_rgb: RGB
    surface_high_rgb: RGB
    surface_edge_rgb: RGB
    marker_outline_rgb: RGB
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: BBox
    point_bboxes_px: Dict[str, BBox]
    surface_cell_bboxes_px: Dict[str, BBox]
    panel_bboxes_px: Dict[str, BBox]


def _bbox(values: Sequence[float]) -> BBox:
    return [round(float(value), 3) for value in values]


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    *,
    stroke_width: int = 0,
) -> BBox:
    try:
        box = draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        return _bbox(box)
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        return _bbox([float(xy[0]), float(xy[1]), float(xy[0]) + float(width), float(xy[1]) + float(height)])


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    *,
    font: ImageFont.ImageFont,
    fill: RGB,
    stroke_fill: RGB,
    stroke_width: int = 0,
    anchor: str | None = None,
) -> BBox:
    kwargs: Dict[str, Any] = {}
    if anchor is not None:
        kwargs["anchor"] = str(anchor)
    draw_text_traced(draw,
        (float(xy[0]), float(xy[1])),
        str(text),
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=max(0, int(stroke_width)),
        **kwargs,
     role="readout", required=False,)
    if anchor is None:
        return _text_bbox(draw, xy, str(text), font, stroke_width=max(0, int(stroke_width)))
    try:
        box = draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, stroke_width=max(0, int(stroke_width)), anchor=str(anchor))
        return _bbox(box)
    except Exception:
        return _bbox([float(xy[0]), float(xy[1]), float(xy[0]), float(xy[1])])


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


def _choice_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    return int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))


def _balanced_int(
    *,
    low: int,
    high: int,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    if int(low) > int(high):
        raise ValueError(f"invalid integer support for {namespace}")
    return int(low) + (_choice_index(params, instance_seed=int(instance_seed), namespace=str(namespace)) % (int(high) - int(low) + 1))


def _balanced_choice(values: Sequence[Any], *, params: Mapping[str, Any], instance_seed: int, namespace: str) -> Any:
    support = list(values)
    if not support:
        raise ValueError(f"empty support for {namespace}")
    return support[_choice_index(params, instance_seed=int(instance_seed), namespace=str(namespace)) % len(support)]


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


def _resolve_extremum(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_EXTREMA,
        task_id=TASK_ID,
        explicit_key="extremum_direction",
        weights_key="extremum_direction_weights",
        balance_flag_key="balanced_extremum_direction_sampling",
        axis_namespace="extremum_direction",
    )


def _resolve_trend(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_TRENDS,
        task_id=TASK_ID,
        explicit_key="trend_direction",
        weights_key="trend_direction_weights",
        balance_flag_key="balanced_trend_direction_sampling",
        axis_namespace="trend_direction",
    )


def _resolve_render_params(params: Mapping[str, Any]) -> _RenderParams:
    left = int(params.get("plot_margin_left_px", group_default(_RENDER_DEFAULTS, "plot_margin_left_px", 96)))
    right = int(params.get("plot_margin_right_px", group_default(_RENDER_DEFAULTS, "plot_margin_right_px", 72)))
    top = int(params.get("plot_margin_top_px", group_default(_RENDER_DEFAULTS, "plot_margin_top_px", 70)))
    bottom = int(params.get("plot_margin_bottom_px", group_default(_RENDER_DEFAULTS, "plot_margin_bottom_px", 112)))
    left, right, top, bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(left),
        right_px=int(right),
        top_px=int(top),
        bottom_px=int(bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=_render_style_seed(params),
        namespace=f"{TASK_ID}.layout",
    )
    return _RenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1280))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 860))),
        plot_margin_left_px=int(left),
        plot_margin_right_px=int(right),
        plot_margin_top_px=int(top),
        plot_margin_bottom_px=int(bottom),
        panel_gap_px=int(params.get("panel_gap_px", group_default(_RENDER_DEFAULTS, "panel_gap_px", 28))),
        point_radius_px=int(params.get("point_radius_px", group_default(_RENDER_DEFAULTS, "point_radius_px", 7))),
        line_width_px=int(params.get("line_width_px", group_default(_RENDER_DEFAULTS, "line_width_px", 3))),
        axis_line_width_px=int(params.get("axis_line_width_px", group_default(_RENDER_DEFAULTS, "axis_line_width_px", 2))),
        grid_line_width_px=int(params.get("grid_line_width_px", group_default(_RENDER_DEFAULTS, "grid_line_width_px", 1))),
        tick_font_size_px=int(params.get("tick_font_size_px", group_default(_RENDER_DEFAULTS, "tick_font_size_px", 16))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", 21))),
        title_font_size_px=int(params.get("title_font_size_px", group_default(_RENDER_DEFAULTS, "title_font_size_px", 28))),
        panel_title_font_size_px=int(params.get("panel_title_font_size_px", group_default(_RENDER_DEFAULTS, "panel_title_font_size_px", 18))),
        plot_fill_rgb=_resolve_rgb(params, "plot_fill_rgb", (248, 251, 255)),
        panel_fill_rgb=_resolve_rgb(params, "panel_fill_rgb", (255, 255, 255)),
        panel_border_rgb=_resolve_rgb(params, "panel_border_rgb", (200, 207, 218)),
        axis_color_rgb=_resolve_rgb(params, "axis_color_rgb", (63, 69, 79)),
        grid_color_rgb=_resolve_rgb(params, "grid_color_rgb", (216, 223, 234)),
        text_color_rgb=_resolve_rgb(params, "text_color_rgb", (35, 39, 47)),
        text_stroke_rgb=_resolve_rgb(params, "text_stroke_rgb", (255, 255, 255)),
        surface_low_rgb=_resolve_rgb(params, "surface_low_rgb", (93, 141, 202)),
        surface_high_rgb=_resolve_rgb(params, "surface_high_rgb", (214, 91, 76)),
        surface_edge_rgb=_resolve_rgb(params, "surface_edge_rgb", (102, 110, 96)),
        marker_outline_rgb=_resolve_rgb(params, "marker_outline_rgb", (34, 42, 54)),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def _sample_labels(count: int, *, instance_seed: int, namespace: str) -> Tuple[str, ...]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace}.labels")
    labels = resolve_chart_entity_labels(
        rng,
        count=int(count),
        min_chars=2,
        max_chars=6,
        allow_spaces=False,
    ).labels
    return tuple(str(label) for label in labels)


def _value_to_unit(value: float, value_range: Tuple[float, float]) -> float:
    low, high = float(value_range[0]), float(value_range[1])
    if math.isclose(low, high):
        return 0.0
    return max(0.0, min(1.0, (float(value) - low) / (high - low)))


def _project_3d(
    x_value: float,
    y_value: float,
    z_value: float,
    *,
    plot_bbox: Sequence[float],
    x_range: Tuple[float, float],
    y_range: Tuple[float, float],
    z_range: Tuple[float, float],
) -> Tuple[float, float]:
    left, top, right, bottom = [float(value) for value in plot_bbox]
    width = max(1.0, right - left)
    height = max(1.0, bottom - top)
    origin = (left + 0.18 * width, bottom - 0.10 * height)
    x_vec = (0.52 * width, -0.14 * height)
    y_vec = (0.24 * width, -0.24 * height)
    z_vec = (0.0, -0.56 * height)
    x_unit = _value_to_unit(float(x_value), x_range)
    y_unit = _value_to_unit(float(y_value), y_range)
    z_unit = _value_to_unit(float(z_value), z_range)
    return (
        float(origin[0] + x_unit * x_vec[0] + y_unit * y_vec[0] + z_unit * z_vec[0]),
        float(origin[1] + x_unit * x_vec[1] + y_unit * y_vec[1] + z_unit * z_vec[1]),
    )


def _blend(low: RGB, high: RGB, value: float) -> RGB:
    weight = max(0.0, min(1.0, float(value)))
    return tuple(int(round((1.0 - weight) * float(a) + weight * float(b))) for a, b in zip(low, high))


def _point_bbox(px: float, py: float, radius: float) -> BBox:
    return _bbox([float(px) - float(radius), float(py) - float(radius), float(px) + float(radius), float(py) + float(radius)])


def _draw_3d_axes(
    draw: ImageDraw.ImageDraw,
    *,
    plot_bbox: Sequence[float],
    x_range: Tuple[float, float],
    y_range: Tuple[float, float],
    z_range: Tuple[float, float],
    x_axis_label: str,
    y_axis_label: str,
    z_axis_label: str,
    params: _RenderParams,
    tick_values: Sequence[float] = (0.0, 0.5, 1.0),
    x_tick_labels: Sequence[str] | None = None,
    y_tick_labels: Sequence[str] | None = None,
    label_xy_ticks: bool = True,
    label_z_ticks: bool = True,
) -> None:
    axis_font = load_font(max(12, int(params.tick_font_size_px)), bold=True)
    label_font = load_font(max(14, int(params.label_font_size_px)), bold=True)
    x0, y0 = _project_3d(x_range[0], y_range[0], z_range[0], plot_bbox=plot_bbox, x_range=x_range, y_range=y_range, z_range=z_range)
    x_tip = _project_3d(x_range[1], y_range[0], z_range[0], plot_bbox=plot_bbox, x_range=x_range, y_range=y_range, z_range=z_range)
    y_tip = _project_3d(x_range[0], y_range[1], z_range[0], plot_bbox=plot_bbox, x_range=x_range, y_range=y_range, z_range=z_range)
    z_tip = _project_3d(x_range[0], y_range[0], z_range[1], plot_bbox=plot_bbox, x_range=x_range, y_range=y_range, z_range=z_range)
    for start, end in [((x0, y0), x_tip), ((x0, y0), y_tip), ((x0, y0), z_tip)]:
        draw.line([start, end], fill=params.axis_color_rgb, width=max(2, int(params.axis_line_width_px)))

    for tick in tick_values:
        xv = float(x_range[0]) + float(tick) * (float(x_range[1]) - float(x_range[0]))
        yv = float(y_range[0]) + float(tick) * (float(y_range[1]) - float(y_range[0]))
        zv = float(z_range[0]) + float(tick) * (float(z_range[1]) - float(z_range[0]))
        x_base = _project_3d(xv, y_range[0], z_range[0], plot_bbox=plot_bbox, x_range=x_range, y_range=y_range, z_range=z_range)
        x_grid = _project_3d(xv, y_range[1], z_range[0], plot_bbox=plot_bbox, x_range=x_range, y_range=y_range, z_range=z_range)
        y_base = _project_3d(x_range[0], yv, z_range[0], plot_bbox=plot_bbox, x_range=x_range, y_range=y_range, z_range=z_range)
        y_grid = _project_3d(x_range[1], yv, z_range[0], plot_bbox=plot_bbox, x_range=x_range, y_range=y_range, z_range=z_range)
        z_base = _project_3d(x_range[0], y_range[0], zv, plot_bbox=plot_bbox, x_range=x_range, y_range=y_range, z_range=z_range)
        z_grid_x = _project_3d(x_range[1], y_range[0], zv, plot_bbox=plot_bbox, x_range=x_range, y_range=y_range, z_range=z_range)
        z_grid_y = _project_3d(x_range[0], y_range[1], zv, plot_bbox=plot_bbox, x_range=x_range, y_range=y_range, z_range=z_range)
        draw.line([x_base, x_grid], fill=params.grid_color_rgb, width=max(1, int(params.grid_line_width_px)))
        draw.line([y_base, y_grid], fill=params.grid_color_rgb, width=max(1, int(params.grid_line_width_px)))
        draw.line([z_base, z_grid_x], fill=params.grid_color_rgb, width=max(1, int(params.grid_line_width_px)))
        draw.line([z_base, z_grid_y], fill=params.grid_color_rgb, width=max(1, int(params.grid_line_width_px)))
        xi = int(round(float(tick) * (len(x_tick_labels or ()) - 1))) if x_tick_labels else -1
        yi = int(round(float(tick) * (len(y_tick_labels or ()) - 1))) if y_tick_labels else -1
        x_label = str(x_tick_labels[xi]) if x_tick_labels and 0 <= xi < len(x_tick_labels) else str(int(round(xv)))
        y_label = str(y_tick_labels[yi]) if y_tick_labels and 0 <= yi < len(y_tick_labels) else str(int(round(yv)))
        z_label = str(int(round(zv)))
        if label_xy_ticks:
            _draw_text(draw, (x_base[0], x_base[1] + 20), x_label, font=axis_font, fill=params.text_color_rgb, stroke_fill=params.text_stroke_rgb, stroke_width=2, anchor="mt")
            _draw_text(draw, (y_base[0] - 15, y_base[1] + 6), y_label, font=axis_font, fill=params.text_color_rgb, stroke_fill=params.text_stroke_rgb, stroke_width=2, anchor="rt")
        if label_z_ticks:
            _draw_text(draw, (z_base[0] - 13, z_base[1]), z_label, font=axis_font, fill=params.text_color_rgb, stroke_fill=params.text_stroke_rgb, stroke_width=2, anchor="rm")

    if str(x_axis_label).strip():
        _draw_text(draw, (x_tip[0] + 52, x_tip[1] + 22), x_axis_label, font=label_font, fill=params.text_color_rgb, stroke_fill=params.text_stroke_rgb, stroke_width=2, anchor="lm")
    if str(y_axis_label).strip():
        _draw_text(draw, (y_tip[0] + 72, y_tip[1] + 54), y_axis_label, font=label_font, fill=params.text_color_rgb, stroke_fill=params.text_stroke_rgb, stroke_width=2, anchor="lm")
    if str(z_axis_label).strip():
        _draw_text(draw, (z_tip[0] - 86, z_tip[1] - 10), z_axis_label, font=label_font, fill=params.text_color_rgb, stroke_fill=params.text_stroke_rgb, stroke_width=2, anchor="rm")


def _draw_categorical_axis_labels(
    draw: ImageDraw.ImageDraw,
    *,
    plot_bbox: Sequence[float],
    dataset: _Dataset,
    params: _RenderParams,
) -> None:
    tick_font = load_font(max(12, int(params.tick_font_size_px)), bold=True)
    for x_index, x_label in enumerate(dataset.x_labels):
        px, py = _project_3d(
            float(x_index),
            dataset.y_range[0],
            dataset.z_range[0],
            plot_bbox=plot_bbox,
            x_range=dataset.x_range,
            y_range=dataset.y_range,
            z_range=dataset.z_range,
        )
        _draw_text(
            draw,
            (px, py + 24),
            str(x_label),
            font=tick_font,
            fill=params.text_color_rgb,
            stroke_fill=params.text_stroke_rgb,
            stroke_width=2,
            anchor="mt",
        )
    for y_index, y_label in enumerate(dataset.y_labels):
        px, py = _project_3d(
            dataset.x_range[0],
            float(y_index),
            dataset.z_range[0],
            plot_bbox=plot_bbox,
            x_range=dataset.x_range,
            y_range=dataset.y_range,
            z_range=dataset.z_range,
        )
        _draw_text(
            draw,
            (px - 20, py + 4),
            str(y_label),
            font=tick_font,
            fill=params.text_color_rgb,
            stroke_fill=params.text_stroke_rgb,
            stroke_width=2,
            anchor="rt",
        )


def _draw_point_label(
    draw: ImageDraw.ImageDraw,
    *,
    point_xy: Tuple[float, float],
    label: str,
    font: ImageFont.ImageFont,
    params: _RenderParams,
    radius: float,
) -> None:
    px, py = float(point_xy[0]), float(point_xy[1])
    candidates = (
        ((px + radius + 8.0, py - radius - 8.0), "lt"),
        ((px - radius - 8.0, py - radius - 8.0), "rt"),
        ((px + radius + 8.0, py + radius + 8.0), "la"),
        ((px - radius - 8.0, py + radius + 8.0), "ra"),
    )
    pad = 10.0
    best_xy, best_anchor = candidates[0]
    for xy, anchor in candidates:
        try:
            box = _bbox(draw.textbbox(xy, str(label), font=font, stroke_width=2, anchor=anchor))
        except Exception:
            box = _text_bbox(draw, xy, str(label), font, stroke_width=2)
        if pad <= box[0] and box[2] <= float(params.canvas_width) - pad and pad <= box[1] and box[3] <= float(params.canvas_height) - pad:
            best_xy, best_anchor = xy, anchor
            break
    _draw_text(
        draw,
        best_xy,
        str(label),
        font=font,
        fill=params.text_color_rgb,
        stroke_fill=params.text_stroke_rgb,
        stroke_width=2,
        anchor=best_anchor,
    )


def _draw_point(
    draw: ImageDraw.ImageDraw,
    *,
    point: _Point3D,
    plot_bbox: Sequence[float],
    dataset: _Dataset,
    params: _RenderParams,
    point_font: ImageFont.ImageFont,
    label_points: bool = True,
) -> BBox:
    px, py = _project_3d(
        point.x_value,
        point.y_value,
        point.z_value,
        plot_bbox=plot_bbox,
        x_range=dataset.x_range,
        y_range=dataset.y_range,
        z_range=dataset.z_range,
    )
    radius = float(params.point_radius_px)
    bbox = _point_bbox(px, py, radius)
    if point.shape == "square":
        draw.rounded_rectangle(bbox, radius=2, fill=point.color_rgb, outline=params.marker_outline_rgb, width=2)
    elif point.shape == "triangle":
        draw.polygon([(px, py - radius), (px - radius, py + radius), (px + radius, py + radius)], fill=point.color_rgb, outline=params.marker_outline_rgb)
    else:
        draw.ellipse(bbox, fill=point.color_rgb, outline=params.marker_outline_rgb, width=2)
    if label_points and point.label:
        _draw_point_label(draw, point_xy=(px, py), label=point.label, font=point_font, params=params, radius=radius)
    return bbox


def _render_scatter_or_lines(
    image: Image.Image,
    *,
    dataset: _Dataset,
    params: _RenderParams,
    title: str,
    connect_by_label: bool = False,
) -> _Rendered:
    draw = ImageDraw.Draw(image)
    plot_bbox = [
        float(params.plot_margin_left_px),
        float(params.plot_margin_top_px),
        float(params.canvas_width - params.plot_margin_right_px),
        float(params.canvas_height - params.plot_margin_bottom_px),
    ]
    title_font = load_font(int(params.title_font_size_px), bold=True)
    point_font = load_font(max(15, int(params.label_font_size_px) - 2), bold=True)
    draw.rounded_rectangle(
        [plot_bbox[0] - 42, plot_bbox[1] - 50, plot_bbox[2] + 42, plot_bbox[3] + 68],
        radius=8,
        fill=params.panel_fill_rgb,
        outline=params.panel_border_rgb,
        width=2,
    )
    draw.rectangle(plot_bbox, fill=params.plot_fill_rgb)
    _draw_text(draw, (plot_bbox[0], plot_bbox[1] - 38), title, font=title_font, fill=params.text_color_rgb, stroke_fill=params.text_stroke_rgb, stroke_width=1)
    x_ticks = dataset.x_labels if dataset.x_labels else None
    y_ticks = dataset.y_labels if dataset.y_labels else None
    _draw_3d_axes(
        draw,
        plot_bbox=plot_bbox,
        x_range=dataset.x_range,
        y_range=dataset.y_range,
        z_range=dataset.z_range,
        x_axis_label=dataset.x_axis_label,
        y_axis_label=dataset.y_axis_label,
        z_axis_label=dataset.z_axis_label,
        params=params,
        tick_values=(0.0, 0.25, 0.5, 0.75, 1.0),
        x_tick_labels=x_ticks,
        y_tick_labels=y_ticks,
    )
    point_bboxes: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []
    if connect_by_label:
        by_label: Dict[str, List[_Point3D]] = {}
        for point in dataset.points:
            by_label.setdefault(str(point.label), []).append(point)
        for label, points in by_label.items():
            ordered = sorted(points, key=lambda item: float(item.x_value))
            projected = [
                _project_3d(p.x_value, p.y_value, p.z_value, plot_bbox=plot_bbox, x_range=dataset.x_range, y_range=dataset.y_range, z_range=dataset.z_range)
                for p in ordered
            ]
            if len(projected) >= 2:
                draw.line(projected, fill=ordered[0].color_rgb, width=int(params.line_width_px))
            entities.append({"entity_id": f"series_{label}", "entity_type": "series_3d", "bbox_xyxy": _bbox_union([_point_bbox(px, py, params.point_radius_px) for px, py in projected]), "attrs": {"label": str(label)}})
    for point in sorted(dataset.points, key=lambda item: (float(item.y_value), float(item.x_value), float(item.z_value))):
        bbox = _draw_point(
            draw,
            point=point,
            plot_bbox=plot_bbox,
            dataset=dataset,
            params=params,
            point_font=point_font,
            label_points=not connect_by_label or str(point.point_id).endswith("_0"),
        )
        point_bboxes[str(point.point_id)] = bbox
        entities.append(
            {
                "entity_id": str(point.point_id),
                "entity_type": "point_3d",
                "bbox_xyxy": list(bbox),
                "attrs": {
                    "label": str(point.label),
                    "x_value": round(float(point.x_value), 3),
                    "y_value": round(float(point.y_value), 3),
                    "z_value": round(float(point.z_value), 3),
                },
            }
        )
    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=_bbox(plot_bbox),
        point_bboxes_px=dict(point_bboxes),
        surface_cell_bboxes_px={},
        panel_bboxes_px={},
    )


def _render_surface(image: Image.Image, *, dataset: _Dataset, params: _RenderParams) -> _Rendered:
    draw = ImageDraw.Draw(image)
    plot_bbox = [
        float(params.plot_margin_left_px),
        float(params.plot_margin_top_px),
        float(params.canvas_width - params.plot_margin_right_px),
        float(params.canvas_height - params.plot_margin_bottom_px),
    ]
    title_font = load_font(int(params.title_font_size_px), bold=True)
    draw.rounded_rectangle(
        [plot_bbox[0] - 42, plot_bbox[1] - 50, plot_bbox[2] + 42, plot_bbox[3] + 68],
        radius=8,
        fill=params.panel_fill_rgb,
        outline=params.panel_border_rgb,
        width=2,
    )
    draw.rectangle(plot_bbox, fill=params.plot_fill_rgb)
    _draw_text(draw, (plot_bbox[0], plot_bbox[1] - 38), "3D Surface Chart", font=title_font, fill=params.text_color_rgb, stroke_fill=params.text_stroke_rgb, stroke_width=1)
    _draw_3d_axes(
        draw,
        plot_bbox=plot_bbox,
        x_range=dataset.x_range,
        y_range=dataset.y_range,
        z_range=dataset.z_range,
        x_axis_label=dataset.x_axis_label,
        y_axis_label=dataset.y_axis_label,
        z_axis_label=dataset.z_axis_label,
        params=params,
        x_tick_labels=dataset.x_labels,
        y_tick_labels=dataset.y_labels,
        label_xy_ticks=False,
    )
    _draw_categorical_axis_labels(draw, plot_bbox=plot_bbox, dataset=dataset, params=params)
    x_count = len(dataset.x_labels)
    y_count = len(dataset.y_labels)
    values_by_xy = {(cell.x_index, cell.y_index): int(cell.value) for cell in dataset.surface_cells}
    cells_by_xy = {(cell.x_index, cell.y_index): cell for cell in dataset.surface_cells}
    cell_bboxes: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []
    value_low, value_high = dataset.z_range
    for y_index in reversed(range(y_count - 1)):
        for x_index in range(x_count - 1):
            corners = []
            corner_values = []
            for dx, dy in ((0, 0), (1, 0), (1, 1), (0, 1)):
                xv = float(x_index + dx)
                yv = float(y_index + dy)
                z = float(values_by_xy[(x_index + dx, y_index + dy)])
                corner_values.append(z)
                corners.append(
                    _project_3d(
                        xv,
                        yv,
                        z,
                        plot_bbox=plot_bbox,
                        x_range=dataset.x_range,
                        y_range=dataset.y_range,
                        z_range=dataset.z_range,
                    )
                )
            color = _blend(params.surface_low_rgb, params.surface_high_rgb, (sum(corner_values) / len(corner_values) - value_low) / max(1.0, value_high - value_low))
            draw.polygon(corners, fill=color)
            draw.line([*corners, corners[0]], fill=params.surface_edge_rgb, width=max(1, int(params.grid_line_width_px)))
    point_font = load_font(max(14, int(params.label_font_size_px) - 4), bold=True)
    for cell in dataset.surface_cells:
        px, py = _project_3d(
            float(cell.x_index),
            float(cell.y_index),
            float(cell.value),
            plot_bbox=plot_bbox,
            x_range=dataset.x_range,
            y_range=dataset.y_range,
            z_range=dataset.z_range,
        )
        radius = max(4.0, float(params.point_radius_px) - 2.0)
        bbox = _point_bbox(px, py, radius)
        draw.ellipse(bbox, fill=(255, 255, 255), outline=params.marker_outline_rgb, width=2)
        cell_bboxes[str(cell.cell_id)] = bbox
        entities.append(
            {
                "entity_id": str(cell.cell_id),
                "entity_type": "surface_cell",
                "bbox_xyxy": list(bbox),
                "attrs": {
                    "x_label": str(cell.x_label),
                    "y_label": str(cell.y_label),
                    "x_index": int(cell.x_index),
                    "y_index": int(cell.y_index),
                    "value": int(cell.value),
                },
            }
        )
    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=_bbox(plot_bbox),
        point_bboxes_px={},
        surface_cell_bboxes_px=dict(cell_bboxes),
        panel_bboxes_px={},
    )


def _render_small_multiples(image: Image.Image, *, dataset: _Dataset, params: _RenderParams) -> _Rendered:
    draw = ImageDraw.Draw(image)
    title_font = load_font(int(params.title_font_size_px), bold=True)
    panel_font = load_font(int(params.panel_title_font_size_px), bold=True)
    _draw_text(draw, (46, 28), "3D Panel Comparison", font=title_font, fill=params.text_color_rgb, stroke_fill=params.text_stroke_rgb, stroke_width=1)
    cols = 3 if len(dataset.panels) > 4 else 2
    rows = int(math.ceil(len(dataset.panels) / cols))
    outer_left = float(params.plot_margin_left_px)
    outer_top = float(params.plot_margin_top_px)
    outer_right = float(params.canvas_width - params.plot_margin_right_px)
    outer_bottom = float(params.canvas_height - params.plot_margin_bottom_px)
    gap = float(params.panel_gap_px)
    panel_w = (outer_right - outer_left - gap * float(cols - 1)) / float(cols)
    panel_h = (outer_bottom - outer_top - gap * float(rows - 1)) / float(rows)
    panel_bboxes: Dict[str, BBox] = {}
    point_bboxes: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []
    for index, panel in enumerate(dataset.panels):
        col = index % cols
        row = index // cols
        box = [
            outer_left + float(col) * (panel_w + gap),
            outer_top + float(row) * (panel_h + gap),
            outer_left + float(col) * (panel_w + gap) + panel_w,
            outer_top + float(row) * (panel_h + gap) + panel_h,
        ]
        panel_bboxes[str(panel.panel_label)] = _bbox(box)
        draw.rounded_rectangle(box, radius=7, fill=params.panel_fill_rgb, outline=params.panel_border_rgb, width=2)
        _draw_text(draw, (box[0] + 12, box[1] + 10), f"Panel {panel.panel_label}", font=panel_font, fill=params.text_color_rgb, stroke_fill=params.text_stroke_rgb, stroke_width=1)
        plot_bbox = [box[0] + 34, box[1] + 46, box[2] - 30, box[3] - 30]
        mini_params = params
        _draw_3d_axes(
            draw,
            plot_bbox=plot_bbox,
            x_range=dataset.x_range,
            y_range=dataset.y_range,
            z_range=dataset.z_range,
            x_axis_label="",
            y_axis_label="",
            z_axis_label="",
            params=mini_params,
            tick_values=(0.0, 1.0),
            label_xy_ticks=False,
            label_z_ticks=False,
        )
        projected = []
        for step, value in enumerate(panel.values):
            point = _Point3D(
                point_id=f"panel_{panel.panel_label}_point_{step}",
                label=str(panel.panel_label),
                x_value=float(step),
                y_value=float(step % 2),
                z_value=float(value),
                color_rgb=panel.color_rgb,
            )
            px, py = _project_3d(point.x_value, point.y_value, point.z_value, plot_bbox=plot_bbox, x_range=dataset.x_range, y_range=dataset.y_range, z_range=dataset.z_range)
            projected.append((px, py))
            bbox = _point_bbox(px, py, max(4.0, float(params.point_radius_px) - 2.0))
            point_bboxes[str(point.point_id)] = bbox
        if len(projected) >= 2:
            draw.line(projected, fill=panel.color_rgb, width=max(2, int(params.line_width_px)))
        for step, (px, py) in enumerate(projected):
            bbox = point_bboxes[f"panel_{panel.panel_label}_point_{step}"]
            draw.ellipse(bbox, fill=panel.color_rgb, outline=params.marker_outline_rgb, width=1)
        entities.append(
            {
                "entity_id": f"panel_{panel.panel_label}",
                "entity_type": "three_d_panel",
                "bbox_xyxy": list(panel_bboxes[str(panel.panel_label)]),
                "attrs": {
                    "panel_label": str(panel.panel_label),
                    "values": [int(value) for value in panel.values],
                    "value_range": int(max(panel.values) - min(panel.values)),
                },
            }
        )
    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=_bbox([outer_left, outer_top, outer_right, outer_bottom]),
        point_bboxes_px=dict(point_bboxes),
        surface_cell_bboxes_px={},
        panel_bboxes_px=dict(panel_bboxes),
    )


def _dataset_reference_nearest(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    category_count = _balanced_int(
        low=_gen_int(params, "category_count_min", 5),
        high=_gen_int(params, "category_count_max", 8),
        params=params,
        instance_seed=instance_seed,
        namespace="nearest.category_count",
    )
    target_value = _balanced_int(low=25, high=75, params=params, instance_seed=instance_seed, namespace="nearest.target")
    labels = _sample_labels(int(category_count), instance_seed=instance_seed, namespace="nearest")
    answer_label = str(_balanced_choice(labels, params=params, instance_seed=instance_seed, namespace="nearest.answer_label"))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.nearest.points")
    points: List[_Point3D] = []
    for index, label in enumerate(labels):
        if str(label) == answer_label:
            y_value = float(target_value + rng.choice([-2, -1, 1, 2]))
        else:
            offset = int(rng.choice([-1, 1])) * int(rng.randint(8, 31))
            y_value = float(max(5, min(95, int(target_value) + int(offset))))
            if abs(y_value - float(target_value)) <= 5:
                y_value = float(max(5, min(95, int(target_value) + (12 if offset >= 0 else -12))))
        points.append(
            _Point3D(
                point_id=f"point_{label}",
                label=str(label),
                x_value=float(rng.randint(8, 92)),
                y_value=float(y_value),
                z_value=float(rng.randint(8, 92)),
                color_rgb=_PALETTE[int(index) % len(_PALETTE)],
            )
        )
    distances = {str(point.label): round(abs(float(point.y_value) - float(target_value)), 3) for point in points}
    return _Dataset(
        scene_variant="three_d_scatter",
        points=tuple(points),
        surface_cells=(),
        panels=(),
        x_axis_label="Score",
        y_axis_label="Distance",
        z_axis_label="Volume",
        x_range=(0.0, 100.0),
        y_range=(0.0, 100.0),
        z_range=(0.0, 100.0),
        x_labels=(),
        y_labels=(),
        query=_Query(
            query_id="reference_nearest_label",
            scene_variant="three_d_scatter",
            answer=str(answer_label),
            answer_type="string",
            evidence_point_ids=(f"point_{answer_label}",),
            trace={
                "target_axis": "y",
                "target_axis_label": "Distance",
                "target_axis_value": int(target_value),
                "distances_from_target": dict(distances),
                "category_count": int(category_count),
            },
        ),
    )


def _dataset_surface_extremum(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    x_count = _balanced_int(low=_gen_int(params, "surface_x_count_min", 5), high=_gen_int(params, "surface_x_count_max", 7), params=params, instance_seed=instance_seed, namespace="surface.x_count")
    y_count = _balanced_int(low=_gen_int(params, "surface_y_count_min", 4), high=_gen_int(params, "surface_y_count_max", 6), params=params, instance_seed=instance_seed, namespace="surface.y_count")
    extremum, extremum_probabilities = _resolve_extremum(params, instance_seed=instance_seed)
    x_labels = _sample_labels(int(x_count), instance_seed=instance_seed, namespace="surface.x")
    y_labels = _sample_labels(int(y_count), instance_seed=instance_seed, namespace="surface.y")
    target_y = str(_balanced_choice(y_labels, params=params, instance_seed=instance_seed, namespace="surface.target_y"))
    answer_x = str(_balanced_choice(x_labels, params=params, instance_seed=instance_seed, namespace=f"surface.answer_x:{target_y}:{extremum}"))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.surface.values")
    cells: List[_SurfaceCell] = []
    for y_index, y_label in enumerate(y_labels):
        row_values = [int(rng.randint(25, 74)) for _ in range(int(x_count))]
        if str(y_label) == target_y:
            answer_index = list(x_labels).index(answer_x)
            if str(extremum) == "highest":
                row_values = [int(min(value, 70)) for value in row_values]
                row_values[answer_index] = int(rng.randint(86, 96))
            else:
                row_values = [int(max(value, 30)) for value in row_values]
                row_values[answer_index] = int(rng.randint(7, 16))
        for x_index, x_label in enumerate(x_labels):
            cells.append(
                _SurfaceCell(
                    cell_id=f"cell_{x_label}_{y_label}",
                    x_label=str(x_label),
                    y_label=str(y_label),
                    x_index=int(x_index),
                    y_index=int(y_index),
                    value=int(row_values[x_index]),
                )
            )
    row_values_by_x = {str(cell.x_label): int(cell.value) for cell in cells if str(cell.y_label) == target_y}
    return _Dataset(
        scene_variant="three_d_surface",
        points=(),
        surface_cells=tuple(cells),
        panels=(),
        x_axis_label="Platform",
        y_axis_label="Group",
        z_axis_label="Value",
        x_range=(0.0, float(max(1, int(x_count) - 1))),
        y_range=(0.0, float(max(1, int(y_count) - 1))),
        z_range=(0.0, 100.0),
        x_labels=tuple(x_labels),
        y_labels=tuple(y_labels),
        query=_Query(
            query_id="surface_extremum_label",
            scene_variant="three_d_surface",
            answer=str(answer_x),
            answer_type="string",
            evidence_cell_ids=(f"cell_{answer_x}_{target_y}",),
            trace={
                "target_y_category": str(target_y),
                "extremum_direction": str(extremum),
                "extremum_direction_probabilities": dict(extremum_probabilities),
                "row_values_by_x": dict(row_values_by_x),
                "x_count": int(x_count),
                "y_count": int(y_count),
            },
        ),
    )


def _dataset_series_trend(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    series_count = _balanced_int(low=_gen_int(params, "series_count_min", 4), high=_gen_int(params, "series_count_max", 6), params=params, instance_seed=instance_seed, namespace="trend.series_count")
    time_count = _balanced_int(low=_gen_int(params, "time_count_min", 5), high=_gen_int(params, "time_count_max", 7), params=params, instance_seed=instance_seed, namespace="trend.time_count")
    trend_direction, trend_probabilities = _resolve_trend(params, instance_seed=instance_seed)
    labels = _sample_labels(int(series_count), instance_seed=instance_seed, namespace="trend.series")
    answer_label = str(_balanced_choice(labels, params=params, instance_seed=instance_seed, namespace=f"trend.answer:{trend_direction}"))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.trend.values")
    points: List[_Point3D] = []
    deltas: Dict[str, int] = {}
    for series_index, label in enumerate(labels):
        if str(label) == answer_label:
            delta = int(rng.randint(38, 55)) * (1 if str(trend_direction) == "increase" else -1)
        else:
            delta = int(rng.randint(-24, 28))
            if str(trend_direction) == "increase":
                delta = min(int(delta), 24)
            else:
                delta = max(int(delta), -24)
        start_low = 18 if delta >= 0 else 58
        start_high = 38 if delta >= 0 else 82
        start = int(rng.randint(start_low, start_high))
        end = max(5, min(96, int(start) + int(delta)))
        deltas[str(label)] = int(end) - int(start)
        for time_index in range(int(time_count)):
            t = float(time_index) / float(max(1, int(time_count) - 1))
            value = float(start) + (float(end - start) * t) + rng.uniform(-3.0, 3.0)
            points.append(
                _Point3D(
                    point_id=f"series_{label}_{time_index}",
                    label=str(label),
                    x_value=float(time_index),
                    y_value=float(series_index),
                    z_value=max(0.0, min(100.0, float(value))),
                    color_rgb=_PALETTE[int(series_index) % len(_PALETTE)],
                )
            )
    return _Dataset(
        scene_variant="three_d_scatter",
        points=tuple(points),
        surface_cells=(),
        panels=(),
        x_axis_label="Year",
        y_axis_label="Series",
        z_axis_label="Value",
        x_range=(0.0, float(max(1, int(time_count) - 1))),
        y_range=(0.0, float(max(1, int(series_count) - 1))),
        z_range=(0.0, 100.0),
        x_labels=tuple(str(value) for value in _TIME_POOL[: int(time_count)]),
        y_labels=tuple(labels),
        query=_Query(
            query_id="series_trend_label",
            scene_variant="three_d_scatter",
            answer=str(answer_label),
            answer_type="string",
            evidence_point_ids=(
                f"series_{answer_label}_0",
                f"series_{answer_label}_{int(time_count) - 1}",
            ),
            trace={
                "trend_direction": str(trend_direction),
                "trend_direction_probabilities": dict(trend_probabilities),
                "series_count": int(series_count),
                "time_count": int(time_count),
                "deltas_by_series": dict(deltas),
            },
        ),
    )


def _dataset_panel_variation(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    panel_count = _balanced_int(low=_gen_int(params, "panel_count_min", 4), high=_gen_int(params, "panel_count_max", 6), params=params, instance_seed=instance_seed, namespace="panel.panel_count")
    time_count = _balanced_int(low=5, high=7, params=params, instance_seed=instance_seed, namespace="panel.time_count")
    labels = _sample_labels(int(panel_count), instance_seed=instance_seed, namespace="panel")
    answer_label = str(_balanced_choice(labels, params=params, instance_seed=instance_seed, namespace="panel.answer"))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.panel.values")
    panels: List[_Panel3D] = []
    ranges: Dict[str, int] = {}
    for index, label in enumerate(labels):
        if str(label) == answer_label:
            low = int(rng.randint(8, 20))
            high = int(rng.randint(80, 96))
        else:
            low = int(rng.randint(22, 42))
            high = int(rng.randint(55, 74))
        values = [int(round(low + (high - low) * (step / max(1, time_count - 1)) + rng.uniform(-5, 5))) for step in range(int(time_count))]
        if str(label) == answer_label:
            values[0] = low
            values[-1] = high
        values = [max(0, min(100, int(value))) for value in values]
        ranges[str(label)] = int(max(values) - min(values))
        panels.append(_Panel3D(panel_label=str(label), values=tuple(values), color_rgb=_PALETTE[int(index) % len(_PALETTE)]))
    return _Dataset(
        scene_variant="three_d_small_multiples",
        points=(),
        surface_cells=(),
        panels=tuple(panels),
        x_axis_label="Step",
        y_axis_label="Band",
        z_axis_label="Value",
        x_range=(0.0, float(max(1, int(time_count) - 1))),
        y_range=(0.0, 1.0),
        z_range=(0.0, 100.0),
        x_labels=(),
        y_labels=(),
        query=_Query(
            query_id="panel_variation_label",
            scene_variant="three_d_small_multiples",
            answer=str(answer_label),
            answer_type="string",
            evidence_panel_labels=(str(answer_label),),
            trace={
                "panel_count": int(panel_count),
                "time_count": int(time_count),
                "ranges_by_panel": dict(ranges),
            },
        ),
    )


def _build_dataset(query_id: str, params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    if str(query_id) == "reference_nearest_label":
        return _dataset_reference_nearest(params, instance_seed=int(instance_seed))
    if str(query_id) == "surface_extremum_label":
        return _dataset_surface_extremum(params, instance_seed=int(instance_seed))
    if str(query_id) == "series_trend_label":
        return _dataset_series_trend(params, instance_seed=int(instance_seed))
    if str(query_id) == "panel_variation_label":
        return _dataset_panel_variation(params, instance_seed=int(instance_seed))
    raise ValueError(f"unsupported 3D chart query id: {query_id}")


def _render_dataset(background: Image.Image, *, dataset: _Dataset, params: _RenderParams) -> _Rendered:
    image = background.convert("RGB")
    if str(dataset.scene_variant) == "three_d_surface":
        return _render_surface(image, dataset=dataset, params=params)
    if str(dataset.scene_variant) == "three_d_small_multiples":
        return _render_small_multiples(image, dataset=dataset, params=params)
    title = "3D Series Trend Chart" if str(dataset.query.query_id) == "series_trend_label" else "3D Scatter Chart"
    return _render_scatter_or_lines(
        image,
        dataset=dataset,
        params=params,
        title=title,
        connect_by_label=str(dataset.query.query_id) == "series_trend_label",
    )


def _projected_evidence(dataset: _Dataset, rendered: _Rendered) -> Dict[str, Any]:
    boxes: List[BBox] = []
    for point_id in dataset.query.evidence_point_ids:
        if str(point_id) in rendered.point_bboxes_px:
            boxes.append(list(rendered.point_bboxes_px[str(point_id)]))
    for cell_id in dataset.query.evidence_cell_ids:
        if str(cell_id) in rendered.surface_cell_bboxes_px:
            boxes.append(list(rendered.surface_cell_bboxes_px[str(cell_id)]))
    for panel_label in dataset.query.evidence_panel_labels:
        if str(panel_label) in rendered.panel_bboxes_px:
            boxes.append(list(rendered.panel_bboxes_px[str(panel_label)]))
    return {
        "type": "bbox_set",
        "bbox_set": list(boxes),
        "point_ids": [str(value) for value in dataset.query.evidence_point_ids],
        "surface_cell_ids": [str(value) for value in dataset.query.evidence_cell_ids],
        "panel_labels": [str(value) for value in dataset.query.evidence_panel_labels],
    }


def _prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, str]:
    query = dataset.query
    trace = dict(query.trace or {})
    answer_hint = str(prompt_defaults["answer_hint_count"] if query.answer_type == "integer" else prompt_defaults["answer_hint_label"])
    slots: Dict[str, str] = {
        "object_description": str(prompt_defaults["object_description"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": answer_hint,
        "evidence_hint": str(prompt_defaults["evidence_hint"]),
        "json_example": str(prompt_defaults["json_example_count"] if query.answer_type == "integer" else prompt_defaults["json_example_label"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only_count"] if query.answer_type == "integer" else prompt_defaults["json_example_answer_only_label"]),
        "target_axis_label": str(trace.get("target_axis_label", "Distance")),
        "target_axis_value": str(trace.get("target_axis_value", "")),
        "target_y_category": str(trace.get("target_y_category", "")),
        "extremum_phrase": str(trace.get("extremum_direction", "highest")),
        "trend_direction_phrase": "increase" if str(trace.get("trend_direction", "increase")) == "increase" else "decrease",
        "panel_variation_phrase": "largest vertical range",
    }
    return slots


class ChartsThreeDPanelQueryTask:
    """Shared generator for synthetic 3D chart panel questions."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "three_d"
    scene_id = SCENE_ID
    default_dataset_enabled = False

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        dataset = _build_dataset(str(query_id), params, instance_seed=int(instance_seed))
        render_params = _resolve_render_params(params)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.chart_font",
            params=params,
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _render_dataset(background, dataset=dataset, params=render_params)
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_label",
                "answer_hint_count",
                "evidence_hint",
                "json_example_label",
                "json_example_count",
                "json_example_answer_only_label",
                "json_example_answer_only_count",
                "object_description",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(dataset.query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=_prompt_slots(dataset, prompt_defaults),
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer" if dataset.query.answer_type == "integer" else "string", value=dataset.query.answer)
        projected = _projected_evidence(dataset, rendered)
        evidence_gt = TypedValue(type="bbox_set", value=list(projected["bbox_set"]))
        trace_params = dict(dataset.query.trace or {})
        trace_params.update(
            {
                "query_id": str(dataset.query.query_id),
                "scene_variant": str(dataset.scene_variant),
                "query_id_probabilities": dict(query_id_probabilities),
                "answer": dataset.query.answer,
                "answer_type": str(dataset.query.answer_type),
                "x_axis_label": str(dataset.x_axis_label),
                "y_axis_label": str(dataset.y_axis_label),
                "z_axis_label": str(dataset.z_axis_label),
                "x_range": [float(value) for value in dataset.x_range],
                "y_range": [float(value) for value in dataset.y_range],
                "z_range": [float(value) for value in dataset.z_range],
                "point_count": len(dataset.points),
                "surface_cell_count": len(dataset.surface_cells),
                "panel_count": len(dataset.panels),
            }
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_three_d_panel",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(dataset.query.query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "answer": dataset.query.answer,
                    "evidence_point_ids": [str(value) for value in dataset.query.evidence_point_ids],
                    "evidence_cell_ids": [str(value) for value in dataset.query.evidence_cell_ids],
                    "evidence_panel_labels": [str(value) for value in dataset.query.evidence_panel_labels],
                },
            },
            "query_spec": {
                "query_id": str(dataset.query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(trace_params),
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(dataset.scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "axis_labels": {
                    "x": str(dataset.x_axis_label),
                    "y": str(dataset.y_axis_label),
                    "z": str(dataset.z_axis_label),
                },
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "point_bboxes_px": dict(rendered.point_bboxes_px),
                "surface_cell_bboxes_px": dict(rendered.surface_cell_bboxes_px),
                "panel_bboxes_px": dict(rendered.panel_bboxes_px),
            },
            "execution_trace": {
                "question_format": "surface_3d_query",
                **dict(trace_params),
                "points": [
                    {
                        "point_id": str(point.point_id),
                        "label": str(point.label),
                        "x_value": round(float(point.x_value), 3),
                        "y_value": round(float(point.y_value), 3),
                        "z_value": round(float(point.z_value), 3),
                    }
                    for point in dataset.points
                ],
                "surface_cells": [
                    {
                        "cell_id": str(cell.cell_id),
                        "x_label": str(cell.x_label),
                        "y_label": str(cell.y_label),
                        "value": int(cell.value),
                    }
                    for cell in dataset.surface_cells
                ],
                "panels": [
                    {
                        "panel_label": str(panel.panel_label),
                        "values": [int(value) for value in panel.values],
                        "value_range": int(max(panel.values) - min(panel.values)),
                    }
                    for panel in dataset.panels
                ],
            },
            "witness_symbolic": {
                "type": "integer" if dataset.query.answer_type == "integer" else "label",
                "value": dataset.query.answer,
            },
            "projected_evidence": dict(projected),
        }
        visual_count = max(1, len(dataset.points) + len(dataset.surface_cells) + len(dataset.panels))
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": clamp_unit_interval(float(visual_count) / 40.0),
                "reasoning_load": float(_REASONING_LOAD_BY_VARIANT[str(dataset.query.query_id)]),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(dataset.scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(dataset.query.query_id),
            scene_id=SCENE_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsThreeDReferenceNearestLabelTask(FixedChartQueryVariantTaskMixin, ChartsThreeDPanelQueryTask):
    """Return the 3D point label nearest to a target axis value."""

    task_id = "task_charts__surface_3d__reference_nearest_label"
    fixed_query_id = "reference_nearest_label"


@register_task
class ChartsThreeDSurfaceExtremumLabelTask(FixedChartQueryVariantTaskMixin, ChartsThreeDPanelQueryTask):
    """Return the surface-grid category with an extremal value under a slice."""

    task_id = "task_charts__surface_3d__surface_extremum_label"
    fixed_query_id = "surface_extremum_label"


@register_task
class ChartsThreeDSeriesTrendLabelTask(FixedChartQueryVariantTaskMixin, ChartsThreeDPanelQueryTask):
    """Return the 3D series label with the requested trend extremum."""

    task_id = "task_charts__surface_3d__series_trend_label"
    fixed_query_id = "series_trend_label"


@register_task
class ChartsThreeDPanelVariationLabelTask(FixedChartQueryVariantTaskMixin, ChartsThreeDPanelQueryTask):
    """Return the small-multiple 3D panel with the largest vertical range."""

    task_id = "task_charts__surface_3d__panel_variation_label"
    fixed_query_id = "panel_variation_label"


__all__ = [
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
    "ChartsThreeDPanelQueryTask",
    "ChartsThreeDPanelVariationLabelTask",
    "ChartsThreeDReferenceNearestLabelTask",
    "ChartsThreeDSeriesTrendLabelTask",
    "ChartsThreeDSurfaceExtremumLabelTask",
]
