"""Rendering helpers for radial Sankey chart tasks."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from .....core.seed import spawn_rng
from ....shared.bbox_projection import round_bbox as _round_bbox
from ....shared.drawing import draw_centered_text
from ....shared.text_rendering import fit_font_to_box, load_font
from .radial_sankey_common import (
    BBox,
    Point,
    TASK_ID,
    _RadialRenderParams,
    _RenderedRadialSankey,
    _clamp_bbox,
)


def _angle_point(center: Point, radius: float, angle_degrees: float) -> Point:
    theta = math.radians(float(angle_degrees))
    return (
        float(center[0] + (float(radius) * math.cos(theta))),
        float(center[1] + (float(radius) * math.sin(theta))),
    )


def _cubic_point(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    inv = 1.0 - float(t)
    x = (inv**3 * p0[0]) + (3 * inv * inv * t * p1[0]) + (3 * inv * t * t * p2[0]) + (t**3 * p3[0])
    y = (inv**3 * p0[1]) + (3 * inv * inv * t * p1[1]) + (3 * inv * t * t * p2[1]) + (t**3 * p3[1])
    return (float(x), float(y))


def _curve_points(start: Point, end: Point, center: Point, *, bend: float, steps: int = 44) -> List[Point]:
    c1 = (
        float(start[0] + (float(center[0] - start[0]) * float(bend))),
        float(start[1] + (float(center[1] - start[1]) * float(bend))),
    )
    c2 = (
        float(end[0] + (float(center[0] - end[0]) * float(bend))),
        float(end[1] + (float(center[1] - end[1]) * float(bend))),
    )
    return [
        _cubic_point(start, c1, c2, end, float(index) / float(max(1, int(steps) - 1)))
        for index in range(int(steps))
    ]


def _curve_bbox(points: Sequence[Point], *, stroke_width: int, canvas_width: int, canvas_height: int) -> List[float]:
    pad = max(2.0, 0.5 * float(stroke_width) + 2.0)
    return _clamp_bbox(
        (
            min(point[0] for point in points) - pad,
            min(point[1] for point in points) - pad,
            max(point[0] for point in points) + pad,
            max(point[1] for point in points) + pad,
        ),
        width=int(canvas_width),
        height=int(canvas_height),
    )


def _flow_width(value: int, *, render_params: _RadialRenderParams, value_min: int, value_max: int) -> int:
    if int(value_max) <= int(value_min):
        return int(render_params.min_flow_width_px)
    norm = (float(value) - float(value_min)) / float(value_max - value_min)
    width = float(render_params.min_flow_width_px) + (
        clamp_unit_interval(norm) * float(render_params.max_flow_width_px - render_params.min_flow_width_px)
    )
    return max(1, int(round(width)))


def _value_label_size(draw: ImageDraw.ImageDraw, *, text: str, render_params: _RadialRenderParams) -> Tuple[float, float]:
    font = load_font(int(render_params.value_label_font_size_px), bold=True)
    text_bbox = draw.textbbox((0, 0), str(text), font=font)
    text_width = float(text_bbox[2] - text_bbox[0])
    text_height = float(text_bbox[3] - text_bbox[1])
    return (max(38.0, float(text_width + 18.0)), max(28.0, float(text_height + 12.0)))


def _value_label_bbox(draw: ImageDraw.ImageDraw, *, text: str, center: Point, render_params: _RadialRenderParams) -> BBox:
    label_width, label_height = _value_label_size(draw, text=str(text), render_params=render_params)
    cx, cy = float(center[0]), float(center[1])
    return (
        float(cx - (0.5 * label_width)),
        float(cy - (0.5 * label_height)),
        float(cx + (0.5 * label_width)),
        float(cy + (0.5 * label_height)),
    )


def _draw_value_label(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Point,
    render_params: _RadialRenderParams,
) -> List[float]:
    font = load_font(int(render_params.value_label_font_size_px), bold=True)
    bbox = _value_label_bbox(draw, text=str(text), center=center, render_params=render_params)
    draw.rounded_rectangle(
        bbox,
        radius=8,
        fill=tuple(int(channel) for channel in render_params.value_label_fill_rgb),
        outline=tuple(int(channel) for channel in render_params.value_label_border_rgb),
        width=1,
    )
    draw_centered_text(
        draw,
        text=str(text),
        center=(float(center[0]), float(center[1])),
        font=font,
        fill=render_params.value_label_text_rgb,
        stroke_fill=render_params.value_label_fill_rgb,
        stroke_width=1,
    )
    return _round_bbox(bbox)


def _resolve_value_label_centers(
    draw: ImageDraw.ImageDraw,
    *,
    label_specs: Sequence[Mapping[str, Any]],
    plot_bbox: Sequence[float],
    render_params: _RadialRenderParams,
) -> Dict[str, Point]:
    group = sorted(
        [dict(spec) for spec in label_specs],
        key=lambda spec: (float(spec["desired_center"][1]), float(spec["desired_center"][0]), str(spec["link_id"])),
    )
    if not group:
        return {}
    top_limit = float(plot_bbox[1]) + 22.0
    bottom_limit = float(plot_bbox[3]) - 22.0
    available_height = max(1.0, float(bottom_limit - top_limit))
    heights = [_value_label_size(draw, text=str(spec["text"]), render_params=render_params)[1] for spec in group]
    total_label_height = sum(float(height) for height in heights)
    if len(group) > 1:
        effective_gap = min(
            float(render_params.value_label_gap_px),
            max(2.0, (available_height - total_label_height) / float(len(group) - 1)),
        )
    else:
        effective_gap = 0.0

    placed: List[Tuple[Dict[str, Any], float, float]] = []
    previous_bottom = float("-inf")
    for spec, height in zip(group, heights):
        half_height = 0.5 * float(height)
        desired_x, desired_y = [float(value) for value in spec["desired_center"]]
        min_center_y = float(top_limit + half_height)
        max_center_y = float(bottom_limit - half_height)
        center_y = max(min_center_y, min(max_center_y, float(desired_y)))
        if placed:
            center_y = max(float(center_y), float(previous_bottom + effective_gap + half_height))
        placed.append((spec, float(center_y), float(height)))
        previous_bottom = float(center_y + half_height)

    overflow = max(0.0, float(previous_bottom - bottom_limit))
    if overflow > 0.0:
        placed = [(spec, float(center_y - overflow), height) for spec, center_y, height in placed]
    first_top = float(placed[0][1] - (0.5 * placed[0][2]))
    underflow = max(0.0, float(top_limit - first_top))
    if underflow > 0.0:
        placed = [(spec, float(center_y + underflow), height) for spec, center_y, height in placed]

    resolved: Dict[str, Point] = {}
    for spec, center_y, _height in placed:
        desired_x = max(float(plot_bbox[0]) + 28.0, min(float(plot_bbox[2]) - 28.0, float(spec["desired_center"][0])))
        resolved[str(spec["link_id"])] = (float(desired_x), float(center_y))
    return resolved


def _node_angles(
    *,
    sources: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    instance_seed: int,
) -> Dict[str, float]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.node_angles")
    rotation = float(rng.choice([-12, -8, -4, 0, 4, 8, 12]))

    def _arc_angles(count: int, start: float, end: float) -> List[float]:
        if int(count) == 1:
            return [0.5 * (float(start) + float(end)) + float(rotation)]
        return [
            float(start + ((end - start) * float(index) / float(count - 1)) + float(rotation))
            for index in range(int(count))
        ]

    angles: Dict[str, float] = {}
    for node, angle in zip(sources, _arc_angles(len(sources), 132.0, 228.0)):
        angles[str(node["node_id"])] = float(angle)
    for node, angle in zip(targets, _arc_angles(len(targets), -48.0, 48.0)):
        angles[str(node["node_id"])] = float(angle)
    return angles


def _render_radial_sankey(
    background: Image.Image,
    *,
    scene_title: str,
    sources: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    links: Sequence[Mapping[str, Any]],
    render_params: _RadialRenderParams,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> _RenderedRadialSankey:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    outer = float(render_params.outer_margin_px)
    offset_x = float(render_params.layout_offset_x_px)
    offset_y = float(render_params.layout_offset_y_px)
    panel_bbox: BBox = (
        outer + offset_x,
        outer + offset_y,
        float(render_params.canvas_width) - outer + offset_x,
        float(render_params.canvas_height) - outer + offset_y,
    )
    title_bbox: BBox = (
        panel_bbox[0] + float(render_params.panel_padding_px),
        panel_bbox[1] + 10.0,
        panel_bbox[2] - float(render_params.panel_padding_px),
        panel_bbox[1] + float(render_params.title_band_height_px),
    )
    plot_bbox: BBox = (
        panel_bbox[0] + float(render_params.panel_padding_px),
        title_bbox[3] + 18.0,
        panel_bbox[2] - float(render_params.panel_padding_px),
        panel_bbox[3] - float(render_params.panel_padding_px),
    )
    center = (0.5 * (plot_bbox[0] + plot_bbox[2]), 0.5 * (plot_bbox[1] + plot_bbox[3]))
    radius = min(
        float(render_params.ring_radius_px),
        0.5 * min(float(plot_bbox[2] - plot_bbox[0]), float(plot_bbox[3] - plot_bbox[1])) - 58.0,
    )
    chord_radius = max(30.0, float(radius - render_params.chord_radius_inset_px))

    draw.rounded_rectangle(panel_bbox, radius=16, fill=render_params.panel_fill_rgb, outline=render_params.panel_border_rgb, width=2)
    draw.rounded_rectangle(plot_bbox, radius=12, fill=render_params.plot_fill_rgb, outline=render_params.panel_border_rgb, width=1)
    ring_bbox = (
        center[0] - float(radius),
        center[1] - float(radius),
        center[0] + float(radius),
        center[1] + float(radius),
    )
    draw.ellipse(ring_bbox, outline=render_params.ring_line_rgb, width=2)
    title_text_bbox = draw_centered_text(
        draw,
        text=str(scene_title),
        center=(0.5 * (title_bbox[0] + title_bbox[2]), 0.5 * (title_bbox[1] + title_bbox[3])),
        font=load_font(int(render_params.title_font_size_px), bold=True),
        fill=render_params.title_color_rgb,
        stroke_fill=render_params.panel_fill_rgb,
        stroke_width=1,
    )

    angles = _node_angles(sources=sources, targets=targets, instance_seed=int(instance_seed))
    all_nodes = [*sources, *targets]
    node_center_map: Dict[str, Point] = {
        str(node["node_id"]): _angle_point(center, float(radius), float(angles[str(node["node_id"])]))
        for node in all_nodes
    }
    chord_anchor_map: Dict[str, Point] = {
        str(node["node_id"]): _angle_point(center, float(chord_radius), float(angles[str(node["node_id"])]))
        for node in all_nodes
    }

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    flow_draw = ImageDraw.Draw(overlay)
    palette = tuple(render_params.flow_palette_rgb)
    link_bbox_map: Dict[str, List[float]] = {}
    link_center_map: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []

    sorted_links = sorted(links, key=lambda link: (str(link["source_label"]), str(link["target_label"]), str(link["link_id"])))
    for index, link in enumerate(sorted_links):
        link_id = str(link["link_id"])
        color = palette[int(index) % len(palette)]
        start = chord_anchor_map[str(link["source_id"])]
        end = chord_anchor_map[str(link["target_id"])]
        bend = 0.42 + (0.05 * float(index % 3))
        points = _curve_points(start, end, center, bend=float(bend))
        stroke_width = _flow_width(
            int(link["value"]),
            render_params=render_params,
            value_min=int(value_min),
            value_max=int(value_max),
        )
        flow_draw.line(
            points,
            fill=(int(color[0]), int(color[1]), int(color[2]), int(render_params.flow_alpha)),
            width=int(stroke_width),
            joint="curve",
        )
        bbox = _curve_bbox(
            points,
            stroke_width=int(stroke_width),
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
        )
        label_t = 0.34 if int(index) % 2 == 0 else 0.66
        label_point = points[int(round(float(label_t) * float(len(points) - 1)))]
        outward_angle = math.atan2(float(label_point[1] - center[1]), float(label_point[0] - center[0]))
        label_center = (
            float(label_point[0] + (16.0 * math.cos(outward_angle))),
            float(label_point[1] + (16.0 * math.sin(outward_angle))),
        )
        link_bbox_map[str(link_id)] = list(bbox)
        link_center_map[str(link_id)] = [round(float(label_center[0]), 3), round(float(label_center[1]), 3)]

    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(image)
    value_label_specs = [
        {
            "link_id": str(link["link_id"]),
            "text": str(int(link["value"])),
            "desired_center": tuple(float(value) for value in link_center_map[str(link["link_id"])]),
        }
        for link in sorted_links
    ]
    resolved_centers = _resolve_value_label_centers(
        draw,
        label_specs=value_label_specs,
        plot_bbox=plot_bbox,
        render_params=render_params,
    )
    link_label_bbox_map: Dict[str, List[float]] = {}
    for link in sorted_links:
        link_id = str(link["link_id"])
        center_px = tuple(float(value) for value in resolved_centers[str(link_id)])
        link_center_map[str(link_id)] = [round(float(center_px[0]), 3), round(float(center_px[1]), 3)]
        link_label_bbox_map[str(link_id)] = _draw_value_label(
            draw,
            text=str(int(link["value"])),
            center=center_px,
            render_params=render_params,
        )
        entities.append(
            {
                "entity_id": str(link_id),
                "entity_type": "radial_sankey_link",
                "bbox_xyxy": list(link_bbox_map[str(link_id)]),
                "attrs": {
                    "source_id": str(link["source_id"]),
                    "source_label": str(link["source_label"]),
                    "target_id": str(link["target_id"]),
                    "target_label": str(link["target_label"]),
                    "value": int(link["value"]),
                    "label_bbox_xyxy": list(link_label_bbox_map[str(link_id)]),
                },
            }
        )

    node_bbox_map: Dict[str, List[float]] = {}
    node_label_bbox_map: Dict[str, List[float]] = {}
    for node in all_nodes:
        node_id = str(node["node_id"])
        cx, cy = node_center_map[str(node_id)]
        half_w = 0.5 * float(render_params.node_width_px)
        half_h = 0.5 * float(render_params.node_height_px)
        bbox = (
            float(cx - half_w),
            float(cy - half_h),
            float(cx + half_w),
            float(cy + half_h),
        )
        fill = render_params.source_node_fill_rgb if str(node["role"]) == "source" else render_params.target_node_fill_rgb
        node_bbox_map[str(node_id)] = _clamp_bbox(bbox, width=int(render_params.canvas_width), height=int(render_params.canvas_height))
        draw.rounded_rectangle(
            bbox,
            radius=12,
            fill=tuple(int(channel) for channel in fill),
            outline=tuple(int(channel) for channel in render_params.node_border_rgb),
            width=max(1, int(render_params.node_border_width_px)),
        )
        label_font = fit_font_to_box(
            draw,
            text=str(node["label"]),
            max_width=float(bbox[2] - bbox[0] - 12.0),
            max_height=float(bbox[3] - bbox[1] - 8.0),
            bold=True,
            min_size_px=12,
            max_size_px=int(render_params.node_label_font_size_px),
            fill_ratio=0.9,
        )
        label_bbox = draw_centered_text(
            draw,
            text=str(node["label"]),
            center=(float(cx), float(cy)),
            font=label_font,
            fill=render_params.node_text_rgb,
            stroke_fill=tuple(int(channel) for channel in fill),
            stroke_width=1,
        )
        node_label_bbox_map[str(node_id)] = list(label_bbox)
        entities.append(
            {
                "entity_id": str(node_id),
                "entity_type": "radial_sankey_node",
                "bbox_xyxy": list(node_bbox_map[str(node_id)]),
                "attrs": {
                    "label": str(node["label"]),
                    "role": str(node["role"]),
                    "angle_degrees": round(float(angles[str(node_id)]), 3),
                },
            }
        )

    entities.insert(0, {"entity_id": "radial_flow_panel", "entity_type": "flow_panel", "bbox_xyxy": _round_bbox(panel_bbox)})
    entities.insert(
        1,
        {
            "entity_id": "radial_flow_title",
            "entity_type": "flow_title",
            "bbox_xyxy": list(title_text_bbox),
            "attrs": {"title": str(scene_title)},
        },
    )
    return _RenderedRadialSankey(
        image=image,
        entities=tuple(dict(item) for item in entities),
        panel_bbox_px=_round_bbox(panel_bbox),
        title_bbox_px=list(title_text_bbox),
        plot_bbox_px=_round_bbox(plot_bbox),
        node_bbox_map=dict(node_bbox_map),
        node_label_bbox_map=dict(node_label_bbox_map),
        link_bbox_map=dict(link_bbox_map),
        link_label_bbox_map=dict(link_label_bbox_map),
        link_center_map=dict(link_center_map),
    )
