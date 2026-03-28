"""Shared node-link graph rendering helpers for graph-domain tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import networkx as nx
from PIL import Image, ImageDraw

from ...shared.text_rendering import draw_text_centered, load_font
from .graph_sampling import GraphCountSample


Point = Tuple[int, int]
BBox = Tuple[int, int, int, int]
SUPPORTED_NODE_SHAPE_VARIANTS: Tuple[str, ...] = ("circle", "rounded_square", "hexagon")
SUPPORTED_LAYOUT_TRANSFORM_VARIANTS: Tuple[str, ...] = (
    "identity",
    "rotate_90",
    "rotate_180",
    "rotate_270",
    "mirror_left_right",
    "mirror_up_down",
)


@dataclass(frozen=True)
class GraphRenderParams:
    """Resolved render-time parameters for one graph scene."""

    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    panel_title_font_size_px: int
    node_shape_variant: str
    node_radius_px: int
    edge_width_px: int
    node_border_width_px: int
    label_font_size_px: int
    background_color_rgb: Tuple[int, int, int]
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    title_color_rgb: Tuple[int, int, int]
    edge_color_rgb: Tuple[int, int, int]
    node_fill_rgb: Tuple[int, int, int]
    node_border_rgb: Tuple[int, int, int]
    label_text_rgb: Tuple[int, int, int]
    label_stroke_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class RenderedGraphNode:
    """Trace-ready node placement for one rendered graph scene."""

    label: str
    degree: int
    center_xy: Point
    bbox_xyxy: BBox
    neighbors: Tuple[str, ...]


@dataclass(frozen=True)
class RenderedGraphEdge:
    """Trace-ready edge segment for one rendered graph scene."""

    edge_id: str
    node_u_label: str
    node_v_label: str
    segment_px: Tuple[Point, Point]


@dataclass(frozen=True)
class RenderedGraphScene:
    """Full render output for one graph scene."""

    image: Image.Image
    panel_geometry: Dict[str, Any]
    nodes: Tuple[RenderedGraphNode, ...]
    edges: Tuple[RenderedGraphEdge, ...]
    layout_variant: str
    layout_transform_variant: str
    crossing_count: int


def _resolve_panel_geometry(
    *,
    canvas_width: int,
    canvas_height: int,
    outer_margin_px: int,
    panel_padding_px: int,
    title_font_size_px: int,
) -> Dict[str, BBox | List[int]]:
    """Resolve one single-panel graph layout with a title band."""

    width = int(canvas_width)
    height = int(canvas_height)
    margin = int(outer_margin_px)
    panel = (int(margin), int(margin), int(width - margin), int(height - margin))
    title_band_height = max(40, int(round(float(title_font_size_px) * 1.8)))
    title_band = (int(panel[0]), int(panel[1]), int(panel[2]), int(panel[1] + title_band_height))
    content = (
        int(panel[0] + panel_padding_px),
        int(title_band[3] + max(8, int(panel_padding_px // 2))),
        int(panel[2] - panel_padding_px),
        int(panel[3] - panel_padding_px),
    )
    return {
        "canvas_size": [int(width), int(height)],
        "scene_panel_xyxy": [int(value) for value in panel],
        "title_band_xyxy": [int(value) for value in title_band],
        "scene_content_xyxy": [int(value) for value in content],
    }


def _draw_panel_chrome(
    image: Image.Image,
    *,
    panel_geometry: Mapping[str, Any],
    render_params: GraphRenderParams,
    scene_title: str,
    fill_background: bool,
) -> None:
    """Draw one rounded single-panel graph scene with title."""

    draw = ImageDraw.Draw(image)
    if bool(fill_background):
        draw.rectangle((0, 0, image.size[0], image.size[1]), fill=tuple(int(v) for v in render_params.background_color_rgb))
    panel = tuple(int(value) for value in panel_geometry["scene_panel_xyxy"])
    draw.rounded_rectangle(
        panel,
        radius=max(0, int(render_params.panel_corner_radius_px)),
        fill=tuple(int(v) for v in render_params.panel_fill_rgb),
        outline=tuple(int(v) for v in render_params.panel_border_rgb),
        width=2,
    )
    title_center = (0.5 * float(panel[0] + panel[2]), 0.5 * float(panel_geometry["title_band_xyxy"][1] + panel_geometry["title_band_xyxy"][3]))
    draw_text_centered(
        draw,
        text=str(scene_title),
        center=title_center,
        font=load_font(int(render_params.panel_title_font_size_px), bold=True),
        fill=tuple(int(v) for v in render_params.title_color_rgb),
        stroke_fill=tuple(int(v) for v in render_params.panel_fill_rgb),
        stroke_width=2,
    )


def _scale_layout_to_content(
    raw_positions: Mapping[int, Sequence[float]],
    *,
    content_bbox: BBox,
    node_radius_px: int,
) -> Dict[int, Point]:
    """Scale raw layout positions into pixel centers inside one content box."""

    xs = [float(pos[0]) for pos in raw_positions.values()]
    ys = [float(pos[1]) for pos in raw_positions.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    inset = max(4, int(node_radius_px) + 4)
    target_x0 = float(x0 + inset)
    target_y0 = float(y0 + inset)
    target_x1 = float(x1 - inset)
    target_y1 = float(y1 - inset)
    source_w = float(max_x - min_x)
    source_h = float(max_y - min_y)

    scaled: Dict[int, Point] = {}
    for node, position in raw_positions.items():
        if float(source_w) <= 1e-9:
            px = 0.5 * float(target_x0 + target_x1)
        else:
            px = float(target_x0) + (
                ((float(position[0]) - float(min_x)) / float(source_w)) * float(max(1.0, target_x1 - target_x0))
            )
        if float(source_h) <= 1e-9:
            py = 0.5 * float(target_y0 + target_y1)
        else:
            py = float(target_y0) + (
                ((float(position[1]) - float(min_y)) / float(source_h)) * float(max(1.0, target_y1 - target_y0))
            )
        scaled[int(node)] = (int(round(px)), int(round(py)))
    return scaled


def _transform_raw_layout(
    raw_positions: Mapping[int, Sequence[float]],
    *,
    layout_transform_variant: str,
) -> Dict[int, Tuple[float, float]]:
    """Apply one global D4-style transform to raw layout coordinates."""

    transform = str(layout_transform_variant)
    transformed: Dict[int, Tuple[float, float]] = {}
    for node, position in raw_positions.items():
        x = float(position[0])
        y = float(position[1])
        if transform == "rotate_90":
            point = (-y, x)
        elif transform == "rotate_180":
            point = (-x, -y)
        elif transform == "rotate_270":
            point = (y, -x)
        elif transform == "mirror_left_right":
            point = (-x, y)
        elif transform == "mirror_up_down":
            point = (x, -y)
        else:
            point = (x, y)
            transform = "identity"
        transformed[int(node)] = (float(point[0]), float(point[1]))
    return transformed


def _spring_layout(graph: nx.Graph, *, seed: int) -> Dict[int, Point]:
    """Return one spring layout in abstract coordinates."""

    node_count = max(1, int(graph.number_of_nodes()))
    layout = nx.spring_layout(
        graph,
        seed=int(seed) % (2**32 - 1),
        k=1.8 / math.sqrt(float(node_count)),
        iterations=150,
        scale=1.0,
    )
    return {int(node): (float(position[0]), float(position[1])) for node, position in layout.items()}


def _circular_layout(graph: nx.Graph) -> Dict[int, Point]:
    """Return one circular layout in abstract coordinates."""

    layout = nx.circular_layout(graph, scale=1.0)
    return {int(node): (float(position[0]), float(position[1])) for node, position in layout.items()}


def _shell_layout(graph: nx.Graph) -> Dict[int, Point]:
    """Return one shell layout in abstract coordinates."""

    sorted_nodes = sorted((int(node) for node in graph.nodes()), key=lambda node: (-int(graph.degree(node)), int(node)))
    inner_shell_size = max(1, min(len(sorted_nodes) - 1, int(round(len(sorted_nodes) * 0.35)))) if len(sorted_nodes) > 2 else 1
    shells = [sorted_nodes[:inner_shell_size], sorted_nodes[inner_shell_size:]]
    layout = nx.shell_layout(graph, nlist=shells, scale=1.0)
    return {int(node): (float(position[0]), float(position[1])) for node, position in layout.items()}


def _min_node_distance(positions: Mapping[int, Point]) -> float:
    """Return the minimum pairwise node-center distance."""

    points = list(positions.values())
    if len(points) < 2:
        return float("inf")
    min_distance = float("inf")
    for index, left in enumerate(points):
        for right in points[index + 1 :]:
            distance = math.hypot(float(right[0]) - float(left[0]), float(right[1]) - float(left[1]))
            min_distance = min(min_distance, float(distance))
    return float(min_distance)


def _resolve_positions(
    graph: nx.Graph,
    *,
    layout_variant: str,
    layout_transform_variant: str,
    content_bbox: BBox,
    node_radius_px: int,
    layout_seed: int,
) -> Tuple[Dict[int, Point], str, str]:
    """Resolve pixel node centers for one graph layout variant."""

    requested = str(layout_variant)
    if requested == "shell":
        raw_positions = _shell_layout(graph)
    elif requested == "spring":
        raw_positions = _spring_layout(graph, seed=int(layout_seed))
    else:
        raw_positions = _circular_layout(graph)
        requested = "circular"
    actual_transform = str(layout_transform_variant)
    raw_positions = _transform_raw_layout(raw_positions, layout_transform_variant=actual_transform)
    positions = _scale_layout_to_content(
        raw_positions,
        content_bbox=tuple(int(value) for value in content_bbox),
        node_radius_px=int(node_radius_px),
    )
    if _min_node_distance(positions) < float(max(18, int(node_radius_px) * 2 + 4)):
        fallback_positions = _scale_layout_to_content(
            _transform_raw_layout(_circular_layout(graph), layout_transform_variant=actual_transform),
            content_bbox=tuple(int(value) for value in content_bbox),
            node_radius_px=int(node_radius_px),
        )
        return fallback_positions, "circular", actual_transform
    return positions, requested, actual_transform


def _orientation(a: Point, b: Point, c: Point) -> int:
    """Return one orientation sign for segment intersection testing."""

    value = ((int(b[1]) - int(a[1])) * (int(c[0]) - int(b[0]))) - ((int(b[0]) - int(a[0])) * (int(c[1]) - int(b[1])))
    if value == 0:
        return 0
    return 1 if value > 0 else 2


def _segments_intersect(left: Tuple[Point, Point], right: Tuple[Point, Point]) -> bool:
    """Return whether two closed line segments intersect."""

    p1, q1 = left
    p2, q2 = right
    o1 = _orientation(p1, q1, p2)
    o2 = _orientation(p1, q1, q2)
    o3 = _orientation(p2, q2, p1)
    o4 = _orientation(p2, q2, q1)
    return bool(o1 != o2 and o3 != o4)


def _count_edge_crossings(segments: Sequence[Tuple[Tuple[str, str], Tuple[Point, Point]]]) -> int:
    """Count strict edge crossings, ignoring edges that share endpoints."""

    crossings = 0
    for index, (left_labels, left_segment) in enumerate(segments):
        left_endpoints = set(left_labels)
        for right_labels, right_segment in segments[index + 1 :]:
            if left_endpoints.intersection(set(right_labels)):
                continue
            if _segments_intersect(left_segment, right_segment):
                crossings += 1
    return int(crossings)


def _regular_polygon_points(*, center: Point, radius: int, sides: int, rotation_degrees: float) -> Tuple[Point, ...]:
    """Return polygon vertices for one regular polygon node glyph."""

    cx = float(center[0])
    cy = float(center[1])
    start = math.radians(float(rotation_degrees))
    return tuple(
        (
            int(round(cx + (float(radius) * math.cos(start + ((2.0 * math.pi * index) / float(sides)))))),
            int(round(cy + (float(radius) * math.sin(start + ((2.0 * math.pi * index) / float(sides)))))),
        )
        for index in range(int(sides))
    )


def _draw_node_shape(
    draw: ImageDraw.ImageDraw,
    *,
    center: Point,
    radius: int,
    node_shape_variant: str,
    fill_rgb: Sequence[int],
    outline_rgb: Sequence[int],
    outline_width: int,
) -> BBox:
    """Draw one node glyph and return its bounding box."""

    bbox = (
        int(center[0] - radius),
        int(center[1] - radius),
        int(center[0] + radius),
        int(center[1] + radius),
    )
    shape = str(node_shape_variant)
    fill = tuple(int(value) for value in fill_rgb)
    outline = tuple(int(value) for value in outline_rgb)
    if shape == "rounded_square":
        draw.rounded_rectangle(
            bbox,
            radius=max(4, int(round(float(radius) * 0.35))),
            fill=fill,
            outline=outline,
            width=int(outline_width),
        )
    elif shape == "hexagon":
        draw.polygon(
            _regular_polygon_points(center=center, radius=int(radius), sides=6, rotation_degrees=30.0),
            fill=fill,
            outline=outline,
            width=int(outline_width),
        )
    else:
        draw.ellipse(
            bbox,
            fill=fill,
            outline=outline,
            width=int(outline_width),
        )
    return bbox


def render_graph_scene(
    *,
    graph_sample: GraphCountSample,
    layout_variant: str,
    layout_transform_variant: str,
    render_params: GraphRenderParams,
    layout_seed: int,
    scene_title: str = "Graph",
    base_image: Image.Image | None = None,
) -> RenderedGraphScene:
    """Render one labeled single-panel node-link graph scene."""

    panel_geometry = _resolve_panel_geometry(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        outer_margin_px=int(render_params.outer_margin_px),
        panel_padding_px=int(render_params.panel_padding_px),
        title_font_size_px=int(render_params.panel_title_font_size_px),
    )
    if base_image is None:
        image = Image.new("RGB", (int(render_params.canvas_width), int(render_params.canvas_height)))
        fill_background = True
    else:
        image = base_image.convert("RGB").copy()
        fill_background = False
    _draw_panel_chrome(
        image,
        panel_geometry=panel_geometry,
        render_params=render_params,
        scene_title=str(scene_title),
        fill_background=bool(fill_background),
    )
    draw = ImageDraw.Draw(image)
    content_bbox = tuple(int(value) for value in panel_geometry["scene_content_xyxy"])
    positions, actual_layout_variant, actual_layout_transform_variant = _resolve_positions(
        graph_sample.graph,
        layout_variant=str(layout_variant),
        layout_transform_variant=str(layout_transform_variant),
        content_bbox=content_bbox,
        node_radius_px=int(render_params.node_radius_px),
        layout_seed=int(layout_seed),
    )

    label_to_node = {str(label): int(node) for node, label in zip(graph_sample.graph.nodes(), graph_sample.node_labels)}
    edge_segments: List[Tuple[Tuple[str, str], Tuple[Point, Point]]] = []
    rendered_edges: List[RenderedGraphEdge] = []
    for left_label, right_label in graph_sample.edge_labels:
        left_node = int(label_to_node[str(left_label)])
        right_node = int(label_to_node[str(right_label)])
        start = tuple(int(value) for value in positions[left_node])
        end = tuple(int(value) for value in positions[right_node])
        draw.line(
            (start[0], start[1], end[0], end[1]),
            fill=tuple(int(v) for v in render_params.edge_color_rgb),
            width=int(render_params.edge_width_px),
        )
        edge_segments.append(((str(left_label), str(right_label)), (start, end)))
        rendered_edges.append(
            RenderedGraphEdge(
                edge_id=f"edge_{str(left_label)}_{str(right_label)}",
                node_u_label=str(left_label),
                node_v_label=str(right_label),
                segment_px=(start, end),
            )
        )

    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    rendered_nodes: List[RenderedGraphNode] = []
    radius = int(render_params.node_radius_px)
    for node, label in zip(graph_sample.graph.nodes(), graph_sample.node_labels):
        center = tuple(int(value) for value in positions[int(node)])
        bbox = _draw_node_shape(
            draw,
            center=center,
            radius=int(radius),
            node_shape_variant=str(render_params.node_shape_variant),
            fill_rgb=tuple(int(v) for v in render_params.node_fill_rgb),
            outline_rgb=tuple(int(v) for v in render_params.node_border_rgb),
            outline_width=int(render_params.node_border_width_px),
        )
        draw_text_centered(
            draw,
            text=str(label),
            center=(float(center[0]), float(center[1])),
            font=label_font,
            fill=tuple(int(v) for v in render_params.label_text_rgb),
            stroke_fill=tuple(int(v) for v in render_params.label_stroke_rgb),
            stroke_width=2,
        )
        rendered_nodes.append(
            RenderedGraphNode(
                label=str(label),
                degree=int(graph_sample.degrees_by_label[str(label)]),
                center_xy=center,
                bbox_xyxy=tuple(int(value) for value in bbox),
                neighbors=tuple(str(value) for value in graph_sample.adjacency_by_label[str(label)]),
            )
        )

    return RenderedGraphScene(
        image=image,
        panel_geometry={str(key): value for key, value in panel_geometry.items()},
        nodes=tuple(rendered_nodes),
        edges=tuple(rendered_edges),
        layout_variant=str(actual_layout_variant),
        layout_transform_variant=str(actual_layout_transform_variant),
        crossing_count=_count_edge_crossings(edge_segments),
    )


__all__ = [
    "GraphRenderParams",
    "RenderedGraphEdge",
    "RenderedGraphNode",
    "RenderedGraphScene",
    "SUPPORTED_LAYOUT_TRANSFORM_VARIANTS",
    "SUPPORTED_NODE_SHAPE_VARIANTS",
    "render_graph_scene",
]
