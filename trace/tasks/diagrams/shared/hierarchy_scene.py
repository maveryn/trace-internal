"""Hierarchy-diagram scene renderer shared across diagrams-domain hierarchy tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.drawing import draw_rounded_rect
from .common import draw_diagram_text_in_box, resolve_diagram_panel_geometry, round_diagram_bbox
from .hierarchy_common import HierarchyRenderParams


BBox = Tuple[float, float, float, float]
Point = Tuple[float, float]


@dataclass(frozen=True)
class RenderedHierarchyScene:
    """Rendered hierarchy scene plus traced node and connector geometry."""

    image: Image.Image
    entities: List[Dict[str, object]]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    node_bbox_map: Dict[str, List[float]]
    node_label_bbox_map: Dict[str, List[float]]
    edge_bbox_map: Dict[str, List[float]]


def _children_by_parent(edge_specs: Sequence[Mapping[str, object]]) -> Dict[str, List[str]]:
    """Build an ordered children lookup from rendered edge specs."""

    children: Dict[str, List[str]] = {}
    for edge_spec in edge_specs:
        parent_id = str(edge_spec["source_node_id"])
        children.setdefault(parent_id, []).append(str(edge_spec["target_node_id"]))
    return children


def _leaf_order(root_node_id: str, children_by_parent: Mapping[str, Sequence[str]]) -> List[str]:
    """Return leaf nodes in deterministic left-to-right DFS order."""

    ordered: List[str] = []

    def _walk(node_id: str) -> None:
        child_ids = [str(child_id) for child_id in children_by_parent.get(str(node_id), [])]
        if not child_ids:
            ordered.append(str(node_id))
            return
        for child_id in child_ids:
            _walk(str(child_id))

    _walk(str(root_node_id))
    return ordered


def _node_centers(
    *,
    content_bbox: BBox,
    node_specs: Sequence[Mapping[str, object]],
    root_node_id: str,
    children_by_parent: Mapping[str, Sequence[str]],
    render_params: HierarchyRenderParams,
) -> Dict[str, Point]:
    """Resolve top-down org-chart centers for all nodes in the hierarchy."""

    left, top, right, bottom = [float(value) for value in content_bbox]
    node_height_half = 0.5 * float(render_params.node_height_px)
    node_width_half = 0.5 * float(render_params.node_width_px)
    side_padding = max(82.0, node_width_half + 18.0)
    leaf_left = float(left + side_padding)
    leaf_right = float(right - side_padding)

    depths = {str(node_spec["node_id"]): int(node_spec["depth"]) for node_spec in node_specs}
    max_depth = max(depths.values())
    y_min = float(top + node_height_half + 16.0)
    y_max = float(bottom - node_height_half - 20.0)
    depth_step = 0.0 if max_depth <= 0 else float((y_max - y_min) / float(max_depth))

    ordered_leaves = _leaf_order(str(root_node_id), children_by_parent)
    if len(ordered_leaves) <= 1:
        leaf_x_map = {str(ordered_leaves[0]): 0.5 * float(leaf_left + leaf_right)}
    else:
        leaf_step = float((leaf_right - leaf_left) / float(len(ordered_leaves) - 1))
        leaf_x_map = {
            str(node_id): float(leaf_left + (leaf_step * index))
            for index, node_id in enumerate(ordered_leaves)
        }

    centers: Dict[str, Point] = {}

    def _x_position(node_id: str) -> float:
        child_ids = [str(child_id) for child_id in children_by_parent.get(str(node_id), [])]
        if not child_ids:
            return float(leaf_x_map[str(node_id)])
        child_positions = [_x_position(str(child_id)) for child_id in child_ids]
        return float(sum(child_positions) / float(len(child_positions)))

    for node_spec in node_specs:
        node_id = str(node_spec["node_id"])
        centers[node_id] = (
            float(_x_position(node_id)),
            float(y_min + (depth_step * int(node_spec["depth"]))),
        )
    return centers


def _node_bbox(center: Point, *, render_params: HierarchyRenderParams) -> BBox:
    """Resolve one hierarchy node bbox from its center."""

    cx, cy = float(center[0]), float(center[1])
    half_w = 0.5 * float(render_params.node_width_px)
    half_h = 0.5 * float(render_params.node_height_px)
    return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)


def _edge_bbox(points: Sequence[Point]) -> List[float]:
    """Return the axis-aligned bbox of a routed connector polyline."""

    return round_diagram_bbox(
        (
            min(float(point[0]) for point in points),
            min(float(point[1]) for point in points),
            max(float(point[0]) for point in points),
            max(float(point[1]) for point in points),
        )
    )


def render_hierarchy_scene(
    background: Image.Image,
    *,
    scene_title: str,
    root_node_id: str,
    node_specs: Sequence[Mapping[str, object]],
    edge_specs: Sequence[Mapping[str, object]],
    render_params: HierarchyRenderParams,
) -> RenderedHierarchyScene:
    """Render one org-chart hierarchy scene and trace node/connector geometry."""

    image = background.copy()
    draw = ImageDraw.Draw(image)
    entities: List[Dict[str, object]] = []
    node_bbox_map: Dict[str, List[float]] = {}
    node_label_bbox_map: Dict[str, List[float]] = {}
    edge_bbox_map: Dict[str, List[float]] = {}

    panel_bbox, title_bbox, content_bbox = resolve_diagram_panel_geometry(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        outer_margin_px=int(render_params.outer_margin_px),
        title_band_height_px=int(render_params.title_band_height_px),
        panel_padding_px=int(render_params.panel_padding_px),
    )
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

    children_by_parent = _children_by_parent(edge_specs)
    node_centers = _node_centers(
        content_bbox=content_bbox,
        node_specs=node_specs,
        root_node_id=str(root_node_id),
        children_by_parent=children_by_parent,
        render_params=render_params,
    )
    node_boxes_by_id = {
        str(node_spec["node_id"]): _node_bbox(node_centers[str(node_spec["node_id"])], render_params=render_params)
        for node_spec in node_specs
    }

    for node_spec in node_specs:
        parent_id = str(node_spec["node_id"])
        child_ids = [str(child_id) for child_id in children_by_parent.get(parent_id, [])]
        if not child_ids:
            continue
        parent_box = node_boxes_by_id[parent_id]
        parent_center_x = 0.5 * float(parent_box[0] + parent_box[2])
        parent_bottom_y = float(parent_box[3])
        child_top_y = min(float(node_boxes_by_id[child_id][1]) for child_id in child_ids)
        branch_y = float(parent_bottom_y + max(12.0, 0.36 * float(child_top_y - parent_bottom_y)))
        if len(child_ids) > 1:
            horizontal_left = min(float(node_centers[child_id][0]) for child_id in child_ids)
            horizontal_right = max(float(node_centers[child_id][0]) for child_id in child_ids)
            draw.line(
                [(parent_center_x, parent_bottom_y), (parent_center_x, branch_y)],
                fill=tuple(int(value) for value in render_params.connector_color_rgb),
                width=max(1, int(render_params.connector_width_px)),
            )
            draw.line(
                [(horizontal_left, branch_y), (horizontal_right, branch_y)],
                fill=tuple(int(value) for value in render_params.connector_color_rgb),
                width=max(1, int(render_params.connector_width_px)),
            )
        for child_id in child_ids:
            child_center_x = float(node_centers[child_id][0])
            child_top = float(node_boxes_by_id[child_id][1])
            if len(child_ids) == 1:
                path = [
                    (parent_center_x, parent_bottom_y),
                    (parent_center_x, branch_y),
                    (child_center_x, branch_y),
                    (child_center_x, child_top),
                ]
            else:
                path = [
                    (child_center_x, branch_y),
                    (child_center_x, child_top),
                ]
            draw.line(
                path,
                fill=tuple(int(value) for value in render_params.connector_color_rgb),
                width=max(1, int(render_params.connector_width_px)),
            )
            edge_spec = next(
                edge for edge in edge_specs if str(edge["source_node_id"]) == parent_id and str(edge["target_node_id"]) == child_id
            )
            edge_bbox = _edge_bbox(
                [
                    (parent_center_x, parent_bottom_y),
                    (parent_center_x, branch_y),
                    (child_center_x, branch_y),
                    (child_center_x, child_top),
                ]
            )
            edge_bbox_map[str(edge_spec["edge_id"])] = edge_bbox
            entities.append(
                {
                    "entity_id": str(edge_spec["edge_id"]),
                    "entity_type": "diagram_edge",
                    "bbox_xyxy": list(edge_bbox),
                    "source_node_id": parent_id,
                    "target_node_id": child_id,
                }
            )

    for node_spec in node_specs:
        node_id = str(node_spec["node_id"])
        node_bbox_id = str(node_spec["node_bbox_id"])
        node_label_bbox_id = str(node_spec["node_label_bbox_id"])
        node_box = node_boxes_by_id[node_id]
        fill_rgb = render_params.root_fill_rgb if str(node_id) == str(root_node_id) else render_params.node_fill_rgb
        draw_rounded_rect(
            draw,
            node_box,
            radius=int(render_params.node_corner_radius_px),
            fill=fill_rgb,
            outline=render_params.node_border_rgb,
            width=int(render_params.node_border_width_px),
        )
        label_bbox = draw_diagram_text_in_box(
            draw,
            bbox=node_box,
            text=str(node_spec["node_label"]),
            font_size_px=int(render_params.label_font_size_px),
            bold=True,
            fill=render_params.label_color_rgb,
            stroke_fill=render_params.label_stroke_rgb,
            padding_px=8,
        )
        node_bbox_map[node_bbox_id] = round_diagram_bbox(node_box)
        node_label_bbox_map[node_label_bbox_id] = list(label_bbox)
        entities.append(
            {
                "entity_id": node_bbox_id,
                "entity_type": "diagram_node",
                "bbox_xyxy": round_diagram_bbox(node_box),
                "node_id": node_id,
                "text": str(node_spec["node_label"]),
                "depth": int(node_spec["depth"]),
            }
        )
        entities.append(
            {
                "entity_id": node_label_bbox_id,
                "entity_type": "diagram_node_label",
                "bbox_xyxy": list(label_bbox),
                "node_id": node_id,
                "text": str(node_spec["node_label"]),
            }
        )

    return RenderedHierarchyScene(
        image=image,
        entities=entities,
        panel_bbox_px=round_diagram_bbox(panel_bbox),
        title_bbox_px=list(title_text_bbox),
        node_bbox_map=node_bbox_map,
        node_label_bbox_map=node_label_bbox_map,
        edge_bbox_map=edge_bbox_map,
    )


__all__ = ["RenderedHierarchyScene", "render_hierarchy_scene"]
