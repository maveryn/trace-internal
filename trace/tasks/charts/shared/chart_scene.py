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
    "bar",
    "line",
    "scatter",
    "pie",
    "donut",
    "horizontal_bar",
    "dot_plot",
    "lollipop",
)


@dataclass(frozen=True)
class ChartMarkSpec:
    """One symbolic chart mark."""

    label: str
    value: int


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
        side = float(min(plot_width, plot_height))
        pie_margin = float(max(72, int(render_params.label_font_size_px) * 3))
        diameter = float(max(140.0, float(side) - float(pie_margin)))
        radius = 0.5 * float(diameter)
        hole_radius = float(radius * 0.42) if selected_variant == "donut" else 0.0
        center_x = 0.5 * float(plot_left + plot_right)
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
        label_radius = float(radius) + float(max(28, int(render_params.label_font_size_px) + 8))
        center_radius = (
            float(0.5 * (float(radius) + float(hole_radius)))
            if hole_radius > 0.0
            else float(radius) * 0.56
        )
        for index, mark in enumerate(marks):
            sweep = 360.0 * (float(int(mark.value)) / float(total_value))
            end_angle = float(start_angle + sweep)
            draw.pieslice(
                pie_bbox,
                start=float(start_angle),
                end=float(end_angle),
                fill=render_params.mark_fill_rgb,
                outline=render_params.mark_outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )
            mid_angle = float(start_angle + (0.5 * sweep))
            theta = math.radians(float(mid_angle))
            mark_center = (
                float(center_x + (center_radius * math.cos(theta))),
                float(center_y + (center_radius * math.sin(theta))),
            )
            label_center = (
                float(center_x + (label_radius * math.cos(theta))),
                float(center_y + (label_radius * math.sin(theta))),
            )
            label_text = f"{str(mark.label)} {int(mark.value)}"
            label_center = _clamp_text_center_to_canvas(
                draw,
                text=str(label_text),
                center=label_center,
                font=label_font,
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
            )
            draw_text_centered(
                draw,
                text=str(label_text),
                center=label_center,
                font=label_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=int(render_params.label_stroke_width_px),
            )
            label_bbox = _text_bbox(draw, text=str(label_text), center=label_center, font=label_font)

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
            plot_bbox_px=tuple(int(round(value)) for value in pie_bbox),
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
            draw.rectangle(
                bar_bbox,
                fill=render_params.mark_fill_rgb,
                outline=render_params.mark_outline_rgb,
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
            left = float(x_center - 0.5 * float(bar_width))
            right = float(x_center + 0.5 * float(bar_width))
            bar_bbox = (float(left), float(y_center), float(right), float(plot_bottom))
            draw.rectangle(
                bar_bbox,
                fill=render_params.mark_fill_rgb,
                outline=render_params.mark_outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )
        elif selected_variant == "lollipop":
            draw.line(
                [(float(x_center), float(plot_bottom)), (float(x_center), float(y_center))],
                fill=render_params.mark_outline_rgb,
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
                fill=render_params.mark_fill_rgb,
                outline=render_params.mark_outline_rgb,
                width=int(render_params.mark_outline_width_px),
            )
        elif selected_variant in {"scatter", "dot_plot"}:
            radius = float(render_params.point_radius_px)
            ellipse_box = (
                float(x_center - radius),
                float(y_center - radius),
                float(x_center + radius),
                float(y_center + radius),
            )
            draw.ellipse(
                ellipse_box,
                fill=render_params.mark_fill_rgb,
                outline=render_params.mark_outline_rgb,
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
                },
            }
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


__all__ = [
    "ChartMarkSpec",
    "ChartRenderParams",
    "RenderedChartScene",
    "SUPPORTED_CHART_SCENE_VARIANTS",
    "render_labeled_chart_scene",
    "resolve_chart_render_params",
]
