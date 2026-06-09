"""Area chart panel tasks for chart-domain reasoning."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import round_bbox as _round_bbox
from ...shared.color_distance import sample_color_palette_with_distance_constraints
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ...shared.text_rendering import draw_text_centered, load_font, temporary_default_font_family
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import (
    build_chart_complexity,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.information_style import make_chart_information_background, resolve_chart_information_style
from ..shared.label_assets import resolve_chart_entity_labels
from ..shared.labeled_chart_common import sample_chart_labels
from ..shared.visual_defaults import load_chart_noise_defaults


TASK_ID = "charts_area_panel_query_base"
SCENE_ID = "area"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "interval_area_value",
    "stacked_band_interval_sum_value",
    "stacked_dominance_label",
)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "area")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="area", apply_prob=0.0)

_QUERY_REASONING_LOAD: Dict[str, float] = {
    "interval_area_value": 0.78,
    "stacked_band_interval_sum_value": 0.62,
    "stacked_dominance_label": 0.72,
}
_DEFAULT_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (72, 132, 204),
    (225, 127, 72),
    (92, 166, 106),
    (166, 114, 190),
    (214, 177, 69),
    (86, 170, 176),
)


@dataclass(frozen=True)
class _AreaRenderParams:
    canvas_width: int
    canvas_height: int
    plot_margin_left_px: int
    plot_margin_right_px: int
    plot_margin_top_px: int
    plot_margin_bottom_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    tick_length_px: int
    label_font_size_px: int
    tick_font_size_px: int
    value_font_size_px: int
    legend_font_size_px: int
    label_stroke_width_px: int
    area_outline_width_px: int
    point_radius_px: int
    axis_color_rgb: Tuple[int, int, int]
    grid_color_rgb: Tuple[int, int, int]
    plot_fill_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    legend_border_rgb: Tuple[int, int, int]
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedAreaPanel:
    image: Image.Image
    plot_bbox_px: Tuple[int, int, int, int]
    y_axis_max: int
    y_ticks: Tuple[int, ...]
    entities: Tuple[Dict[str, Any], ...]
    point_traces: Tuple[Dict[str, Any], ...]
    legend_traces: Tuple[Dict[str, Any], ...]


def _as_rgb(value: Sequence[int] | None, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
    if value is None or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])


def _semantic_palette(params: Mapping[str, Any]) -> Tuple[Tuple[int, int, int], ...]:
    raw_palette = params.get("series_palette_rgb", group_default(_RENDER_DEFAULTS, "series_palette_rgb", _DEFAULT_PALETTE))
    if isinstance(raw_palette, Sequence):
        colors = tuple(
            _as_rgb(item, _DEFAULT_PALETTE[index % len(_DEFAULT_PALETTE)])
            for index, item in enumerate(raw_palette)
            if isinstance(item, Sequence)
        )
        if colors:
            return colors
    return tuple(tuple(int(channel) for channel in color) for color in _DEFAULT_PALETTE)


def _params_with_information_style(params: Mapping[str, Any], style: Any) -> Dict[str, Any]:
    styled = dict(params)
    styled.update(
        {
            "axis_color_rgb": list(style.axis_rgb),
            "grid_color_rgb": list(style.grid_rgb),
            "plot_fill_rgb": list(style.surface_rgb),
            "text_color_rgb": list(style.text_rgb),
            "text_stroke_rgb": list(style.text_stroke_rgb),
            "legend_border_rgb": list(style.panel_border_rgb),
        }
    )
    return styled


def _int_default(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> _AreaRenderParams:
    canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1060)))
    canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 680)))
    margin_left = int(params.get("plot_margin_left_px", group_default(_RENDER_DEFAULTS, "plot_margin_left_px", 84)))
    margin_right = int(params.get("plot_margin_right_px", group_default(_RENDER_DEFAULTS, "plot_margin_right_px", 172)))
    margin_top = int(params.get("plot_margin_top_px", group_default(_RENDER_DEFAULTS, "plot_margin_top_px", 48)))
    margin_bottom = int(params.get("plot_margin_bottom_px", group_default(_RENDER_DEFAULTS, "plot_margin_bottom_px", 84)))
    margin_left, margin_right, margin_top, margin_bottom, jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="charts.area.layout",
    )
    return _AreaRenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        plot_margin_left_px=int(margin_left),
        plot_margin_right_px=int(margin_right),
        plot_margin_top_px=int(margin_top),
        plot_margin_bottom_px=int(margin_bottom),
        axis_line_width_px=int(
            resolve_render_int(
                params,
                _RENDER_DEFAULTS,
                "axis_line_width_px",
                2,
                instance_seed=int(instance_seed),
                namespace=TASK_ID,
            )
        ),
        grid_line_width_px=int(
            resolve_render_int(
                params,
                _RENDER_DEFAULTS,
                "grid_line_width_px",
                1,
                instance_seed=int(instance_seed),
                namespace=TASK_ID,
            )
        ),
        tick_length_px=int(params.get("tick_length_px", group_default(_RENDER_DEFAULTS, "tick_length_px", 8))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", 19))),
        tick_font_size_px=int(params.get("tick_font_size_px", group_default(_RENDER_DEFAULTS, "tick_font_size_px", 16))),
        value_font_size_px=int(params.get("value_font_size_px", group_default(_RENDER_DEFAULTS, "value_font_size_px", 14))),
        legend_font_size_px=int(params.get("legend_font_size_px", group_default(_RENDER_DEFAULTS, "legend_font_size_px", 17))),
        label_stroke_width_px=int(
            resolve_render_int(
                params,
                _RENDER_DEFAULTS,
                "label_stroke_width_px",
                2,
                instance_seed=int(instance_seed),
                namespace=TASK_ID,
            )
        ),
        area_outline_width_px=int(
            resolve_render_int(
                params,
                _RENDER_DEFAULTS,
                "area_outline_width_px",
                3,
                instance_seed=int(instance_seed),
                namespace=TASK_ID,
            )
        ),
        point_radius_px=int(
            resolve_render_int(
                params,
                _RENDER_DEFAULTS,
                "point_radius_px",
                6,
                instance_seed=int(instance_seed),
                namespace=TASK_ID,
            )
        ),
        axis_color_rgb=resolve_render_rgb(
            params,
            _RENDER_DEFAULTS,
            "axis_color_rgb",
            (68, 72, 82),
            instance_seed=int(instance_seed),
            namespace=TASK_ID,
        ),
        grid_color_rgb=resolve_render_rgb(
            params,
            _RENDER_DEFAULTS,
            "grid_color_rgb",
            (222, 226, 232),
            instance_seed=int(instance_seed),
            namespace=TASK_ID,
        ),
        plot_fill_rgb=resolve_render_rgb(
            params,
            _RENDER_DEFAULTS,
            "plot_fill_rgb",
            (255, 255, 255),
            instance_seed=int(instance_seed),
            namespace=TASK_ID,
        ),
        text_color_rgb=resolve_render_rgb(
            params,
            _RENDER_DEFAULTS,
            "text_color_rgb",
            (38, 42, 50),
            instance_seed=int(instance_seed),
            namespace=TASK_ID,
        ),
        text_stroke_rgb=resolve_render_rgb(
            params,
            _RENDER_DEFAULTS,
            "text_stroke_rgb",
            (255, 255, 255),
            instance_seed=int(instance_seed),
            namespace=TASK_ID,
        ),
        legend_border_rgb=resolve_render_rgb(
            params,
            _RENDER_DEFAULTS,
            "legend_border_rgb",
            (188, 196, 210),
            instance_seed=int(instance_seed),
            namespace=TASK_ID,
        ),
        layout_jitter_meta=dict(jitter_meta),
    )


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, center: Tuple[float, float], font) -> List[float]:
    raw = draw.textbbox((0, 0), str(text), font=font)
    width = float(raw[2] - raw[0])
    height = float(raw[3] - raw[1])
    return _round_bbox(
        (
            float(center[0]) - 0.5 * width,
            float(center[1]) - 0.5 * height,
            float(center[0]) + 0.5 * width,
            float(center[1]) + 0.5 * height,
        )
    )


def _axis_max(max_value: int, *, tick_step: int) -> int:
    step = max(1, int(tick_step))
    return max(step, int(math.ceil(float(max_value) / float(step)) * step))


def _y_for_value(value: float, *, plot_top: int, plot_bottom: int, y_axis_max: int) -> float:
    span = float(max(1, int(plot_bottom) - int(plot_top)))
    return float(plot_bottom) - ((float(value) / float(max(1, int(y_axis_max)))) * span)


def _sample_palette(*, instance_seed: int, count: int) -> Tuple[Tuple[int, int, int], ...]:
    rng = spawn_rng(int(instance_seed), "charts.area.palette")
    raw_palette = _RENDER_DEFAULTS.get("series_palette_rgb")
    if isinstance(raw_palette, Sequence) and len(raw_palette) >= int(count):
        palette = [_as_rgb(item, _DEFAULT_PALETTE[index % len(_DEFAULT_PALETTE)]) for index, item in enumerate(raw_palette)]
        rng.shuffle(palette)
        return tuple(palette[: int(count)])
    palette = sample_color_palette_with_distance_constraints(
        rng,
        palette_size=int(count),
        channel_min=30,
        channel_max=220,
        anchor_colors=((255, 255, 255), (248, 248, 248)),
        min_distance=42.0,
        distance_space="lab",
    )
    return tuple(tuple(int(channel) for channel in color) for color in palette)


def _render_area_panel(
    background: Image.Image,
    *,
    x_labels: Sequence[str],
    series_labels: Sequence[str],
    series_values: Mapping[str, Sequence[int]],
    stacked: bool,
    query_points: Sequence[Tuple[str, str]],
    instance_seed: int,
    params: Mapping[str, Any],
    render_params: _AreaRenderParams | None = None,
) -> _RenderedAreaPanel:
    render_params = render_params or _render_params(params, instance_seed=int(instance_seed))
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    plot_left = int(render_params.plot_margin_left_px)
    plot_top = int(render_params.plot_margin_top_px)
    plot_right = int(render_params.canvas_width - render_params.plot_margin_right_px)
    plot_bottom = int(render_params.canvas_height - render_params.plot_margin_bottom_px)
    plot_bbox = (int(plot_left), int(plot_top), int(plot_right), int(plot_bottom))
    draw.rectangle(plot_bbox, fill=render_params.plot_fill_rgb)

    x_label_list = [str(label) for label in x_labels]
    series_label_list = [str(label) for label in series_labels]
    point_count = len(x_label_list)
    if int(point_count) < 2:
        raise ValueError("area chart requires at least two x labels")
    x_edge_pad = float(max(18, int(render_params.label_font_size_px)))
    x_start = float(plot_left) + float(x_edge_pad)
    x_end = float(plot_right) - float(x_edge_pad)
    x_step = float(x_end - x_start) / float(max(1, int(point_count) - 1))
    x_centers = [float(x_start) + float(index) * float(x_step) for index in range(int(point_count))]
    totals_by_x = [
        sum(int(series_values[str(series_label)][index]) for series_label in series_label_list)
        for index in range(int(point_count))
    ]
    max_visible = max(totals_by_x if bool(stacked) else [int(series_values[series_label_list[0]][i]) for i in range(point_count)])
    tick_step = int(params.get("y_axis_tick_step", group_default(_RENDER_DEFAULTS, "y_axis_tick_step", 10)))
    y_axis_max = _axis_max(int(max_visible), tick_step=int(tick_step))
    y_ticks = tuple(range(0, int(y_axis_max) + 1, max(1, int(tick_step))))
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    value_font = load_font(int(render_params.value_font_size_px), bold=True)
    legend_font = load_font(int(render_params.legend_font_size_px), bold=True)

    for tick in y_ticks:
        y = _y_for_value(float(tick), plot_top=plot_top, plot_bottom=plot_bottom, y_axis_max=int(y_axis_max))
        draw.line(
            [(float(plot_left), float(y)), (float(plot_right), float(y))],
            fill=render_params.grid_color_rgb,
            width=int(render_params.grid_line_width_px),
        )
        draw_text_centered(
            draw,
            text=str(int(tick)),
            center=(float(plot_left - 28), float(y)),
            font=tick_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
    draw.line(
        [(plot_left, plot_top), (plot_left, plot_bottom), (plot_right, plot_bottom)],
        fill=render_params.axis_color_rgb,
        width=int(render_params.axis_line_width_px),
    )

    palette = _sample_palette(instance_seed=int(instance_seed), count=max(1, len(series_label_list)))
    point_traces: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    query_set = {(str(series), str(label)) for series, label in query_points}

    cumulative_lower = [0 for _ in range(int(point_count))]
    for series_index, series_label in enumerate(series_label_list):
        values = [int(value) for value in series_values[str(series_label)]]
        if len(values) != int(point_count):
            raise ValueError("each area series must match x label count")
        lower = list(cumulative_lower) if bool(stacked) else [0 for _ in values]
        upper = [int(low) + int(value) for low, value in zip(lower, values)]
        fill_rgb = tuple(int(channel) for channel in palette[int(series_index) % len(palette)])
        outline_rgb = tuple(max(0, int(channel * 0.58)) for channel in fill_rgb)
        upper_points = [
            (
                float(x_centers[index]),
                _y_for_value(float(upper[index]), plot_top=plot_top, plot_bottom=plot_bottom, y_axis_max=int(y_axis_max)),
            )
            for index in range(int(point_count))
        ]
        lower_points = [
            (
                float(x_centers[index]),
                _y_for_value(float(lower[index]), plot_top=plot_top, plot_bottom=plot_bottom, y_axis_max=int(y_axis_max)),
            )
            for index in range(int(point_count) - 1, -1, -1)
        ]
        polygon_points = list(upper_points) + list(lower_points)
        draw.polygon(polygon_points, fill=fill_rgb, outline=None)
        if not bool(stacked):
            queried_indices = [
                index
                for index, x_label in enumerate(x_label_list)
                if (str(series_label), str(x_label)) in query_set
            ]
            if len(queried_indices) >= 2:
                start_index = min(int(index) for index in queried_indices)
                end_index = max(int(index) for index in queried_indices)
                highlight_upper = [upper_points[index] for index in range(int(start_index), int(end_index) + 1)]
                highlight_lower = [
                    (float(x_centers[index]), float(plot_bottom))
                    for index in range(int(end_index), int(start_index) - 1, -1)
                ]
                overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
                overlay_draw = ImageDraw.Draw(overlay)
                overlay_draw.polygon(
                    list(highlight_upper) + list(highlight_lower),
                    fill=(255, 224, 92, 78),
                )
                boundary_color = (118, 92, 12, 190)
                for boundary_index in (int(start_index), int(end_index)):
                    overlay_draw.line(
                        [
                            (float(x_centers[boundary_index]), float(plot_bottom)),
                            (
                                float(x_centers[boundary_index]),
                                float(
                                    _y_for_value(
                                        float(upper[boundary_index]),
                                        plot_top=plot_top,
                                        plot_bottom=plot_bottom,
                                        y_axis_max=int(y_axis_max),
                                    )
                                ),
                            ),
                        ],
                        fill=boundary_color,
                        width=max(2, int(render_params.area_outline_width_px)),
                    )
                image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
                draw = ImageDraw.Draw(image)
        draw.line(upper_points, fill=outline_rgb, width=int(render_params.area_outline_width_px), joint="curve")
        if bool(stacked):
            draw.line(
                [
                    (
                        float(x_centers[index]),
                        _y_for_value(float(lower[index]), plot_top=plot_top, plot_bottom=plot_bottom, y_axis_max=int(y_axis_max)),
                    )
                    for index in range(int(point_count))
                ],
                fill=outline_rgb,
                width=max(1, int(render_params.area_outline_width_px) - 1),
                joint="curve",
            )
        for index, x_label in enumerate(x_label_list):
            center_y_value = float(lower[index]) + 0.5 * float(values[index])
            band_center = (
                float(x_centers[index]),
                _y_for_value(center_y_value, plot_top=plot_top, plot_bottom=plot_bottom, y_axis_max=int(y_axis_max)),
            )
            point_y = _y_for_value(float(upper[index]), plot_top=plot_top, plot_bottom=plot_bottom, y_axis_max=int(y_axis_max))
            radius = float(render_params.point_radius_px)
            mark_center = tuple(float(value) for value in band_center)
            value_center = tuple(float(value) for value in band_center)
            point_bbox: List[float] | None = None
            if not bool(stacked):
                mark_center = (float(x_centers[index]), float(point_y))
                value_center = (float(x_centers[index]), float(point_y - 20.0))
                point_bbox = _round_bbox(
                    (
                        float(mark_center[0] - radius),
                        float(mark_center[1] - radius),
                        float(mark_center[0] + radius),
                        float(mark_center[1] + radius),
                    )
                )
                draw.ellipse(
                    (
                        float(mark_center[0] - radius),
                        float(mark_center[1] - radius),
                        float(mark_center[0] + radius),
                        float(mark_center[1] + radius),
                    ),
                    fill=render_params.plot_fill_rgb,
                    outline=outline_rgb,
                    width=max(1, int(render_params.area_outline_width_px) - 1),
                )
            text = str(int(values[index]))
            draw_text_centered(
                draw,
                text=text,
                center=value_center,
                font=value_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=int(render_params.label_stroke_width_px),
            )
            text_bbox = _text_bbox(draw, text=text, center=value_center, font=value_font)
            segment_bbox = [
                round(float(x_centers[index] - 0.5 * max(20.0, x_step * 0.55)), 3),
                round(float(_y_for_value(float(upper[index]), plot_top=plot_top, plot_bottom=plot_bottom, y_axis_max=int(y_axis_max))), 3),
                round(float(x_centers[index] + 0.5 * max(20.0, x_step * 0.55)), 3),
                round(float(_y_for_value(float(lower[index]), plot_top=plot_top, plot_bottom=plot_bottom, y_axis_max=int(y_axis_max))), 3),
            ]
            trace = {
                "entity_id": f"area_{series_index}_{index}",
                "series_label": str(series_label),
                "x_label": str(x_label),
                "x_rank": int(index),
                "series_rank": int(series_index),
                "value": int(values[index]),
                "lower_value": int(lower[index]),
                "upper_value": int(upper[index]),
                "mark_center_px": [round(float(mark_center[0]), 3), round(float(mark_center[1]), 3)],
                "mark_bbox_px": list(point_bbox if point_bbox is not None else segment_bbox),
                "value_center_px": [round(float(value_center[0]), 3), round(float(value_center[1]), 3)],
                "value_bbox_px": list(text_bbox),
                "band_segment_bbox_px": list(segment_bbox),
                "queried": bool((str(series_label), str(x_label)) in query_set),
                "fill_rgb": [int(channel) for channel in fill_rgb],
                "outline_rgb": [int(channel) for channel in outline_rgb],
            }
            point_traces.append(dict(trace))
            entities.append(
                {
                    "entity_id": str(trace["entity_id"]),
                    "entity_type": "area_band_value" if bool(stacked) else "area_point_value",
                    "attrs": dict(trace),
                }
            )
        cumulative_lower = list(upper)

    for index, x_label in enumerate(x_label_list):
        draw.line(
            [(float(x_centers[index]), float(plot_bottom)), (float(x_centers[index]), float(plot_bottom + render_params.tick_length_px))],
            fill=render_params.axis_color_rgb,
            width=max(1, int(render_params.axis_line_width_px)),
        )
        draw_text_centered(
            draw,
            text=str(x_label),
            center=(float(x_centers[index]), float(plot_bottom + render_params.tick_length_px + render_params.label_font_size_px)),
            font=label_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=int(render_params.label_stroke_width_px),
        )

    legend_traces: List[Dict[str, Any]] = []
    legend_left = float(plot_right + 24)
    legend_top = float(plot_top + 18)
    swatch = float(max(18, int(render_params.legend_font_size_px)))
    row_h = float(max(34, int(render_params.legend_font_size_px) + 16))
    if bool(stacked):
        legend_width = float(max(130.0, render_params.canvas_width - legend_left - 24.0))
        legend_height = float(len(series_label_list) * row_h + 16.0)
        legend_bbox = (legend_left - 10.0, legend_top - 10.0, legend_left + legend_width, legend_top + legend_height)
        draw.rounded_rectangle(
            legend_bbox,
            radius=6,
            fill=render_params.plot_fill_rgb,
            outline=render_params.legend_border_rgb,
            width=1,
        )
        for series_index, series_label in enumerate(series_label_list):
            row_y = legend_top + series_index * row_h
            fill_rgb = tuple(int(channel) for channel in palette[int(series_index) % len(palette)])
            swatch_bbox = (legend_left, row_y, legend_left + swatch, row_y + swatch)
            draw.rectangle(swatch_bbox, fill=fill_rgb, outline=tuple(max(0, int(channel * 0.58)) for channel in fill_rgb), width=2)
            text_center = (legend_left + swatch + 12 + 52, row_y + swatch * 0.5)
            draw_text_traced(draw,
                (legend_left + swatch + 12, row_y - 1),
                str(series_label),
                font=legend_font,
                fill=render_params.text_color_rgb,
                stroke_width=1,
                stroke_fill=render_params.text_stroke_rgb,
             role="readout", required=False,)
            text_bbox = draw.textbbox((legend_left + swatch + 12, row_y - 1), str(series_label), font=legend_font)
            legend_trace = {
                "entity_id": f"legend_{series_index}",
                "series_label": str(series_label),
                "series_rank": int(series_index),
                "swatch_bbox_px": _round_bbox(swatch_bbox),
                "label_center_px": [round(float(text_center[0]), 3), round(float(text_center[1]), 3)],
                "label_bbox_px": _round_bbox(text_bbox),
                "fill_rgb": [int(channel) for channel in fill_rgb],
            }
            legend_traces.append(dict(legend_trace))
            entities.append(
                {
                    "entity_id": str(legend_trace["entity_id"]),
                    "entity_type": "legend_entry",
                    "attrs": dict(legend_trace),
                }
            )

    return _RenderedAreaPanel(
        image=image,
        plot_bbox_px=tuple(int(value) for value in plot_bbox),
        y_axis_max=int(y_axis_max),
        y_ticks=tuple(int(value) for value in y_ticks),
        entities=tuple(dict(entity) for entity in entities),
        point_traces=tuple(dict(trace) for trace in point_traces),
        legend_traces=tuple(dict(trace) for trace in legend_traces),
    )


def _sample_point_count(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, Tuple[int, int]]:
    point_min, point_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="point_count_min",
        max_key="point_count_max",
        fallback_min=7,
        fallback_max=10,
        context=f"generation defaults for {TASK_ID}",
    )
    rng = spawn_rng(int(instance_seed), "charts.area.point_count")
    return int(rng.randint(int(point_min), int(point_max))), (int(point_min), int(point_max))


def _sample_interval(
    *,
    point_count: int,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[int, int, Tuple[int, int]]:
    span_min, span_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="interval_span_min",
        max_key="interval_span_max",
        fallback_min=3,
        fallback_max=5,
        context=f"generation defaults for {TASK_ID}",
    )
    span_max = min(int(span_max), max(1, int(point_count) - 1))
    span_min = min(int(span_min), int(span_max))
    rng = spawn_rng(int(instance_seed), "charts.area.interval")
    span = int(rng.randint(int(span_min), int(span_max)))
    start = int(rng.randint(0, int(point_count) - int(span) - 1))
    return int(start), int(start + span), (int(span_min), int(span_max))


def _sample_single_values(*, point_count: int, params: Mapping[str, Any], instance_seed: int) -> Tuple[int, ...]:
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="single_value_min",
        max_key="single_value_max",
        fallback_min=6,
        fallback_max=42,
        context=f"generation defaults for {TASK_ID}",
    )
    even_values = [value for value in range(int(value_min), int(value_max) + 1) if int(value) % 2 == 0]
    if not even_values:
        raise ValueError("single area values require at least one even value")
    rng = spawn_rng(int(instance_seed), "charts.area.single_values")
    return tuple(int(even_values[rng.randrange(len(even_values))]) for _ in range(int(point_count)))


def _sample_stacked_values(
    *,
    category_count: int,
    point_count: int,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[int, ...], ...]:
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="stacked_value_min",
        max_key="stacked_value_max",
        fallback_min=4,
        fallback_max=16,
        context=f"generation defaults for {TASK_ID}",
    )
    rng = spawn_rng(int(instance_seed), "charts.area.stacked_values")
    return tuple(
        tuple(int(rng.randint(int(value_min), int(value_max))) for _ in range(int(point_count)))
        for _ in range(int(category_count))
    )


def _sample_categories(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[str, ...], Tuple[int, int]]:
    cat_min, cat_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="category_count_min",
        max_key="category_count_max",
        fallback_min=3,
        fallback_max=4,
        context=f"generation defaults for {TASK_ID}",
    )
    rng = spawn_rng(int(instance_seed), "charts.area.categories")
    count = int(rng.randint(int(cat_min), int(cat_max)))
    label_max_chars = int(params.get("category_label_max_chars", group_default(_GEN_DEFAULTS, "category_label_max_chars", 6)))
    labels = resolve_chart_entity_labels(
        rng,
        count=int(count),
        min_chars=2,
        max_chars=int(label_max_chars),
        allow_spaces=False,
    ).labels
    return tuple(str(label) for label in labels), (int(cat_min), int(cat_max))


def _trapezoid_interval_area(values: Sequence[int], start_index: int, end_index: int) -> int:
    total = 0
    for index in range(int(start_index), int(end_index)):
        total += (int(values[index]) + int(values[index + 1])) // 2
    return int(total)


def _make_prompt(
    *,
    query_id: str,
    prompt_defaults: Mapping[str, Any],
    slots: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, str], Dict[str, Any], Dict[str, Any], str]:
    prompt_selection = render_task_prompt_variants(
        domain="charts",
        task_group="area",
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
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


class ChartsAreaPanelQueryTask:
    """Generate one area-chart panel query."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "area"
    allowed_query_ids: Tuple[str, ...] = ("interval_area_value",)

    def _select_query_id(self, instance_seed: int, *, params: Mapping[str, Any]) -> str:
        allowed_query_ids = tuple(str(query_id) for query_id in self.allowed_query_ids)
        requested_query_id = params.get("query_id")
        if requested_query_id is not None:
            if str(requested_query_id) not in set(allowed_query_ids):
                raise ValueError(f"unsupported area query_id for {self.task_id}: {requested_query_id}")
            return str(requested_query_id)
        if len(allowed_query_ids) == 1:
            return str(allowed_query_ids[0])
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.query_id")
        return str(allowed_query_ids[int(rng.randrange(len(allowed_query_ids)))])

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id = self._select_query_id(int(instance_seed), params=params)
        if query_id not in set(SUPPORTED_QUERY_IDS):
            raise ValueError(f"unsupported area query_id: {query_id}")
        point_count, point_count_range = _sample_point_count(params, instance_seed=int(instance_seed))
        x_labels = sample_chart_labels(
            count=int(point_count),
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.labels:{str(query_id)}:{int(point_count)}",
        )
        start_index, end_index, interval_span_range = _sample_interval(
            point_count=int(point_count),
            params=params,
            instance_seed=int(instance_seed),
        )
        start_label = str(x_labels[int(start_index)])
        end_label = str(x_labels[int(end_index)])
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_integer",
                "answer_hint_label",
                "object_description_single_area",
                "object_description_stacked_area",
                "annotation_hint_interval_area_value",
                "annotation_hint_stacked_band_interval_sum_value",
                "annotation_hint_stacked_dominance_label",
                "json_example_interval_area_value",
                "json_example_stacked_band_interval_sum_value",
                "json_example_stacked_dominance_label",
                "json_example_answer_only_interval_area_value",
                "json_example_answer_only_stacked_band_interval_sum_value",
                "json_example_answer_only_stacked_dominance_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )

        if query_id == "interval_area_value":
            values = _sample_single_values(point_count=int(point_count), params=params, instance_seed=int(instance_seed))
            series_labels = ("Series",)
            series_values = {"Series": tuple(int(value) for value in values)}
            answer_value: int | str = _trapezoid_interval_area(values, int(start_index), int(end_index))
            annotation_pairs = [("Series", str(x_labels[index])) for index in range(int(start_index), int(end_index) + 1)]
            stacked = False
            object_description = str(prompt_defaults["object_description_single_area"])
            answer_type = "integer"
            question_format = "numeric_open"
            extra_trace = {
                "interval_area": int(answer_value),
                "unit_spacing": 1,
                "trapezoid_terms": [
                    {
                        "left_label": str(x_labels[index]),
                        "right_label": str(x_labels[index + 1]),
                        "left_value": int(values[index]),
                        "right_value": int(values[index + 1]),
                        "area": int((int(values[index]) + int(values[index + 1])) // 2),
                    }
                    for index in range(int(start_index), int(end_index))
                ],
            }
        else:
            category_labels, category_count_range = _sample_categories(params=params, instance_seed=int(instance_seed))
            stacked_values = _sample_stacked_values(
                category_count=len(category_labels),
                point_count=int(point_count),
                params=params,
                instance_seed=int(instance_seed),
            )
            series_labels = tuple(str(label) for label in category_labels)
            series_values = {
                str(label): tuple(int(value) for value in stacked_values[index])
                for index, label in enumerate(series_labels)
            }
            rng = spawn_rng(int(instance_seed), "charts.area.query_category")
            if query_id == "stacked_band_interval_sum_value":
                selected_category = str(series_labels[int(rng.randrange(len(series_labels)))])
                answer_value = int(sum(int(series_values[selected_category][index]) for index in range(int(start_index), int(end_index) + 1)))
                annotation_pairs = [(selected_category, str(x_labels[index])) for index in range(int(start_index), int(end_index) + 1)]
                extra_trace = {
                    "category_label": str(selected_category),
                    "category_count": int(len(series_labels)),
                    "category_count_range": list(category_count_range),
                    "interval_values": [int(series_values[selected_category][index]) for index in range(int(start_index), int(end_index) + 1)],
                    "interval_sum": int(answer_value),
                }
                answer_type = "integer"
                question_format = "numeric_open"
            else:
                totals_by_category = {
                    str(label): int(sum(int(series_values[str(label)][index]) for index in range(int(start_index), int(end_index) + 1)))
                    for label in series_labels
                }
                sorted_totals = sorted(totals_by_category.items(), key=lambda item: (-int(item[1]), str(item[0])))
                top_label, top_total = sorted_totals[0]
                second_total = int(sorted_totals[1][1]) if len(sorted_totals) > 1 else -1
                margin_min = _int_default(params, "dominance_margin_min", 3)
                if int(top_total) - int(second_total) < int(margin_min):
                    raise ValueError("stacked dominance query did not have a unique enough winner")
                answer_value = str(top_label)
                annotation_pairs = [
                    (str(top_label), str(x_labels[index]))
                    for index in range(int(start_index), int(end_index) + 1)
                ]
                extra_trace = {
                    "category_count": int(len(series_labels)),
                    "category_count_range": list(category_count_range),
                    "totals_by_category": {str(key): int(value) for key, value in totals_by_category.items()},
                    "winning_category": str(top_label),
                    "winning_total": int(top_total),
                    "runner_up_total": int(second_total),
                    "dominance_margin": int(top_total) - int(second_total),
                }
                answer_type = "string"
                question_format = "label_open"
            stacked = True
            object_description = str(prompt_defaults["object_description_stacked_area"])

        information_style, information_style_meta = resolve_chart_information_style(
            instance_seed=int(instance_seed),
            params=params,
            scene_id=SCENE_ID,
            task_group=self.task_group,
            protected_colors=_semantic_palette(params),
        )
        render_style_params = _params_with_information_style(params, information_style)
        area_render_params = _render_params(render_style_params, instance_seed=int(instance_seed))
        background, background_meta = make_chart_information_background(
            canvas_width=int(area_render_params.canvas_width),
            canvas_height=int(area_render_params.canvas_height),
            style=information_style,
            instance_seed=int(instance_seed),
            namespace=f"charts.{self.task_group}.{SCENE_ID}.information_scene_background",
        )
        chart_font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _render_area_panel(
                background,
                x_labels=x_labels,
                series_labels=series_labels,
                series_values=series_values,
                stacked=bool(stacked),
                query_points=annotation_pairs,
                instance_seed=int(instance_seed),
                params=render_style_params,
                render_params=area_render_params,
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        trace_by_pair = {
            (str(trace["series_label"]), str(trace["x_label"])): trace
            for trace in rendered.point_traces
        }
        annotation_points = [
            list(trace_by_pair[(str(series), str(label))]["mark_center_px"])
            for series, label in annotation_pairs
            if (str(series), str(label)) in trace_by_pair
        ]
        answer_hint_key = "answer_hint_integer" if str(answer_type) == "integer" else "answer_hint_label"
        slots = {
            "object_description": str(object_description),
            "start_label": str(start_label),
            "end_label": str(end_label),
            "category_label": str(extra_trace.get("category_label", "")),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults[f"annotation_hint_{query_id}"]),
            "answer_hint": str(prompt_defaults[answer_hint_key]),
            "json_example": str(prompt_defaults[f"json_example_{query_id}"]),
            "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{query_id}"]),
        }
        prompt, prompt_variants, prompt_variant, prompt_variants_for_trace, active_prompt_key = _make_prompt(
            query_id=str(query_id),
            prompt_defaults=prompt_defaults,
            slots=slots,
            instance_seed=int(instance_seed),
        )

        values_by_series = {
            str(series): [int(value) for value in values]
            for series, values in series_values.items()
        }
        query_params = {
            "query_id": str(query_id),
            "point_count": int(point_count),
            "point_count_range": list(point_count_range),
            "x_labels": [str(label) for label in x_labels],
            "series_labels": [str(label) for label in series_labels],
            "start_index": int(start_index),
            "end_index": int(end_index),
            "start_label": str(start_label),
            "end_label": str(end_label),
            "interval_span": int(end_index) - int(start_index),
            "interval_span_range": list(interval_span_range),
            "stacked": bool(stacked),
            **dict(extra_trace),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_area_panel",
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
                "canvas_width": int(rendered.image.size[0]),
                "canvas_height": int(rendered.image.size[1]),
                "coord_space": "pixel",
                "scene_variant": "stacked_area" if bool(stacked) else "area",
                "information_scene_style": dict(information_style_meta),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "y_axis_max": int(rendered.y_axis_max),
                "y_ticks": [int(tick) for tick in rendered.y_ticks],
                "layout_jitter": dict(area_render_params.layout_jitter_meta),
                "text_style": {
                    "label_font_size_px": int(area_render_params.label_font_size_px),
                    "tick_font_size_px": int(area_render_params.tick_font_size_px),
                    "value_font_size_px": int(area_render_params.value_font_size_px),
                    "legend_font_size_px": int(area_render_params.legend_font_size_px),
                    "label_stroke_width_px": int(area_render_params.label_stroke_width_px),
                    "font_asset_version": str(font_asset_version()),
                    "chart_font_family": str(chart_font_family),
                    "chart_font_exclude_tags": [],
                },
                "axis_style": {
                    "axis_line_width_px": int(area_render_params.axis_line_width_px),
                    "grid_line_width_px": int(area_render_params.grid_line_width_px),
                    "tick_length_px": int(area_render_params.tick_length_px),
                },
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "point_traces": [dict(trace) for trace in rendered.point_traces],
                "legend_traces": [dict(trace) for trace in rendered.legend_traces],
            },
            "execution_trace": {
                "query_id": str(query_id),
                "answer_value": answer_value,
                "question_format": str(question_format),
                "values_by_series": dict(values_by_series),
                "annotation_pairs": [[str(series), str(label)] for series, label in annotation_pairs],
                **dict(query_params),
            },
            "witness_symbolic": {
                "type": "point_set",
                "count": int(len(annotation_points)),
            },
            "projected_annotation": {
                "type": "point_set",
                "point_set": list(annotation_points),
                "pixel_point_set": list(annotation_points),
            },
        }
        visual_count = int(point_count) * max(1, len(series_labels))
        visual_bounds = [int(point_count_range[0]), int(point_count_range[1]) * max(1, int(_int_default(params, "category_count_max", 4)))]
        interval_span = int(end_index) - int(start_index)
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(visual_count), visual_bounds),
                "reasoning_load": float(_QUERY_REASONING_LOAD[str(query_id)]),
                "interval_span": normalize_int_with_bounds(int(interval_span), interval_span_range),
            },
        )
        answer_gt = (
            TypedValue(type="integer", value=int(answer_value))
            if str(answer_type) == "integer"
            else TypedValue(type="string", value=str(answer_value))
        )
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=TypedValue(type="point_set", value=[list(point) for point in annotation_points]),
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
        if str(self.task_id) != TASK_ID:
            shared_gen_defaults, shared_render_defaults, _ = split_generation_rendering_prompt_defaults(
                _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
            )
            task_gen_defaults, task_render_defaults, _ = split_generation_rendering_prompt_defaults(
                _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
                task_id=str(self.task_id),
            )
            task_override_params = {
                str(key): value
                for key, value in task_gen_defaults.items()
                if shared_gen_defaults.get(str(key)) != value
            }
            task_override_params.update(
                {
                    str(key): value
                    for key, value in task_render_defaults.items()
                    if shared_render_defaults.get(str(key)) != value
                }
            )
            effective_params = dict(task_override_params)
            effective_params.update(dict(params))
            params = effective_params
        attempts = max(1, int(max_attempts))
        last_error: Exception | None = None
        for attempt in range(attempts):
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), "charts.area.retry", int(attempt)))
            try:
                return self._generate_once(int(attempt_seed), params=params)
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


@register_task
class ChartsAreaIntervalAreaValueTask(ChartsAreaPanelQueryTask):
    """Compute interval area over a filled area chart."""

    task_id = "task_charts__area__interval_area_value"
    allowed_query_ids = ("interval_area_value",)


@register_task
class ChartsAreaStackedBandIntervalSumValueTask(ChartsAreaPanelQueryTask):
    """Compute an interval sum for one band in a stacked area chart."""

    task_id = "task_charts__area__stacked_band_interval_sum_value"
    allowed_query_ids = ("stacked_band_interval_sum_value",)


@register_task
class ChartsAreaStackedDominanceLabelTask(ChartsAreaPanelQueryTask):
    """Find the dominant stacked-area category over a labeled interval."""

    task_id = "task_charts__area__stacked_band_dominance_label"
    allowed_query_ids = ("stacked_dominance_label",)


__all__ = [
    "ChartsAreaIntervalAreaValueTask",
    "ChartsAreaPanelQueryTask",
    "ChartsAreaStackedDominanceLabelTask",
    "ChartsAreaStackedBandIntervalSumValueTask",
]
