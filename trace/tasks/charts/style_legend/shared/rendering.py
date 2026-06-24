"""Rendering helpers for the style-legend chart scene."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from PIL import ImageDraw, ImageFont

from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.render_variation import apply_layout_jitter_to_margins
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font

from .defaults import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    RENDER_DEFAULTS,
    gen_int,
    render_style_seed,
    resolve_int,
    resolve_rgb,
)
from .state import BBox, Point, RGB, SCENE_NAMESPACE, RenderParams, RenderedStyleLegend, StyleLegendDataset, bbox, point, point_id


def resolve_render_params(params: Mapping[str, Any], *, chart_font_family: str) -> RenderParams:
    """Resolve all scene-level render knobs before drawing any chart marks."""

    canvas_width = resolve_int(params, "style_legend_canvas_width", resolve_int(params, "canvas_width", 1280))
    canvas_height = resolve_int(params, "style_legend_canvas_height", resolve_int(params, "canvas_height", 820))
    margins = {
        "left": resolve_int(params, "style_legend_margin_left_px", 88),
        "right": resolve_int(params, "style_legend_margin_right_px", 210),
        "top": resolve_int(params, "style_legend_margin_top_px", 92),
        "bottom": resolve_int(params, "style_legend_margin_bottom_px", 104),
    }
    left_px, right_px, top_px, bottom_px, jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margins["left"]),
        right_px=int(margins["right"]),
        top_px=int(margins["top"]),
        bottom_px=int(margins["bottom"]),
        params=params,
        defaults=RENDER_DEFAULTS,
        instance_seed=render_style_seed(params),
        namespace=SCENE_NAMESPACE,
    )
    return RenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        margin_left_px=int(left_px),
        margin_right_px=int(right_px),
        margin_top_px=int(top_px),
        margin_bottom_px=int(bottom_px),
        title_font_size_px=resolve_int(params, "style_legend_title_font_size_px", 25),
        tick_font_size_px=resolve_int(params, "style_legend_tick_font_size_px", 14),
        label_font_size_px=resolve_int(params, "style_legend_label_font_size_px", 15),
        legend_font_size_px=resolve_int(params, "style_legend_legend_font_size_px", 15),
        axis_line_width_px=resolve_int(params, "style_legend_axis_line_width_px", 2),
        grid_line_width_px=resolve_int(params, "style_legend_grid_line_width_px", 1),
        point_radius_px=resolve_int(params, "style_legend_point_radius_px", 6),
        text_rgb=resolve_rgb(params, "style_legend_text_rgb", (38, 44, 54)),
        muted_text_rgb=resolve_rgb(params, "style_legend_muted_text_rgb", (88, 96, 110)),
        text_stroke_rgb=resolve_rgb(params, "style_legend_text_stroke_rgb", (255, 255, 255)),
        axis_rgb=resolve_rgb(params, "style_legend_axis_rgb", (52, 58, 68)),
        grid_rgb=resolve_rgb(params, "style_legend_grid_rgb", (218, 224, 232)),
        panel_fill_rgb=resolve_rgb(params, "style_legend_panel_fill_rgb", (255, 255, 255)),
        panel_outline_rgb=resolve_rgb(params, "style_legend_panel_outline_rgb", (190, 199, 214)),
        threshold_rgb=resolve_rgb(params, "style_legend_threshold_rgb", (146, 71, 62)),
        font_family=str(chart_font_family),
        layout_jitter_meta=dict(jitter_meta),
    )


def text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    *,
    stroke_width: int = 0,
) -> BBox:
    try:
        box = draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        return bbox(list(box))
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        return bbox([float(xy[0]), float(xy[1]), float(xy[0]) + float(width), float(xy[1]) + float(height)])


def draw_centered(
    draw: ImageDraw.ImageDraw,
    *,
    center: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: RGB,
    stroke_fill: RGB,
    stroke_width: int,
) -> BBox:
    try:
        box = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        width = float(box[2] - box[0])
        height = float(box[3] - box[1])
        x = float(center[0]) - 0.5 * width - float(box[0])
        y = float(center[1]) - 0.5 * height - float(box[1])
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        x = float(center[0]) - 0.5 * float(width)
        y = float(center[1]) - 0.5 * float(height)
    draw_text_traced(
        draw,
        (float(x), float(y)),
        str(text),
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=max(0, int(stroke_width)),
        role="readout",
        required=False,
    )
    return text_bbox(draw, (float(x), float(y)), str(text), font, stroke_width=max(0, int(stroke_width)))


def line_segments_for_style(style: str, *, width: int) -> tuple[tuple[float, float], ...]:
    resolved = str(style)
    if resolved == "dotted":
        return ((0.0, max(5.0, float(width) * 4.5)),)
    if resolved == "dashdot":
        return ((max(12.0, float(width) * 7.0), max(5.0, float(width) * 3.5)), (0.0, max(5.0, float(width) * 3.5)))
    if resolved == "long_dash":
        return ((max(20.0, float(width) * 11.0), max(8.0, float(width) * 5.0)),)
    if resolved == "short_dash":
        return ((max(8.0, float(width) * 4.5), max(5.0, float(width) * 3.0)),)
    return ((max(14.0, float(width) * 8.0), max(6.0, float(width) * 4.0)),)


def draw_styled_segment(
    draw: ImageDraw.ImageDraw,
    p0: tuple[float, float],
    p1: tuple[float, float],
    *,
    fill: RGB,
    width: int,
    style: str,
) -> None:
    """Draw one visible line segment while preserving the sampled line pattern."""

    if str(style) == "solid":
        draw.line([p0, p1], fill=fill, width=max(1, int(width)))
        return
    x0, y0 = float(p0[0]), float(p0[1])
    x1, y1 = float(p1[0]), float(p1[1])
    dx = x1 - x0
    dy = y1 - y0
    length = math.hypot(dx, dy)
    if length <= 0.0:
        return
    ux = dx / length
    uy = dy / length
    cursor = 0.0
    pattern = line_segments_for_style(str(style), width=max(1, int(width)))
    pattern_index = 0
    while cursor <= length:
        draw_len, gap_len = pattern[int(pattern_index) % len(pattern)]
        if draw_len <= 0.0:
            radius = max(1.0, float(width) * 0.8)
            cx = x0 + ux * cursor
            cy = y0 + uy * cursor
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=fill)
            cursor += float(gap_len)
        else:
            end = min(length, cursor + draw_len)
            draw.line(
                [(x0 + ux * cursor, y0 + uy * cursor), (x0 + ux * end, y0 + uy * end)],
                fill=fill,
                width=max(1, int(width)),
            )
            cursor = end + float(gap_len)
        pattern_index += 1


def draw_styled_polyline(
    draw: ImageDraw.ImageDraw,
    points: Sequence[tuple[float, float]],
    *,
    fill: RGB,
    width: int,
    style: str,
) -> None:
    for p0, p1 in zip(points, points[1:]):
        draw_styled_segment(draw, p0, p1, fill=fill, width=int(width), style=str(style))


def draw_marker(
    draw: ImageDraw.ImageDraw,
    *,
    center: tuple[float, float],
    radius: float,
    shape: str,
    fill: RGB,
    outline: RGB,
    marker_fill: str,
    width: int = 2,
) -> BBox:
    cx, cy = float(center[0]), float(center[1])
    r = float(radius)
    marker_bbox = [cx - r, cy - r, cx + r, cy + r]
    resolved_fill = fill if str(marker_fill) == "filled" else (255, 255, 255)
    if str(shape) == "square":
        draw.rectangle(marker_bbox, fill=resolved_fill, outline=outline, width=max(1, int(width)))
    elif str(shape) == "diamond":
        draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=resolved_fill, outline=outline)
        draw.line([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy), (cx, cy - r)], fill=outline, width=max(1, int(width)))
    elif str(shape) == "triangle":
        draw.polygon([(cx, cy - r), (cx + r, cy + r), (cx - r, cy + r)], fill=resolved_fill, outline=outline)
        draw.line([(cx, cy - r), (cx + r, cy + r), (cx - r, cy + r), (cx, cy - r)], fill=outline, width=max(1, int(width)))
    elif str(shape) == "ring":
        draw.ellipse(marker_bbox, fill=(255, 255, 255), outline=outline, width=max(2, int(width) + 1))
    elif str(shape) == "cross":
        draw.line([(cx - r, cy - r), (cx + r, cy + r)], fill=outline, width=max(2, int(width)))
        draw.line([(cx - r, cy + r), (cx + r, cy - r)], fill=outline, width=max(2, int(width)))
    else:
        draw.ellipse(marker_bbox, fill=resolved_fill, outline=outline, width=max(1, int(width)))
    return bbox(marker_bbox)


def value_to_y(value: int, *, plot_top: float, plot_bottom: float, value_min: int, value_max: int) -> float:
    span = max(1, int(value_max) - int(value_min))
    return float(plot_bottom) - ((float(value) - float(value_min)) / float(span)) * float(plot_bottom - plot_top)


def x_to_pixel(index: int, *, plot_left: float, plot_right: float, x_count: int) -> float:
    if int(x_count) <= 1:
        return 0.5 * float(plot_left + plot_right)
    return float(plot_left) + (float(index) / float(int(x_count) - 1)) * float(plot_right - plot_left)


def union_bboxes(boxes: Sequence[Sequence[float]]) -> BBox:
    clean = [tuple(float(value) for value in box[:4]) for box in boxes if len(box) >= 4]
    if not clean:
        return []
    return bbox([min(box[0] for box in clean), min(box[1] for box in clean), max(box[2] for box in clean), max(box[3] for box in clean)])


def render_legend(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: StyleLegendDataset,
    render_params: RenderParams,
    plot_bbox: Sequence[float],
    font: ImageFont.ImageFont,
) -> tuple[BBox, dict[str, BBox]]:
    """Render legend swatches with the same line and marker styles as the plot."""

    plot_left, plot_top, plot_right, _plot_bottom = [float(value) for value in plot_bbox]
    row_height = max(30.0, float(render_params.legend_font_size_px) + 15.0)
    swatch_width = 58.0
    swatch_height = 20.0
    pad = 10.0
    if str(dataset.legend_position) == "top":
        left = float(plot_left)
        top = max(8.0, float(plot_top) - row_height - 14.0)
        column_width = max(160.0, (float(plot_right) - float(plot_left)) / max(1, len(dataset.series)))
    elif str(dataset.legend_position) == "inside_top_right":
        column_width = 162.0
        left = float(plot_right) - column_width - 12.0
        top = float(plot_top) + 12.0
    else:
        column_width = 170.0
        left = float(plot_right) + 30.0
        top = float(plot_top) + 10.0

    row_bboxes: dict[str, BBox] = {}
    all_boxes: list[BBox] = []
    if str(dataset.legend_position) == "top":
        for index, series in enumerate(dataset.series):
            x0 = float(left) + float(index) * float(column_width)
            y0 = float(top)
            swatch_y = float(y0 + 0.5 * row_height)
            swatch_x0 = float(x0 + pad)
            swatch_x1 = float(swatch_x0 + swatch_width)
            draw_styled_segment(
                draw,
                (swatch_x0, swatch_y),
                (swatch_x1, swatch_y),
                fill=series.style.color_rgb,
                width=int(series.style.line_width_px),
                style=str(series.style.line_style),
            )
            draw_marker(
                draw,
                center=(0.5 * (swatch_x0 + swatch_x1), swatch_y),
                radius=max(4.0, 0.78 * float(render_params.point_radius_px)),
                shape=str(series.style.marker_shape),
                fill=series.style.color_rgb,
                outline=series.style.color_rgb,
                marker_fill=str(series.style.marker_fill),
                width=2,
            )
            label_x = float(swatch_x1 + 9.0)
            label_y = float(swatch_y - 0.5 * float(render_params.legend_font_size_px))
            draw_text_traced(draw, (label_x, label_y), str(series.label), font=font, fill=render_params.text_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1, role="readout", required=False)
            label_bbox = text_bbox(draw, (label_x, label_y), str(series.label), font, stroke_width=1)
            row_bbox = union_bboxes(([swatch_x0, swatch_y - swatch_height, swatch_x1, swatch_y + swatch_height], label_bbox))
            row_bboxes[str(series.series_id)] = row_bbox
            all_boxes.append(row_bbox)
    else:
        frame_height = float(len(dataset.series)) * float(row_height) + 2.0 * pad
        frame_width = float(column_width) + 2.0 * pad
        frame_bbox = [left - pad, top - pad, left + frame_width, top + frame_height]
        draw.rounded_rectangle(frame_bbox, radius=5, fill=render_params.panel_fill_rgb, outline=render_params.panel_outline_rgb, width=1)
        all_boxes.append(bbox(frame_bbox))
        for index, series in enumerate(dataset.series):
            y0 = float(top) + float(index) * float(row_height)
            swatch_y = float(y0 + 0.5 * row_height)
            swatch_x0 = float(left)
            swatch_x1 = float(left + swatch_width)
            draw_styled_segment(
                draw,
                (swatch_x0, swatch_y),
                (swatch_x1, swatch_y),
                fill=series.style.color_rgb,
                width=int(series.style.line_width_px),
                style=str(series.style.line_style),
            )
            draw_marker(
                draw,
                center=(0.5 * (swatch_x0 + swatch_x1), swatch_y),
                radius=max(4.0, 0.78 * float(render_params.point_radius_px)),
                shape=str(series.style.marker_shape),
                fill=series.style.color_rgb,
                outline=series.style.color_rgb,
                marker_fill=str(series.style.marker_fill),
                width=2,
            )
            label_x = float(swatch_x1 + 12.0)
            label_y = float(swatch_y - 0.5 * float(render_params.legend_font_size_px))
            draw_text_traced(draw, (label_x, label_y), str(series.label), font=font, fill=render_params.text_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1, role="readout", required=False)
            label_bbox = text_bbox(draw, (label_x, label_y), str(series.label), font, stroke_width=1)
            row_bbox = union_bboxes(([swatch_x0, swatch_y - swatch_height, swatch_x1, swatch_y + swatch_height], label_bbox))
            row_bboxes[str(series.series_id)] = row_bbox
            all_boxes.append(row_bbox)
    return union_bboxes(all_boxes), dict(row_bboxes)


def render_dataset(
    dataset: StyleLegendDataset,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    chart_font_family: str,
) -> RenderedStyleLegend:
    """Render a sampled style-legend dataset without owning any public objective."""

    render_params = resolve_render_params(params, chart_font_family=str(chart_font_family))
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        fallback_color=(247, 248, 250),
    )
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    legend_font = load_font(int(render_params.legend_font_size_px), bold=True)

    plot_left = float(render_params.margin_left_px)
    plot_top = float(render_params.margin_top_px)
    plot_right = float(render_params.canvas_width - render_params.margin_right_px)
    plot_bottom = float(render_params.canvas_height - render_params.margin_bottom_px)
    if str(dataset.legend_position) == "top":
        plot_top = max(float(plot_top), 150.0)
        plot_right = float(render_params.canvas_width - 72)
    if str(dataset.legend_position) == "inside_top_right":
        plot_right = float(render_params.canvas_width - 72)
    plot_bbox = bbox([plot_left, plot_top, plot_right, plot_bottom])
    draw.rectangle(plot_bbox, fill=render_params.panel_fill_rgb, outline=render_params.panel_outline_rgb, width=1)

    title_options = params.get("style_legend_title_options", group_default(RENDER_DEFAULTS, "style_legend_title_options", ("Scientific Series Comparison",)))
    titles = tuple(str(value) for value in title_options) if isinstance(title_options, Sequence) and not isinstance(title_options, (str, bytes)) else ("Scientific Series Comparison",)
    title = str(balanced_title_choice(titles, params, instance_seed=int(instance_seed)))
    if title:
        title_y = 58.0 if str(dataset.legend_position) == "top" else max(24.0, plot_top - 43.0)
        draw_centered(
            draw,
            center=(0.5 * (plot_left + plot_right), float(title_y)),
            text=str(title),
            font=title_font,
            fill=render_params.text_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )

    value_min = int(gen_int(params, "style_legend_value_min", 0))
    value_max = int(gen_int(params, "style_legend_value_max", 100))
    tick_step = int(gen_int(params, "style_legend_tick_step", 20))
    for tick in range(int(value_min), int(value_max) + 1, max(1, int(tick_step))):
        y = value_to_y(int(tick), plot_top=plot_top, plot_bottom=plot_bottom, value_min=int(value_min), value_max=int(value_max))
        draw.line([(plot_left, y), (plot_right, y)], fill=render_params.grid_rgb, width=int(render_params.grid_line_width_px))
        draw.line([(plot_left - 6, y), (plot_left, y)], fill=render_params.axis_rgb, width=int(render_params.axis_line_width_px))
        draw_centered(
            draw,
            center=(plot_left - 28.0, y),
            text=str(tick),
            font=tick_font,
            fill=render_params.muted_text_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
    draw.line([(plot_left, plot_top), (plot_left, plot_bottom)], fill=render_params.axis_rgb, width=int(render_params.axis_line_width_px))
    draw.line([(plot_left, plot_bottom), (plot_right, plot_bottom)], fill=render_params.axis_rgb, width=int(render_params.axis_line_width_px))

    x_points = [
        x_to_pixel(int(index), plot_left=plot_left, plot_right=plot_right, x_count=len(dataset.x_labels))
        for index in range(len(dataset.x_labels))
    ]
    for index, label in enumerate(dataset.x_labels):
        x = float(x_points[int(index)])
        draw.line([(x, plot_bottom), (x, plot_bottom + 6)], fill=render_params.axis_rgb, width=1)
        draw_centered(
            draw,
            center=(x, plot_bottom + 24.0),
            text=str(label),
            font=tick_font,
            fill=render_params.text_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )

    threshold_bbox: BBox | None = None
    if dataset.threshold_value is not None:
        y = value_to_y(int(dataset.threshold_value), plot_top=plot_top, plot_bottom=plot_bottom, value_min=int(value_min), value_max=int(value_max))
        draw_styled_segment(draw, (plot_left, y), (plot_right, y), fill=render_params.threshold_rgb, width=2, style="dashed")
        label = f"T={int(dataset.threshold_value)}"
        draw_text_traced(draw, (plot_right - 52.0, y - 20.0), label, font=tick_font, fill=render_params.threshold_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1, role="readout", required=False)
        threshold_bbox = text_bbox(draw, (plot_right - 52.0, y - 20.0), label, tick_font, stroke_width=1)

    point_map: dict[str, dict[str, Point]] = {}
    point_bboxes: dict[str, BBox] = {}
    entities: list[dict[str, Any]] = []
    for series in dataset.series:
        points: list[tuple[float, float]] = []
        series_point_map: dict[str, Point] = {}
        for x_index, value in enumerate(series.values):
            x = float(x_points[int(x_index)])
            y = value_to_y(int(value), plot_top=plot_top, plot_bottom=plot_bottom, value_min=int(value_min), value_max=int(value_max))
            points.append((x, y))
            series_point_map[str(dataset.x_labels[int(x_index)])] = point(x, y)
        draw_styled_polyline(
            draw,
            points,
            fill=series.style.color_rgb,
            width=int(series.style.line_width_px),
            style=str(series.style.line_style),
        )
        for x_index, marker_point in enumerate(points):
            marker_bbox = draw_marker(
                draw,
                center=marker_point,
                radius=float(render_params.point_radius_px),
                shape=str(series.style.marker_shape),
                fill=series.style.color_rgb,
                outline=series.style.color_rgb,
                marker_fill=str(series.style.marker_fill),
                width=2,
            )
            marker_id = point_id(str(series.series_id), int(x_index))
            point_bboxes[str(marker_id)] = marker_bbox
            entities.append(
                {
                    "entity_id": str(marker_id),
                    "entity_type": "style_legend_series_marker",
                    "bbox_px": list(marker_bbox),
                    "attrs": {
                        "series_id": str(series.series_id),
                        "series_label": str(series.label),
                        "x_label": str(dataset.x_labels[int(x_index)]),
                        "x_index": int(x_index),
                        "value": int(series.values[int(x_index)]),
                        "point_px": list(point(marker_point[0], marker_point[1])),
                        "line_style": str(series.style.line_style),
                        "marker_shape": str(series.style.marker_shape),
                        "marker_fill": str(series.style.marker_fill),
                        "color_rgb": [int(channel) for channel in series.style.color_rgb],
                    },
                }
            )
        point_map[str(series.series_id)] = dict(series_point_map)

    legend_bbox, legend_items = render_legend(
        draw,
        dataset=dataset,
        render_params=render_params,
        plot_bbox=plot_bbox,
        font=legend_font,
    )
    image, noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    render_meta = {
        "background_style": dict(background_meta),
        "post_image_noise": dict(noise_meta),
        "chart_font_family": str(chart_font_family),
        "style_palette_mode": str(dataset.palette_mode),
        "style_palette_mode_probabilities": dict(dataset.palette_mode_probabilities),
        "legend_position": str(dataset.legend_position),
        "legend_position_probabilities": dict(dataset.legend_position_probabilities),
        "layout_jitter": dict(render_params.layout_jitter_meta),
        "rendering_contract": "scientific_style_legend_line_chart",
    }
    return RenderedStyleLegend(
        image=image,
        entities=tuple(dict(entity) for entity in entities),
        plot_bbox_px=list(plot_bbox),
        legend_bbox_px=list(legend_bbox),
        legend_item_bboxes_px=dict(legend_items),
        point_map_px=dict(point_map),
        point_bboxes_px=dict(point_bboxes),
        threshold_bbox_px=threshold_bbox,
        render_meta=dict(render_meta),
    )


def balanced_title_choice(titles: Sequence[str], params: Mapping[str, Any], *, instance_seed: int) -> str:
    from .defaults import balanced_choice

    return str(balanced_choice(tuple(str(value) for value in titles), params, instance_seed=int(instance_seed), namespace=f"{SCENE_NAMESPACE}.title"))
