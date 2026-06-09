"""Rendering helpers for synthetic 3D chart panel tasks."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from ...shared.bbox_projection import bbox_union_raw as _bbox_union
from ...shared.config_defaults import group_default
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import fit_font_to_box, load_font
from .panel_common import (
    _RENDER_DEFAULTS,
    TASK_ID,
    BBox,
    RGB,
    _Dataset,
    _Point3D,
    _RenderParams,
    _Rendered,
    _bbox,
    _resolve_rgb,
    _render_style_seed,
)

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

def _resolve_render_params(params: Mapping[str, Any]) -> _RenderParams:
    def rint(key: str, fallback: int) -> int:
        return int(
            resolve_render_int(
                params,
                _RENDER_DEFAULTS,
                str(key),
                int(fallback),
                instance_seed=_render_style_seed(params),
                namespace=TASK_ID,
            )
        )

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
        point_radius_px=rint("point_radius_px", 7),
        line_width_px=rint("line_width_px", 3),
        axis_line_width_px=rint("axis_line_width_px", 2),
        grid_line_width_px=rint("grid_line_width_px", 1),
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
