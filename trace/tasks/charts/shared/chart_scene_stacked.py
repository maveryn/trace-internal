"""Shared chart-scene stacked composition renderers."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ...shared.text_rendering import draw_text_centered, load_font
from .chart_scene_types import (
    BoxPlotSpec,
    ChartColor,
    ChartMarkSpec,
    ChartRenderParams,
    HistogramBinSpec,
    MultiSeriesChartMarkSpec,
    RenderedChartScene,
    SUPPORTED_CHART_SCENE_VARIANTS,
    SUPPORTED_COMPOSITION_CHART_SCENE_VARIANTS,
    SUPPORTED_DISTRIBUTION_CHART_SCENE_VARIANTS,
    SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS,
    ViolinPlotSpec,
)
from .chart_scene_primitives import (
    _axis_slot_centers,
    _axis_ticks,
    _bbox_from_points,
    _clamp_text_center_to_canvas,
    _darken_rgb,
    _draw_styled_line,
    _draw_violin_polygon,
    _guide_lines_enabled,
    _label_center_for_variant,
    _radar_polygon_points,
    _resolve_plot_bbox,
    _resolve_value_axis,
    _scatter_slot_centers,
    _slot_centers,
    _text_bbox,
    _text_size,
    _tick_x,
    _tick_y,
    _union_bboxes,
    _violin_palette_color,
    resolve_chart_render_params,
    value_axis_render_metadata,
)

from .chart_scene_multiseries import (
    _MULTISERIES_GROUP_WIDTH_FRACTION,
    _MULTISERIES_LEGEND_WIDTH_FRACTION,
    _MULTISERIES_LEGEND_WIDTH_MAX_FRACTION,
    _MULTISERIES_LEGEND_MIN_WIDTH_PX,
)

def render_stacked_chart_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    marks: Sequence[MultiSeriesChartMarkSpec],
    render_params: ChartRenderParams,
) -> RenderedChartScene:
    """Render one stacked composition chart scene onto `background`."""

    selected_variant = str(scene_variant)
    if selected_variant not in set(SUPPORTED_COMPOSITION_CHART_SCENE_VARIANTS):
        raise ValueError(f"unsupported composition chart scene_variant: {selected_variant}")
    if len(marks) < 6:
        raise ValueError("stacked charts require at least six marks")

    category_specs: Dict[int, str] = {}
    series_specs: Dict[int, str] = {}
    marks_by_key: Dict[Tuple[int, int], MultiSeriesChartMarkSpec] = {}
    for mark in marks:
        category_specs[int(mark.category_rank)] = str(mark.category_label)
        series_specs[int(mark.series_rank)] = str(mark.series_label)
        key = (int(mark.category_rank), int(mark.series_rank))
        if key in marks_by_key:
            raise ValueError("duplicate stacked mark for category/series pair")
        marks_by_key[key] = mark
    category_ranks = sorted(category_specs.keys())
    series_ranks = sorted(series_specs.keys())
    expected_keys = {
        (int(category_rank), int(series_rank))
        for category_rank in category_ranks
        for series_rank in series_ranks
    }
    if set(marks_by_key.keys()) != expected_keys:
        raise ValueError("stacked charts require one mark per category/series pair")

    categories = [(int(rank), str(category_specs[int(rank)])) for rank in category_ranks]
    series_list = [(int(rank), str(series_specs[int(rank)])) for rank in series_ranks]

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    plot_left, plot_top, plot_right, plot_bottom = _resolve_plot_bbox(render_params)
    draw.rectangle((int(plot_left), int(plot_top), int(plot_right), int(plot_bottom)), fill=render_params.plot_fill_rgb)

    plot_width = float(max(1, int(plot_right) - int(plot_left)))
    legend_width = float(
        min(
            max(_MULTISERIES_LEGEND_MIN_WIDTH_PX, plot_width * _MULTISERIES_LEGEND_WIDTH_FRACTION),
            plot_width * _MULTISERIES_LEGEND_WIDTH_MAX_FRACTION,
        )
    )
    legend_gap = float(max(18.0, float(render_params.label_font_size_px)))
    chart_right = int(max(int(plot_left) + 180, int(round(float(plot_right) - float(legend_width) - float(legend_gap)))))
    chart_bbox = (int(plot_left), int(plot_top), int(chart_right), int(plot_bottom))

    stack_totals_by_category = {
        str(category_label): int(
            sum(int(marks_by_key[(int(category_rank), int(series_rank))].value) for series_rank, _ in series_list)
        )
        for category_rank, category_label in categories
    }
    max_total = max(int(value) for value in stack_totals_by_category.values())
    y_axis_max = max(8, int(max_total) + 1)
    y_ticks = _axis_ticks(y_axis_max)

    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    axis_color = tuple(int(value) for value in render_params.axis_color_rgb)
    grid_color = tuple(int(value) for value in render_params.grid_color_rgb)

    if selected_variant == "stacked_horizontal_bar":
        for tick_value in y_ticks:
            x_px = _tick_x(
                int(tick_value),
                x_axis_max=int(y_axis_max),
                plot_left=int(plot_left),
                plot_right=int(chart_right),
            )
            draw.line(
                [(float(x_px), float(plot_top)), (float(x_px), float(plot_bottom))],
                fill=grid_color,
                width=int(render_params.grid_line_width_px),
            )
            draw.line(
                [
                    (float(x_px), float(plot_bottom)),
                    (float(x_px), float(plot_bottom) + float(render_params.tick_length_px)),
                ],
                fill=axis_color,
                width=int(render_params.axis_line_width_px),
            )
    else:
        for tick_value in y_ticks:
            y_px = _tick_y(
                int(tick_value),
                y_axis_max=int(y_axis_max),
                plot_top=int(plot_top),
                plot_bottom=int(plot_bottom),
            )
            draw.line(
                [(float(plot_left), float(y_px)), (float(chart_right), float(y_px))],
                fill=grid_color,
                width=int(render_params.grid_line_width_px),
            )
            draw.line(
                [
                    (float(plot_left) - float(render_params.tick_length_px), float(y_px)),
                    (float(plot_left), float(y_px)),
                ],
                fill=axis_color,
                width=int(render_params.axis_line_width_px),
            )

    draw.line(
        [(float(plot_left), float(plot_top)), (float(plot_left), float(plot_bottom))],
        fill=axis_color,
        width=int(render_params.axis_line_width_px),
    )
    draw.line(
        [(float(plot_left), float(plot_bottom)), (float(chart_right), float(plot_bottom))],
        fill=axis_color,
        width=int(render_params.axis_line_width_px),
    )

    if selected_variant == "stacked_horizontal_bar":
        category_centers = _axis_slot_centers(
            count=len(categories),
            start_px=int(plot_top),
            end_px=int(plot_bottom),
        )
        slot_height = float(max(1.0, (float(plot_bottom) - float(plot_top)) / max(1, len(categories))))
        bar_height = float(max(18.0, float(render_params.bar_width_fraction) * float(slot_height)))
    else:
        category_centers = _slot_centers(
            count=len(categories),
            plot_left=int(plot_left),
            plot_right=int(chart_right),
        )
        slot_width = float(max(1.0, (float(chart_right) - float(plot_left)) / max(1, len(categories))))
        bar_width = float(max(18.0, float(render_params.bar_width_fraction) * float(slot_width)))

    category_label_meta: Dict[str, Dict[str, List[float]]] = {}
    for category_rank, category_label in categories:
        if selected_variant == "stacked_horizontal_bar":
            category_center_y = float(category_centers[int(category_rank)])
            label_center = (
                float(plot_left) - float(max(24, int(render_params.label_font_size_px) + 10)),
                float(category_center_y),
            )
        else:
            category_center_x = float(category_centers[int(category_rank)])
            label_center = (
                float(category_center_x),
                float(plot_bottom) + float(render_params.tick_length_px) + 18.0,
            )
        draw_text_centered(
            draw,
            text=str(category_label),
            center=label_center,
            font=label_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=int(render_params.label_stroke_width_px),
        )
        label_bbox = _text_bbox(draw, text=str(category_label), center=label_center, font=label_font)
        category_label_meta[str(category_label)] = {
            "center": [round(float(label_center[0]), 3), round(float(label_center[1]), 3)],
            "bbox": [round(float(value), 3) for value in label_bbox],
        }

    mark_records: List[Dict[str, Any]] = []
    mark_bboxes_by_category: Dict[str, List[Tuple[float, float, float, float]]] = {
        str(category_label): []
        for _, category_label in categories
    }

    for category_rank, category_label in categories:
        cumulative_value = 0
        for series_rank, series_label in series_list:
            mark = marks_by_key[(int(category_rank), int(series_rank))]
            fill_rgb = (
                tuple(int(channel) for channel in mark.fill_rgb)
                if isinstance(mark.fill_rgb, tuple)
                else tuple(int(value) for value in render_params.mark_fill_rgb)
            )
            outline_rgb = (
                tuple(int(channel) for channel in mark.outline_rgb)
                if isinstance(mark.outline_rgb, tuple)
                else tuple(int(value) for value in render_params.mark_outline_rgb)
            )
            segment_start = int(cumulative_value)
            segment_end = int(cumulative_value) + int(mark.value)
            if selected_variant == "stacked_horizontal_bar":
                y_center = float(category_centers[int(category_rank)])
                x_start = _tick_x(
                    int(segment_start),
                    x_axis_max=int(y_axis_max),
                    plot_left=int(plot_left),
                    plot_right=int(chart_right),
                )
                x_end = _tick_x(
                    int(segment_end),
                    x_axis_max=int(y_axis_max),
                    plot_left=int(plot_left),
                    plot_right=int(chart_right),
                )
                mark_bbox = (
                    float(x_start),
                    float(y_center - 0.5 * float(bar_height)),
                    float(x_end),
                    float(y_center + 0.5 * float(bar_height)),
                )
                value_center = (float(0.5 * (x_start + x_end)), float(y_center))
            else:
                x_center = float(category_centers[int(category_rank)])
                y_top = _tick_y(
                    int(segment_end),
                    y_axis_max=int(y_axis_max),
                    plot_top=int(plot_top),
                    plot_bottom=int(plot_bottom),
                )
                y_bottom = _tick_y(
                    int(segment_start),
                    y_axis_max=int(y_axis_max),
                    plot_top=int(plot_top),
                    plot_bottom=int(plot_bottom),
                )
                mark_bbox = (
                    float(x_center - 0.5 * float(bar_width)),
                    float(y_top),
                    float(x_center + 0.5 * float(bar_width)),
                    float(y_bottom),
                )
                value_center = (float(x_center), float(0.5 * (y_top + y_bottom)))
            draw.rectangle(
                mark_bbox,
                fill=fill_rgb,
                outline=outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )
            value_center = _clamp_text_center_to_canvas(
                draw,
                text=str(mark.value),
                center=value_center,
                font=tick_font,
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
            )
            draw_text_centered(
                draw,
                text=str(mark.value),
                center=value_center,
                font=tick_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=max(1, int(round(0.06 * float(render_params.tick_font_size_px)))),
            )
            value_bbox = _text_bbox(draw, text=str(mark.value), center=value_center, font=tick_font)
            mark_bboxes_by_category[str(category_label)].append(tuple(float(value) for value in mark_bbox))
            mark_records.append(
                {
                    "category_label": str(category_label),
                    "series_label": str(series_label),
                    "category_rank": int(category_rank),
                    "series_rank": int(series_rank),
                    "value": int(mark.value),
                    "mark_center_px": [
                        round(float(0.5 * (mark_bbox[0] + mark_bbox[2])), 3),
                        round(float(0.5 * (mark_bbox[1] + mark_bbox[3])), 3),
                    ],
                    "mark_bbox_px": [round(float(value), 3) for value in mark_bbox],
                    "value_center_px": [round(float(value_center[0]), 3), round(float(value_center[1]), 3)],
                    "value_bbox_px": [round(float(value), 3) for value in value_bbox],
                    "fill_rgb": [int(channel) for channel in fill_rgb],
                    "outline_rgb": [int(channel) for channel in outline_rgb],
                }
            )
            cumulative_value = int(segment_end)

    legend_left = float(chart_right) + float(legend_gap)
    legend_top = float(plot_top) + 16.0
    legend_row_height = float(max(render_params.label_font_size_px + 16, 42))
    legend_swatch_side = float(max(28, int(round(render_params.label_font_size_px * 1.05))))
    legend_frame_pad = float(max(3, int(round(render_params.mark_outline_width_px * 1.5))))
    legend_text_gap = float(max(16, int(render_params.label_font_size_px * 0.8)))
    legend_frame_fill = tuple(int(value) for value in render_params.plot_fill_rgb)
    legend_meta_by_series: Dict[str, Dict[str, List[float]]] = {}
    for index, (_, series_label) in enumerate(series_list):
        sample_record = next(record for record in mark_records if str(record["series_label"]) == str(series_label))
        fill_rgb = tuple(int(channel) for channel in sample_record["fill_rgb"])
        outline_rgb = tuple(int(channel) for channel in sample_record["outline_rgb"])
        row_y = float(legend_top) + float(index) * float(legend_row_height)
        swatch_bbox = (
            float(legend_left),
            float(row_y),
            float(legend_left + legend_swatch_side),
            float(row_y + legend_swatch_side),
        )
        legend_frame_bbox = (
            float(swatch_bbox[0] - legend_frame_pad),
            float(swatch_bbox[1] - legend_frame_pad),
            float(swatch_bbox[2] + legend_frame_pad),
            float(swatch_bbox[3] + legend_frame_pad),
        )
        draw.rectangle(
            legend_frame_bbox,
            fill=legend_frame_fill,
            outline=axis_color,
            width=max(1, int(render_params.mark_outline_width_px)),
        )
        draw.rectangle(
            swatch_bbox,
            fill=fill_rgb,
            outline=outline_rgb,
            width=max(2, int(render_params.mark_outline_width_px)),
        )
        label_width, _ = _text_size(draw, text=str(series_label), font=label_font)
        label_left = float(legend_frame_bbox[2]) + float(legend_text_gap)
        label_center = (
            float(label_left + (0.5 * label_width)),
            float(0.5 * (swatch_bbox[1] + swatch_bbox[3])),
        )
        draw_text_centered(
            draw,
            text=str(series_label),
            center=label_center,
            font=label_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=int(render_params.label_stroke_width_px),
        )
        label_bbox = _text_bbox(draw, text=str(series_label), center=label_center, font=label_font)
        legend_meta_by_series[str(series_label)] = {
            "swatch_bbox": [round(float(value), 3) for value in swatch_bbox],
            "label_bbox": [round(float(value), 3) for value in label_bbox],
        }

    category_group_bboxes = {}
    for _, category_label in categories:
        label_bbox = tuple(float(value) for value in category_label_meta[str(category_label)]["bbox"])
        union_inputs = [label_bbox] + [
            tuple(float(value) for value in bbox)
            for bbox in mark_bboxes_by_category[str(category_label)]
        ]
        category_group_bboxes[str(category_label)] = [
            round(float(value), 3) for value in _union_bboxes(union_inputs)
        ]

    mark_traces: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    for record in mark_records:
        category_label = str(record["category_label"])
        category_center = list(category_label_meta[category_label]["center"])
        category_bbox = list(category_label_meta[category_label]["bbox"])
        category_group_bbox = list(category_group_bboxes[category_label])
        legend_meta = legend_meta_by_series.get(str(record["series_label"]), {})
        mark_trace = {
            "entity_id": f"segment_{category_label}_{str(record['series_label'])}",
            "category_label": str(category_label),
            "series_label": str(record["series_label"]),
            "category_rank": int(record["category_rank"]),
            "series_rank": int(record["series_rank"]),
            "value": int(record["value"]),
            "mark_center_px": list(record["mark_center_px"]),
            "mark_bbox_px": list(record["mark_bbox_px"]),
            "value_center_px": list(record["value_center_px"]),
            "value_bbox_px": list(record["value_bbox_px"]),
            "category_label_center_px": list(category_center),
            "category_label_bbox_px": list(category_bbox),
            "category_group_bbox_px": list(category_group_bbox),
            "legend_swatch_bbox_px": list(legend_meta.get("swatch_bbox", [])),
            "legend_label_bbox_px": list(legend_meta.get("label_bbox", [])),
            "mark_fill_rgb": list(record["fill_rgb"]),
            "mark_outline_rgb": list(record["outline_rgb"]),
        }
        mark_traces.append(mark_trace)
        entities.append(
            {
                "entity_id": str(mark_trace["entity_id"]),
                "entity_type": "segment",
                "attrs": {
                    "category_label": str(category_label),
                    "series_label": str(record["series_label"]),
                    "category_rank": int(record["category_rank"]),
                    "series_rank": int(record["series_rank"]),
                    "value": int(record["value"]),
                    "scene_variant": str(selected_variant),
                    "mark_center_px": list(mark_trace["mark_center_px"]),
                    "mark_bbox_px": list(mark_trace["mark_bbox_px"]),
                    "value_center_px": list(mark_trace["value_center_px"]),
                    "category_group_bbox_px": list(mark_trace["category_group_bbox_px"]),
                    "legend_swatch_bbox_px": list(mark_trace["legend_swatch_bbox_px"]),
                    "legend_label_bbox_px": list(mark_trace["legend_label_bbox_px"]),
                    "mark_fill_rgb": list(mark_trace["mark_fill_rgb"]),
                    "mark_outline_rgb": list(mark_trace["mark_outline_rgb"]),
                },
            }
        )

    return RenderedChartScene(
        image=image,
        mark_traces=tuple(dict(item) for item in mark_traces),
        entities=tuple(dict(item) for item in entities),
        plot_bbox_px=tuple(int(value) for value in chart_bbox),
        y_axis_max=int(y_axis_max),
        y_ticks=tuple(int(value) for value in y_ticks),
        scene_variant=str(selected_variant),
    )


__all__ = [
    'render_stacked_chart_scene',
]
