"""Shared labeled chart-scene rendering helpers for chart tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ...shared.text_rendering import draw_text_centered, load_font


ChartColor = Tuple[int, int, int]

SUPPORTED_CHART_SCENE_VARIANTS: Tuple[str, ...] = (
    "area",
    "bar",
    "line",
    "scatter",
    "radar",
    "pie",
    "donut",
    "horizontal_bar",
    "dot_plot",
    "lollipop",
)

SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS: Tuple[str, ...] = (
    "grouped_bar",
    "grouped_horizontal_bar",
    "multi_line",
    "grouped_lollipop",
)

SUPPORTED_COMPOSITION_CHART_SCENE_VARIANTS: Tuple[str, ...] = (
    "stacked_bar",
    "stacked_horizontal_bar",
)

SUPPORTED_DISTRIBUTION_CHART_SCENE_VARIANTS: Tuple[str, ...] = (
    "boxplot",
    "histogram",
    "violin",
)

_MULTISERIES_GROUP_WIDTH_FRACTION = 0.60
_MULTISERIES_LEGEND_WIDTH_FRACTION = 0.18
_MULTISERIES_LEGEND_WIDTH_MAX_FRACTION = 0.24
_MULTISERIES_LEGEND_MIN_WIDTH_PX = 140.0


@dataclass(frozen=True)
class ChartMarkSpec:
    """One symbolic chart mark."""

    label: str
    value: int
    fill_rgb: ChartColor | None = None
    outline_rgb: ChartColor | None = None


@dataclass(frozen=True)
class MultiSeriesChartMarkSpec:
    """One symbolic chart mark in a multiseries scene."""

    category_label: str
    series_label: str
    category_rank: int
    series_rank: int
    value: int
    fill_rgb: ChartColor | None = None
    outline_rgb: ChartColor | None = None


@dataclass(frozen=True)
class HistogramBinSpec:
    """One numeric histogram bin."""

    label: str
    count: int
    interval_start: int
    interval_end: int
    fill_rgb: ChartColor | None = None
    outline_rgb: ChartColor | None = None


@dataclass(frozen=True)
class BoxPlotSpec:
    """One rendered categorical boxplot."""

    label: str
    whisker_min: int
    q1: int
    median: int
    q3: int
    whisker_max: int
    fill_rgb: ChartColor | None = None
    outline_rgb: ChartColor | None = None


@dataclass(frozen=True)
class ViolinPlotSpec:
    """One rendered violin plot summary."""

    label: str
    support_min: int
    support_max: int
    mode_values: Tuple[int, ...]
    fill_rgb: ChartColor | None = None
    outline_rgb: ChartColor | None = None


@dataclass(frozen=True)
class ChartRenderParams:
    """Resolved render parameters for one labeled chart scene."""

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
    label_stroke_width_px: int
    mark_outline_width_px: int
    line_width_px: int
    point_radius_px: int
    bar_width_fraction: float
    axis_color_rgb: ChartColor
    grid_color_rgb: ChartColor
    mark_fill_rgb: ChartColor
    mark_outline_rgb: ChartColor
    text_color_rgb: ChartColor
    text_stroke_rgb: ChartColor
    plot_fill_rgb: ChartColor


@dataclass(frozen=True)
class RenderedChartScene:
    """Rendered chart payload plus trace-ready metadata."""

    image: Image.Image
    mark_traces: Tuple[Dict[str, Any], ...]
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: Tuple[int, int, int, int]
    y_axis_max: int
    y_ticks: Tuple[int, ...]
    scene_variant: str


def _text_bbox(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
) -> Tuple[float, float, float, float]:
    """Return one text bbox centered around `center`."""

    try:
        raw = draw.textbbox((0, 0), str(text), font=font)
        width = float(raw[2] - raw[0])
        height = float(raw[3] - raw[1])
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        width = float(width)
        height = float(height)
    center_x = float(center[0])
    center_y = float(center[1])
    return (
        float(center_x - (0.5 * width)),
        float(center_y - (0.5 * height)),
        float(center_x + (0.5 * width)),
        float(center_y + (0.5 * height)),
    )


def _resolve_plot_bbox(params: ChartRenderParams) -> Tuple[int, int, int, int]:
    """Resolve one axis-aligned plot bbox within the chart canvas."""

    left = int(params.plot_margin_left_px)
    top = int(params.plot_margin_top_px)
    right = int(params.canvas_width) - int(params.plot_margin_right_px)
    bottom = int(params.canvas_height) - int(params.plot_margin_bottom_px)
    if right <= left or bottom <= top:
        raise ValueError("chart plot margins leave no drawable plot area")
    return (int(left), int(top), int(right), int(bottom))


def _tick_y(value: int, *, y_axis_max: int, plot_top: int, plot_bottom: int) -> float:
    """Map one integer chart value to plot-space pixel y coordinate."""

    span = max(1, int(y_axis_max))
    plot_height = float(max(1, int(plot_bottom) - int(plot_top)))
    return float(plot_bottom) - (float(value) / float(span)) * float(plot_height)


def _tick_x(value: int, *, x_axis_max: int, plot_left: int, plot_right: int) -> float:
    """Map one integer chart value to plot-space pixel x coordinate."""

    span = max(1, int(x_axis_max))
    plot_width = float(max(1, int(plot_right) - int(plot_left)))
    return float(plot_left) + (float(value) / float(span)) * float(plot_width)


def _label_center_for_variant(
    *,
    scene_variant: str,
    mark_center: Tuple[float, float],
    bar_bbox: Tuple[float, float, float, float] | None,
    point_radius_px: int,
    label_font_size_px: int,
) -> Tuple[float, float]:
    """Resolve one readable label center for the selected chart type."""

    center_x = float(mark_center[0])
    center_y = float(mark_center[1])
    if str(scene_variant) == "bar":
        if bar_bbox is None:
            raise ValueError("bar chart labels require bar bbox")
        return (
            float(center_x),
            float(bar_bbox[3]) + float(max(16, int(label_font_size_px) + 4)),
        )
    if str(scene_variant) == "horizontal_bar":
        if bar_bbox is None:
            raise ValueError("horizontal_bar labels require bar bbox")
        return (
            float(bar_bbox[0]) - float(max(20, int(label_font_size_px) + 8)),
            float(center_y),
        )
    return (
        float(center_x),
        float(center_y) - float(max(int(point_radius_px) + 14, int(label_font_size_px))),
    )


def _scatter_slot_centers(
    rng,
    *,
    count: int,
    plot_left: int,
    plot_right: int,
) -> Tuple[float, ...]:
    """Return stable per-point scatter x coordinates with bounded jitter."""

    usable_width = float(max(1, int(plot_right) - int(plot_left)))
    slot_width = float(usable_width / max(1, int(count)))
    centers: List[float] = []
    for index in range(int(count)):
        slot_left = float(plot_left) + float(index) * float(slot_width)
        slot_center = float(slot_left) + 0.5 * float(slot_width)
        jitter = float(rng.uniform(-0.18, 0.18)) * float(slot_width)
        centers.append(float(slot_center + jitter))
    return tuple(float(value) for value in centers)


def _slot_centers(*, count: int, plot_left: int, plot_right: int) -> Tuple[float, ...]:
    """Return equally spaced x-slot centers for ordered chart marks."""

    usable_width = float(max(1, int(plot_right) - int(plot_left)))
    slot_width = float(usable_width / max(1, int(count)))
    return tuple(
        float(plot_left) + (float(index) + 0.5) * float(slot_width)
        for index in range(int(count))
    )


def _axis_slot_centers(*, count: int, start_px: int, end_px: int) -> Tuple[float, ...]:
    """Return equally spaced slot centers along one arbitrary axis span."""

    usable_span = float(max(1, int(end_px) - int(start_px)))
    slot_width = float(usable_span / max(1, int(count)))
    return tuple(
        float(start_px) + (float(index) + 0.5) * float(slot_width)
        for index in range(int(count))
    )


def _clamp_text_center_to_canvas(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
    canvas_width: int,
    canvas_height: int,
    margin_px: float = 4.0,
) -> Tuple[float, float]:
    """Clamp one centered text label so its bbox stays inside the image canvas."""

    bbox = _text_bbox(draw, text=str(text), center=center, font=font)
    margin = float(max(0.0, float(margin_px)))
    dx = 0.0
    dy = 0.0
    if float(bbox[0]) < float(margin):
        dx = float(margin) - float(bbox[0])
    elif float(bbox[2]) > float(canvas_width) - float(margin):
        dx = (float(canvas_width) - float(margin)) - float(bbox[2])
    if float(bbox[1]) < float(margin):
        dy = float(margin) - float(bbox[1])
    elif float(bbox[3]) > float(canvas_height) - float(margin):
        dy = (float(canvas_height) - float(margin)) - float(bbox[3])
    return (float(center[0]) + float(dx), float(center[1]) + float(dy))


def _bbox_from_points(points: Sequence[Tuple[float, float]]) -> Tuple[float, float, float, float]:
    """Return the axis-aligned bbox enclosing one point sequence."""

    if not points:
        raise ValueError("bbox requires at least one point")
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return (float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys)))


def _union_bboxes(
    bboxes: Sequence[Tuple[float, float, float, float]],
) -> Tuple[float, float, float, float]:
    """Return one enclosing bbox for a non-empty bbox list."""

    if not bboxes:
        raise ValueError("union requires at least one bbox")
    return _bbox_from_points(
        [
            (float(x0), float(y0))
            for x0, y0, _, _ in bboxes
        ]
        + [
            (float(x1), float(y1))
            for _, _, x1, y1 in bboxes
        ]
    )


def _radar_polygon_points(
    *,
    center_x: float,
    center_y: float,
    radius: float,
    angles_rad: Sequence[float],
) -> List[Tuple[float, float]]:
    """Return polygon vertices for one radar ring or data polygon."""

    return [
        (
            float(center_x + (float(radius) * math.cos(float(angle)))),
            float(center_y + (float(radius) * math.sin(float(angle)))),
        )
        for angle in angles_rad
    ]


def _normalize_color(value: Sequence[int], fallback: ChartColor) -> ChartColor:
    """Normalize RGB-like input into a clamped 3-channel tuple."""

    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return (
            max(0, min(255, int(value[0]))),
            max(0, min(255, int(value[1]))),
            max(0, min(255, int(value[2]))),
        )
    return tuple(int(channel) for channel in fallback)


def resolve_chart_render_params(params: Mapping[str, Any]) -> ChartRenderParams:
    """Resolve one chart render-parameter block from config-like values."""

    return ChartRenderParams(
        canvas_width=int(params["canvas_width"]),
        canvas_height=int(params["canvas_height"]),
        plot_margin_left_px=int(params["plot_margin_left_px"]),
        plot_margin_right_px=int(params["plot_margin_right_px"]),
        plot_margin_top_px=int(params["plot_margin_top_px"]),
        plot_margin_bottom_px=int(params["plot_margin_bottom_px"]),
        axis_line_width_px=int(params["axis_line_width_px"]),
        grid_line_width_px=int(params["grid_line_width_px"]),
        tick_length_px=int(params["tick_length_px"]),
        label_font_size_px=int(params["label_font_size_px"]),
        tick_font_size_px=int(params["tick_font_size_px"]),
        label_stroke_width_px=int(params["label_stroke_width_px"]),
        mark_outline_width_px=int(params["mark_outline_width_px"]),
        line_width_px=int(params["line_width_px"]),
        point_radius_px=int(params["point_radius_px"]),
        bar_width_fraction=float(params["bar_width_fraction"]),
        axis_color_rgb=_normalize_color(params.get("axis_color_rgb", (74, 78, 86)), (74, 78, 86)),
        grid_color_rgb=_normalize_color(params.get("grid_color_rgb", (224, 227, 232)), (224, 227, 232)),
        mark_fill_rgb=_normalize_color(params.get("mark_fill_rgb", (86, 138, 214)), (86, 138, 214)),
        mark_outline_rgb=_normalize_color(params.get("mark_outline_rgb", (50, 76, 116)), (50, 76, 116)),
        text_color_rgb=_normalize_color(params.get("text_color_rgb", (38, 41, 48)), (38, 41, 48)),
        text_stroke_rgb=_normalize_color(params.get("text_stroke_rgb", (255, 255, 255)), (255, 255, 255)),
        plot_fill_rgb=_normalize_color(params.get("plot_fill_rgb", (255, 255, 255)), (255, 255, 255)),
    )


def render_labeled_chart_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    marks: Sequence[ChartMarkSpec],
    render_params: ChartRenderParams,
    instance_seed: int,
) -> RenderedChartScene:
    """Render one labeled chart scene onto `background`."""

    selected_variant = str(scene_variant)
    if selected_variant not in set(SUPPORTED_CHART_SCENE_VARIANTS):
        raise ValueError(f"unsupported chart scene_variant: {selected_variant}")
    if len(marks) < 2:
        raise ValueError("charts require at least two marks")

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    plot_left, plot_top, plot_right, plot_bottom = _resolve_plot_bbox(render_params)
    plot_bbox = (int(plot_left), int(plot_top), int(plot_right), int(plot_bottom))
    draw.rectangle(plot_bbox, fill=render_params.plot_fill_rgb)

    max_value = max(int(mark.value) for mark in marks)
    y_axis_max = max(4, int(max_value) + 1)
    y_ticks = tuple(range(0, int(y_axis_max) + 1))

    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    axis_color = tuple(int(value) for value in render_params.axis_color_rgb)
    grid_color = tuple(int(value) for value in render_params.grid_color_rgb)

    if selected_variant in {"pie", "donut"}:
        plot_width = float(max(1, int(plot_right) - int(plot_left)))
        plot_height = float(max(1, int(plot_bottom) - int(plot_top)))
        legend_width = float(min(max(150.0, plot_width * 0.28), plot_width * 0.38))
        legend_gap = float(max(18.0, float(render_params.label_font_size_px)))
        chart_right = float(plot_right) - float(legend_width) - float(legend_gap)
        chart_width = float(max(140.0, chart_right - float(plot_left)))
        side = float(min(chart_width, plot_height))
        pie_margin = float(max(28.0, int(render_params.label_font_size_px) * 1.8))
        diameter = float(max(140.0, float(side) - float(pie_margin)))
        radius = 0.5 * float(diameter)
        hole_radius = float(radius * 0.42) if selected_variant == "donut" else 0.0
        center_x = float(plot_left) + (0.5 * float(chart_width))
        center_y = 0.5 * float(plot_top + plot_bottom)
        pie_bbox = (
            float(center_x - radius),
            float(center_y - radius),
            float(center_x + radius),
            float(center_y + radius),
        )
        total_value = int(sum(int(mark.value) for mark in marks))
        if int(total_value) <= 0:
            raise ValueError("pie charts require a positive total value")
        mark_traces: List[Dict[str, Any]] = []
        entities: List[Dict[str, Any]] = []
        start_angle = -90.0
        percentage_radius = (
            float(0.5 * (float(radius) + float(hole_radius)))
            if hole_radius > 0.0
            else float(radius) * 0.60
        )
        legend_left = float(chart_right + float(legend_gap))
        legend_top = float(plot_top) + float(max(12.0, 0.5 * (plot_height - (len(marks) * (render_params.label_font_size_px + 10)))))
        legend_row_height = float(max(render_params.label_font_size_px + 10, 34))
        legend_swatch_side = float(max(18, int(round(render_params.label_font_size_px * 0.75))))
        for index, mark in enumerate(marks):
            sweep = 360.0 * (float(int(mark.value)) / float(total_value))
            end_angle = float(start_angle + sweep)
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
            draw.pieslice(
                pie_bbox,
                start=float(start_angle),
                end=float(end_angle),
                fill=fill_rgb,
                outline=outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )
            mid_angle = float(start_angle + (0.5 * sweep))
            theta = math.radians(float(mid_angle))
            mark_center = (
                float(center_x + (percentage_radius * math.cos(theta))),
                float(center_y + (percentage_radius * math.sin(theta))),
            )
            percent_radius = float(percentage_radius)
            if float(abs(sweep)) < 18.0:
                percent_radius = float(radius) + 16.0
            percent_center = (
                float(center_x + (percent_radius * math.cos(theta))),
                float(center_y + (percent_radius * math.sin(theta))),
            )
            percent_text = f"{int(mark.value)}%"
            percent_center = _clamp_text_center_to_canvas(
                draw,
                text=str(percent_text),
                center=percent_center,
                font=label_font,
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
            )
            draw_text_centered(
                draw,
                text=str(percent_text),
                center=percent_center,
                font=label_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=int(render_params.label_stroke_width_px),
            )
            percent_bbox = _text_bbox(draw, text=str(percent_text), center=percent_center, font=label_font)

            legend_row_y = float(legend_top) + float(index) * float(legend_row_height)
            legend_swatch_bbox = (
                float(legend_left),
                float(legend_row_y),
                float(legend_left + legend_swatch_side),
                float(legend_row_y + legend_swatch_side),
            )
            draw.rectangle(
                legend_swatch_bbox,
                fill=fill_rgb,
                outline=outline_rgb,
                width=max(1, int(render_params.mark_outline_width_px)),
            )
            label_center = (
                float(legend_swatch_bbox[2]) + float(max(14, int(render_params.label_font_size_px) * 0.7)),
                float(0.5 * (legend_swatch_bbox[1] + legend_swatch_bbox[3])),
            )
            draw_text_centered(
                draw,
                text=str(mark.label),
                center=label_center,
                font=label_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=int(render_params.label_stroke_width_px),
            )
            label_bbox = _text_bbox(draw, text=str(mark.label), center=label_center, font=label_font)

            step_count = max(2, int(math.ceil(abs(float(sweep)) / 18.0)))
            sector_points: List[Tuple[float, float]] = [(float(center_x), float(center_y))]
            for step in range(int(step_count) + 1):
                angle = float(start_angle + (float(step) / float(step_count)) * float(sweep))
                angle_rad = math.radians(float(angle))
                sector_points.append(
                    (
                        float(center_x + (radius * math.cos(angle_rad))),
                        float(center_y + (radius * math.sin(angle_rad))),
                    )
                )
            mark_bbox = _bbox_from_points(sector_points)
            mark_trace = {
                "entity_id": f"mark_{str(mark.label)}",
                "label": str(mark.label),
                "value": int(mark.value),
                "x_rank": int(index),
                "mark_center_px": [round(float(mark_center[0]), 3), round(float(mark_center[1]), 3)],
                "mark_bbox_px": [round(float(value), 3) for value in mark_bbox],
                "label_center_px": [round(float(label_center[0]), 3), round(float(label_center[1]), 3)],
                "label_bbox_px": [round(float(value), 3) for value in label_bbox],
                "percentage_center_px": [round(float(percent_center[0]), 3), round(float(percent_center[1]), 3)],
                "percentage_bbox_px": [round(float(value), 3) for value in percent_bbox],
                "legend_swatch_bbox_px": [round(float(value), 3) for value in legend_swatch_bbox],
                "mark_fill_rgb": [int(channel) for channel in fill_rgb],
                "mark_outline_rgb": [int(channel) for channel in outline_rgb],
                "start_angle_deg": round(float(start_angle), 3),
                "end_angle_deg": round(float(end_angle), 3),
            }
            mark_traces.append(mark_trace)
            entities.append(
                {
                    "entity_id": str(mark_trace["entity_id"]),
                    "entity_type": "slice",
                    "attrs": {
                        "label": str(mark.label),
                        "value": int(mark.value),
                        "x_rank": int(index),
                        "scene_variant": str(selected_variant),
                        "mark_center_px": list(mark_trace["mark_center_px"]),
                        "mark_bbox_px": list(mark_trace["mark_bbox_px"]),
                        "label_center_px": list(mark_trace["label_center_px"]),
                        "legend_swatch_bbox_px": list(mark_trace["legend_swatch_bbox_px"]),
                        "percentage_center_px": list(mark_trace["percentage_center_px"]),
                        "mark_fill_rgb": list(mark_trace["mark_fill_rgb"]),
                        "mark_outline_rgb": list(mark_trace["mark_outline_rgb"]),
                        "start_angle_deg": float(mark_trace["start_angle_deg"]),
                        "end_angle_deg": float(mark_trace["end_angle_deg"]),
                    },
                }
            )
            start_angle = float(end_angle)

        if hole_radius > 0.0:
            inner_bbox = (
                float(center_x - hole_radius),
                float(center_y - hole_radius),
                float(center_x + hole_radius),
                float(center_y + hole_radius),
            )
            draw.ellipse(
                inner_bbox,
                fill=render_params.plot_fill_rgb,
                outline=render_params.mark_outline_rgb,
                width=max(1, int(render_params.mark_outline_width_px)),
            )

        return RenderedChartScene(
            image=image,
            mark_traces=tuple(dict(item) for item in mark_traces),
            entities=tuple(dict(item) for item in entities),
            plot_bbox_px=tuple(int(value) for value in plot_bbox),
            y_axis_max=int(y_axis_max),
            y_ticks=tuple(int(value) for value in y_ticks),
            scene_variant=str(selected_variant),
        )

    if selected_variant == "radar":
        plot_width = float(max(1, int(plot_right) - int(plot_left)))
        plot_height = float(max(1, int(plot_bottom) - int(plot_top)))
        center_x = 0.5 * float(plot_left + plot_right)
        center_y = 0.5 * float(plot_top + plot_bottom)
        outer_padding = float(max(72.0, float(render_params.label_font_size_px) * 2.2))
        radius = 0.5 * float(min(plot_width, plot_height)) - float(outer_padding)
        radius = float(max(120.0, radius))
        count = len(marks)
        angles_rad = tuple(
            float((-math.pi / 2.0) + (2.0 * math.pi * float(index) / float(count)))
            for index in range(int(count))
        )

        radar_ring_ticks = sorted(
            {
                int(max(1, int(round(float(y_axis_max) * ratio))))
                for ratio in (1.0 / 3.0, 2.0 / 3.0, 1.0)
            }
        )

        for ring_value in radar_ring_ticks:
            ring_radius = float(radius) * (float(ring_value) / float(max(1, int(y_axis_max))))
            ring_points = _radar_polygon_points(
                center_x=float(center_x),
                center_y=float(center_y),
                radius=float(ring_radius),
                angles_rad=angles_rad,
            )
            draw.polygon(
                ring_points,
                outline=grid_color,
                width=max(1, int(render_params.grid_line_width_px)),
            )
            tick_center = (
                float(center_x),
                float(center_y - float(ring_radius)),
            )
            tick_center = _clamp_text_center_to_canvas(
                draw,
                text=str(ring_value),
                center=(float(tick_center[0]), float(tick_center[1]) - 12.0),
                font=tick_font,
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
            )
            draw_text_centered(
                draw,
                text=str(ring_value),
                center=tick_center,
                font=tick_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=max(1, int(round(0.06 * float(render_params.tick_font_size_px)))),
            )

        for angle in angles_rad:
            spoke_end = (
                float(center_x + (float(radius) * math.cos(float(angle)))),
                float(center_y + (float(radius) * math.sin(float(angle)))),
            )
            draw.line(
                [(float(center_x), float(center_y)), (float(spoke_end[0]), float(spoke_end[1]))],
                fill=grid_color,
                width=max(1, int(render_params.grid_line_width_px)),
            )

        polygon_points: List[Tuple[float, float]] = []
        mark_traces: List[Dict[str, Any]] = []
        entities: List[Dict[str, Any]] = []
        for index, (mark, angle) in enumerate(zip(marks, angles_rad)):
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
            radial_fraction = float(int(mark.value)) / float(max(1, int(y_axis_max)))
            point_radius = float(radius) * float(radial_fraction)
            x_center = float(center_x + (float(point_radius) * math.cos(float(angle))))
            y_center = float(center_y + (float(point_radius) * math.sin(float(angle))))
            polygon_points.append((float(x_center), float(y_center)))

            point_marker_radius = float(render_params.point_radius_px)
            ellipse_box = (
                float(x_center - point_marker_radius),
                float(y_center - point_marker_radius),
                float(x_center + point_marker_radius),
                float(y_center + point_marker_radius),
            )
            draw.ellipse(
                ellipse_box,
                fill=fill_rgb,
                outline=outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )

            value_center = (
                float(center_x + (max(18.0, float(point_radius) - 18.0) * math.cos(float(angle)))),
                float(center_y + (max(18.0, float(point_radius) - 18.0) * math.sin(float(angle)))),
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

            label_radius = float(radius) + float(max(28, int(render_params.label_font_size_px) + 8))
            label_center = (
                float(center_x + (float(label_radius) * math.cos(float(angle)))),
                float(center_y + (float(label_radius) * math.sin(float(angle)))),
            )
            label_center = _clamp_text_center_to_canvas(
                draw,
                text=str(mark.label),
                center=label_center,
                font=label_font,
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
            )
            draw_text_centered(
                draw,
                text=str(mark.label),
                center=label_center,
                font=label_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=int(render_params.label_stroke_width_px),
            )
            label_bbox = _text_bbox(draw, text=str(mark.label), center=label_center, font=label_font)

            mark_bbox = [float(value) for value in ellipse_box]
            mark_trace = {
                "entity_id": f"mark_{str(mark.label)}",
                "label": str(mark.label),
                "value": int(mark.value),
                "x_rank": int(index),
                "mark_center_px": [round(float(x_center), 3), round(float(y_center), 3)],
                "mark_bbox_px": [round(float(value), 3) for value in mark_bbox],
                "label_center_px": [round(float(label_center[0]), 3), round(float(label_center[1]), 3)],
                "label_bbox_px": [round(float(value), 3) for value in label_bbox],
                "value_center_px": [round(float(value_center[0]), 3), round(float(value_center[1]), 3)],
                "value_bbox_px": [round(float(value), 3) for value in value_bbox],
                "mark_fill_rgb": [int(channel) for channel in fill_rgb],
                "mark_outline_rgb": [int(channel) for channel in outline_rgb],
            }
            mark_traces.append(mark_trace)
            entities.append(
                {
                    "entity_id": str(mark_trace["entity_id"]),
                    "entity_type": "point",
                    "attrs": {
                        "label": str(mark.label),
                        "value": int(mark.value),
                        "x_rank": int(index),
                        "scene_variant": str(selected_variant),
                        "mark_center_px": list(mark_trace["mark_center_px"]),
                        "mark_bbox_px": list(mark_trace["mark_bbox_px"]),
                        "label_center_px": list(mark_trace["label_center_px"]),
                        "value_center_px": list(mark_trace["value_center_px"]),
                        "mark_fill_rgb": list(mark_trace["mark_fill_rgb"]),
                        "mark_outline_rgb": list(mark_trace["mark_outline_rgb"]),
                    },
                }
            )

        if len(polygon_points) >= 2:
            draw.line(
                [*polygon_points, polygon_points[0]],
                fill=tuple(int(value) for value in render_params.mark_outline_rgb),
                width=max(1, int(render_params.line_width_px) - 1),
            )

        return RenderedChartScene(
            image=image,
            mark_traces=tuple(dict(item) for item in mark_traces),
            entities=tuple(dict(item) for item in entities),
            plot_bbox_px=tuple(int(value) for value in plot_bbox),
            y_axis_max=int(y_axis_max),
            y_ticks=tuple(int(value) for value in y_ticks),
            scene_variant=str(selected_variant),
        )

    if selected_variant == "horizontal_bar":
        for tick_value in y_ticks:
            x_px = _tick_x(
                int(tick_value),
                x_axis_max=int(y_axis_max),
                plot_left=int(plot_left),
                plot_right=int(plot_right),
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
            tick_center = (
                float(x_px),
                float(plot_bottom) + float(render_params.tick_length_px) + 18.0,
            )
            draw_text_centered(
                draw,
                text=str(tick_value),
                center=tick_center,
                font=tick_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=max(1, int(round(0.06 * float(render_params.tick_font_size_px)))),
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
                [(float(plot_left), float(y_px)), (float(plot_right), float(y_px))],
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
            tick_center = (
                float(plot_left) - float(render_params.tick_length_px) - 18.0,
                float(y_px),
            )
            draw_text_centered(
                draw,
                text=str(tick_value),
                center=tick_center,
                font=tick_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=max(1, int(round(0.06 * float(render_params.tick_font_size_px)))),
            )

    draw.line(
        [(float(plot_left), float(plot_top)), (float(plot_left), float(plot_bottom))],
        fill=axis_color,
        width=int(render_params.axis_line_width_px),
    )
    draw.line(
        [(float(plot_left), float(plot_bottom)), (float(plot_right), float(plot_bottom))],
        fill=axis_color,
        width=int(render_params.axis_line_width_px),
    )

    base_centers = _slot_centers(count=len(marks), plot_left=int(plot_left), plot_right=int(plot_right))
    if selected_variant == "scatter":
        scatter_rng = spawn_rng(int(instance_seed), f"charts.scatter_slots.{selected_variant}")
        x_centers = _scatter_slot_centers(
            scatter_rng,
            count=len(marks),
            plot_left=int(plot_left),
            plot_right=int(plot_right),
        )
    else:
        x_centers = base_centers
    y_slot_centers = _axis_slot_centers(count=len(marks), start_px=int(plot_top), end_px=int(plot_bottom))

    line_points: List[Tuple[float, float]] = []
    mark_traces: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    slot_width = float(max(1.0, (float(plot_right) - float(plot_left)) / max(1, len(marks))))
    bar_width = float(max(12.0, float(render_params.bar_width_fraction) * float(slot_width)))
    slot_height = float(max(1.0, (float(plot_bottom) - float(plot_top)) / max(1, len(marks))))
    horizontal_bar_height = float(max(12.0, float(render_params.bar_width_fraction) * float(slot_height)))

    for index, mark in enumerate(marks):
        bar_bbox: Tuple[float, float, float, float] | None = None
        if selected_variant == "horizontal_bar":
            y_center = float(y_slot_centers[index])
            x_extent = _tick_x(
                int(mark.value),
                x_axis_max=int(y_axis_max),
                plot_left=int(plot_left),
                plot_right=int(plot_right),
            )
            x_center = float(plot_left) + 0.5 * float(x_extent - float(plot_left))
            top = float(y_center - 0.5 * float(horizontal_bar_height))
            bottom = float(y_center + 0.5 * float(horizontal_bar_height))
            bar_bbox = (float(plot_left), float(top), float(x_extent), float(bottom))
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
            draw.rectangle(
                bar_bbox,
                fill=fill_rgb,
                outline=outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )
        else:
            x_center = float(x_centers[index])
            y_center = _tick_y(
                int(mark.value),
                y_axis_max=int(y_axis_max),
                plot_top=int(plot_top),
                plot_bottom=int(plot_bottom),
            )
            line_points.append((float(x_center), float(y_center)))

        if selected_variant == "bar":
            resolved_bar_width = float(bar_width)
            left = float(x_center - 0.5 * float(bar_width))
            right = float(x_center + 0.5 * float(bar_width))
            left = float(x_center - 0.5 * float(resolved_bar_width))
            right = float(x_center + 0.5 * float(resolved_bar_width))
            bar_bbox = (float(left), float(y_center), float(right), float(plot_bottom))
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
            draw.rectangle(
                bar_bbox,
                fill=fill_rgb,
                outline=outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )
        elif selected_variant == "lollipop":
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
            draw.line(
                [(float(x_center), float(plot_bottom)), (float(x_center), float(y_center))],
                fill=outline_rgb,
                width=max(1, int(render_params.line_width_px) - 1),
            )
            radius = float(render_params.point_radius_px)
            ellipse_box = (
                float(x_center - radius),
                float(y_center - radius),
                float(x_center + radius),
                float(y_center + radius),
            )
            draw.ellipse(
                ellipse_box,
                fill=fill_rgb,
                outline=outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )
        elif selected_variant in {"scatter", "dot_plot"}:
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
            radius = float(render_params.point_radius_px)
            ellipse_box = (
                float(x_center - radius),
                float(y_center - radius),
                float(x_center + radius),
                float(y_center + radius),
            )
            draw.ellipse(
                ellipse_box,
                fill=fill_rgb,
                outline=outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )

        label_center = _label_center_for_variant(
            scene_variant=selected_variant,
            mark_center=(float(x_center), float(y_center)),
            bar_bbox=bar_bbox,
            point_radius_px=int(render_params.point_radius_px),
            label_font_size_px=int(render_params.label_font_size_px),
        )
        draw_text_centered(
            draw,
            text=str(mark.label),
            center=label_center,
            font=label_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=int(render_params.label_stroke_width_px),
        )

        label_bbox = _text_bbox(draw, text=str(mark.label), center=label_center, font=label_font)
        mark_bbox = (
            list(bar_bbox)
            if bar_bbox is not None
            else [
                float(x_center - float(render_params.point_radius_px)),
                float(y_center - float(render_params.point_radius_px)),
                float(x_center + float(render_params.point_radius_px)),
                float(y_center + float(render_params.point_radius_px)),
            ]
        )
        mark_trace = {
            "entity_id": f"mark_{str(mark.label)}",
            "label": str(mark.label),
            "value": int(mark.value),
            "x_rank": int(index),
            "mark_center_px": [round(float(x_center), 3), round(float(y_center), 3)],
            "mark_bbox_px": [round(float(value), 3) for value in mark_bbox],
            "label_center_px": [round(float(label_center[0]), 3), round(float(label_center[1]), 3)],
            "label_bbox_px": [round(float(value), 3) for value in label_bbox],
            "mark_fill_rgb": [
                int(channel)
                for channel in (
                    tuple(int(channel) for channel in mark.fill_rgb)
                    if isinstance(mark.fill_rgb, tuple)
                    else tuple(int(value) for value in render_params.mark_fill_rgb)
                )
            ],
            "mark_outline_rgb": [
                int(channel)
                for channel in (
                    tuple(int(channel) for channel in mark.outline_rgb)
                    if isinstance(mark.outline_rgb, tuple)
                    else tuple(int(value) for value in render_params.mark_outline_rgb)
                )
            ],
        }
        mark_traces.append(mark_trace)
        entities.append(
            {
                "entity_id": str(mark_trace["entity_id"]),
                "entity_type": "bar" if selected_variant in {"bar", "horizontal_bar"} else "point",
                "attrs": {
                    "label": str(mark.label),
                    "value": int(mark.value),
                    "x_rank": int(index),
                    "scene_variant": str(selected_variant),
                    "mark_center_px": list(mark_trace["mark_center_px"]),
                    "mark_bbox_px": list(mark_trace["mark_bbox_px"]),
                    "label_center_px": list(mark_trace["label_center_px"]),
                    "mark_fill_rgb": list(mark_trace["mark_fill_rgb"]),
                    "mark_outline_rgb": list(mark_trace["mark_outline_rgb"]),
                },
            }
        )

    if selected_variant == "area":
        polygon_points = list(line_points)
        polygon_points.extend(
            [
                (float(line_points[-1][0]), float(plot_bottom)),
                (float(line_points[0][0]), float(plot_bottom)),
            ]
        )
        draw.polygon(
            polygon_points,
            fill=render_params.mark_fill_rgb,
            outline=None,
        )
        draw.line(
            line_points,
            fill=render_params.mark_outline_rgb,
            width=int(render_params.line_width_px),
            joint="curve",
        )
        for trace in mark_traces:
            center_x, center_y = trace["mark_center_px"]
            radius = float(render_params.point_radius_px)
            ellipse_box = (
                float(center_x - radius),
                float(center_y - radius),
                float(center_x + radius),
                float(center_y + radius),
            )
            draw.ellipse(
                ellipse_box,
                fill=render_params.mark_fill_rgb,
                outline=render_params.mark_outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )
            draw_text_centered(
                draw,
                text=str(trace["label"]),
                center=(float(trace["label_center_px"][0]), float(trace["label_center_px"][1])),
                font=label_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=int(render_params.label_stroke_width_px),
            )

    if selected_variant == "line":
        draw.line(
            line_points,
            fill=render_params.mark_outline_rgb,
            width=int(render_params.line_width_px),
            joint="curve",
        )
        for trace in mark_traces:
            center_x, center_y = trace["mark_center_px"]
            radius = float(render_params.point_radius_px)
            ellipse_box = (
                float(center_x - radius),
                float(center_y - radius),
                float(center_x + radius),
                float(center_y + radius),
            )
            draw.ellipse(
                ellipse_box,
                fill=render_params.mark_fill_rgb,
                outline=render_params.mark_outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )

    return RenderedChartScene(
        image=image,
        mark_traces=tuple(dict(item) for item in mark_traces),
        entities=tuple(dict(item) for item in entities),
        plot_bbox_px=tuple(int(value) for value in plot_bbox),
        y_axis_max=int(y_axis_max),
        y_ticks=tuple(int(value) for value in y_ticks),
        scene_variant=str(selected_variant),
    )


def render_multiseries_chart_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    marks: Sequence[MultiSeriesChartMarkSpec],
    render_params: ChartRenderParams,
    instance_seed: int,
) -> RenderedChartScene:
    """Render one multiseries chart scene onto `background`."""

    del instance_seed
    selected_variant = str(scene_variant)
    if selected_variant not in set(SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS):
        raise ValueError(f"unsupported multiseries chart scene_variant: {selected_variant}")
    if len(marks) < 4:
        raise ValueError("multiseries charts require at least four marks")

    category_specs: Dict[int, str] = {}
    series_specs: Dict[int, str] = {}
    marks_by_key: Dict[Tuple[int, int], MultiSeriesChartMarkSpec] = {}
    for mark in marks:
        category_specs[int(mark.category_rank)] = str(mark.category_label)
        series_specs[int(mark.series_rank)] = str(mark.series_label)
        key = (int(mark.category_rank), int(mark.series_rank))
        if key in marks_by_key:
            raise ValueError("duplicate multiseries mark for category/series pair")
        marks_by_key[key] = mark
    category_ranks = sorted(category_specs.keys())
    series_ranks = sorted(series_specs.keys())
    if not category_ranks or not series_ranks:
        raise ValueError("multiseries charts require at least one category and one series")
    expected_keys = {
        (int(category_rank), int(series_rank))
        for category_rank in category_ranks
        for series_rank in series_ranks
    }
    if set(marks_by_key.keys()) != expected_keys:
        raise ValueError("multiseries charts require one mark per category/series pair")

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

    max_value = max(int(mark.value) for mark in marks)
    y_axis_max = max(4, int(max_value) + 1)
    y_ticks = tuple(range(0, int(y_axis_max) + 1))

    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    axis_color = tuple(int(value) for value in render_params.axis_color_rgb)
    grid_color = tuple(int(value) for value in render_params.grid_color_rgb)

    if selected_variant == "grouped_horizontal_bar":
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
            tick_center = (
                float(x_px),
                float(plot_bottom) + float(render_params.tick_length_px) + 18.0,
            )
            draw_text_centered(
                draw,
                text=str(tick_value),
                center=tick_center,
                font=tick_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=max(1, int(round(0.06 * float(render_params.tick_font_size_px)))),
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
            tick_center = (
                float(plot_left) - float(render_params.tick_length_px) - 18.0,
                float(y_px),
            )
            draw_text_centered(
                draw,
                text=str(tick_value),
                center=tick_center,
                font=tick_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=max(1, int(round(0.06 * float(render_params.tick_font_size_px)))),
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

    if selected_variant == "grouped_horizontal_bar":
        category_centers = _axis_slot_centers(
            count=len(categories),
            start_px=int(plot_top),
            end_px=int(plot_bottom),
        )
        slot_height = float(max(1.0, (float(plot_bottom) - float(plot_top)) / max(1, len(categories))))
        group_inner_height = float(slot_height * _MULTISERIES_GROUP_WIDTH_FRACTION)
        subgroup_height = float(group_inner_height / max(1, len(series_list)))
        bar_height = float(max(8.0, float(render_params.bar_width_fraction) * float(subgroup_height)))
    else:
        category_centers = _slot_centers(
            count=len(categories),
            plot_left=int(plot_left),
            plot_right=int(chart_right),
        )
        slot_width = float(max(1.0, (float(chart_right) - float(plot_left)) / max(1, len(categories))))
        # Leave more whitespace between adjacent category groups so dense
        # multiseries charts remain readable at the upper category-count range.
        group_inner_width = float(slot_width * _MULTISERIES_GROUP_WIDTH_FRACTION)
        subgroup_width = float(group_inner_width / max(1, len(series_list)))
        bar_width = float(max(8.0, float(render_params.bar_width_fraction) * float(subgroup_width)))

    category_label_meta: Dict[str, Dict[str, List[float]]] = {}
    for category_rank, category_label in categories:
        if selected_variant == "grouped_horizontal_bar":
            category_center_y = float(category_centers[int(category_rank)])
            label_center = (
                float(plot_left) - float(max(20, int(render_params.label_font_size_px) + 8)),
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
    series_points: Dict[str, List[Tuple[int, Tuple[float, float]]]] = {
        str(series_label): []
        for _, series_label in series_list
    }
    mark_bboxes_by_category: Dict[str, List[Tuple[float, float, float, float]]] = {
        str(category_label): []
        for _, category_label in categories
    }

    for category_rank, category_label in categories:
        if selected_variant == "grouped_horizontal_bar":
            category_center_y = float(category_centers[int(category_rank)])
            group_top = float(category_center_y) - 0.5 * float(group_inner_height)
        else:
            category_center_x = float(category_centers[int(category_rank)])
            group_left = float(category_center_x) - 0.5 * float(group_inner_width)
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
            if selected_variant == "multi_line":
                x_center = float(category_center_x)
                y_center = _tick_y(
                    int(mark.value),
                    y_axis_max=int(y_axis_max),
                    plot_top=int(plot_top),
                    plot_bottom=int(plot_bottom),
                )
            elif selected_variant == "grouped_horizontal_bar":
                y_center = float(group_top) + (float(series_rank) + 0.5) * float(subgroup_height)
                x_extent = _tick_x(
                    int(mark.value),
                    x_axis_max=int(y_axis_max),
                    plot_left=int(plot_left),
                    plot_right=int(chart_right),
                )
                x_center = float(plot_left) + 0.5 * float(x_extent - float(plot_left))
            else:
                x_center = float(group_left) + (float(series_rank) + 0.5) * float(subgroup_width)
                y_center = _tick_y(
                    int(mark.value),
                    y_axis_max=int(y_axis_max),
                    plot_top=int(plot_top),
                    plot_bottom=int(plot_bottom),
                )

            if selected_variant == "grouped_bar":
                mark_bbox = (
                    float(x_center - 0.5 * float(bar_width)),
                    float(y_center),
                    float(x_center + 0.5 * float(bar_width)),
                    float(plot_bottom),
                )
            elif selected_variant == "grouped_horizontal_bar":
                mark_bbox = (
                    float(plot_left),
                    float(y_center - 0.5 * float(bar_height)),
                    float(x_extent),
                    float(y_center + 0.5 * float(bar_height)),
                )
            else:
                point_radius = float(render_params.point_radius_px)
                mark_bbox = (
                    float(x_center - point_radius),
                    float(y_center - point_radius),
                    float(x_center + point_radius),
                    float(y_center + point_radius),
                )
            mark_bboxes_by_category[str(category_label)].append(tuple(float(value) for value in mark_bbox))
            series_points[str(series_label)].append((int(category_rank), (float(x_center), float(y_center))))
            mark_records.append(
                {
                    "category_label": str(category_label),
                    "series_label": str(series_label),
                    "category_rank": int(category_rank),
                    "series_rank": int(series_rank),
                    "value": int(mark.value),
                    "fill_rgb": [int(channel) for channel in fill_rgb],
                    "outline_rgb": [int(channel) for channel in outline_rgb],
                    "mark_center_px": [round(float(x_center), 3), round(float(y_center), 3)],
                    "mark_bbox_px": [round(float(value), 3) for value in mark_bbox],
                }
            )

    if selected_variant == "multi_line":
        for _, series_label in series_list:
            records = sorted(series_points[str(series_label)], key=lambda item: int(item[0]))
            points = [tuple(float(value) for value in point) for _, point in records]
            sample_record = next(record for record in mark_records if str(record["series_label"]) == str(series_label))
            draw.line(
                points,
                fill=tuple(int(channel) for channel in sample_record["outline_rgb"]),
                width=int(render_params.line_width_px),
                joint="curve",
            )

    for record in mark_records:
        fill_rgb = tuple(int(channel) for channel in record["fill_rgb"])
        outline_rgb = tuple(int(channel) for channel in record["outline_rgb"])
        x_center, y_center = record["mark_center_px"]
        if selected_variant in {"grouped_bar", "grouped_horizontal_bar"}:
            draw.rectangle(
                record["mark_bbox_px"],
                fill=fill_rgb,
                outline=outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )
        elif selected_variant == "grouped_lollipop":
            draw.line(
                [(float(x_center), float(plot_bottom)), (float(x_center), float(y_center))],
                fill=outline_rgb,
                width=max(1, int(render_params.line_width_px) - 1),
            )
            draw.ellipse(
                record["mark_bbox_px"],
                fill=fill_rgb,
                outline=outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )
        else:
            draw.ellipse(
                record["mark_bbox_px"],
                fill=fill_rgb,
                outline=outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )

    legend_left = float(chart_right) + float(legend_gap)
    legend_top = float(plot_top) + 16.0
    legend_row_height = float(max(render_params.label_font_size_px + 12, 36))
    legend_swatch_side = float(max(18, int(round(render_params.label_font_size_px * 0.75))))
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
        if selected_variant == "multi_line":
            center_y = 0.5 * float(swatch_bbox[1] + swatch_bbox[3])
            draw.line(
                [(float(swatch_bbox[0]), float(center_y)), (float(swatch_bbox[2]), float(center_y))],
                fill=outline_rgb,
                width=max(1, int(render_params.line_width_px) - 1),
            )
            point_radius = float(max(4, int(round(0.6 * float(render_params.point_radius_px)))))
            draw.ellipse(
                [
                    float(0.5 * (swatch_bbox[0] + swatch_bbox[2]) - point_radius),
                    float(center_y - point_radius),
                    float(0.5 * (swatch_bbox[0] + swatch_bbox[2]) + point_radius),
                    float(center_y + point_radius),
                ],
                fill=fill_rgb,
                outline=outline_rgb,
                width=max(1, int(render_params.mark_outline_width_px)),
            )
        else:
            draw.rectangle(
                swatch_bbox,
                fill=fill_rgb,
                outline=outline_rgb,
                width=max(1, int(render_params.mark_outline_width_px)),
            )
        label_center = (
            float(swatch_bbox[2]) + float(max(14, int(render_params.label_font_size_px) * 0.7)),
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
        mark_trace = {
            "entity_id": f"mark_{category_label}_{str(record['series_label'])}",
            "category_label": str(category_label),
            "series_label": str(record["series_label"]),
            "category_rank": int(record["category_rank"]),
            "series_rank": int(record["series_rank"]),
            "value": int(record["value"]),
            "mark_center_px": list(record["mark_center_px"]),
            "mark_bbox_px": list(record["mark_bbox_px"]),
            "category_label_center_px": list(category_center),
            "category_label_bbox_px": list(category_bbox),
            "category_group_bbox_px": list(category_group_bbox),
            "mark_fill_rgb": list(record["fill_rgb"]),
            "mark_outline_rgb": list(record["outline_rgb"]),
        }
        mark_traces.append(mark_trace)
        entities.append(
            {
                "entity_id": str(mark_trace["entity_id"]),
                "entity_type": "bar" if selected_variant in {"grouped_bar", "grouped_horizontal_bar"} else "point",
                "attrs": {
                    "category_label": str(category_label),
                    "series_label": str(record["series_label"]),
                    "category_rank": int(record["category_rank"]),
                    "series_rank": int(record["series_rank"]),
                    "value": int(record["value"]),
                    "scene_variant": str(selected_variant),
                    "mark_center_px": list(mark_trace["mark_center_px"]),
                    "mark_bbox_px": list(mark_trace["mark_bbox_px"]),
                    "category_label_center_px": list(mark_trace["category_label_center_px"]),
                    "category_group_bbox_px": list(mark_trace["category_group_bbox_px"]),
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
    y_ticks = tuple(range(0, int(y_axis_max) + 1))

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
            draw_text_centered(
                draw,
                text=str(tick_value),
                center=(float(x_px), float(plot_bottom) + float(render_params.tick_length_px) + 18.0),
                font=tick_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=max(1, int(round(0.06 * float(render_params.tick_font_size_px)))),
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
            draw_text_centered(
                draw,
                text=str(tick_value),
                center=(float(plot_left) - float(render_params.tick_length_px) - 18.0, float(y_px)),
                font=tick_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=max(1, int(round(0.06 * float(render_params.tick_font_size_px)))),
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
    legend_row_height = float(max(render_params.label_font_size_px + 12, 36))
    legend_swatch_side = float(max(18, int(round(render_params.label_font_size_px * 0.75))))
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
        draw.rectangle(
            swatch_bbox,
            fill=fill_rgb,
            outline=outline_rgb,
            width=max(1, int(render_params.mark_outline_width_px)),
        )
        label_center = (
            float(swatch_bbox[2]) + float(max(14, int(render_params.label_font_size_px) * 0.7)),
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


def render_histogram_scene(
    background: Image.Image,
    *,
    bins: Sequence[HistogramBinSpec],
    render_params: ChartRenderParams,
) -> RenderedChartScene:
    """Render one contiguous-bin histogram scene."""

    if len(bins) < 2:
        raise ValueError("histograms require at least two bins")

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    plot_left, plot_top, plot_right, plot_bottom = _resolve_plot_bbox(render_params)
    plot_bbox = (int(plot_left), int(plot_top), int(plot_right), int(plot_bottom))
    draw.rectangle(plot_bbox, fill=render_params.plot_fill_rgb)

    max_count = max(int(bin_spec.count) for bin_spec in bins)
    y_axis_max = max(4, int(max_count) + 1)
    y_ticks = tuple(range(0, int(y_axis_max) + 1))
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    axis_color = tuple(int(value) for value in render_params.axis_color_rgb)
    grid_color = tuple(int(value) for value in render_params.grid_color_rgb)

    for tick_value in y_ticks:
        y_px = _tick_y(
            int(tick_value),
            y_axis_max=int(y_axis_max),
            plot_top=int(plot_top),
            plot_bottom=int(plot_bottom),
        )
        draw.line(
            [(float(plot_left), float(y_px)), (float(plot_right), float(y_px))],
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
        draw_text_centered(
            draw,
            text=str(tick_value),
            center=(
                float(plot_left) - float(render_params.tick_length_px) - 18.0,
                float(y_px),
            ),
            font=tick_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=max(1, int(round(0.06 * float(render_params.tick_font_size_px)))),
        )

    draw.line(
        [(float(plot_left), float(plot_top)), (float(plot_left), float(plot_bottom))],
        fill=axis_color,
        width=int(render_params.axis_line_width_px),
    )
    draw.line(
        [(float(plot_left), float(plot_bottom)), (float(plot_right), float(plot_bottom))],
        fill=axis_color,
        width=int(render_params.axis_line_width_px),
    )

    plot_width = float(max(1, int(plot_right) - int(plot_left)))
    slot_width = float(plot_width / max(1, len(bins)))
    mark_traces: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    for index, bin_spec in enumerate(bins):
        left = float(plot_left) + float(index) * float(slot_width)
        right = float(plot_left) + float(index + 1) * float(slot_width)
        top = _tick_y(
            int(bin_spec.count),
            y_axis_max=int(y_axis_max),
            plot_top=int(plot_top),
            plot_bottom=int(plot_bottom),
        )
        bar_bbox = (float(left), float(top), float(right), float(plot_bottom))
        fill_rgb = (
            tuple(int(channel) for channel in bin_spec.fill_rgb)
            if isinstance(bin_spec.fill_rgb, tuple)
            else tuple(int(value) for value in render_params.mark_fill_rgb)
        )
        outline_rgb = (
            tuple(int(channel) for channel in bin_spec.outline_rgb)
            if isinstance(bin_spec.outline_rgb, tuple)
            else tuple(int(value) for value in render_params.mark_outline_rgb)
        )
        draw.rectangle(
            bar_bbox,
            fill=fill_rgb,
            outline=outline_rgb,
            width=int(render_params.mark_outline_width_px),
        )
        x_center = 0.5 * float(left + right)
        label_center = (
            float(x_center),
            float(plot_bottom) + float(max(18, int(render_params.label_font_size_px) + 6)),
        )
        draw_text_centered(
            draw,
            text=str(bin_spec.label),
            center=label_center,
            font=tick_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=max(1, int(round(0.06 * float(render_params.tick_font_size_px)))),
        )
        label_bbox = _text_bbox(draw, text=str(bin_spec.label), center=label_center, font=tick_font)
        mark_center = (float(x_center), float(0.5 * (float(top) + float(plot_bottom))))
        mark_trace = {
            "entity_id": f"bin_{index}",
            "label": str(bin_spec.label),
            "value": int(bin_spec.count),
            "x_rank": int(index),
            "interval_start": int(bin_spec.interval_start),
            "interval_end": int(bin_spec.interval_end),
            "mark_center_px": [round(float(mark_center[0]), 3), round(float(mark_center[1]), 3)],
            "mark_bbox_px": [round(float(value), 3) for value in bar_bbox],
            "label_center_px": [round(float(label_center[0]), 3), round(float(label_center[1]), 3)],
            "label_bbox_px": [round(float(value), 3) for value in label_bbox],
            "mark_fill_rgb": [int(channel) for channel in fill_rgb],
            "mark_outline_rgb": [int(channel) for channel in outline_rgb],
        }
        mark_traces.append(mark_trace)
        entities.append(
            {
                "entity_id": str(mark_trace["entity_id"]),
                "entity_type": "bin",
                "attrs": {
                    "label": str(bin_spec.label),
                    "count": int(bin_spec.count),
                    "x_rank": int(index),
                    "interval_start": int(bin_spec.interval_start),
                    "interval_end": int(bin_spec.interval_end),
                    "scene_variant": "histogram",
                    "mark_center_px": list(mark_trace["mark_center_px"]),
                    "mark_bbox_px": list(mark_trace["mark_bbox_px"]),
                    "label_center_px": list(mark_trace["label_center_px"]),
                    "mark_fill_rgb": list(mark_trace["mark_fill_rgb"]),
                    "mark_outline_rgb": list(mark_trace["mark_outline_rgb"]),
                },
            }
        )

    return RenderedChartScene(
        image=image,
        mark_traces=tuple(dict(item) for item in mark_traces),
        entities=tuple(dict(item) for item in entities),
        plot_bbox_px=tuple(int(value) for value in plot_bbox),
        y_axis_max=int(y_axis_max),
        y_ticks=tuple(int(value) for value in y_ticks),
        scene_variant="histogram",
    )


def render_boxplot_scene(
    background: Image.Image,
    *,
    boxplots: Sequence[BoxPlotSpec],
    render_params: ChartRenderParams,
) -> RenderedChartScene:
    """Render one categorical boxplot scene."""

    if len(boxplots) < 2:
        raise ValueError("boxplot scenes require at least two categories")

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    plot_left, plot_top, plot_right, plot_bottom = _resolve_plot_bbox(render_params)
    plot_bbox = (int(plot_left), int(plot_top), int(plot_right), int(plot_bottom))
    draw.rectangle(plot_bbox, fill=render_params.plot_fill_rgb)

    max_value = max(int(spec.whisker_max) for spec in boxplots)
    y_axis_max = max(4, int(max_value) + 1)
    y_ticks = tuple(range(0, int(y_axis_max) + 1))
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    axis_color = tuple(int(value) for value in render_params.axis_color_rgb)
    grid_color = tuple(int(value) for value in render_params.grid_color_rgb)

    for tick_value in y_ticks:
        y_px = _tick_y(
            int(tick_value),
            y_axis_max=int(y_axis_max),
            plot_top=int(plot_top),
            plot_bottom=int(plot_bottom),
        )
        draw.line(
            [(float(plot_left), float(y_px)), (float(plot_right), float(y_px))],
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
        draw_text_centered(
            draw,
            text=str(tick_value),
            center=(
                float(plot_left) - float(render_params.tick_length_px) - 18.0,
                float(y_px),
            ),
            font=tick_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=max(1, int(round(0.06 * float(render_params.tick_font_size_px)))),
        )

    draw.line(
        [(float(plot_left), float(plot_top)), (float(plot_left), float(plot_bottom))],
        fill=axis_color,
        width=int(render_params.axis_line_width_px),
    )
    draw.line(
        [(float(plot_left), float(plot_bottom)), (float(plot_right), float(plot_bottom))],
        fill=axis_color,
        width=int(render_params.axis_line_width_px),
    )

    centers = _slot_centers(count=len(boxplots), plot_left=int(plot_left), plot_right=int(plot_right))
    slot_width = float(max(1.0, (float(plot_right) - float(plot_left)) / max(1, len(boxplots))))
    box_width = float(max(18.0, float(render_params.bar_width_fraction) * float(slot_width)))
    whisker_cap = float(max(14.0, 0.55 * float(box_width)))

    mark_traces: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    for index, spec in enumerate(boxplots):
        x_center = float(centers[index])
        y_whisker_min = _tick_y(int(spec.whisker_min), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))
        y_q1 = _tick_y(int(spec.q1), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))
        y_median = _tick_y(int(spec.median), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))
        y_q3 = _tick_y(int(spec.q3), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))
        y_whisker_max = _tick_y(int(spec.whisker_max), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))

        fill_rgb = (
            tuple(int(channel) for channel in spec.fill_rgb)
            if isinstance(spec.fill_rgb, tuple)
            else tuple(int(value) for value in render_params.mark_fill_rgb)
        )
        outline_rgb = (
            tuple(int(channel) for channel in spec.outline_rgb)
            if isinstance(spec.outline_rgb, tuple)
            else tuple(int(value) for value in render_params.mark_outline_rgb)
        )

        draw.line(
            [(float(x_center), float(y_whisker_max)), (float(x_center), float(y_whisker_min))],
            fill=outline_rgb,
            width=max(1, int(render_params.line_width_px) - 1),
        )
        draw.line(
            [
                (float(x_center - 0.5 * whisker_cap), float(y_whisker_max)),
                (float(x_center + 0.5 * whisker_cap), float(y_whisker_max)),
            ],
            fill=outline_rgb,
            width=max(1, int(render_params.line_width_px) - 1),
        )
        draw.line(
            [
                (float(x_center - 0.5 * whisker_cap), float(y_whisker_min)),
                (float(x_center + 0.5 * whisker_cap), float(y_whisker_min)),
            ],
            fill=outline_rgb,
            width=max(1, int(render_params.line_width_px) - 1),
        )

        box_bbox = (
            float(x_center - 0.5 * float(box_width)),
            float(y_q3),
            float(x_center + 0.5 * float(box_width)),
            float(y_q1),
        )
        draw.rectangle(
            box_bbox,
            fill=fill_rgb,
            outline=outline_rgb,
            width=int(render_params.mark_outline_width_px),
        )
        draw.line(
            [(float(box_bbox[0]), float(y_median)), (float(box_bbox[2]), float(y_median))],
            fill=outline_rgb,
            width=max(1, int(render_params.line_width_px) - 1),
        )

        label_center = (
            float(x_center),
            float(plot_bottom) + float(max(18, int(render_params.label_font_size_px) + 6)),
        )
        draw_text_centered(
            draw,
            text=str(spec.label),
            center=label_center,
            font=label_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=int(render_params.label_stroke_width_px),
        )
        label_bbox = _text_bbox(draw, text=str(spec.label), center=label_center, font=label_font)
        mark_bbox = (
            float(box_bbox[0]),
            float(min(y_whisker_max, y_whisker_min)),
            float(box_bbox[2]),
            float(max(y_whisker_max, y_whisker_min)),
        )
        mark_center = (float(x_center), float(0.5 * (float(box_bbox[1]) + float(box_bbox[3]))))
        mark_trace = {
            "entity_id": f"boxplot_{str(spec.label)}",
            "label": str(spec.label),
            "value": int(spec.median),
            "x_rank": int(index),
            "whisker_min": int(spec.whisker_min),
            "q1": int(spec.q1),
            "median": int(spec.median),
            "q3": int(spec.q3),
            "whisker_max": int(spec.whisker_max),
            "mark_center_px": [round(float(mark_center[0]), 3), round(float(mark_center[1]), 3)],
            "mark_bbox_px": [round(float(value), 3) for value in mark_bbox],
            "label_center_px": [round(float(label_center[0]), 3), round(float(label_center[1]), 3)],
            "label_bbox_px": [round(float(value), 3) for value in label_bbox],
            "mark_fill_rgb": [int(channel) for channel in fill_rgb],
            "mark_outline_rgb": [int(channel) for channel in outline_rgb],
        }
        mark_traces.append(mark_trace)
        entities.append(
            {
                "entity_id": str(mark_trace["entity_id"]),
                "entity_type": "boxplot",
                "attrs": {
                    "label": str(spec.label),
                    "x_rank": int(index),
                    "scene_variant": "boxplot",
                    "whisker_min": int(spec.whisker_min),
                    "q1": int(spec.q1),
                    "median": int(spec.median),
                    "q3": int(spec.q3),
                    "whisker_max": int(spec.whisker_max),
                    "mark_center_px": list(mark_trace["mark_center_px"]),
                    "mark_bbox_px": list(mark_trace["mark_bbox_px"]),
                    "label_center_px": list(mark_trace["label_center_px"]),
                    "mark_fill_rgb": list(mark_trace["mark_fill_rgb"]),
                    "mark_outline_rgb": list(mark_trace["mark_outline_rgb"]),
                },
            }
        )

    return RenderedChartScene(
        image=image,
        mark_traces=tuple(dict(item) for item in mark_traces),
        entities=tuple(dict(item) for item in entities),
        plot_bbox_px=tuple(int(value) for value in plot_bbox),
        y_axis_max=int(y_axis_max),
        y_ticks=tuple(int(value) for value in y_ticks),
        scene_variant="boxplot",
    )


def render_violin_scene(
    background: Image.Image,
    *,
    violins: Sequence[ViolinPlotSpec],
    render_params: ChartRenderParams,
) -> RenderedChartScene:
    """Render one categorical violin-plot scene."""

    if len(violins) < 2:
        raise ValueError("violin scenes require at least two categories")

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    plot_left, plot_top, plot_right, plot_bottom = _resolve_plot_bbox(render_params)
    plot_bbox = (int(plot_left), int(plot_top), int(plot_right), int(plot_bottom))
    draw.rectangle(plot_bbox, fill=render_params.plot_fill_rgb)

    max_value = max(int(spec.support_max) for spec in violins)
    y_axis_max = max(4, int(max_value) + 1)
    y_ticks = tuple(range(0, int(y_axis_max) + 1))
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    axis_color = tuple(int(value) for value in render_params.axis_color_rgb)
    grid_color = tuple(int(value) for value in render_params.grid_color_rgb)

    for tick_value in y_ticks:
        y_px = _tick_y(
            int(tick_value),
            y_axis_max=int(y_axis_max),
            plot_top=int(plot_top),
            plot_bottom=int(plot_bottom),
        )
        draw.line(
            [(float(plot_left), float(y_px)), (float(plot_right), float(y_px))],
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
        draw_text_centered(
            draw,
            text=str(tick_value),
            center=(
                float(plot_left) - float(render_params.tick_length_px) - 18.0,
                float(y_px),
            ),
            font=tick_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=max(1, int(round(0.06 * float(render_params.tick_font_size_px)))),
        )

    draw.line(
        [(float(plot_left), float(plot_top)), (float(plot_left), float(plot_bottom))],
        fill=axis_color,
        width=int(render_params.axis_line_width_px),
    )
    draw.line(
        [(float(plot_left), float(plot_bottom)), (float(plot_right), float(plot_bottom))],
        fill=axis_color,
        width=int(render_params.axis_line_width_px),
    )

    centers = _slot_centers(count=len(violins), plot_left=int(plot_left), plot_right=int(plot_right))
    slot_width = float(max(1.0, (float(plot_right) - float(plot_left)) / max(1, len(violins))))
    half_width = float(max(16.0, 0.44 * float(slot_width)))

    mark_traces: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    for index, spec in enumerate(violins):
        x_center = float(centers[index])
        support_min = int(spec.support_min)
        support_max = int(spec.support_max)
        mode_values = [int(value) for value in spec.mode_values]
        support_span = max(2, int(support_max) - int(support_min))

        fill_rgb = (
            tuple(int(channel) for channel in spec.fill_rgb)
            if isinstance(spec.fill_rgb, tuple)
            else tuple(int(value) for value in render_params.mark_fill_rgb)
        )
        outline_rgb = (
            tuple(int(channel) for channel in spec.outline_rgb)
            if isinstance(spec.outline_rgb, tuple)
            else tuple(int(value) for value in render_params.mark_outline_rgb)
        )

        def _width_fraction(value: float) -> float:
            total = 0.16
            for mode in mode_values:
                sigma = max(0.9, 0.16 * float(support_span))
                delta = (float(value) - float(mode)) / float(sigma)
                total += 0.52 * math.exp(-0.5 * float(delta * delta))
            if len(mode_values) >= 2:
                valley_center = 0.5 * float(mode_values[0] + mode_values[-1])
                valley_sigma = max(0.8, 0.12 * float(support_span))
                valley_delta = (float(value) - float(valley_center)) / float(valley_sigma)
                total -= 0.20 * math.exp(-0.5 * float(valley_delta * valley_delta))
            return max(0.10, min(1.0, float(total)))

        sample_values = [float(support_min) + (float(step) / 40.0) * float(support_max - support_min) for step in range(41)]
        right_points: List[Tuple[float, float]] = []
        left_points: List[Tuple[float, float]] = []
        for sample_value in sample_values:
            y_px = _tick_y(
                int(round(sample_value)),
                y_axis_max=int(y_axis_max),
                plot_top=int(plot_top),
                plot_bottom=int(plot_bottom),
            )
            width = float(half_width) * float(_width_fraction(sample_value))
            right_points.append((float(x_center + width), float(y_px)))
            left_points.append((float(x_center - width), float(y_px)))
        polygon_points = right_points + list(reversed(left_points))
        draw.polygon(
            polygon_points,
            fill=fill_rgb,
            outline=outline_rgb,
        )
        draw.line(
            [(float(x_center), float(_tick_y(support_min, y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom)))),
             (float(x_center), float(_tick_y(support_max, y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))))],
            fill=outline_rgb,
            width=max(1, int(render_params.line_width_px) - 2),
        )
        mode_center_points: List[List[float]] = []
        for mode in mode_values:
            mode_y = _tick_y(int(mode), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))
            mode_width = float(half_width) * float(_width_fraction(float(mode)))
            draw.line(
                [(float(x_center - 0.78 * mode_width), float(mode_y)), (float(x_center + 0.78 * mode_width), float(mode_y))],
                fill=outline_rgb,
                width=max(1, int(render_params.line_width_px) - 1),
            )
            mode_center_points.append([round(float(x_center), 3), round(float(mode_y), 3)])

        label_center = (
            float(x_center),
            float(plot_bottom) + float(max(18, int(render_params.label_font_size_px) + 6)),
        )
        draw_text_centered(
            draw,
            text=str(spec.label),
            center=label_center,
            font=label_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=int(render_params.label_stroke_width_px),
        )
        label_bbox = _text_bbox(draw, text=str(spec.label), center=label_center, font=label_font)
        violin_bbox = _bbox_from_points(polygon_points)
        mark_center = [round(float(x_center), 3), round(float(0.5 * (violin_bbox[1] + violin_bbox[3])), 3)]
        mark_trace = {
            "entity_id": f"violin_{str(spec.label)}",
            "label": str(spec.label),
            "value": int(mode_values[-1]),
            "x_rank": int(index),
            "support_min": int(support_min),
            "support_max": int(support_max),
            "mode_values": [int(value) for value in mode_values],
            "mark_center_px": list(mark_center),
            "mark_bbox_px": [round(float(value), 3) for value in violin_bbox],
            "label_center_px": [round(float(label_center[0]), 3), round(float(label_center[1]), 3)],
            "label_bbox_px": [round(float(value), 3) for value in label_bbox],
            "mode_center_points_px": [list(point) for point in mode_center_points],
            "mark_fill_rgb": [int(channel) for channel in fill_rgb],
            "mark_outline_rgb": [int(channel) for channel in outline_rgb],
        }
        mark_traces.append(mark_trace)
        entities.append(
            {
                "entity_id": str(mark_trace["entity_id"]),
                "entity_type": "violin",
                "attrs": {
                    "label": str(spec.label),
                    "x_rank": int(index),
                    "scene_variant": "violin",
                    "support_min": int(support_min),
                    "support_max": int(support_max),
                    "mode_values": [int(value) for value in mode_values],
                    "mark_center_px": list(mark_trace["mark_center_px"]),
                    "mark_bbox_px": list(mark_trace["mark_bbox_px"]),
                    "label_center_px": list(mark_trace["label_center_px"]),
                    "mode_center_points_px": [list(point) for point in mark_trace["mode_center_points_px"]],
                    "mark_fill_rgb": list(mark_trace["mark_fill_rgb"]),
                    "mark_outline_rgb": list(mark_trace["mark_outline_rgb"]),
                },
            }
        )

    return RenderedChartScene(
        image=image,
        mark_traces=tuple(dict(item) for item in mark_traces),
        entities=tuple(dict(item) for item in entities),
        plot_bbox_px=tuple(int(value) for value in plot_bbox),
        y_axis_max=int(y_axis_max),
        y_ticks=tuple(int(value) for value in y_ticks),
        scene_variant="violin",
    )


__all__ = [
    "BoxPlotSpec",
    "ChartMarkSpec",
    "ChartRenderParams",
    "HistogramBinSpec",
    "MultiSeriesChartMarkSpec",
    "RenderedChartScene",
    "SUPPORTED_CHART_SCENE_VARIANTS",
    "SUPPORTED_DISTRIBUTION_CHART_SCENE_VARIANTS",
    "SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS",
    "ViolinPlotSpec",
    "render_boxplot_scene",
    "render_histogram_scene",
    "render_labeled_chart_scene",
    "render_multiseries_chart_scene",
    "render_violin_scene",
    "resolve_chart_render_params",
]
