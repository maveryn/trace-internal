"""Rendering helpers for 3D bar-grid chart tasks."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from ...shared.bbox_projection import bbox_union as _bbox_union, round_bbox as _bbox
from ...shared.config_defaults import group_default
from ...shared.text_rendering import load_font
from ...shared.text_legibility import draw_text_traced
from .grid_common import BBox, RGB, _Dataset, _RENDER_DEFAULTS, _RenderParams, _RenderedBarGrid, _render_params


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
    draw_text_traced(draw,
        (float(xy[0]), float(xy[1])),
        str(text),
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=max(0, int(stroke_width)),
        **kwargs,
     role="readout", required=False,)
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


def _axis_max(max_value: int, *, tick_step: int) -> int:
    step = max(1, int(tick_step))
    return max(step, int(math.ceil(float(max_value) / float(step)) * step))


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
    annotation_set = set(str(bar_id) for bar_id in dataset.query.annotation_bar_ids)
    bar_traces: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    value_label_specs: List[Tuple[Tuple[float, float], str, BBox]] = []
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
        value_text = str(int(bar.value))
        value_stroke_width = max(1, int(render_params.label_stroke_width_px) + 1)
        value_bbox = _text_bbox(
            draw,
            label_xy,
            value_text,
            value_font,
            stroke_width=int(value_stroke_width),
            anchor="mb",
        )
        value_label_specs.append((label_xy, value_text, list(value_bbox)))
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
            "queried": bool(str(bar.bar_id) in annotation_set),
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

    for label_xy, value_text, _ in value_label_specs:
        _draw_text(
            draw,
            label_xy,
            value_text,
            font=value_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=max(1, int(render_params.label_stroke_width_px) + 1),
            anchor="mb",
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
