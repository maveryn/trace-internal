"""Rendering helpers for parallel-coordinates chart tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw

from ....shared.bbox_projection import bbox_union as _bbox_union, round_bbox as _bbox
from ....shared.text_legibility import draw_text_traced
from ....shared.text_rendering import load_font
from .profile_common import BBox, _Dataset, _RenderParams, _Rendered

def _text_bbox(draw: ImageDraw.ImageDraw, xy: Tuple[float, float], text: str, font: Any, *, stroke_width: int = 0) -> BBox:
    box = draw.textbbox(tuple(float(value) for value in xy), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    return _bbox([box[0], box[1], box[2], box[3]])

def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    *,
    fill: RGB,
    stroke_fill: RGB,
    stroke_width: int = 0,
) -> BBox:
    box = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    width = float(box[2] - box[0])
    height = float(box[3] - box[1])
    x = float(xy[0]) - width / 2.0
    y = float(xy[1]) - height / 2.0
    draw_text_traced(
        draw,
        (x, y),
        str(text),
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=max(0, int(stroke_width)),
     role="readout", required=False,)
    return _bbox([x, y, x + width, y + height])

def _render_parallel_coordinates(background: Image.Image, *, dataset: _Dataset, render_params: _RenderParams) -> _Rendered:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    panel_margin = 34
    left = float(render_params.plot_margin_left_px)
    right = float(width - int(render_params.plot_margin_right_px))
    top = float(render_params.plot_margin_top_px)
    bottom = float(height - int(render_params.plot_margin_bottom_px))
    plot_bbox = _bbox([left, top, right, bottom])
    panel_bbox = [panel_margin, 36, width - panel_margin, height - 42]
    draw.rounded_rectangle(panel_bbox, radius=8, fill=render_params.panel_fill_rgb, outline=render_params.panel_border_rgb, width=1)
    draw.rectangle([left, top, right, bottom], fill=render_params.plot_fill_rgb)

    title_font = load_font(render_params.title_font_size_px, bold=True)
    label_font = load_font(render_params.label_font_size_px, bold=True)
    tick_font = load_font(render_params.tick_font_size_px, bold=False)
    threshold_font = load_font(render_params.threshold_font_size_px, bold=True)
    draw_text_traced(draw, (panel_margin + 22, 50), "Profile Comparison", font=title_font, fill=render_params.text_rgb, role="readout", required=False)

    value_min = int(dataset.query.params["value_min"])
    value_max = int(dataset.query.params["value_max"])

    def y_px(value: float) -> float:
        ratio = (float(value) - float(value_min)) / max(1.0, float(value_max) - float(value_min))
        return bottom - (ratio * (bottom - top))

    axis_count = len(dataset.metrics)
    axis_x: Dict[int, float] = {}
    for axis_index in range(axis_count):
        x = left + (float(axis_index) * (right - left) / max(1, axis_count - 1))
        axis_x[int(axis_index)] = float(x)

    tick_values = [value_min, int(round((value_min + value_max) / 2.0)), value_max]
    for tick in tick_values:
        y = y_px(float(tick))
        draw.line([left, y, right, y], fill=render_params.grid_rgb, width=render_params.grid_line_width_px)
        draw_text_traced(
            draw,
            (left - 46, y - 9),
            str(int(tick)),
            font=tick_font,
            fill=render_params.muted_text_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
         role="readout", required=False,)

    selected_axes = {int(dataset.query.axis_i), int(dataset.query.axis_j)}
    threshold_bboxes: Dict[int, BBox] = {}
    for axis_index, metric in enumerate(dataset.metrics):
        x = axis_x[int(axis_index)]
        selected = int(axis_index) in selected_axes
        axis_rgb = render_params.selected_axis_rgb if selected else render_params.axis_rgb
        axis_width = render_params.selected_axis_line_width_px if selected else render_params.axis_line_width_px
        draw.line([x, top, x, bottom], fill=axis_rgb, width=axis_width)
        _draw_centered_text(
            draw,
            (x, bottom + 34),
            str(metric),
            label_font,
            fill=render_params.text_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
        for tick in tick_values:
            y = y_px(float(tick))
            draw.line([x - 5, y, x + 5, y], fill=axis_rgb, width=2)
        if dataset.query.threshold is not None and selected:
            y = y_px(float(dataset.query.threshold))
            draw.line([x - 22, y, x + 22, y], fill=render_params.threshold_rgb, width=3)
            text_bbox = _text_bbox(draw, (x + 26, y - 9), str(dataset.query.threshold), threshold_font, stroke_width=1)
            draw_text_traced(
                draw,
                (x + 26, y - 9),
                str(dataset.query.threshold),
                font=threshold_font,
                fill=render_params.threshold_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=1,
             role="readout", required=False,)
            threshold_bboxes[int(axis_index)] = _bbox_union([[x - 22, y - 2, x + 22, y + 2], text_bbox], padding=2)

    point_bboxes: Dict[str, BBox] = {}
    segment_bboxes: Dict[str, BBox] = {}
    profile_bboxes: Dict[str, BBox] = {}
    label_bboxes: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []
    radius = float(render_params.point_radius_px)

    # Draw less emphasized lines first so labels and points stay legible.
    for profile in dataset.profiles:
        points = [(axis_x[index], y_px(profile.values[index])) for index in range(axis_count)]
        line_rgb = tuple(int(c) for c in profile.color_rgb)
        draw.line(points, fill=line_rgb, width=render_params.line_width_px, joint="curve")
        profile_segment_boxes: List[BBox] = []
        for axis_index in range(axis_count):
            x, y = points[int(axis_index)]
            point_box = _bbox([x - radius, y - radius, x + radius, y + radius])
            point_bboxes[f"{profile.profile_id}:axis_{axis_index}"] = point_box
            draw.ellipse(point_box, fill=line_rgb, outline=(255, 255, 255), width=2)
        for axis_index in range(axis_count - 1):
            x0, y0 = points[int(axis_index)]
            x1, y1 = points[int(axis_index) + 1]
            seg_box = _bbox([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)])
            padded = _bbox_union([seg_box], padding=8)
            segment_bboxes[f"{profile.profile_id}:axis_{axis_index}_{axis_index + 1}"] = padded
            profile_segment_boxes.append(padded)
        label_left_xy = (left - 74, points[0][1] - 10)
        label_right_xy = (right + 48, points[-1][1] - 10)
        for suffix, xy in (("left", label_left_xy), ("right", label_right_xy)):
            box = _text_bbox(draw, xy, profile.label, label_font, stroke_width=2)
            draw_text_traced(
                draw,
                xy,
                profile.label,
                font=label_font,
                fill=line_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=2,
             role="readout", required=False,)
            label_bboxes[f"{profile.profile_id}:{suffix}"] = box
        profile_bboxes[profile.profile_id] = _bbox_union(
            profile_segment_boxes
            + [point_bboxes[f"{profile.profile_id}:axis_{index}"] for index in range(axis_count)]
            + [label_bboxes[f"{profile.profile_id}:left"], label_bboxes[f"{profile.profile_id}:right"]],
            padding=4,
        )
        entities.append(
            {
                "entity_id": profile.profile_id,
                "entity_type": "parallel_coordinate_profile",
                "label": profile.label,
                "values": [int(value) for value in profile.values],
                "color_rgb": list(line_rgb),
                "bbox_px": list(profile_bboxes[profile.profile_id]),
            }
        )

    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=list(plot_bbox),
        axis_x_px={int(k): float(v) for k, v in axis_x.items()},
        point_bboxes_px=dict(point_bboxes),
        segment_bboxes_px=dict(segment_bboxes),
        profile_bboxes_px=dict(profile_bboxes),
        label_bboxes_px=dict(label_bboxes),
        threshold_bboxes_px=dict(threshold_bboxes),
    )
