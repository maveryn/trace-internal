"""Synthetic 3D bar-grid chart query tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from collections import defaultdict
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.color_distance import sample_color_palette_with_distance_constraints
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.bbox_projection import bbox_union as _bbox_union, round_bbox as _bbox
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ...shared.text_rendering import load_font
from ..shared.complexity import (
    build_chart_complexity,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.labeled_chart_common import sample_chart_labels
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

_SERIES_LABEL_POOL: Tuple[str, ...] = (
    "Solar",
    "Wind",
    "Hydro",
    "Geo",
    "Bio",
    "Coal",
    "Gas",
    "Nuke",
)
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
    evidence_bar_ids: Tuple[str, ...]
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


def _polygon_bbox(points: Sequence[Tuple[float, float]]) -> BBox:
    return _bbox(
        (
            min(float(point[0]) for point in points),
            min(float(point[1]) for point in points),
            max(float(point[0]) for point in points),
            max(float(point[1]) for point in points),
        )
    )


def _text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    *,
    anchor: str | None = None,
    stroke_width: int = 0,
) -> BBox:
    kwargs: Dict[str, Any] = {}
    if anchor is not None:
        kwargs["anchor"] = str(anchor)
    return _bbox(
        draw.textbbox(
            (float(xy[0]), float(xy[1])),
            str(text),
            font=font,
            stroke_width=max(0, int(stroke_width)),
            **kwargs,
        )
    )


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
    draw.text(
        (float(xy[0]), float(xy[1])),
        str(text),
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=max(0, int(stroke_width)),
        **kwargs,
    )
    return _text_bbox(draw, xy, str(text), font, anchor=anchor, stroke_width=max(0, int(stroke_width)))


def _shade(color: RGB, factor: float) -> RGB:
    return tuple(max(0, min(255, int(round(float(channel) * float(factor))))) for channel in color)


def _lighten(color: RGB, amount: float) -> RGB:
    return tuple(
        max(0, min(255, int(round(float(channel) + (255.0 - float(channel)) * float(amount)))))
        for channel in color
    )


def _draw_front_highlight(
    draw: ImageDraw.ImageDraw,
    front: Sequence[Tuple[float, float]],
    *,
    face_color: RGB,
    edge_width: int,
) -> None:
    left_x = float(front[0][0])
    right_x = float(front[1][0])
    bottom_y = float(front[0][1])
    top_y = float(front[2][1])
    if bottom_y - top_y < 18.0 or right_x - left_x < 16.0:
        return
    inset = max(2.0, float(edge_width) + 1.0)
    highlight_w = max(4.0, min(10.0, (right_x - left_x) * 0.20))
    draw.rounded_rectangle(
        (left_x + inset, top_y + inset, left_x + inset + highlight_w, bottom_y - inset),
        radius=2,
        fill=_lighten(face_color, 0.22),
    )


def _draw_side_stripes(
    draw: ImageDraw.ImageDraw,
    side: Sequence[Tuple[float, float]],
    *,
    face_color: RGB,
    edge_width: int,
) -> None:
    front_bottom = side[0]
    back_bottom = side[1]
    back_top = side[2]
    front_top = side[3]
    height = float(front_bottom[1]) - float(front_top[1])
    if height < 22.0:
        return
    stripe_color = _shade(face_color, 0.54)
    step = 14.0
    offset = 10.0
    while offset < height - 4.0:
        front_x = float(front_bottom[0]) + (float(front_top[0]) - float(front_bottom[0])) * (offset / height)
        front_y = float(front_bottom[1]) + (float(front_top[1]) - float(front_bottom[1])) * (offset / height)
        back_x = float(back_bottom[0]) + (float(back_top[0]) - float(back_bottom[0])) * (offset / height)
        back_y = float(back_bottom[1]) + (float(back_top[1]) - float(back_bottom[1])) * (offset / height)
        draw.line(
            [(front_x + 1.0, front_y), (back_x - 1.0, back_y)],
            fill=stripe_color,
            width=max(1, int(edge_width) - 1),
        )
        offset += step


def _draw_top_ridge(
    draw: ImageDraw.ImageDraw,
    top: Sequence[Tuple[float, float]],
    *,
    face_color: RGB,
    edge_width: int,
) -> None:
    if len(top) < 4:
        return
    left_front, right_front, right_back, left_back = top[0], top[1], top[2], top[3]
    ridge_front = (
        float(left_front[0]) * 0.50 + float(right_front[0]) * 0.50,
        float(left_front[1]) * 0.50 + float(right_front[1]) * 0.50,
    )
    ridge_back = (
        float(left_back[0]) * 0.50 + float(right_back[0]) * 0.50,
        float(left_back[1]) * 0.50 + float(right_back[1]) * 0.50,
    )
    draw.line(
        [ridge_front, ridge_back],
        fill=_lighten(face_color, 0.44),
        width=max(1, int(edge_width)),
    )


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


def _axis_max(max_value: int, *, tick_step: int) -> int:
    step = max(1, int(tick_step))
    return max(step, int(math.ceil(float(max_value) / float(step)) * step))


def _sample_palette(*, instance_seed: int, count: int) -> Tuple[RGB, ...]:
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.palette")
    raw_palette = _RENDER_DEFAULTS.get("series_palette_rgb")
    if isinstance(raw_palette, Sequence) and not isinstance(raw_palette, (str, bytes)) and len(raw_palette) >= int(count):
        palette = [_as_rgb(item, _DEFAULT_PALETTE[index % len(_DEFAULT_PALETTE)]) for index, item in enumerate(raw_palette)]
        rng.shuffle(palette)
        return tuple(palette[: int(count)])
    palette = sample_color_palette_with_distance_constraints(
        rng,
        palette_size=int(count),
        channel_min=35,
        channel_max=218,
        anchor_colors=((255, 255, 255), (248, 248, 248)),
        min_distance=44.0,
        distance_space="lab",
    )
    return tuple(tuple(int(channel) for channel in color) for color in palette)


def _sample_x_labels(*, count: int, instance_seed: int) -> Tuple[str, ...]:
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.x_labels")
    if rng.random() < 0.58:
        start = int(rng.randint(2014, 2026 - int(count)))
        return tuple(str(start + index) for index in range(int(count)))
    return tuple(str(label) for label in sample_chart_labels(count=int(count), instance_seed=int(instance_seed)))


def _sample_series_labels(*, count: int, instance_seed: int) -> Tuple[str, ...]:
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.series_labels")
    labels = list(_SERIES_LABEL_POOL)
    rng.shuffle(labels)
    return tuple(str(label) for label in labels[: int(count)])


def _sample_query_id(
    params: Mapping[str, Any],
    *,
    allowed_query_ids: Sequence[str],
    instance_seed: int,
) -> str:
    allowed = tuple(str(value) for value in allowed_query_ids)
    allowed_set = set(allowed)
    explicit = params.get("query_id")
    if explicit is not None and str(explicit) != "default":
        query_id = str(explicit)
        if query_id not in allowed_set:
            raise ValueError(f"unsupported 3D bar query_id for this public task: {query_id}")
        return query_id
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.query_id")
    raw_weights = params.get("query_id_weights", params.get("query_id_weights"))
    if isinstance(raw_weights, Mapping):
        weights = [max(0.0, float(raw_weights.get(query_id, 0.0))) for query_id in allowed]
        if sum(weights) > 0.0:
            threshold = rng.random() * sum(weights)
            cumulative = 0.0
            for query_id, weight in zip(allowed, weights):
                cumulative += float(weight)
                if threshold <= cumulative:
                    return str(query_id)
    return str(allowed[int(rng.randrange(len(allowed)))])


def _int_sequence_default(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), list(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return tuple(int(value) for value in fallback)
    values = tuple(int(value) for value in raw)
    return values if values else tuple(int(value) for value in fallback)


def _condition_answer_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    return tuple(
        int(value)
        for value in _int_sequence_default(params, "condition_count_answer_support", (1, 2, 3, 4, 5))
        if int(value) > 0
    )


def _sample_grid(
    params: Mapping[str, Any],
    *,
    query_id: str,
    instance_seed: int,
) -> Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[Tuple[int, ...], ...], Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
    condition_query = str(query_id) in set(CONDITION_COUNT_QUERY_IDS)
    category_min_key = "condition_category_count_min" if condition_query else "category_count_min"
    category_max_key = "condition_category_count_max" if condition_query else "category_count_max"
    series_min_key = "condition_series_count_min" if condition_query else "series_count_min"
    series_max_key = "condition_series_count_max" if condition_query else "series_count_max"
    x_min, x_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=category_min_key,
        max_key=category_max_key,
        fallback_min=4,
        fallback_max=6,
        context=f"generation defaults for {TASK_ID}",
    )
    series_min, series_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=series_min_key,
        max_key=series_max_key,
        fallback_min=3,
        fallback_max=5,
        context=f"generation defaults for {TASK_ID}",
    )
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=6,
        fallback_max=36,
        context=f"generation defaults for {TASK_ID}",
    )
    x_max = max(int(x_min), min(int(x_max), 8))
    series_max = max(int(series_min), min(int(series_max), len(_SERIES_LABEL_POOL)))
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.grid")
    x_count = int(rng.randint(int(x_min), int(x_max)))
    series_count = int(rng.randint(int(series_min), int(series_max)))
    x_labels = _sample_x_labels(count=int(x_count), instance_seed=int(instance_seed))
    series_labels = _sample_series_labels(count=int(series_count), instance_seed=int(instance_seed))
    values = tuple(
        tuple(int(rng.randint(int(value_min), int(value_max))) for _ in range(int(series_count)))
        for _ in range(int(x_count))
    )
    return (
        x_labels,
        series_labels,
        values,
        (int(x_min), int(x_max)),
        (int(series_min), int(series_max)),
        (int(value_min), int(value_max)),
    )


def _choose_interval(*, x_count: int, params: Mapping[str, Any], instance_seed: int) -> Tuple[int, int, Tuple[int, int]]:
    span_min, span_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="interval_category_count_min",
        max_key="interval_category_count_max",
        fallback_min=2,
        fallback_max=4,
        context=f"generation defaults for {TASK_ID}",
    )
    span_max = min(int(span_max), int(x_count))
    span_min = min(int(span_min), int(span_max))
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.interval")
    span_count = int(rng.randint(int(span_min), int(span_max)))
    start = int(rng.randint(0, int(x_count) - int(span_count)))
    return int(start), int(start + span_count - 1), (int(span_min), int(span_max))


def _valid_threshold(
    values: Sequence[int],
    *,
    want_at_least: bool,
    rng: Any,
    target_counts: Sequence[int] | None = None,
) -> Tuple[int, int] | None:
    if len(values) < 2:
        return None
    lower = min(int(value) for value in values)
    upper = max(int(value) for value in values)
    candidates_by_count: Dict[int, List[int]] = defaultdict(list)
    for threshold in range(int(lower), int(upper) + 1):
        if bool(want_at_least):
            count = sum(1 for value in values if int(value) >= int(threshold))
        else:
            count = sum(1 for value in values if int(value) < int(threshold))
        if 1 <= int(count) <= len(values) - 1:
            candidates_by_count[int(count)].append(int(threshold))
    if not candidates_by_count:
        return None
    preferred_counts = [
        int(count)
        for count in (target_counts or ())
        if int(count) in candidates_by_count
    ]
    available_counts = preferred_counts or sorted(int(count) for count in candidates_by_count.keys())
    target_count = int(available_counts[int(rng.randrange(len(available_counts)))])
    thresholds = candidates_by_count[int(target_count)]
    threshold = int(thresholds[int(rng.randrange(len(thresholds)))])
    return int(threshold), int(target_count)


def _build_query(
    *,
    query_id: str,
    x_labels: Sequence[str],
    series_labels: Sequence[str],
    values: Sequence[Sequence[int]],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Query:
    rng = spawn_rng(int(instance_seed), f"charts.three_d_bar.query.{query_id}")
    x_count = len(x_labels)
    series_count = len(series_labels)

    def bar_id(x_index: int, series_index: int) -> str:
        return f"bar_{int(x_index)}_{int(series_index)}"

    if query_id == "series_total_value":
        series_index = int(rng.randrange(series_count))
        answer = int(sum(int(values[x_index][series_index]) for x_index in range(x_count)))
        evidence = tuple(bar_id(x_index, series_index) for x_index in range(x_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            evidence_bar_ids=evidence,
            trace={
                "series_label": str(series_labels[series_index]),
                "series_index": int(series_index),
                "selected_values": [int(values[x_index][series_index]) for x_index in range(x_count)],
            },
        )
    if query_id == "category_total_value":
        x_index = int(rng.randrange(x_count))
        answer = int(sum(int(values[x_index][series_index]) for series_index in range(series_count)))
        evidence = tuple(bar_id(x_index, series_index) for series_index in range(series_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            evidence_bar_ids=evidence,
            trace={
                "category_label": str(x_labels[x_index]),
                "category_index": int(x_index),
                "selected_values": [int(values[x_index][series_index]) for series_index in range(series_count)],
            },
        )
    if query_id == "series_interval_total_value":
        series_index = int(rng.randrange(series_count))
        start_index, end_index, span_range = _choose_interval(x_count=int(x_count), params=params, instance_seed=int(instance_seed))
        answer = int(sum(int(values[x_index][series_index]) for x_index in range(int(start_index), int(end_index) + 1)))
        evidence = tuple(bar_id(x_index, series_index) for x_index in range(int(start_index), int(end_index) + 1))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            evidence_bar_ids=evidence,
            trace={
                "series_label": str(series_labels[series_index]),
                "series_index": int(series_index),
                "start_category_label": str(x_labels[start_index]),
                "end_category_label": str(x_labels[end_index]),
                "start_category_index": int(start_index),
                "end_category_index": int(end_index),
                "interval_category_count": int(end_index) - int(start_index) + 1,
                "interval_category_count_range": list(span_range),
                "selected_values": [int(values[x_index][series_index]) for x_index in range(int(start_index), int(end_index) + 1)],
            },
        )
    if query_id == "series_total_gap_value":
        totals = [int(sum(int(values[x_index][series_index]) for x_index in range(x_count))) for series_index in range(series_count)]
        pairs = [(a, b) for a in range(series_count) for b in range(a + 1, series_count) if int(totals[a]) != int(totals[b])]
        if not pairs:
            raise ValueError("series totals are not distinct enough for a gap query")
        series_a, series_b = pairs[int(rng.randrange(len(pairs)))]
        answer = abs(int(totals[series_a]) - int(totals[series_b]))
        evidence = tuple(bar_id(x_index, series_index) for series_index in (series_a, series_b) for x_index in range(x_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            evidence_bar_ids=evidence,
            trace={
                "series_label_a": str(series_labels[series_a]),
                "series_label_b": str(series_labels[series_b]),
                "series_index_a": int(series_a),
                "series_index_b": int(series_b),
                "series_total_a": int(totals[series_a]),
                "series_total_b": int(totals[series_b]),
            },
        )
    if query_id == "category_total_gap_value":
        totals = [int(sum(int(values[x_index][series_index]) for series_index in range(series_count))) for x_index in range(x_count)]
        pairs = [(a, b) for a in range(x_count) for b in range(a + 1, x_count) if int(totals[a]) != int(totals[b])]
        if not pairs:
            raise ValueError("category totals are not distinct enough for a gap query")
        x_a, x_b = pairs[int(rng.randrange(len(pairs)))]
        answer = abs(int(totals[x_a]) - int(totals[x_b]))
        evidence = tuple(bar_id(x_index, series_index) for x_index in (x_a, x_b) for series_index in range(series_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            evidence_bar_ids=evidence,
            trace={
                "category_label_a": str(x_labels[x_a]),
                "category_label_b": str(x_labels[x_b]),
                "category_index_a": int(x_a),
                "category_index_b": int(x_b),
                "category_total_a": int(totals[x_a]),
                "category_total_b": int(totals[x_b]),
            },
        )
    if query_id == "category_extremum_gap_value":
        valid_categories = [
            x_index
            for x_index in range(x_count)
            if max(int(value) for value in values[x_index]) > min(int(value) for value in values[x_index])
        ]
        if not valid_categories:
            raise ValueError("category values are not distinct enough for an extremum gap")
        x_index = int(valid_categories[int(rng.randrange(len(valid_categories)))])
        category_values = [int(values[x_index][series_index]) for series_index in range(series_count)]
        answer = int(max(category_values) - min(category_values))
        evidence = tuple(bar_id(x_index, series_index) for series_index in range(series_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            evidence_bar_ids=evidence,
            trace={
                "category_label": str(x_labels[x_index]),
                "category_index": int(x_index),
                "category_values": list(category_values),
                "max_value": int(max(category_values)),
                "min_value": int(min(category_values)),
            },
        )
    if query_id == "series_threshold_count":
        series_index = int(rng.randrange(series_count))
        series_values = [int(values[x_index][series_index]) for x_index in range(x_count)]
        threshold_info = _valid_threshold(
            series_values,
            want_at_least=True,
            rng=rng,
            target_counts=_condition_answer_support(params),
        )
        if threshold_info is None:
            raise ValueError("series threshold query has no nontrivial count")
        threshold, answer = threshold_info
        evidence = tuple(bar_id(x_index, series_index) for x_index in range(x_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            evidence_bar_ids=evidence,
            trace={
                "series_label": str(series_labels[series_index]),
                "series_index": int(series_index),
                "comparison_phrase": "at least",
                "threshold": int(threshold),
                "selected_values": list(series_values),
            },
        )
    if query_id == "category_threshold_count":
        x_index = int(rng.randrange(x_count))
        category_values = [int(values[x_index][series_index]) for series_index in range(series_count)]
        threshold_info = _valid_threshold(
            category_values,
            want_at_least=False,
            rng=rng,
            target_counts=_condition_answer_support(params),
        )
        if threshold_info is None:
            raise ValueError("category threshold query has no nontrivial count")
        threshold, answer = threshold_info
        evidence = tuple(bar_id(x_index, series_index) for series_index in range(series_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            evidence_bar_ids=evidence,
            trace={
                "category_label": str(x_labels[x_index]),
                "category_index": int(x_index),
                "comparison_phrase": "below",
                "threshold": int(threshold),
                "selected_values": list(category_values),
            },
        )
    if query_id == "series_comparison_count":
        pairs_by_count: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
        for series_a in range(series_count):
            for series_b in range(series_count):
                if series_a == series_b:
                    continue
                count = sum(1 for x_index in range(x_count) if int(values[x_index][series_a]) > int(values[x_index][series_b]))
                if 1 <= int(count) <= int(x_count) - 1:
                    pairs_by_count[int(count)].append((int(series_a), int(series_b)))
        if not pairs_by_count:
            raise ValueError("series comparison query has no nontrivial count")
        preferred_counts = [
            int(count)
            for count in _condition_answer_support(params)
            if int(count) in pairs_by_count
        ]
        available_counts = preferred_counts or sorted(int(count) for count in pairs_by_count.keys())
        answer = int(available_counts[int(rng.randrange(len(available_counts)))])
        pairs = pairs_by_count[int(answer)]
        series_a, series_b = pairs[int(rng.randrange(len(pairs)))]
        evidence = tuple(bar_id(x_index, series_index) for series_index in (series_a, series_b) for x_index in range(x_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            evidence_bar_ids=evidence,
            trace={
                "series_label_a": str(series_labels[series_a]),
                "series_label_b": str(series_labels[series_b]),
                "series_index_a": int(series_a),
                "series_index_b": int(series_b),
                "selected_values_a": [int(values[x_index][series_a]) for x_index in range(x_count)],
                "selected_values_b": [int(values[x_index][series_b]) for x_index in range(x_count)],
            },
        )
    raise ValueError(f"unsupported 3D bar query_id: {query_id}")


def _build_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_Dataset, Dict[str, Any]]:
    x_labels, series_labels, values, x_count_range, series_count_range, value_range = _sample_grid(
        params,
        query_id=str(query_id),
        instance_seed=int(instance_seed),
    )
    palette = _sample_palette(instance_seed=int(instance_seed), count=len(series_labels))
    bars: List[_BarCell] = []
    for x_index, x_label in enumerate(x_labels):
        for series_index, series_label in enumerate(series_labels):
            bars.append(
                _BarCell(
                    bar_id=f"bar_{int(x_index)}_{int(series_index)}",
                    x_label=str(x_label),
                    series_label=str(series_label),
                    x_index=int(x_index),
                    series_index=int(series_index),
                    value=int(values[x_index][series_index]),
                    color_rgb=tuple(int(channel) for channel in palette[int(series_index) % len(palette)]),
                )
            )
    query = _build_query(
        query_id=str(query_id),
        x_labels=x_labels,
        series_labels=series_labels,
        values=values,
        params=params,
        instance_seed=int(instance_seed),
    )
    ranges = {
        "category_count_range": list(x_count_range),
        "series_count_range": list(series_count_range),
        "value_range": list(value_range),
    }
    return (
        _Dataset(
            x_labels=tuple(str(label) for label in x_labels),
            series_labels=tuple(str(label) for label in series_labels),
            bars=tuple(bars),
            query=query,
        ),
        dict(ranges),
    )


def _render_bar_grid(
    background: Image.Image,
    *,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _RenderedBarGrid:
    render_params = _render_params(params, instance_seed=int(instance_seed))
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    x_count = len(dataset.x_labels)
    series_count = len(dataset.series_labels)
    plot_left = float(render_params.plot_margin_left_px)
    plot_top = float(render_params.plot_margin_top_px)
    plot_right = float(render_params.canvas_width - render_params.plot_margin_right_px)
    plot_bottom = float(render_params.canvas_height - render_params.plot_margin_bottom_px)
    plot_bbox = _bbox((plot_left, plot_top, plot_right, plot_bottom))

    panel_bbox = [plot_left - 58, plot_top - 42, plot_right + 64, plot_bottom + 82]
    draw.rounded_rectangle(
        panel_bbox,
        radius=8,
        fill=render_params.panel_fill_rgb,
        outline=render_params.panel_border_rgb,
        width=2,
    )
    draw.rectangle((plot_left, plot_top, plot_right, plot_bottom), fill=render_params.plot_fill_rgb)

    title_font = load_font(max(18, int(render_params.label_font_size_px) + 1), bold=True)
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    value_font = load_font(int(render_params.value_font_size_px), bold=True)
    legend_font = load_font(int(render_params.legend_font_size_px), bold=True)

    _draw_text(
        draw,
        (plot_left, plot_top - 34),
        "3D Bar Chart",
        font=title_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
    )

    max_value = max(int(bar.value) for bar in dataset.bars)
    tick_step = int(params.get("z_axis_tick_step", group_default(_RENDER_DEFAULTS, "z_axis_tick_step", 10)))
    y_axis_max = _axis_max(int(max_value), tick_step=int(tick_step))
    y_ticks = tuple(range(0, int(y_axis_max) + 1, max(1, int(tick_step))))

    depth_dx = float(render_params.depth_axis_dx_px)
    depth_dy = float(render_params.depth_axis_dy_px)
    face_dx = float(render_params.bar_face_dx_px)
    face_dy = float(render_params.bar_face_dy_px)
    origin_x = float(plot_left + 62)
    origin_y = float(plot_bottom - 26)
    available_w = max(140.0, float(plot_right - origin_x - (series_count - 1) * depth_dx - 36.0))
    x_step = available_w / float(max(1, x_count - 1))
    bar_width = min(
        float(render_params.bar_width_px),
        max(24.0, x_step * 0.46),
    )
    bar_style_meta = {
        "variant": str(render_params.bar_style_variant),
        "depth_axis_dx_px": int(round(depth_dx)),
        "depth_axis_dy_px": int(round(depth_dy)),
        "bar_face_dx_px": int(round(face_dx)),
        "bar_face_dy_px": int(round(face_dy)),
        "bar_width_px": int(round(bar_width)),
    }
    z_scale = max(1.0, float(origin_y - plot_top - (series_count - 1) * depth_dy - 36.0) / float(max(1, y_axis_max)))

    def base_xy(x_index: int, series_index: int) -> Tuple[float, float]:
        return (
            float(origin_x + int(x_index) * x_step + int(series_index) * depth_dx),
            float(origin_y - int(series_index) * depth_dy),
        )

    # Base grid, axes, and z ticks.
    back_end = base_xy(x_count - 1, series_count - 1)
    front_end = base_xy(x_count - 1, 0)
    depth_end = base_xy(0, series_count - 1)
    for x_index in range(x_count):
        start = base_xy(x_index, 0)
        end = base_xy(x_index, series_count - 1)
        draw.line([start, end], fill=render_params.grid_color_rgb, width=int(render_params.grid_line_width_px))
    for series_index in range(series_count):
        start = base_xy(0, series_index)
        end = base_xy(x_count - 1, series_index)
        draw.line([start, end], fill=render_params.grid_color_rgb, width=int(render_params.grid_line_width_px))
    draw.line([(origin_x, origin_y), front_end], fill=render_params.axis_color_rgb, width=int(render_params.axis_line_width_px))
    draw.line([(origin_x, origin_y), depth_end], fill=render_params.axis_color_rgb, width=int(render_params.axis_line_width_px))
    draw.line([(origin_x, origin_y), (origin_x, origin_y - float(y_axis_max) * z_scale)], fill=render_params.axis_color_rgb, width=int(render_params.axis_line_width_px))
    draw.line([depth_end, back_end], fill=render_params.axis_color_rgb, width=int(render_params.axis_line_width_px))

    for tick in y_ticks:
        y = float(origin_y - int(tick) * z_scale)
        draw.line(
            [(origin_x - render_params.tick_length_px, y), (origin_x, y)],
            fill=render_params.axis_color_rgb,
            width=max(1, int(render_params.axis_line_width_px)),
        )
        _draw_text(
            draw,
            (origin_x - render_params.tick_length_px - 8, y),
            str(int(tick)),
            font=tick_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
            anchor="rm",
        )

    for x_index, x_label in enumerate(dataset.x_labels):
        bx, by = base_xy(x_index, 0)
        draw.line(
            [(bx, by), (bx, by + render_params.tick_length_px)],
            fill=render_params.axis_color_rgb,
            width=max(1, int(render_params.axis_line_width_px)),
        )
        _draw_text(
            draw,
            (bx, by + render_params.tick_length_px + 10),
            str(x_label),
            font=label_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=int(render_params.label_stroke_width_px),
            anchor="mt",
        )
    evidence_set = set(str(bar_id) for bar_id in dataset.query.evidence_bar_ids)
    bar_traces: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    bars_by_id = {str(bar.bar_id): bar for bar in dataset.bars}
    draw_order = sorted(dataset.bars, key=lambda bar: (-int(bar.series_index), int(bar.x_index)))
    for bar in draw_order:
        bx, by = base_xy(int(bar.x_index), int(bar.series_index))
        top_y = float(by - int(bar.value) * z_scale)
        half_w = float(bar_width) * 0.5
        front = [
            (bx - half_w, by),
            (bx + half_w, by),
            (bx + half_w, top_y),
            (bx - half_w, top_y),
        ]
        side = [
            (bx + half_w, by),
            (bx + half_w + face_dx, by - face_dy),
            (bx + half_w + face_dx, top_y - face_dy),
            (bx + half_w, top_y),
        ]
        top = [
            (bx - half_w, top_y),
            (bx + half_w, top_y),
            (bx + half_w + face_dx, top_y - face_dy),
            (bx - half_w + face_dx, top_y - face_dy),
        ]
        face_color = tuple(int(channel) for channel in bar.color_rgb)
        edge_width = max(1, int(render_params.bar_edge_width_px))
        draw.polygon(side, fill=_shade(face_color, 0.72), outline=render_params.bar_edge_rgb)
        draw.polygon(front, fill=face_color, outline=render_params.bar_edge_rgb)
        draw.polygon(top, fill=_lighten(face_color, 0.25), outline=render_params.bar_edge_rgb)
        if str(render_params.bar_style_variant) in {"front_highlight", "mixed_faces"}:
            _draw_front_highlight(draw, front, face_color=face_color, edge_width=edge_width)
        if str(render_params.bar_style_variant) in {"side_stripes", "mixed_faces"}:
            _draw_side_stripes(draw, side, face_color=face_color, edge_width=edge_width)
        if str(render_params.bar_style_variant) in {"top_ridge", "mixed_faces"}:
            _draw_top_ridge(draw, top, face_color=face_color, edge_width=edge_width)
        draw.line(front + [front[0]], fill=render_params.bar_edge_rgb, width=edge_width)
        draw.line(side + [side[0]], fill=render_params.bar_edge_rgb, width=edge_width)
        draw.line(top + [top[0]], fill=render_params.bar_edge_rgb, width=edge_width)
        label_xy = (float(bx + face_dx * 0.5), float(top_y - face_dy - 6.0))
        value_bbox = _draw_text(
            draw,
            label_xy,
            str(int(bar.value)),
            font=value_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=int(render_params.label_stroke_width_px),
            anchor="mb",
        )
        bar_bbox = _bbox_union([_polygon_bbox(front), _polygon_bbox(side), _polygon_bbox(top), value_bbox])
        trace = {
            "bar_id": str(bar.bar_id),
            "entity_id": str(bar.bar_id),
            "x_label": str(bar.x_label),
            "series_label": str(bar.series_label),
            "x_index": int(bar.x_index),
            "series_index": int(bar.series_index),
            "value": int(bar.value),
            "top_center_px": [round(float(bx + face_dx * 0.5), 3), round(float(top_y - face_dy * 0.5), 3)],
            "value_center_px": [round(float(label_xy[0]), 3), round(float(label_xy[1]), 3)],
            "value_bbox_px": list(value_bbox),
            "bar_bbox_px": list(bar_bbox),
            "queried": bool(str(bar.bar_id) in evidence_set),
            "fill_rgb": [int(channel) for channel in face_color],
            "bar_style_variant": str(render_params.bar_style_variant),
        }
        bar_traces.append(dict(trace))
        entities.append(
            {
                "entity_id": str(bar.bar_id),
                "entity_type": "three_d_bar",
                "bbox_xyxy": list(bar_bbox),
                "attrs": dict(trace),
            }
        )

    legend_traces: List[Dict[str, Any]] = []
    legend_left = float(plot_right + 24)
    legend_top = float(plot_top + 20)
    swatch = float(max(18, int(render_params.legend_font_size_px)))
    row_h = float(max(32, int(render_params.legend_font_size_px) + 14))
    legend_width = float(max(138.0, render_params.canvas_width - legend_left - 22.0))
    legend_height = float(series_count * row_h + 18.0)
    draw.rounded_rectangle(
        (legend_left - 10, legend_top - 10, legend_left + legend_width, legend_top + legend_height),
        radius=6,
        fill=render_params.plot_fill_rgb,
        outline=render_params.legend_border_rgb,
        width=1,
    )
    by_series = {str(bar.series_label): bar for bar in dataset.bars}
    for series_index, series_label in enumerate(dataset.series_labels):
        row_y = legend_top + float(series_index) * row_h
        color = tuple(int(channel) for channel in by_series[str(series_label)].color_rgb)
        swatch_bbox = _bbox((legend_left, row_y, legend_left + swatch, row_y + swatch))
        draw.rectangle(swatch_bbox, fill=color, outline=render_params.bar_edge_rgb, width=1)
        text_xy = (legend_left + swatch + 12.0, row_y - 1.0)
        label_bbox = _draw_text(
            draw,
            text_xy,
            str(series_label),
            font=legend_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
        trace = {
            "entity_id": f"legend_{series_index}",
            "series_label": str(series_label),
            "series_index": int(series_index),
            "swatch_bbox_px": list(swatch_bbox),
            "label_bbox_px": list(label_bbox),
            "fill_rgb": [int(channel) for channel in color],
        }
        legend_traces.append(dict(trace))
        entities.append(
            {
                "entity_id": str(trace["entity_id"]),
                "entity_type": "legend_entry",
                "bbox_xyxy": _bbox_union([swatch_bbox, label_bbox]),
                "attrs": dict(trace),
            }
        )

    # Ensure traces are ordered by grid coordinate, not draw order.
    ordered_traces = sorted(bar_traces, key=lambda trace: (int(trace["x_index"]), int(trace["series_index"])))
    return _RenderedBarGrid(
        image=image,
        plot_bbox_px=list(plot_bbox),
        y_axis_max=int(y_axis_max),
        y_ticks=tuple(int(tick) for tick in y_ticks),
        entities=tuple(dict(entity) for entity in entities),
        bar_traces=tuple(dict(trace) for trace in ordered_traces),
        legend_traces=tuple(dict(trace) for trace in legend_traces),
        layout_jitter_meta=dict(render_params.layout_jitter_meta),
        bar_style_meta=dict(bar_style_meta),
    )


def _make_prompt(
    *,
    query_id: str,
    prompt_defaults: Mapping[str, Any],
    slots: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, str], Dict[str, Any], Dict[str, Any], str]:
    prompt_selection = render_task_prompt_variants(
        domain="charts",
        task_group="three_d_bar",
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query_id),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    artifacts = build_prompt_trace_artifacts(prompt_selection)
    return (
        str(artifacts.prompt),
        dict(artifacts.prompt_variants),
        dict(artifacts.prompt_variant),
        dict(artifacts.prompt_variants_for_trace),
        str(artifacts.prompt_variant_active_key),
    )


def _quoted(value: str) -> str:
    return f'"{str(value)}"'


class ChartsThreeDBarGridQueryTask:
    """Generate one 3D bar-grid chart query."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "three_d_bar"
    allowed_query_ids: Tuple[str, ...] = AXIS_TOTAL_QUERY_IDS
    default_dataset_enabled = False

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id = _sample_query_id(params, allowed_query_ids=self.allowed_query_ids, instance_seed=int(instance_seed))
        if query_id not in set(SUPPORTED_QUERY_IDS):
            raise ValueError(f"unsupported 3D bar query_id: {query_id}")
        dataset, ranges = _build_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_integer",
                "object_description",
                "evidence_hint_axis_total_value",
                "evidence_hint_axis_gap_value",
                "evidence_hint_condition_count",
                "json_example_axis_total_value",
                "json_example_axis_gap_value",
                "json_example_condition_count",
                "json_example_answer_only_axis_total_value",
                "json_example_answer_only_axis_gap_value",
                "json_example_answer_only_condition_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1120))),
            canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 760))),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered = _render_bar_grid(
            background,
            dataset=dataset,
            params=params,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        trace_by_id = {str(trace["bar_id"]): trace for trace in rendered.bar_traces}
        evidence_points = [
            list(trace_by_id[str(bar_id)]["top_center_px"])
            for bar_id in dataset.query.evidence_bar_ids
            if str(bar_id) in trace_by_id
        ]
        evidence_bboxes = [
            list(trace_by_id[str(bar_id)]["bar_bbox_px"])
            for bar_id in dataset.query.evidence_bar_ids
            if str(bar_id) in trace_by_id
        ]

        task_prompt_group = (
            "axis_total_value"
            if str(query_id) in set(AXIS_TOTAL_QUERY_IDS)
            else "axis_gap_value"
            if str(query_id) in set(AXIS_GAP_QUERY_IDS)
            else "condition_count"
        )
        query_trace = dict(dataset.query.trace)
        slots = {
            "object_description": str(prompt_defaults["object_description"]),
            "series_label": _quoted(str(query_trace.get("series_label", ""))),
            "series_label_a": _quoted(str(query_trace.get("series_label_a", ""))),
            "series_label_b": _quoted(str(query_trace.get("series_label_b", ""))),
            "category_label": _quoted(str(query_trace.get("category_label", ""))),
            "category_label_a": _quoted(str(query_trace.get("category_label_a", ""))),
            "category_label_b": _quoted(str(query_trace.get("category_label_b", ""))),
            "start_category_label": _quoted(str(query_trace.get("start_category_label", ""))),
            "end_category_label": _quoted(str(query_trace.get("end_category_label", ""))),
            "comparison_phrase": str(query_trace.get("comparison_phrase", "")),
            "threshold": str(query_trace.get("threshold", "")),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "evidence_hint": str(prompt_defaults[f"evidence_hint_{task_prompt_group}"]),
            "answer_hint": str(prompt_defaults["answer_hint_integer"]),
            "json_example": str(prompt_defaults[f"json_example_{task_prompt_group}"]),
            "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{task_prompt_group}"]),
        }
        prompt, prompt_variants, prompt_variant, prompt_variants_for_trace, active_prompt_key = _make_prompt(
            query_id=str(query_id),
            prompt_defaults=prompt_defaults,
            slots=slots,
            instance_seed=int(instance_seed),
        )

        values_by_category = {
            str(x_label): {
                str(series_label): int(
                    next(
                        bar.value
                        for bar in dataset.bars
                        if str(bar.x_label) == str(x_label) and str(bar.series_label) == str(series_label)
                    )
                )
                for series_label in dataset.series_labels
            }
            for x_label in dataset.x_labels
        }
        query_params = {
            "query_id": str(query_id),
            "public_task_id": str(self.task_id),
            "category_count": int(len(dataset.x_labels)),
            "series_count": int(len(dataset.series_labels)),
            "category_labels": [str(label) for label in dataset.x_labels],
            "series_labels": [str(label) for label in dataset.series_labels],
            "evidence_bar_ids": [str(bar_id) for bar_id in dataset.query.evidence_bar_ids],
            "answer_value": int(dataset.query.answer),
            **dict(ranges),
            **dict(query_trace),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_three_d_bar_grid",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": dict(query_params),
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_variant),
                "prompt_variant_active_key": str(active_prompt_key),
                "prompt_variants": dict(prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "coord_space": "pixel",
                "scene_variant": "three_d_bar_grid",
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "y_axis_max": int(rendered.y_axis_max),
                "y_ticks": [int(tick) for tick in rendered.y_ticks],
                "layout_jitter": dict(rendered.layout_jitter_meta),
                "bar_style": dict(rendered.bar_style_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "bar_traces": [dict(trace) for trace in rendered.bar_traces],
                "legend_traces": [dict(trace) for trace in rendered.legend_traces],
            },
            "execution_trace": {
                "query_id": str(query_id),
                "answer_value": int(dataset.query.answer),
                "question_format": "numeric_open",
                "values_by_category": dict(values_by_category),
                "evidence_bar_ids": [str(bar_id) for bar_id in dataset.query.evidence_bar_ids],
                **dict(query_params),
            },
            "witness_symbolic": {
                "type": "three_d_bar_grid_values",
                "evidence_bar_ids": [str(bar_id) for bar_id in dataset.query.evidence_bar_ids],
            },
            "projected_evidence": {
                "point_set": list(evidence_points),
                "bbox_set": list(evidence_bboxes),
            },
        }
        bar_count = int(len(dataset.x_labels) * len(dataset.series_labels))
        min_bar_count = int(ranges["category_count_range"][0]) * int(ranges["series_count_range"][0])
        max_bar_count = int(ranges["category_count_range"][1]) * int(ranges["series_count_range"][1])
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(bar_count), (int(min_bar_count), int(max_bar_count))),
                "reasoning_load": float(_QUERY_REASONING_LOAD[str(query_id)]),
                "evidence_count": normalize_int_with_bounds(
                    int(len(dataset.query.evidence_bar_ids)),
                    (1, max(1, int(max_bar_count))),
                ),
                "scene_variant_load": 0.78,
            },
        )
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=TypedValue(type="integer", value=int(dataset.query.answer)),
            evidence_gt=TypedValue(type="point_set", value=[list(point) for point in evidence_points]),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_variants),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        public_overrides = (
            _public_task_param_overrides(str(self.task_id))
            if str(self.task_id) != str(TASK_ID)
            else {}
        )
        if public_overrides:
            merged_params = dict(public_overrides)
            merged_params.update(dict(params))
            params = merged_params
        attempts = max(1, int(max_attempts))
        last_error: Exception | None = None
        for attempt in range(attempts):
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), "charts.three_d_bar.retry", int(attempt)))
            try:
                return self._generate_once(int(attempt_seed), params=params)
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


@register_task
class ChartsThreeDBarAxisAggregateValueTask(ChartsThreeDBarGridQueryTask):
    """Compute totals or gaps over comparable slices in a 3D bar chart."""

    task_id = "task_charts__bar_3d__axis_aggregate_value"
    allowed_query_ids = AXIS_TOTAL_QUERY_IDS + AXIS_GAP_QUERY_IDS
    default_dataset_enabled = True


@register_task
class ChartsThreeDBarConditionCountTask(ChartsThreeDBarGridQueryTask):
    """Count bars satisfying a threshold or pairwise condition in a 3D bar chart."""

    task_id = "task_charts__bar_3d__condition_count"
    allowed_query_ids = CONDITION_COUNT_QUERY_IDS
    default_dataset_enabled = True


__all__ = [
    "ChartsThreeDBarAxisAggregateValueTask",
    "ChartsThreeDBarConditionCountTask",
    "ChartsThreeDBarGridQueryTask",
]
