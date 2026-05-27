"""Shared labeled chart-scene rendering helpers for chart tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw

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
    visible: bool = True


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
    value_axis_window_enabled: bool = False
    value_axis_span_min: int = 10
    value_axis_span_max: int = 25
    value_axis_hard_max: int = 99
    value_axis_major_tick_step: int = 5
    value_axis_minor_tick_step: int = 1
    value_axis_allow_nonzero_min: bool = True
    guide_line_mode: str = "off"
    guide_line_prob: float = 0.0
    guide_line_style: str = "dashed"
    guide_line_width_px: int = 1
    guide_line_color_rgb: ChartColor = (150, 156, 166)
    layout_jitter_px: Tuple[int, int] = (0, 0)
    layout_jitter_meta: Dict[str, Any] | None = None
    violin_mode_line_style: str = "full"
    violin_fill_style: str = "solid"
    violin_width_scale: float = 1.0
    violin_smoothing_scale: float = 1.0
    violin_palette_mode: str = "single"
    violin_palette_offset: int = 0


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
    value_axis_min: int = 0
    value_axis_max: int = 0
    value_axis_span: int = 0
    value_axis_major_ticks: Tuple[int, ...] = ()
    value_axis_minor_ticks: Tuple[int, ...] = ()
    value_axis_window_enabled: bool = False
    guide_line_style: str = "none"
    guide_lines: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)


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


def _text_size(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    font,
) -> Tuple[float, float]:
    """Return one text width/height pair in pixels."""

    try:
        raw = draw.textbbox((0, 0), str(text), font=font)
        return (float(raw[2] - raw[0]), float(raw[3] - raw[1]))
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        return (float(width), float(height))


def _resolve_plot_bbox(params: ChartRenderParams) -> Tuple[int, int, int, int]:
    """Resolve one axis-aligned plot bbox within the chart canvas."""

    left = int(params.plot_margin_left_px)
    top = int(params.plot_margin_top_px)
    right = int(params.canvas_width) - int(params.plot_margin_right_px)
    bottom = int(params.canvas_height) - int(params.plot_margin_bottom_px)
    if right <= left or bottom <= top:
        raise ValueError("chart plot margins leave no drawable plot area")
    return (int(left), int(top), int(right), int(bottom))


def _tick_y(
    value: int,
    *,
    y_axis_min: int = 0,
    y_axis_max: int,
    plot_top: int,
    plot_bottom: int,
) -> float:
    """Map one integer chart value to plot-space pixel y coordinate."""

    span = max(1, int(y_axis_max) - int(y_axis_min))
    plot_height = float(max(1, int(plot_bottom) - int(plot_top)))
    return float(plot_bottom) - ((float(value) - float(y_axis_min)) / float(span)) * float(plot_height)


def _tick_x(
    value: int,
    *,
    x_axis_min: int = 0,
    x_axis_max: int,
    plot_left: int,
    plot_right: int,
) -> float:
    """Map one integer chart value to plot-space pixel x coordinate."""

    span = max(1, int(x_axis_max) - int(x_axis_min))
    plot_width = float(max(1, int(plot_right) - int(plot_left)))
    return float(plot_left) + ((float(value) - float(x_axis_min)) / float(span)) * float(plot_width)


def _axis_ticks(axis_max: int, *, axis_min: int = 0, step: int | None = None) -> Tuple[int, ...]:
    """Return readable integer ticks for a chart axis."""

    min_value = int(axis_min)
    max_value = max(1, int(axis_max))
    if int(max_value) < int(min_value):
        min_value, max_value = int(max_value), int(min_value)
    if step is None:
        span = int(max_value) - int(min_value)
        if int(span) <= 25:
            return tuple(range(int(min_value), int(max_value) + 1))
        target_step = max(1, int(math.ceil(float(span) / 10.0)))
        nice_steps = (2, 5, 10, 20, 25, 50, 100)
        resolved_step = next((candidate for candidate in nice_steps if int(candidate) >= int(target_step)), int(target_step))
    else:
        resolved_step = max(1, int(step))
    ticks = [int(value) for value in range(int(min_value), int(max_value) + 1, int(resolved_step))]
    if not ticks or ticks[0] != int(min_value):
        ticks.insert(0, int(min_value))
    if ticks[-1] != int(max_value):
        ticks.append(int(max_value))
    return tuple(int(value) for value in ticks)


def _resolve_value_axis(
    values: Sequence[int],
    *,
    render_params: ChartRenderParams,
) -> Tuple[int, int, Tuple[int, ...], Tuple[int, ...], bool]:
    """Resolve one readable value-axis window for axis-based charts."""

    if not values:
        return 0, 4, _axis_ticks(4), _axis_ticks(4), False
    data_min = int(min(int(value) for value in values))
    data_max = int(max(int(value) for value in values))
    if not bool(render_params.value_axis_window_enabled):
        axis_min = 0
        axis_max = max(4, int(data_max) + 1)
        ticks = _axis_ticks(axis_max)
        return int(axis_min), int(axis_max), ticks, ticks, False

    hard_max = int(max(1, render_params.value_axis_hard_max))
    major_step = max(1, int(render_params.value_axis_major_tick_step))
    minor_step = max(1, int(render_params.value_axis_minor_tick_step))
    span_min = max(1, int(render_params.value_axis_span_min))
    span_max = max(int(span_min), int(render_params.value_axis_span_max))

    if bool(render_params.value_axis_allow_nonzero_min):
        axis_min = int(math.floor(float(data_min) / float(major_step)) * int(major_step))
        if int(data_max) - int(axis_min) > int(span_max) and int(data_max) - int(data_min) <= int(span_max):
            axis_min = int(data_max) - int(span_max)
    else:
        axis_min = 0
    axis_min = max(0, int(axis_min))

    required_span = max(int(span_min), int(data_max) - int(axis_min))
    if int(required_span) <= int(span_max):
        axis_span = int(span_max)
    else:
        axis_span = int(required_span)
    axis_max = int(axis_min) + int(axis_span)

    if int(axis_max) > int(hard_max):
        axis_max = int(hard_max)
        axis_min = max(0, int(axis_max) - int(axis_span))
        if int(data_min) < int(axis_min):
            axis_min = int(data_min)
        if int(data_max) > int(axis_max):
            axis_max = int(data_max)

    if int(axis_min) == int(axis_max):
        axis_max = int(axis_min) + 1
    major_ticks = _axis_ticks(int(axis_max), axis_min=int(axis_min), step=int(major_step))
    minor_ticks = _axis_ticks(int(axis_max), axis_min=int(axis_min), step=int(minor_step))
    return int(axis_min), int(axis_max), major_ticks, minor_ticks, True


def _draw_styled_line(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Tuple[float, float]],
    *,
    fill: ChartColor,
    width: int,
    style: str,
) -> None:
    """Draw a solid, dashed, or dotted line segment."""

    if len(points) < 2:
        return
    x0, y0 = float(points[0][0]), float(points[0][1])
    x1, y1 = float(points[1][0]), float(points[1][1])
    resolved_width = max(1, int(width))
    resolved_style = str(style).strip().lower()
    if resolved_style == "solid":
        draw.line([(x0, y0), (x1, y1)], fill=fill, width=resolved_width)
        return

    dx = float(x1 - x0)
    dy = float(y1 - y0)
    length = math.hypot(dx, dy)
    if length <= 0.0:
        return
    ux = dx / length
    uy = dy / length
    if resolved_style == "dotted":
        gap = max(4.0, float(resolved_width) * 4.0)
        radius = max(1.0, float(resolved_width))
        distance = 0.0
        while distance <= length:
            cx = x0 + ux * distance
            cy = y0 + uy * distance
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=fill)
            distance += gap
        return

    dash = max(8.0, float(resolved_width) * 8.0)
    gap = max(5.0, float(resolved_width) * 5.0)
    distance = 0.0
    while distance < length:
        end = min(length, distance + dash)
        draw.line(
            [
                (x0 + ux * distance, y0 + uy * distance),
                (x0 + ux * end, y0 + uy * end),
            ],
            fill=fill,
            width=resolved_width,
        )
        distance += dash + gap


def _guide_lines_enabled(render_params: ChartRenderParams) -> bool:
    """Return whether value guide lines should be drawn for this render."""

    return str(render_params.guide_line_mode).strip().lower() in {"always", "variant"}


def value_axis_render_metadata(rendered_scene: RenderedChartScene) -> Dict[str, Any]:
    """Return trace/render metadata for the chart value axis."""

    return {
        "value_axis_min": int(rendered_scene.value_axis_min),
        "value_axis_max": int(rendered_scene.value_axis_max),
        "value_axis_span": int(rendered_scene.value_axis_span),
        "value_axis_major_ticks": [int(value) for value in rendered_scene.value_axis_major_ticks],
        "value_axis_minor_ticks": [int(value) for value in rendered_scene.value_axis_minor_ticks],
        "value_axis_window_enabled": bool(rendered_scene.value_axis_window_enabled),
        "guide_line_style": str(rendered_scene.guide_line_style),
        "guide_lines": [dict(line) for line in rendered_scene.guide_lines],
    }


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


def _blend_rgb(foreground: ChartColor, background: ChartColor, foreground_weight: float) -> ChartColor:
    """Blend two RGB colors with a clamped foreground weight."""

    weight = max(0.0, min(1.0, float(foreground_weight)))
    return tuple(
        int(round((weight * float(fg)) + ((1.0 - weight) * float(bg))))
        for fg, bg in zip(foreground, background)
    )


def _darken_rgb(color: ChartColor, factor: float = 0.58) -> ChartColor:
    """Return a darker RGB color for outlines/hatching."""

    scale = max(0.0, min(1.0, float(factor)))
    return tuple(max(0, min(255, int(round(float(channel) * scale)))) for channel in color)


def _violin_palette_color(
    base_fill: ChartColor,
    *,
    index: int,
    offset: int,
    plot_fill: ChartColor,
) -> ChartColor:
    """Return one muted per-violin color while preserving readable contrast."""

    muted_palette: Tuple[ChartColor, ...] = (
        (92, 133, 196),
        (193, 111, 86),
        (94, 155, 116),
        (170, 126, 190),
        (196, 154, 77),
        (90, 154, 168),
        (184, 103, 135),
        (128, 139, 92),
    )
    palette_color = muted_palette[(int(index) + int(offset)) % len(muted_palette)]
    return _blend_rgb(palette_color, base_fill, 0.82) if base_fill else _blend_rgb(palette_color, plot_fill, 0.90)


def _draw_violin_polygon(
    image: Image.Image,
    *,
    points: Sequence[Tuple[float, float]],
    fill_rgb: ChartColor,
    outline_rgb: ChartColor,
    fill_style: str,
    outline_width: int,
    plot_fill_rgb: ChartColor,
) -> None:
    """Draw one violin body with optional lightweight fill styling."""

    style = str(fill_style).strip().lower()
    draw = ImageDraw.Draw(image)
    if style == "light":
        body_fill = _blend_rgb(fill_rgb, plot_fill_rgb, 0.58)
    elif style == "outline":
        body_fill = _blend_rgb(fill_rgb, plot_fill_rgb, 0.28)
    elif style == "hatch":
        body_fill = _blend_rgb(fill_rgb, plot_fill_rgb, 0.34)
    else:
        body_fill = fill_rgb

    draw.polygon(points, fill=body_fill)
    if style == "hatch":
        mask = Image.new("L", image.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.polygon(points, fill=255)
        hatch_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        hatch_draw = ImageDraw.Draw(hatch_layer)
        x0, y0, x1, y1 = [int(round(value)) for value in _bbox_from_points(points)]
        hatch_color = _darken_rgb(outline_rgb, 0.86)
        spacing = max(9, int(round(0.75 * float(outline_width + 10))))
        for start_x in range(x0 - (y1 - y0) - spacing, x1 + spacing, spacing):
            hatch_draw.line(
                [(start_x, y1 + spacing), (start_x + (y1 - y0) + spacing, y0 - spacing)],
                fill=(*hatch_color, 95),
                width=max(1, int(outline_width)),
            )
        hatch_alpha = ImageChops.multiply(hatch_layer.getchannel("A"), mask)
        hatch_layer.putalpha(hatch_alpha)
        composited = Image.alpha_composite(image.convert("RGBA"), hatch_layer)
        image.paste(composited.convert("RGB"))
        draw = ImageDraw.Draw(image)

    draw.line(
        list(points) + [tuple(points[0])],
        fill=outline_rgb,
        width=max(1, int(outline_width)),
        joint="curve",
    )


def resolve_chart_render_params(params: Mapping[str, Any]) -> ChartRenderParams:
    """Resolve one chart render-parameter block from config-like values."""

    def _bool_value(key: str, fallback: bool) -> bool:
        value = params.get(str(key), bool(fallback))
        if isinstance(value, str):
            return str(value).strip().lower() in {"1", "true", "yes", "on", "always"}
        return bool(value)

    def _style_value() -> str:
        explicit = params.get("guide_line_style")
        if explicit is not None:
            return str(explicit)
        styles = params.get("guide_line_styles", ())
        if isinstance(styles, Sequence) and styles and not isinstance(styles, (str, bytes)):
            seed = int(params.get("_guide_style_seed", 0))
            return str(styles[abs(seed) % len(styles)])
        return "dashed"

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
        value_axis_window_enabled=_bool_value("value_axis_window_enabled", False),
        value_axis_span_min=int(params.get("value_axis_span_min", 10)),
        value_axis_span_max=int(params.get("value_axis_span_max", 25)),
        value_axis_hard_max=int(params.get("value_axis_hard_max", 99)),
        value_axis_major_tick_step=int(params.get("value_axis_major_tick_step", 5)),
        value_axis_minor_tick_step=int(params.get("value_axis_minor_tick_step", 1)),
        value_axis_allow_nonzero_min=_bool_value("value_axis_allow_nonzero_min", True),
        guide_line_mode=str(params.get("guide_line_mode", "off")),
        guide_line_prob=float(params.get("guide_line_prob", 0.0)),
        guide_line_style=str(_style_value()),
        guide_line_width_px=int(params.get("guide_line_width_px", 1)),
        guide_line_color_rgb=_normalize_color(params.get("guide_line_color_rgb", (150, 156, 166)), (150, 156, 166)),
        layout_jitter_px=(
            int(params.get("layout_jitter_dx_px", 0)),
            int(params.get("layout_jitter_dy_px", 0)),
        ),
        layout_jitter_meta=dict(params.get("layout_jitter_meta", {}))
        if isinstance(params.get("layout_jitter_meta", {}), dict)
        else None,
        violin_mode_line_style=str(params.get("violin_mode_line_style", "full")),
        violin_fill_style=str(params.get("violin_fill_style", "solid")),
        violin_width_scale=float(params.get("violin_width_scale", 1.0)),
        violin_smoothing_scale=float(params.get("violin_smoothing_scale", 1.0)),
        violin_palette_mode=str(params.get("violin_palette_mode", "single")),
        violin_palette_offset=int(params.get("violin_palette_offset", 0)),
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

    visible_marks = [mark for mark in marks if bool(getattr(mark, "visible", True))]
    if not visible_marks:
        raise ValueError("charts require at least one visible mark")
    max_value = max(int(mark.value) for mark in visible_marks)
    y_axis_min, y_axis_max, y_ticks, y_minor_ticks, value_axis_window_enabled = _resolve_value_axis(
        [int(mark.value) for mark in visible_marks],
        render_params=render_params,
    )
    if selected_variant in {"pie", "donut", "radar"}:
        y_axis_min = 0
        y_axis_max = max(4, int(max_value) + 1)
        y_ticks = _axis_ticks(y_axis_max)
        y_minor_ticks = tuple(int(value) for value in y_ticks)
        value_axis_window_enabled = False

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
        legend_row_height = float(max(render_params.label_font_size_px + 16, 42))
        legend_top = float(plot_top) + float(max(12.0, 0.5 * (plot_height - (len(marks) * legend_row_height))))
        legend_swatch_side = float(max(28, int(round(render_params.label_font_size_px * 1.05))))
        legend_frame_pad = float(max(3, int(round(render_params.mark_outline_width_px * 1.5))))
        legend_text_gap = float(max(16, int(render_params.label_font_size_px * 0.8)))
        legend_frame_fill = tuple(int(value) for value in render_params.plot_fill_rgb)
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
            percent_text = f"{int(mark.value)}"
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
            legend_frame_bbox = (
                float(legend_swatch_bbox[0] - legend_frame_pad),
                float(legend_swatch_bbox[1] - legend_frame_pad),
                float(legend_swatch_bbox[2] + legend_frame_pad),
                float(legend_swatch_bbox[3] + legend_frame_pad),
            )
            draw.rectangle(
                legend_frame_bbox,
                fill=legend_frame_fill,
                outline=axis_color,
                width=max(1, int(render_params.mark_outline_width_px)),
            )
            draw.rectangle(
                legend_swatch_bbox,
                fill=fill_rgb,
                outline=outline_rgb,
                width=max(2, int(render_params.mark_outline_width_px)),
            )
            label_width, _ = _text_size(draw, text=str(mark.label), font=label_font)
            label_left = float(legend_frame_bbox[2]) + float(legend_text_gap)
            label_center = (
                float(label_left + (0.5 * label_width)),
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
                        "label_bbox_px": list(mark_trace["label_bbox_px"]),
                        "legend_swatch_bbox_px": list(mark_trace["legend_swatch_bbox_px"]),
                        "percentage_center_px": list(mark_trace["percentage_center_px"]),
                        "percentage_bbox_px": list(mark_trace["percentage_bbox_px"]),
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
            value_axis_min=0,
            value_axis_max=int(y_axis_max),
            value_axis_span=int(y_axis_max),
            value_axis_major_ticks=tuple(int(value) for value in y_ticks),
            value_axis_minor_ticks=tuple(int(value) for value in y_ticks),
            value_axis_window_enabled=False,
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
            value_axis_min=0,
            value_axis_max=int(y_axis_max),
            value_axis_span=int(y_axis_max),
            value_axis_major_ticks=tuple(int(value) for value in y_ticks),
            value_axis_minor_ticks=tuple(int(value) for value in y_ticks),
            value_axis_window_enabled=False,
        )

    if selected_variant == "horizontal_bar":
        for tick_value in y_minor_ticks:
            x_px = _tick_x(
                int(tick_value),
                x_axis_min=int(y_axis_min),
                x_axis_max=int(y_axis_max),
                plot_left=int(plot_left),
                plot_right=int(plot_right),
            )
            draw.line(
                [(float(x_px), float(plot_top)), (float(x_px), float(plot_bottom))],
                fill=grid_color,
                width=int(render_params.grid_line_width_px),
            )
            if int(tick_value) in set(int(value) for value in y_ticks):
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
        for tick_value in y_minor_ticks:
            y_px = _tick_y(
                int(tick_value),
                y_axis_min=int(y_axis_min),
                y_axis_max=int(y_axis_max),
                plot_top=int(plot_top),
                plot_bottom=int(plot_bottom),
            )
            draw.line(
                [(float(plot_left), float(y_px)), (float(plot_right), float(y_px))],
                fill=grid_color,
                width=int(render_params.grid_line_width_px),
            )
            if int(tick_value) in set(int(value) for value in y_ticks):
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
    guide_lines: List[Dict[str, Any]] = []
    guide_color = tuple(int(value) for value in render_params.guide_line_color_rgb)
    draw_guides = _guide_lines_enabled(render_params)
    slot_width = float(max(1.0, (float(plot_right) - float(plot_left)) / max(1, len(marks))))
    bar_width = float(max(12.0, float(render_params.bar_width_fraction) * float(slot_width)))
    slot_height = float(max(1.0, (float(plot_bottom) - float(plot_top)) / max(1, len(marks))))
    horizontal_bar_height = float(max(12.0, float(render_params.bar_width_fraction) * float(slot_height)))

    for index, mark in enumerate(marks):
        mark_visible = bool(getattr(mark, "visible", True))
        bar_bbox: Tuple[float, float, float, float] | None = None
        if selected_variant == "horizontal_bar":
            y_center = float(y_slot_centers[index])
            x_extent = _tick_x(
                int(mark.value),
                x_axis_min=int(y_axis_min),
                x_axis_max=int(y_axis_max),
                plot_left=int(plot_left),
                plot_right=int(plot_right),
            )
            x_center = float(plot_left) + 0.5 * float(x_extent - float(plot_left))
            mark_point = (float(x_extent), float(y_center))
            top = float(y_center - 0.5 * float(horizontal_bar_height))
            bottom = float(y_center + 0.5 * float(horizontal_bar_height))
            bar_bbox = (float(plot_left), float(top), float(x_extent), float(bottom))
            if mark_visible:
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
            if mark_visible:
                y_center = _tick_y(
                    int(mark.value),
                    y_axis_min=int(y_axis_min),
                    y_axis_max=int(y_axis_max),
                    plot_top=int(plot_top),
                    plot_bottom=int(plot_bottom),
                )
                line_points.append((float(x_center), float(y_center)))
                mark_point = (float(x_center), float(y_center))
            else:
                y_center = float(plot_bottom)
                mark_point = (float(x_center), float(y_center))

        if bool(draw_guides) and bool(mark_visible):
            if selected_variant == "horizontal_bar":
                guide_points = [(float(mark_point[0]), float(plot_bottom)), (float(mark_point[0]), float(mark_point[1]))]
                guide_orientation = "vertical"
            else:
                guide_points = [(float(plot_left), float(mark_point[1])), (float(mark_point[0]), float(mark_point[1]))]
                guide_orientation = "horizontal"
            _draw_styled_line(
                draw,
                guide_points,
                fill=guide_color,
                width=int(render_params.guide_line_width_px),
                style=str(render_params.guide_line_style),
            )
            guide_lines.append(
                {
                    "label": str(mark.label),
                    "value": int(mark.value),
                    "orientation": str(guide_orientation),
                    "points_px": [[round(float(x), 3), round(float(y), 3)] for x, y in guide_points],
                    "style": str(render_params.guide_line_style),
                }
            )

        if mark_visible and selected_variant == "bar":
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
        elif mark_visible and selected_variant == "lollipop":
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
        elif mark_visible and selected_variant in {"scatter", "dot_plot"}:
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

        if mark_visible:
            label_center = _label_center_for_variant(
                scene_variant=selected_variant,
                mark_center=(float(x_center), float(y_center)),
                bar_bbox=bar_bbox,
                point_radius_px=int(render_params.point_radius_px),
                label_font_size_px=int(render_params.label_font_size_px),
            )
        else:
            draw.line(
                [
                    (float(x_center), float(plot_bottom)),
                    (float(x_center), float(plot_bottom) + float(render_params.tick_length_px)),
                ],
                fill=axis_color,
                width=max(1, int(render_params.axis_line_width_px)),
            )
            label_center = (
                float(x_center),
                float(plot_bottom) + float(render_params.tick_length_px) + float(render_params.label_font_size_px),
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
        if mark_visible:
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
            entity_type = "bar" if selected_variant in {"bar", "horizontal_bar"} else "point"
        else:
            mark_bbox = list(label_bbox)
            entity_type = "future_label_slot"
        mark_trace = {
            "entity_id": f"mark_{str(mark.label)}",
            "label": str(mark.label),
            "value": int(mark.value),
            "visible": bool(mark_visible),
            "x_rank": int(index),
            "mark_center_px": [
                round(float(mark_point[0] if mark_visible else label_center[0]), 3),
                round(float(mark_point[1] if mark_visible else label_center[1]), 3),
            ],
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
                "entity_type": str(entity_type),
                "attrs": {
                    "label": str(mark.label),
                    "x_rank": int(index),
                    "scene_variant": str(selected_variant),
                    "mark_center_px": list(mark_trace["mark_center_px"]),
                    "mark_bbox_px": list(mark_trace["mark_bbox_px"]),
                    "label_center_px": list(mark_trace["label_center_px"]),
                    "visible": bool(mark_visible),
                    "mark_fill_rgb": list(mark_trace["mark_fill_rgb"]),
                    "mark_outline_rgb": list(mark_trace["mark_outline_rgb"]),
                    **({"value": int(mark.value)} if mark_visible else {}),
                },
            }
        )

    if selected_variant == "area" and len(line_points) >= 2:
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
        for guide in guide_lines:
            guide_points = [
                (float(point[0]), float(point[1]))
                for point in guide.get("points_px", [])
                if isinstance(point, list) and len(point) == 2
            ]
            _draw_styled_line(
                draw,
                guide_points,
                fill=guide_color,
                width=int(render_params.guide_line_width_px),
                style=str(render_params.guide_line_style),
            )
        draw.line(
            line_points,
            fill=render_params.mark_outline_rgb,
            width=int(render_params.line_width_px),
            joint="curve",
        )
        for trace in mark_traces:
            if not bool(trace.get("visible", True)):
                continue
            center_x, center_y = trace["mark_center_px"]
            fill_rgb = tuple(int(value) for value in trace.get("mark_fill_rgb", render_params.mark_fill_rgb))
            outline_rgb = tuple(int(value) for value in trace.get("mark_outline_rgb", render_params.mark_outline_rgb))
            radius = float(render_params.point_radius_px)
            ellipse_box = (
                float(center_x - radius),
                float(center_y - radius),
                float(center_x + radius),
                float(center_y + radius),
            )
            draw.ellipse(
                ellipse_box,
                fill=fill_rgb,
                outline=outline_rgb,
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

    if selected_variant == "line" and len(line_points) >= 2:
        draw.line(
            line_points,
            fill=render_params.mark_outline_rgb,
            width=int(render_params.line_width_px),
            joint="curve",
        )
        for trace in mark_traces:
            if not bool(trace.get("visible", True)):
                continue
            center_x, center_y = trace["mark_center_px"]
            fill_rgb = tuple(int(value) for value in trace.get("mark_fill_rgb", render_params.mark_fill_rgb))
            outline_rgb = tuple(int(value) for value in trace.get("mark_outline_rgb", render_params.mark_outline_rgb))
            radius = float(render_params.point_radius_px)
            ellipse_box = (
                float(center_x - radius),
                float(center_y - radius),
                float(center_x + radius),
                float(center_y + radius),
            )
            draw.ellipse(
                ellipse_box,
                fill=fill_rgb,
                outline=outline_rgb,
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
        value_axis_min=int(y_axis_min),
        value_axis_max=int(y_axis_max),
        value_axis_span=int(y_axis_max) - int(y_axis_min),
        value_axis_major_ticks=tuple(int(value) for value in y_ticks),
        value_axis_minor_ticks=tuple(int(value) for value in y_minor_ticks),
        value_axis_window_enabled=bool(value_axis_window_enabled),
        guide_line_style=str(render_params.guide_line_style if guide_lines else "none"),
        guide_lines=tuple(dict(item) for item in guide_lines),
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

    y_axis_min, y_axis_max, y_ticks, y_minor_ticks, value_axis_window_enabled = _resolve_value_axis(
        [int(mark.value) for mark in marks],
        render_params=render_params,
    )

    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    axis_color = tuple(int(value) for value in render_params.axis_color_rgb)
    grid_color = tuple(int(value) for value in render_params.grid_color_rgb)

    if selected_variant == "grouped_horizontal_bar":
        major_tick_values = set(int(value) for value in y_ticks)
        for tick_value in y_minor_ticks:
            x_px = _tick_x(
                int(tick_value),
                x_axis_min=int(y_axis_min),
                x_axis_max=int(y_axis_max),
                plot_left=int(plot_left),
                plot_right=int(chart_right),
            )
            draw.line(
                [(float(x_px), float(plot_top)), (float(x_px), float(plot_bottom))],
                fill=grid_color,
                width=int(render_params.grid_line_width_px),
            )
            if int(tick_value) in major_tick_values:
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
        major_tick_values = set(int(value) for value in y_ticks)
        for tick_value in y_minor_ticks:
            y_px = _tick_y(
                int(tick_value),
                y_axis_min=int(y_axis_min),
                y_axis_max=int(y_axis_max),
                plot_top=int(plot_top),
                plot_bottom=int(plot_bottom),
            )
            draw.line(
                [(float(plot_left), float(y_px)), (float(chart_right), float(y_px))],
                fill=grid_color,
                width=int(render_params.grid_line_width_px),
            )
            if int(tick_value) in major_tick_values:
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
    guide_lines: List[Dict[str, Any]] = []
    guide_color = tuple(int(value) for value in render_params.guide_line_color_rgb)
    draw_guides = _guide_lines_enabled(render_params)

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
                    y_axis_min=int(y_axis_min),
                    y_axis_max=int(y_axis_max),
                    plot_top=int(plot_top),
                    plot_bottom=int(plot_bottom),
                )
                mark_point = (float(x_center), float(y_center))
            elif selected_variant == "grouped_horizontal_bar":
                y_center = float(group_top) + (float(series_rank) + 0.5) * float(subgroup_height)
                x_extent = _tick_x(
                    int(mark.value),
                    x_axis_min=int(y_axis_min),
                    x_axis_max=int(y_axis_max),
                    plot_left=int(plot_left),
                    plot_right=int(chart_right),
                )
                x_center = float(plot_left) + 0.5 * float(x_extent - float(plot_left))
                mark_point = (float(x_extent), float(y_center))
            else:
                x_center = float(group_left) + (float(series_rank) + 0.5) * float(subgroup_width)
                y_center = _tick_y(
                    int(mark.value),
                    y_axis_min=int(y_axis_min),
                    y_axis_max=int(y_axis_max),
                    plot_top=int(plot_top),
                    plot_bottom=int(plot_bottom),
                )
                mark_point = (float(x_center), float(y_center))

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
            if bool(draw_guides):
                if selected_variant == "grouped_horizontal_bar":
                    guide_points = [(float(mark_point[0]), float(plot_bottom)), (float(mark_point[0]), float(mark_point[1]))]
                    guide_orientation = "vertical"
                else:
                    guide_points = [(float(plot_left), float(mark_point[1])), (float(mark_point[0]), float(mark_point[1]))]
                    guide_orientation = "horizontal"
                _draw_styled_line(
                    draw,
                    guide_points,
                    fill=guide_color,
                    width=int(render_params.guide_line_width_px),
                    style=str(render_params.guide_line_style),
                )
                guide_lines.append(
                    {
                        "category_label": str(category_label),
                        "series_label": str(series_label),
                        "value": int(mark.value),
                        "orientation": str(guide_orientation),
                        "points_px": [[round(float(x), 3), round(float(y), 3)] for x, y in guide_points],
                        "style": str(render_params.guide_line_style),
                    }
                )
            mark_records.append(
                {
                    "category_label": str(category_label),
                    "series_label": str(series_label),
                    "category_rank": int(category_rank),
                    "series_rank": int(series_rank),
                    "value": int(mark.value),
                    "fill_rgb": [int(channel) for channel in fill_rgb],
                    "outline_rgb": [int(channel) for channel in outline_rgb],
                    "mark_center_px": [round(float(mark_point[0]), 3), round(float(mark_point[1]), 3)],
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
            float(swatch_bbox[0]) - float(legend_frame_pad),
            float(swatch_bbox[1]) - float(legend_frame_pad),
            float(swatch_bbox[2]) + float(legend_frame_pad),
            float(swatch_bbox[3]) + float(legend_frame_pad),
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
        label_width, _ = _text_size(draw, text=str(series_label), font=label_font)
        label_left = float(legend_frame_bbox[2]) + float(legend_text_gap)
        label_center = (
            float(label_left) + 0.5 * float(label_width),
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
        value_axis_min=int(y_axis_min),
        value_axis_max=int(y_axis_max),
        value_axis_span=int(y_axis_max) - int(y_axis_min),
        value_axis_major_ticks=tuple(int(value) for value in y_ticks),
        value_axis_minor_ticks=tuple(int(value) for value in y_minor_ticks),
        value_axis_window_enabled=bool(value_axis_window_enabled),
        guide_line_style=str(render_params.guide_line_style if guide_lines else "none"),
        guide_lines=tuple(dict(item) for item in guide_lines),
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

    y_axis_min, y_axis_max, y_ticks, y_minor_ticks, value_axis_window_enabled = _resolve_value_axis(
        [int(bin_spec.count) for bin_spec in bins],
        render_params=render_params,
    )
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    axis_color = tuple(int(value) for value in render_params.axis_color_rgb)
    grid_color = tuple(int(value) for value in render_params.grid_color_rgb)

    major_tick_values = set(int(value) for value in y_ticks)
    for tick_value in y_minor_ticks:
        y_px = _tick_y(
            int(tick_value),
            y_axis_min=int(y_axis_min),
            y_axis_max=int(y_axis_max),
            plot_top=int(plot_top),
            plot_bottom=int(plot_bottom),
        )
        draw.line(
            [(float(plot_left), float(y_px)), (float(plot_right), float(y_px))],
            fill=grid_color,
            width=int(render_params.grid_line_width_px),
        )
        if int(tick_value) in major_tick_values:
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
    guide_lines: List[Dict[str, Any]] = []
    draw_guides = _guide_lines_enabled(render_params)
    for index, bin_spec in enumerate(bins):
        left = float(plot_left) + float(index) * float(slot_width)
        right = float(plot_left) + float(index + 1) * float(slot_width)
        top = _tick_y(
            int(bin_spec.count),
            y_axis_min=int(y_axis_min),
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
        if bool(draw_guides):
            guide_points = [(float(plot_left), float(top)), (float(x_center), float(top))]
            _draw_styled_line(
                draw,
                guide_points,
                fill=render_params.guide_line_color_rgb,
                width=int(render_params.guide_line_width_px),
                style=str(render_params.guide_line_style),
            )
            guide_lines.append(
                {
                    "entity_id": f"bin_{index}",
                    "label": str(bin_spec.label),
                    "value": int(bin_spec.count),
                    "orientation": "horizontal",
                    "points_px": [[round(float(x), 3), round(float(y), 3)] for x, y in guide_points],
                    "style": str(render_params.guide_line_style),
                }
            )
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
        value_axis_min=int(y_axis_min),
        value_axis_max=int(y_axis_max),
        value_axis_span=int(y_axis_max) - int(y_axis_min),
        value_axis_major_ticks=tuple(int(value) for value in y_ticks),
        value_axis_minor_ticks=tuple(int(value) for value in y_minor_ticks),
        value_axis_window_enabled=bool(value_axis_window_enabled),
        guide_line_style=str(render_params.guide_line_style if guide_lines else "none"),
        guide_lines=tuple(dict(item) for item in guide_lines),
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

    boxplot_values: List[int] = []
    for spec in boxplots:
        boxplot_values.extend([int(spec.whisker_min), int(spec.q1), int(spec.median), int(spec.q3), int(spec.whisker_max)])
    y_axis_min, y_axis_max, y_ticks, y_minor_ticks, value_axis_window_enabled = _resolve_value_axis(
        boxplot_values,
        render_params=render_params,
    )
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    axis_color = tuple(int(value) for value in render_params.axis_color_rgb)
    grid_color = tuple(int(value) for value in render_params.grid_color_rgb)

    major_tick_values = set(int(value) for value in y_ticks)
    for tick_value in y_minor_ticks:
        y_px = _tick_y(
            int(tick_value),
            y_axis_min=int(y_axis_min),
            y_axis_max=int(y_axis_max),
            plot_top=int(plot_top),
            plot_bottom=int(plot_bottom),
        )
        draw.line(
            [(float(plot_left), float(y_px)), (float(plot_right), float(y_px))],
            fill=grid_color,
            width=int(render_params.grid_line_width_px),
        )
        if int(tick_value) in major_tick_values:
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
    guide_lines: List[Dict[str, Any]] = []
    draw_guides = _guide_lines_enabled(render_params)
    for index, spec in enumerate(boxplots):
        x_center = float(centers[index])
        y_whisker_min = _tick_y(int(spec.whisker_min), y_axis_min=int(y_axis_min), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))
        y_q1 = _tick_y(int(spec.q1), y_axis_min=int(y_axis_min), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))
        y_median = _tick_y(int(spec.median), y_axis_min=int(y_axis_min), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))
        y_q3 = _tick_y(int(spec.q3), y_axis_min=int(y_axis_min), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))
        y_whisker_max = _tick_y(int(spec.whisker_max), y_axis_min=int(y_axis_min), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))

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
        if bool(draw_guides):
            guide_points = [(float(plot_left), float(y_median)), (float(x_center), float(y_median))]
            _draw_styled_line(
                draw,
                guide_points,
                fill=render_params.guide_line_color_rgb,
                width=int(render_params.guide_line_width_px),
                style=str(render_params.guide_line_style),
            )
            guide_lines.append(
                {
                    "entity_id": f"boxplot_{str(spec.label)}",
                    "label": str(spec.label),
                    "value": int(spec.median),
                    "stat": "median",
                    "orientation": "horizontal",
                    "points_px": [[round(float(x), 3), round(float(y), 3)] for x, y in guide_points],
                    "style": str(render_params.guide_line_style),
                }
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
        value_axis_min=int(y_axis_min),
        value_axis_max=int(y_axis_max),
        value_axis_span=int(y_axis_max) - int(y_axis_min),
        value_axis_major_ticks=tuple(int(value) for value in y_ticks),
        value_axis_minor_ticks=tuple(int(value) for value in y_minor_ticks),
        value_axis_window_enabled=bool(value_axis_window_enabled),
        guide_line_style=str(render_params.guide_line_style if guide_lines else "none"),
        guide_lines=tuple(dict(item) for item in guide_lines),
    )


def render_paired_boxplot_scene(
    background: Image.Image,
    *,
    before_boxplots: Sequence[BoxPlotSpec],
    after_boxplots: Sequence[BoxPlotSpec],
    render_params: ChartRenderParams,
    before_title: str = "Before",
    after_title: str = "After",
) -> RenderedChartScene:
    """Render matched before/after boxplots as two aligned panels."""

    if len(before_boxplots) < 2 or len(after_boxplots) < 2:
        raise ValueError("paired boxplot scenes require at least two categories per panel")
    if len(before_boxplots) != len(after_boxplots):
        raise ValueError("paired boxplot scenes require equal before/after category counts")
    before_labels = [str(spec.label) for spec in before_boxplots]
    after_labels = [str(spec.label) for spec in after_boxplots]
    if before_labels != after_labels:
        raise ValueError("paired boxplot panels must use the same labels in the same order")

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    plot_left, plot_top, plot_right, plot_bottom = _resolve_plot_bbox(render_params)
    plot_bbox = (int(plot_left), int(plot_top), int(plot_right), int(plot_bottom))
    draw.rectangle(plot_bbox, fill=render_params.plot_fill_rgb)

    plot_width = float(max(1, int(plot_right) - int(plot_left)))
    panel_gap = float(max(42.0, min(82.0, 0.075 * float(plot_width))))
    panel_width = float(max(1.0, (float(plot_width) - float(panel_gap)) / 2.0))
    left_panel = (
        int(plot_left),
        int(plot_top),
        int(round(float(plot_left) + float(panel_width))),
        int(plot_bottom),
    )
    right_panel = (
        int(round(float(plot_left) + float(panel_width) + float(panel_gap))),
        int(plot_top),
        int(plot_right),
        int(plot_bottom),
    )

    boxplot_values: List[int] = []
    for spec in [*before_boxplots, *after_boxplots]:
        boxplot_values.extend([int(spec.whisker_min), int(spec.q1), int(spec.median), int(spec.q3), int(spec.whisker_max)])
    y_axis_min, y_axis_max, y_ticks, y_minor_ticks, value_axis_window_enabled = _resolve_value_axis(
        boxplot_values,
        render_params=render_params,
    )
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    axis_color = tuple(int(value) for value in render_params.axis_color_rgb)
    grid_color = tuple(int(value) for value in render_params.grid_color_rgb)

    title_y = max(12.0, float(plot_top) - float(max(18, int(render_params.label_font_size_px))))
    for panel_bbox, title in ((left_panel, before_title), (right_panel, after_title)):
        panel_left, _, panel_right, _ = panel_bbox
        draw_text_centered(
            draw,
            text=str(title),
            center=(0.5 * (float(panel_left) + float(panel_right)), float(title_y)),
            font=label_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=int(render_params.label_stroke_width_px),
        )

    major_tick_values = set(int(value) for value in y_ticks)
    for tick_value in y_minor_ticks:
        y_px = _tick_y(
            int(tick_value),
            y_axis_min=int(y_axis_min),
            y_axis_max=int(y_axis_max),
            plot_top=int(plot_top),
            plot_bottom=int(plot_bottom),
        )
        for panel_bbox in (left_panel, right_panel):
            panel_left, _, panel_right, _ = panel_bbox
            draw.line(
                [(float(panel_left), float(y_px)), (float(panel_right), float(y_px))],
                fill=grid_color,
                width=int(render_params.grid_line_width_px),
            )
        if int(tick_value) in major_tick_values:
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

    for panel_bbox in (left_panel, right_panel):
        panel_left, panel_top, panel_right, panel_bottom = panel_bbox
        draw.line(
            [(float(panel_left), float(panel_top)), (float(panel_left), float(panel_bottom))],
            fill=axis_color,
            width=int(render_params.axis_line_width_px),
        )
        draw.line(
            [(float(panel_left), float(panel_bottom)), (float(panel_right), float(panel_bottom))],
            fill=axis_color,
            width=int(render_params.axis_line_width_px),
        )

    mark_traces: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    guide_lines: List[Dict[str, Any]] = []
    draw_guides = _guide_lines_enabled(render_params)

    def _draw_panel_boxplots(
        *,
        panel_id: str,
        panel_title: str,
        panel_rank: int,
        panel_bbox: Tuple[int, int, int, int],
        specs: Sequence[BoxPlotSpec],
    ) -> None:
        panel_left, panel_top, panel_right, panel_bottom = panel_bbox
        centers = _slot_centers(count=len(specs), plot_left=int(panel_left), plot_right=int(panel_right))
        slot_width = float(max(1.0, (float(panel_right) - float(panel_left)) / max(1, len(specs))))
        box_width = float(max(18.0, float(render_params.bar_width_fraction) * float(slot_width)))
        whisker_cap = float(max(14.0, 0.55 * float(box_width)))
        for index, spec in enumerate(specs):
            display_label = str(spec.label)
            trace_label = f"{display_label}__{str(panel_id)}"
            x_center = float(centers[index])
            y_whisker_min = _tick_y(int(spec.whisker_min), y_axis_min=int(y_axis_min), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))
            y_q1 = _tick_y(int(spec.q1), y_axis_min=int(y_axis_min), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))
            y_median = _tick_y(int(spec.median), y_axis_min=int(y_axis_min), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))
            y_q3 = _tick_y(int(spec.q3), y_axis_min=int(y_axis_min), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))
            y_whisker_max = _tick_y(int(spec.whisker_max), y_axis_min=int(y_axis_min), y_axis_max=int(y_axis_max), plot_top=int(plot_top), plot_bottom=int(plot_bottom))

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
            if bool(draw_guides):
                guide_points = [(float(panel_left), float(y_median)), (float(x_center), float(y_median))]
                _draw_styled_line(
                    draw,
                    guide_points,
                    fill=render_params.guide_line_color_rgb,
                    width=int(render_params.guide_line_width_px),
                    style=str(render_params.guide_line_style),
                )
                guide_lines.append(
                    {
                        "entity_id": f"boxplot_{trace_label}",
                        "label": str(trace_label),
                        "display_label": str(display_label),
                        "panel": str(panel_id),
                        "panel_title": str(panel_title),
                        "value": int(spec.median),
                        "stat": "median",
                        "orientation": "horizontal",
                        "points_px": [[round(float(x), 3), round(float(y), 3)] for x, y in guide_points],
                        "style": str(render_params.guide_line_style),
                    }
                )

            label_center = (
                float(x_center),
                float(plot_bottom) + float(max(18, int(render_params.label_font_size_px) + 6)),
            )
            draw_text_centered(
                draw,
                text=str(display_label),
                center=label_center,
                font=label_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=int(render_params.label_stroke_width_px),
            )
            label_bbox = _text_bbox(draw, text=str(display_label), center=label_center, font=label_font)
            mark_bbox = (
                float(box_bbox[0]),
                float(min(y_whisker_max, y_whisker_min)),
                float(box_bbox[2]),
                float(max(y_whisker_max, y_whisker_min)),
            )
            mark_center = (float(x_center), float(0.5 * (float(box_bbox[1]) + float(box_bbox[3]))))
            mark_trace = {
                "entity_id": f"boxplot_{trace_label}",
                "label": str(trace_label),
                "display_label": str(display_label),
                "panel": str(panel_id),
                "panel_title": str(panel_title),
                "panel_rank": int(panel_rank),
                "value": int(spec.median),
                "x_rank": int(index),
                "whisker_min": int(spec.whisker_min),
                "q1": int(spec.q1),
                "median": int(spec.median),
                "q3": int(spec.q3),
                "whisker_max": int(spec.whisker_max),
                "panel_bbox_px": [int(value) for value in panel_bbox],
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
                        "label": str(trace_label),
                        "display_label": str(display_label),
                        "panel": str(panel_id),
                        "panel_title": str(panel_title),
                        "panel_rank": int(panel_rank),
                        "x_rank": int(index),
                        "scene_variant": "boxplot",
                        "whisker_min": int(spec.whisker_min),
                        "q1": int(spec.q1),
                        "median": int(spec.median),
                        "q3": int(spec.q3),
                        "whisker_max": int(spec.whisker_max),
                        "panel_bbox_px": list(mark_trace["panel_bbox_px"]),
                        "mark_center_px": list(mark_trace["mark_center_px"]),
                        "mark_bbox_px": list(mark_trace["mark_bbox_px"]),
                        "label_center_px": list(mark_trace["label_center_px"]),
                        "mark_fill_rgb": list(mark_trace["mark_fill_rgb"]),
                        "mark_outline_rgb": list(mark_trace["mark_outline_rgb"]),
                    },
                }
            )

    _draw_panel_boxplots(
        panel_id="before",
        panel_title=str(before_title),
        panel_rank=0,
        panel_bbox=left_panel,
        specs=before_boxplots,
    )
    _draw_panel_boxplots(
        panel_id="after",
        panel_title=str(after_title),
        panel_rank=1,
        panel_bbox=right_panel,
        specs=after_boxplots,
    )

    return RenderedChartScene(
        image=image,
        mark_traces=tuple(dict(item) for item in mark_traces),
        entities=tuple(dict(item) for item in entities),
        plot_bbox_px=tuple(int(value) for value in plot_bbox),
        y_axis_max=int(y_axis_max),
        y_ticks=tuple(int(value) for value in y_ticks),
        scene_variant="boxplot",
        value_axis_min=int(y_axis_min),
        value_axis_max=int(y_axis_max),
        value_axis_span=int(y_axis_max) - int(y_axis_min),
        value_axis_major_ticks=tuple(int(value) for value in y_ticks),
        value_axis_minor_ticks=tuple(int(value) for value in y_minor_ticks),
        value_axis_window_enabled=bool(value_axis_window_enabled),
        guide_line_style=str(render_params.guide_line_style if guide_lines else "none"),
        guide_lines=tuple(dict(item) for item in guide_lines),
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
    y_ticks = _axis_ticks(y_axis_max)
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
    width_scale = max(0.72, min(1.25, float(render_params.violin_width_scale)))
    smoothing_scale = max(0.70, min(1.35, float(render_params.violin_smoothing_scale)))
    fill_style = str(render_params.violin_fill_style).strip().lower()
    if fill_style not in {"solid", "light", "outline", "hatch"}:
        fill_style = "solid"
    mode_line_style = str(render_params.violin_mode_line_style).strip().lower()
    if mode_line_style not in {"full", "short", "dot", "none"}:
        mode_line_style = "full"
    palette_mode = str(render_params.violin_palette_mode).strip().lower()
    if palette_mode not in {"single", "per_violin_muted"}:
        palette_mode = "single"
    half_width = float(max(16.0, 0.44 * float(slot_width) * float(width_scale)))

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
        if palette_mode == "per_violin_muted":
            fill_rgb = _violin_palette_color(
                tuple(int(value) for value in render_params.mark_fill_rgb),
                index=int(index),
                offset=int(render_params.violin_palette_offset),
                plot_fill=tuple(int(value) for value in render_params.plot_fill_rgb),
            )
            outline_rgb = _darken_rgb(fill_rgb, 0.54)

        def _width_fraction(value: float) -> float:
            total = 0.16
            for mode in mode_values:
                sigma = max(0.9, 0.16 * float(support_span) * float(smoothing_scale))
                delta = (float(value) - float(mode)) / float(sigma)
                total += 0.52 * math.exp(-0.5 * float(delta * delta))
            if len(mode_values) >= 2:
                valley_center = 0.5 * float(mode_values[0] + mode_values[-1])
                valley_sigma = max(0.8, 0.12 * float(support_span) * float(smoothing_scale))
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
        _draw_violin_polygon(
            image,
            points=polygon_points,
            fill_rgb=fill_rgb,
            outline_rgb=outline_rgb,
            fill_style=str(fill_style),
            outline_width=int(render_params.mark_outline_width_px),
            plot_fill_rgb=tuple(int(value) for value in render_params.plot_fill_rgb),
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
            if mode_line_style == "short":
                draw.line(
                    [(float(x_center - 0.34 * mode_width), float(mode_y)), (float(x_center + 0.34 * mode_width), float(mode_y))],
                    fill=outline_rgb,
                    width=max(1, int(render_params.line_width_px) - 2),
                )
            elif mode_line_style == "dot":
                radius = max(2.0, 0.38 * float(render_params.point_radius_px))
                draw.ellipse(
                    [
                        float(x_center - radius),
                        float(mode_y - radius),
                        float(x_center + radius),
                        float(mode_y + radius),
                    ],
                    fill=outline_rgb,
                    outline=outline_rgb,
                )
            elif mode_line_style == "full":
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
            "violin_fill_style": str(fill_style),
            "violin_mode_line_style": str(mode_line_style),
            "violin_width_scale": round(float(width_scale), 4),
            "violin_smoothing_scale": round(float(smoothing_scale), 4),
            "violin_palette_mode": str(palette_mode),
            "violin_palette_offset": int(render_params.violin_palette_offset),
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
                    "violin_fill_style": str(mark_trace["violin_fill_style"]),
                    "violin_mode_line_style": str(mark_trace["violin_mode_line_style"]),
                    "violin_width_scale": float(mark_trace["violin_width_scale"]),
                    "violin_smoothing_scale": float(mark_trace["violin_smoothing_scale"]),
                    "violin_palette_mode": str(mark_trace["violin_palette_mode"]),
                    "violin_palette_offset": int(mark_trace["violin_palette_offset"]),
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
    "render_paired_boxplot_scene",
    "render_violin_scene",
    "resolve_chart_render_params",
    "value_axis_render_metadata",
]
