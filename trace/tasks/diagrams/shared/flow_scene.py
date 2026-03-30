"""Flow-diagram scene renderer shared across diagrams-domain flow tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.drawing import draw_arrow, draw_centered_text, draw_rounded_rect
from ...shared.text_rendering import load_font
from .common import draw_diagram_text_in_box, resolve_diagram_panel_geometry, round_diagram_bbox
from .flow_common import FlowRenderParams


BBox = Tuple[float, float, float, float]
Point = Tuple[float, float]


@dataclass(frozen=True)
class RenderedFlowScene:
    """Rendered flow-diagram scene plus traced witness geometry."""

    image: Image.Image
    entities: List[Dict[str, object]]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    lane_bbox_map: Dict[str, List[float]]
    lane_label_bbox_map: Dict[str, List[float]]
    node_bbox_map: Dict[str, List[float]]
    node_label_bbox_map: Dict[str, List[float]]
    edge_label_bbox_map: Dict[str, List[float]]


def _panel_geometry(
    *,
    render_params: FlowRenderParams,
) -> Tuple[BBox, BBox, BBox]:
    """Resolve the panel, title band, and content area."""

    panel, title_band, content = resolve_diagram_panel_geometry(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        outer_margin_px=int(render_params.outer_margin_px),
        title_band_height_px=int(render_params.title_band_height_px),
        panel_padding_px=int(render_params.panel_padding_px),
    )
    return panel, title_band, content


def _node_bbox(
    *,
    center: Point,
    node_kind: str,
    render_params: FlowRenderParams,
) -> BBox:
    """Resolve one node bbox from center and kind."""

    cx, cy = float(center[0]), float(center[1])
    if str(node_kind) == "decision":
        half = 0.5 * float(render_params.decision_diameter_px)
        return (cx - half, cy - half, cx + half, cy + half)
    half_w = 0.5 * float(render_params.node_width_px)
    half_h = 0.5 * float(render_params.node_height_px)
    return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)


def _diamond_points(bbox: BBox) -> List[Tuple[float, float]]:
    """Return the polygon points for one decision diamond."""

    left, top, right, bottom = [float(value) for value in bbox]
    cx = 0.5 * float(left + right)
    cy = 0.5 * float(top + bottom)
    return [(cx, top), (right, cy), (cx, bottom), (left, cy)]


def _lane_geometry(
    *,
    content_bbox: BBox,
    lane_specs: Sequence[Mapping[str, object]],
    render_params: FlowRenderParams,
) -> Dict[str, BBox]:
    """Resolve swimlane rectangles."""

    left, top, right, bottom = [float(value) for value in content_bbox]
    lane_count = max(1, len(lane_specs))
    lane_height = float(bottom - top) / float(lane_count)
    lane_boxes: Dict[str, BBox] = {}
    for index, lane_spec in enumerate(lane_specs):
        lane_top = float(top + index * lane_height)
        lane_bottom = float(top + (index + 1) * lane_height)
        lane_boxes[str(lane_spec["lane_id"])] = (left, lane_top, right, lane_bottom)
    return lane_boxes


def _content_point(
    *,
    content_bbox: BBox,
    rel_point: Sequence[float],
    scene_variant: str,
    render_params: FlowRenderParams,
) -> Point:
    """Project one normalized point into content coordinates."""

    left, top, right, bottom = [float(value) for value in content_bbox]
    inner_left = float(left)
    if str(scene_variant) == "swimlane":
        inner_left = float(left + render_params.lane_gutter_width_px)
    x = float(inner_left + (float(rel_point[0]) * float(right - inner_left)))
    y = float(top + (float(rel_point[1]) * float(bottom - top)))
    return (x, y)


def _clip_point_to_bbox(
    center: Point,
    toward: Point,
    bbox: BBox,
) -> Point:
    """Move a point from a node center to the boundary of its bbox along one ray."""

    cx, cy = float(center[0]), float(center[1])
    tx, ty = float(toward[0]), float(toward[1])
    dx = float(tx - cx)
    dy = float(ty - cy)
    if abs(dx) <= 1e-6 and abs(dy) <= 1e-6:
        return (cx, cy)
    half_w = 0.5 * float(bbox[2] - bbox[0])
    half_h = 0.5 * float(bbox[3] - bbox[1])
    scale_x = float("inf") if abs(dx) <= 1e-6 else float(half_w / abs(dx))
    scale_y = float("inf") if abs(dy) <= 1e-6 else float(half_h / abs(dy))
    scale = min(float(scale_x), float(scale_y))
    return (float(cx + (dx * scale)), float(cy + (dy * scale)))


def _polyline_length(points: Sequence[Point]) -> float:
    """Return total length of one polyline."""

    total = 0.0
    for left, right in zip(points, points[1:]):
        total += math.hypot(float(right[0] - left[0]), float(right[1] - left[1]))
    return float(total)


def _point_along_polyline(points: Sequence[Point], *, ratio: float) -> Point:
    """Return one point interpolated along a polyline."""

    if len(points) < 2:
        return (float(points[0][0]), float(points[0][1]))
    target = float(max(0.0, min(1.0, ratio))) * _polyline_length(points)
    traversed = 0.0
    for left, right in zip(points, points[1:]):
        segment = math.hypot(float(right[0] - left[0]), float(right[1] - left[1]))
        if traversed + segment >= target or segment <= 1e-6:
            local = 0.0 if segment <= 1e-6 else (target - traversed) / segment
            return (
                float(left[0] + ((right[0] - left[0]) * local)),
                float(left[1] + ((right[1] - left[1]) * local)),
            )
        traversed += segment
    return (float(points[-1][0]), float(points[-1][1]))


def _draw_polyline_arrow(
    draw: ImageDraw.ImageDraw,
    *,
    points: Sequence[Point],
    render_params: FlowRenderParams,
) -> None:
    """Draw one routed polyline with an arrowhead on the final segment."""

    if len(points) < 2:
        return
    if len(points) > 2:
        draw.line(
            [tuple(points[index]) for index in range(len(points) - 1)],
            fill=tuple(int(value) for value in render_params.edge_color_rgb),
            width=max(1, int(render_params.edge_width_px)),
        )
    start, end = points[-2], points[-1]
    draw_arrow(
        draw,
        start=(float(start[0]), float(start[1])),
        end=(float(end[0]), float(end[1])),
        fill=tuple(int(value) for value in render_params.edge_color_rgb),
        width=max(1, int(render_params.edge_width_px)),
        head_length_px=float(render_params.arrow_head_length_px),
        head_width_px=float(render_params.arrow_head_width_px),
    )


def render_flow_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    scene_title: str,
    lane_specs: Sequence[Mapping[str, object]],
    node_specs: Sequence[Mapping[str, object]],
    edge_specs: Sequence[Mapping[str, object]],
    render_params: FlowRenderParams,
) -> RenderedFlowScene:
    """Render one flowchart or swimlane scene and trace node/lane geometry."""

    image = background.copy()
    draw = ImageDraw.Draw(image)
    entities: List[Dict[str, object]] = []
    lane_bbox_map: Dict[str, List[float]] = {}
    lane_label_bbox_map: Dict[str, List[float]] = {}
    node_bbox_map: Dict[str, List[float]] = {}
    node_label_bbox_map: Dict[str, List[float]] = {}
    edge_label_bbox_map: Dict[str, List[float]] = {}

    panel_bbox, title_bbox, content_bbox = _panel_geometry(render_params=render_params)
    draw_rounded_rect(
        draw,
        panel_bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=render_params.panel_fill_rgb,
        outline=render_params.panel_border_rgb,
        width=2,
    )
    title_text_bbox = draw_diagram_text_in_box(
        draw,
        bbox=title_bbox,
        text=str(scene_title),
        font_size_px=int(render_params.title_font_size_px),
        bold=True,
        fill=render_params.title_color_rgb,
        stroke_fill=render_params.panel_fill_rgb,
        padding_px=12,
    )
    entities.append(
        {
            "entity_id": "diagram_panel",
            "entity_type": "diagram_panel",
            "bbox_xyxy": round_diagram_bbox(panel_bbox),
        }
    )
    entities.append(
        {
            "entity_id": "diagram_title",
            "entity_type": "diagram_title",
            "bbox_xyxy": list(title_text_bbox),
            "text": str(scene_title),
        }
    )

    if str(scene_variant) == "swimlane":
        lane_boxes = _lane_geometry(content_bbox=content_bbox, lane_specs=lane_specs, render_params=render_params)
        content_left = float(content_bbox[0] + render_params.lane_gutter_width_px)
        for index, lane_spec in enumerate(lane_specs):
            lane_id = str(lane_spec["lane_id"])
            lane_box = lane_boxes[lane_id]
            draw.rectangle(
                lane_box,
                fill=tuple(int(value) for value in render_params.lane_fill_rgb),
                outline=None,
            )
            if index > 0:
                y = float(lane_box[1])
                draw.line(
                    [(float(content_bbox[0]), y), (float(content_bbox[2]), y)],
                    fill=tuple(int(value) for value in render_params.lane_divider_rgb),
                    width=max(1, int(render_params.lane_divider_width_px)),
                )
            draw.line(
                [(content_left, float(lane_box[1])), (content_left, float(lane_box[3]))],
                fill=tuple(int(value) for value in render_params.lane_divider_rgb),
                width=max(1, int(render_params.lane_divider_width_px)),
            )
            lane_label_box = (
                float(content_bbox[0] + 12.0),
                float(lane_box[1] + 8.0),
                float(content_left - 12.0),
                float(lane_box[3] - 8.0),
            )
            label_bbox = draw_diagram_text_in_box(
                draw,
                bbox=lane_label_box,
                text=str(lane_spec["lane_label"]),
                font_size_px=int(render_params.lane_label_font_size_px),
                bold=True,
                fill=render_params.title_color_rgb,
                stroke_fill=render_params.panel_fill_rgb,
                padding_px=6,
            )
            lane_bbox_map[lane_id] = round_diagram_bbox(lane_box)
            lane_label_bbox_map[lane_id] = list(label_bbox)
            entities.append(
                {
                    "entity_id": str(lane_spec["lane_bbox_id"]),
                    "entity_type": "diagram_lane",
                    "bbox_xyxy": round_diagram_bbox(lane_box),
                    "lane_id": lane_id,
                    "text": str(lane_spec["lane_label"]),
                }
            )
            entities.append(
                {
                    "entity_id": str(lane_spec["lane_label_bbox_id"]),
                    "entity_type": "diagram_lane_label",
                    "bbox_xyxy": list(label_bbox),
                    "lane_id": lane_id,
                    "text": str(lane_spec["lane_label"]),
                }
            )

    node_centers: Dict[str, Point] = {}
    node_boxes_by_id: Dict[str, BBox] = {}
    for node_spec in node_specs:
        center = _content_point(
            content_bbox=content_bbox,
            rel_point=node_spec["center_rel"],
            scene_variant=str(scene_variant),
            render_params=render_params,
        )
        node_centers[str(node_spec["node_id"])] = center
        node_box = _node_bbox(center=center, node_kind=str(node_spec["node_kind"]), render_params=render_params)
        node_boxes_by_id[str(node_spec["node_id"])] = node_box

    for edge_spec in edge_specs:
        source_id = str(edge_spec["source_node_id"])
        target_id = str(edge_spec["target_node_id"])
        waypoints = [
            _content_point(
                content_bbox=content_bbox,
                rel_point=waypoint,
                scene_variant=str(scene_variant),
                render_params=render_params,
            )
            for waypoint in edge_spec.get("waypoints_rel", [])
        ]
        points = [node_centers[source_id], *waypoints, node_centers[target_id]]
        if len(points) >= 2:
            points[0] = _clip_point_to_bbox(points[0], points[1], node_boxes_by_id[source_id])
            points[-1] = _clip_point_to_bbox(points[-1], points[-2], node_boxes_by_id[target_id])
        _draw_polyline_arrow(draw, points=points, render_params=render_params)
        entities.append(
            {
                "entity_id": str(edge_spec["edge_id"]),
                "entity_type": "diagram_edge",
                "source_node_id": source_id,
                "target_node_id": target_id,
                "edge_label": edge_spec.get("edge_label"),
            }
        )
        edge_label = edge_spec.get("edge_label")
        if edge_label:
            label_center = _point_along_polyline(points, ratio=0.55)
            font = load_font(int(render_params.branch_label_font_size_px), bold=True)
            text_bbox = draw.textbbox((0, 0), str(edge_label), font=font, stroke_width=1)
            text_w = float(text_bbox[2] - text_bbox[0])
            text_h = float(text_bbox[3] - text_bbox[1])
            padding = float(render_params.branch_label_padding_px)
            label_box = (
                float(label_center[0] - (0.5 * text_w) - padding),
                float(label_center[1] - (0.5 * text_h) - padding),
                float(label_center[0] + (0.5 * text_w) + padding),
                float(label_center[1] + (0.5 * text_h) + padding),
            )
            draw_rounded_rect(
                draw,
                label_box,
                radius=12,
                fill=render_params.branch_label_fill_rgb,
                outline=render_params.branch_label_border_rgb,
                width=2,
            )
            rendered_label_bbox = draw_centered_text(
                draw,
                text=str(edge_label),
                center=label_center,
                font=font,
                fill=render_params.branch_label_text_rgb,
                stroke_fill=render_params.branch_label_fill_rgb,
                stroke_width=1,
            )
            label_bbox_id = str(edge_spec["edge_label_bbox_id"])
            if label_bbox_id:
                edge_label_bbox_map[label_bbox_id] = round_diagram_bbox(label_box)
            entities.append(
                {
                    "entity_id": label_bbox_id,
                    "entity_type": "diagram_edge_label",
                    "bbox_xyxy": round_diagram_bbox(label_box),
                    "text": str(edge_label),
                    "text_bbox_xyxy": list(rendered_label_bbox),
                }
            )

    for node_spec in node_specs:
        node_id = str(node_spec["node_id"])
        node_bbox_id = str(node_spec["node_bbox_id"])
        node_label_bbox_id = str(node_spec["node_label_bbox_id"])
        node_box = node_boxes_by_id[node_id]
        node_label = str(node_spec["node_label"])
        if str(node_spec["node_kind"]) == "decision":
            draw.polygon(
                _diamond_points(node_box),
                fill=tuple(int(value) for value in render_params.decision_fill_rgb),
                outline=tuple(int(value) for value in render_params.node_border_rgb),
                width=max(1, int(render_params.node_border_width_px)),
            )
        else:
            draw_rounded_rect(
                draw,
                node_box,
                radius=int(render_params.node_corner_radius_px),
                fill=render_params.node_fill_rgb,
                outline=render_params.node_border_rgb,
                width=int(render_params.node_border_width_px),
            )
        label_bbox = draw_diagram_text_in_box(
            draw,
            bbox=node_box,
            text=node_label,
            font_size_px=int(render_params.label_font_size_px),
            bold=True,
            fill=render_params.label_color_rgb,
            stroke_fill=render_params.label_stroke_rgb,
            padding_px=10,
        )
        node_bbox_map[node_bbox_id] = round_diagram_bbox(node_box)
        node_label_bbox_map[node_label_bbox_id] = list(label_bbox)
        entities.append(
            {
                "entity_id": node_bbox_id,
                "entity_type": "diagram_node",
                "bbox_xyxy": round_diagram_bbox(node_box),
                "node_id": node_id,
                "node_kind": str(node_spec["node_kind"]),
                "text": node_label,
                "lane_id": node_spec.get("lane_id"),
            }
        )
        entities.append(
            {
                "entity_id": node_label_bbox_id,
                "entity_type": "diagram_node_label",
                "bbox_xyxy": list(label_bbox),
                "node_id": node_id,
                "text": node_label,
            }
        )

    return RenderedFlowScene(
        image=image,
        entities=entities,
        panel_bbox_px=round_diagram_bbox(panel_bbox),
        title_bbox_px=list(title_text_bbox),
        lane_bbox_map=lane_bbox_map,
        lane_label_bbox_map=lane_label_bbox_map,
        node_bbox_map=node_bbox_map,
        node_label_bbox_map=node_label_bbox_map,
        edge_label_bbox_map=edge_label_bbox_map,
    )


__all__ = ["RenderedFlowScene", "render_flow_scene"]
