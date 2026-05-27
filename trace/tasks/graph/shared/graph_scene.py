"""Shared node-link graph rendering helpers for graph-domain tasks."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import networkx as nx
from PIL import Image, ImageDraw, ImageFont

from ...shared.text_rendering import draw_text_centered, fit_font_to_box, load_font
from ...shared.visual_style.information_scene import (
    information_scene_style_from_metadata,
    make_information_scene_background,
)
from .graph_sampling import GraphTopologySample


Point = Tuple[int, int]
BBox = Tuple[int, int, int, int]
SUPPORTED_NODE_SHAPE_VARIANTS: Tuple[str, ...] = ("circle", "rounded_square", "hexagon")
SUPPORTED_EDGE_ROUTING_VARIANTS: Tuple[str, ...] = ("straight", "mixed_arc")
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
    edge_routing_variant: str
    node_radius_px: int
    edge_width_px: int
    arrow_length_px: int
    arrow_width_px: int
    node_border_width_px: int
    label_font_size_px: int
    theme_tone: str
    panel_style_variant: str
    background_color_rgb: Tuple[int, int, int]
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    title_color_rgb: Tuple[int, int, int]
    edge_color_rgb: Tuple[int, int, int]
    node_fill_rgb: Tuple[int, int, int]
    node_border_rgb: Tuple[int, int, int]
    label_text_rgb: Tuple[int, int, int]
    label_stroke_rgb: Tuple[int, int, int]
    information_scene_style: Dict[str, Any] | None = None


@dataclass(frozen=True)
class RenderedGraphNode:
    """Trace-ready node placement for one rendered graph scene."""

    label: str
    degree: int
    center_xy: Point
    bbox_xyxy: BBox
    neighbors: Tuple[str, ...]
    successors: Tuple[str, ...] = ()
    predecessors: Tuple[str, ...] = ()
    color_name: str | None = None
    fill_rgb: Tuple[int, int, int] | None = None
    border_rgb: Tuple[int, int, int] | None = None
    label_text_rgb: Tuple[int, int, int] | None = None
    label_stroke_rgb: Tuple[int, int, int] | None = None


@dataclass(frozen=True)
class RenderedGraphEdge:
    """Trace-ready edge segment for one rendered graph scene."""

    edge_id: str
    node_u_label: str
    node_v_label: str
    directed: bool
    segment_px: Tuple[Point, Point]
    route_variant: str = "straight"
    control_px: Point | None = None
    weight: int | None = None
    weight_label_bbox_xyxy: BBox | None = None
    edge_label: str | None = None
    edge_label_bbox_xyxy: BBox | None = None
    color_name: str | None = None
    edge_color_rgb: Tuple[int, int, int] | None = None


@dataclass(frozen=True)
class RenderedGraphScene:
    """Full render output for one graph scene."""

    image: Image.Image
    panel_geometry: Dict[str, Any]
    nodes: Tuple[RenderedGraphNode, ...]
    edges: Tuple[RenderedGraphEdge, ...]
    layout_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    crossing_count: int
    resolved_label_font_size_px: int
    resolved_label_stroke_width_px: int


def projected_node_point_evidence(
    rendered_scene: RenderedGraphScene,
    labels: Sequence[str],
) -> Dict[str, Any]:
    """Project ordered node labels into pixel point and bbox evidence."""

    requested = [str(label) for label in labels]
    node_by_label = {str(node.label): node for node in rendered_scene.nodes}
    point_map: Dict[str, List[float]] = {}
    point_set: List[List[float]] = []
    bbox_set: List[List[float]] = []
    for label in requested:
        node = node_by_label.get(str(label))
        if node is None:
            continue
        point = [float(node.center_xy[0]), float(node.center_xy[1])]
        bbox = [float(value) for value in node.bbox_xyxy]
        point_map[str(label)] = list(point)
        point_set.append(list(point))
        bbox_set.append(list(bbox))
    return {
        "pixel_point_map": point_map,
        "pixel_point_set": point_set,
        "pixel_point_sequence": list(point_set),
        "pixel_bbox_set": bbox_set,
    }


def projected_edge_pair_evidence(
    rendered_scene: RenderedGraphScene,
    edges: Sequence[Sequence[str]],
) -> Dict[str, Any]:
    """Project ordered edge label pairs into node-center point pairs."""

    node_by_label = {str(node.label): node for node in rendered_scene.nodes}

    point_pair_set: List[List[List[float]]] = []
    for edge in edges:
        endpoints = [str(value) for value in edge]
        if len(endpoints) != 2:
            continue
        left_label, right_label = endpoints
        left_node = node_by_label.get(str(left_label))
        right_node = node_by_label.get(str(right_label))
        if left_node is None or right_node is None:
            continue
        pair = [
            [float(left_node.center_xy[0]), float(left_node.center_xy[1])],
            [float(right_node.center_xy[0]), float(right_node.center_xy[1])],
        ]
        point_pair_set.append([list(point) for point in pair])
    return {
        "point_pair_set": point_pair_set,
    }


def projected_edge_label_bbox_evidence(
    rendered_scene: RenderedGraphScene,
    edge: Sequence[str],
) -> Dict[str, Any]:
    """Project one rendered edge label into bbox evidence."""

    endpoints = [str(value) for value in edge]
    if len(endpoints) != 2:
        return {"bbox_set": [], "pixel_bbox_set": []}
    left_label, right_label = endpoints
    for rendered_edge in rendered_scene.edges:
        if str(rendered_edge.node_u_label) != str(left_label) or str(rendered_edge.node_v_label) != str(right_label):
            continue
        bbox = rendered_edge.edge_label_bbox_xyxy
        if bbox is None:
            return {"bbox_set": [], "pixel_bbox_set": []}
        bbox_value = [float(value) for value in bbox]
        return {"bbox_set": [list(bbox_value)], "pixel_bbox_set": [list(bbox_value)]}
    return {"bbox_set": [], "pixel_bbox_set": []}


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
    if len(sorted_nodes) <= 2:
        return _circular_layout(graph)
    inner_shell_size = max(1, min(len(sorted_nodes) - 1, int(round(len(sorted_nodes) * 0.35)))) if len(sorted_nodes) > 2 else 1
    inner_nodes = tuple(int(node) for node in sorted_nodes[:inner_shell_size])
    outer_nodes = tuple(int(node) for node in sorted_nodes[inner_shell_size:])
    positions: Dict[int, Tuple[float, float]] = {}
    if len(inner_nodes) == 1:
        positions[int(inner_nodes[0])] = (0.0, 0.0)
    else:
        inner_phase = math.pi / float(max(4, len(inner_nodes) * 2))
        for index, node in enumerate(inner_nodes):
            angle = float(inner_phase) + ((2.0 * math.pi * float(index)) / float(len(inner_nodes)))
            positions[int(node)] = (0.46 * math.cos(angle), 0.46 * math.sin(angle))
    outer_phase = math.pi / float(max(3, len(outer_nodes)))
    for index, node in enumerate(outer_nodes):
        angle = float(outer_phase) + ((2.0 * math.pi * float(index)) / float(max(1, len(outer_nodes))))
        positions[int(node)] = (math.cos(angle), math.sin(angle))
    return positions


def _sorted_graph_nodes(graph: nx.Graph) -> Tuple[int, ...]:
    """Return graph nodes in a stable numeric order."""

    return tuple(sorted((int(node) for node in graph.nodes())))


def _component_node_sets(graph: nx.Graph) -> Tuple[Tuple[int, ...], ...]:
    """Return weak/undirected components in stable largest-first order."""

    if graph.is_directed():
        components = nx.weakly_connected_components(graph)  # type: ignore[arg-type]
    else:
        components = nx.connected_components(graph)
    ordered = [tuple(sorted(int(node) for node in component)) for component in components]
    return tuple(sorted(ordered, key=lambda nodes: (-len(nodes), nodes[0] if nodes else 0)))


def _grid_jitter_layout(graph: nx.Graph, *, seed: int) -> Dict[int, Point]:
    """Return a jittered grid layout in abstract coordinates."""

    nodes = _sorted_graph_nodes(graph)
    node_count = len(nodes)
    if node_count <= 0:
        return {}
    rng = random.Random(int(seed) + 17)
    columns = max(1, int(math.ceil(math.sqrt(float(node_count)))))
    rows = max(1, int(math.ceil(float(node_count) / float(columns))))
    positions: Dict[int, Tuple[float, float]] = {}
    for index, node in enumerate(nodes):
        row = int(index // columns)
        column = int(index % columns)
        jitter_x = (rng.random() - 0.5) * 0.28
        jitter_y = (rng.random() - 0.5) * 0.28
        positions[int(node)] = (
            float(column - ((columns - 1) / 2.0) + jitter_x),
            float(row - ((rows - 1) / 2.0) + jitter_y),
        )
    return positions


def _component_subgraph(graph: nx.Graph, nodes: Sequence[int]) -> nx.Graph:
    """Return a copied subgraph for one component."""

    return graph.subgraph(tuple(int(node) for node in nodes)).copy()


def _component_clustered_layout(graph: nx.Graph, *, seed: int) -> Dict[int, Point]:
    """Return a layout that separates connected components into visual clusters."""

    components = _component_node_sets(graph)
    if not components:
        return {}
    if len(components) == 1:
        nodes = tuple(int(node) for node in components[0])
        if len(nodes) <= 2:
            return _circular_layout(graph)
        undirected = graph.to_undirected() if graph.is_directed() else graph
        seed_nodes = [sorted(nodes, key=lambda node: (-int(undirected.degree(int(node))), int(node)))[0]]
        while len(seed_nodes) < min(3, len(nodes)):
            distances_by_candidate = []
            for node in nodes:
                if int(node) in set(seed_nodes):
                    continue
                shortest = min(
                    int(nx.shortest_path_length(undirected, int(node), int(seed_node)))
                    for seed_node in seed_nodes
                )
                distances_by_candidate.append((int(shortest), -int(node), int(node)))
            if not distances_by_candidate:
                break
            seed_nodes.append(max(distances_by_candidate)[2])
        clusters: Dict[int, List[int]] = {int(index): [] for index in range(len(seed_nodes))}
        for node in nodes:
            best_index = min(
                range(len(seed_nodes)),
                key=lambda index: (
                    int(nx.shortest_path_length(undirected, int(node), int(seed_nodes[int(index)]))),
                    int(index),
                ),
            )
            clusters[int(best_index)].append(int(node))
        positions: Dict[int, Tuple[float, float]] = {}
        center_radius = 1.22
        for cluster_index, cluster_nodes in sorted(clusters.items()):
            angle = (2.0 * math.pi * float(cluster_index)) / float(max(1, len(clusters)))
            center = (float(center_radius * math.cos(angle)), float(center_radius * math.sin(angle)))
            ordered = sorted(cluster_nodes)
            if len(ordered) == 1:
                positions[int(ordered[0])] = tuple(float(value) for value in center)
                continue
            local_radius = 0.46 + (0.04 * float(len(ordered)))
            for index, node in enumerate(ordered):
                local_angle = angle + math.pi + ((2.0 * math.pi * float(index)) / float(len(ordered)))
                positions[int(node)] = (
                    float(center[0] + (local_radius * math.cos(local_angle))),
                    float(center[1] + (local_radius * math.sin(local_angle))),
                )
        return positions

    center_radius = max(1.5, 0.72 * float(len(components)))
    positions: Dict[int, Tuple[float, float]] = {}
    for component_index, component_nodes in enumerate(components):
        angle = (2.0 * math.pi * float(component_index)) / float(len(components))
        center = (float(center_radius * math.cos(angle)), float(center_radius * math.sin(angle)))
        subgraph = _component_subgraph(graph, component_nodes)
        if len(component_nodes) == 1:
            local = {int(component_nodes[0]): (0.0, 0.0)}
        elif len(component_nodes) == 2:
            local = {
                int(component_nodes[0]): (-0.35, 0.0),
                int(component_nodes[1]): (0.35, 0.0),
            }
        else:
            local = _spring_layout(subgraph, seed=int(seed) + 31 + int(component_index))
        local_scale = min(0.72, max(0.34, 0.18 * math.sqrt(float(len(component_nodes)))))
        for node, point in local.items():
            positions[int(node)] = (
                float(center[0] + (float(point[0]) * float(local_scale))),
                float(center[1] + (float(point[1]) * float(local_scale))),
            )
    return positions


def _layer_ranks_for_component(graph: nx.Graph, component_nodes: Sequence[int]) -> Dict[int, int]:
    """Return stable layer ranks for one component."""

    nodes = tuple(int(node) for node in component_nodes)
    if not nodes:
        return {}
    subgraph = graph.subgraph(nodes).copy()
    if graph.is_directed() and nx.is_directed_acyclic_graph(subgraph):
        ranks = {int(node): 0 for node in nodes}
        for node in nx.topological_sort(subgraph):
            predecessors = [int(pred) for pred in subgraph.predecessors(int(node))]
            if predecessors:
                ranks[int(node)] = max(int(ranks[int(pred)]) + 1 for pred in predecessors)
        return ranks

    undirected = subgraph.to_undirected() if subgraph.is_directed() else subgraph
    root = sorted(nodes, key=lambda node: (-int(undirected.degree(int(node))), int(node)))[0]
    distances = nx.single_source_shortest_path_length(undirected, int(root))
    return {int(node): int(distances.get(int(node), 0)) for node in nodes}


def _layered_layout(graph: nx.Graph) -> Dict[int, Point]:
    """Return a rank/layer layout in abstract coordinates."""

    components = _component_node_sets(graph)
    positions: Dict[int, Tuple[float, float]] = {}
    x_offset = 0.0
    for component_nodes in components:
        ranks = _layer_ranks_for_component(graph, component_nodes)
        layers: Dict[int, List[int]] = {}
        for node, rank in ranks.items():
            layers.setdefault(int(rank), []).append(int(node))
        if not layers:
            continue
        max_rank = max(layers)
        for rank in sorted(layers):
            layer_nodes = sorted(layers[int(rank)], key=lambda node: (-int(graph.degree(int(node))), int(node)))
            for index, node in enumerate(layer_nodes):
                x_jitter = 0.22 * (float(index) - ((float(len(layer_nodes)) - 1.0) / 2.0))
                y = float(index - ((len(layer_nodes) - 1) / 2.0))
                if len(layer_nodes) == 1 and max_rank > 1:
                    y += 0.34 * math.sin(float(rank) * 1.1)
                positions[int(node)] = (float(x_offset + float(rank) + x_jitter), float(y))
        x_offset += float(max_rank) + 2.0
    return positions


def _label_to_node_map(graph_sample: GraphTopologySample) -> Dict[str, int]:
    """Return a label-to-node map for one topology sample."""

    return {str(label): int(node) for node, label in zip(graph_sample.graph.nodes(), graph_sample.node_labels)}


def _path_spine_nodes(graph_sample: GraphTopologySample) -> Tuple[int, ...]:
    """Return a meaningful path to use as a visual spine."""

    label_to_node = _label_to_node_map(graph_sample)
    target_labels = tuple(str(label) for label in getattr(graph_sample, "target_labels", ()) or ())
    if len(target_labels) >= 2 and all(str(label) in label_to_node for label in target_labels):
        return tuple(int(label_to_node[str(label)]) for label in target_labels)

    graph = graph_sample.graph
    undirected = graph.to_undirected() if graph.is_directed() else graph
    best_path: Tuple[int, ...] = ()
    for component_nodes in _component_node_sets(undirected):
        if len(component_nodes) == 1:
            candidate = tuple(int(node) for node in component_nodes)
        else:
            start = int(component_nodes[0])
            first_distances = nx.single_source_shortest_path_length(undirected, start)
            farthest = max(component_nodes, key=lambda node: (int(first_distances.get(int(node), -1)), -int(node)))
            second_distances = nx.single_source_shortest_path_length(undirected, int(farthest))
            other = max(component_nodes, key=lambda node: (int(second_distances.get(int(node), -1)), -int(node)))
            candidate = tuple(int(node) for node in nx.shortest_path(undirected, int(farthest), int(other)))
        if len(candidate) > len(best_path):
            best_path = tuple(int(node) for node in candidate)
    return best_path or _sorted_graph_nodes(graph)


def _path_spine_layout(graph_sample: GraphTopologySample) -> Dict[int, Point]:
    """Return a layout with one important path as a horizontal spine."""

    graph = graph_sample.graph
    spine = _path_spine_nodes(graph_sample)
    if not spine:
        return _circular_layout(graph)
    spine_index = {int(node): int(index) for index, node in enumerate(spine)}
    positions: Dict[int, Tuple[float, float]] = {
        int(node): (
            float(index),
            0.0 if len(spine) <= 2 else 0.20 * math.sin(float(index) * 1.1),
        )
        for index, node in enumerate(spine)
    }
    undirected = graph.to_undirected() if graph.is_directed() else graph
    buckets: Dict[int, List[Tuple[int, int]]] = {int(index): [] for index in range(len(spine))}
    fallback_bucket = len(spine) - 1
    for node in _sorted_graph_nodes(graph):
        if int(node) in spine_index:
            continue
        best_anchor = fallback_bucket
        best_distance = 10**9
        for anchor_node, anchor_index in spine_index.items():
            try:
                distance = int(nx.shortest_path_length(undirected, int(node), int(anchor_node)))
            except nx.NetworkXNoPath:
                continue
            if (distance, anchor_index) < (best_distance, best_anchor):
                best_distance = int(distance)
                best_anchor = int(anchor_index)
        buckets.setdefault(int(best_anchor), []).append((int(best_distance if best_distance < 10**9 else 1), int(node)))

    for anchor_index, entries in sorted(buckets.items()):
        ordered_entries = sorted(entries, key=lambda item: (item[0], item[1]))
        if not ordered_entries:
            continue
        # Keep each anchor's off-spine branch on one side of the spine. Alternating
        # individual nodes can make non-spine edges cut back through the anchor and
        # visually merge with incident spine edges.
        side = 1.0 if int(anchor_index) % 2 == 0 else -1.0
        center_slot = (float(len(ordered_entries)) - 1.0) / 2.0
        fan_half_angle = min(1.22, 0.68 + (0.22 * float(max(0, len(ordered_entries) - 1))))
        for entry_index, (distance, node) in enumerate(ordered_entries):
            slot = float(entry_index) - float(center_slot)
            distance_scale = float(max(1, int(distance)))
            slot_norm = 0.0 if center_slot <= 0.0 else float(slot) / float(center_slot)
            base_angle = (math.pi / 2.0) if side > 0.0 else (-math.pi / 2.0)
            angle = float(base_angle) + (float(slot_norm) * float(fan_half_angle))
            radius = 1.48 + (0.78 * distance_scale) + (0.12 * abs(float(slot)))
            horizontal_shift = float(radius) * math.cos(float(angle))
            vertical_shift = float(radius) * math.sin(float(angle))
            positions[int(node)] = (float(anchor_index) + float(horizontal_shift), float(vertical_shift))
    return positions


def _radial_tree_layout(graph_sample: GraphTopologySample, *, seed: int) -> Dict[int, Point]:
    """Return a rooted radial layout for each component."""

    graph = graph_sample.graph
    undirected = graph.to_undirected() if graph.is_directed() else graph
    label_to_node = _label_to_node_map(graph_sample)
    source_label = str(getattr(graph_sample, "source_label", "") or "")
    preferred_root = label_to_node.get(source_label)
    components = _component_node_sets(undirected)
    if not components:
        return {}
    component_center_radius = 0.0 if len(components) == 1 else max(1.7, 0.70 * float(len(components)))
    positions: Dict[int, Tuple[float, float]] = {}
    for component_index, component_nodes in enumerate(components):
        component_set = set(int(node) for node in component_nodes)
        if preferred_root in component_set:
            root = int(preferred_root)
        else:
            root = sorted(component_nodes, key=lambda node: (-int(undirected.degree(int(node))), int(node)))[0]
        if len(components) == 1:
            center = (0.0, 0.0)
        else:
            angle = (2.0 * math.pi * float(component_index)) / float(len(components))
            center = (
                float(component_center_radius * math.cos(angle)),
                float(component_center_radius * math.sin(angle)),
            )
        distances = nx.single_source_shortest_path_length(undirected.subgraph(component_nodes), int(root))
        layers: Dict[int, List[int]] = {}
        for node in component_nodes:
            layers.setdefault(int(distances.get(int(node), 0)), []).append(int(node))
        phase = (random.Random(int(seed) + 43 + int(component_index)).random() * 2.0 * math.pi)
        layer_scale = 0.62 if len(components) > 1 else 1.0
        for distance, layer_nodes in sorted(layers.items()):
            ordered = sorted(layer_nodes, key=lambda node: (-int(undirected.degree(int(node))), int(node)))
            if int(distance) == 0:
                positions[int(root)] = tuple(float(value) for value in center)
                continue
            for index, node in enumerate(ordered):
                angle = (
                    float(phase)
                    + ((2.0 * math.pi * float(index)) / float(max(1, len(ordered))))
                    + (0.19 * float(distance))
                )
                radius = (1.16 * float(distance) * float(layer_scale)) + (0.08 * float(index))
                positions[int(node)] = (
                    float(center[0] + (radius * math.cos(angle))),
                    float(center[1] + (radius * math.sin(angle))),
                )
    return positions


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


def _min_incident_edge_angle_degrees(graph: nx.Graph, positions: Mapping[int, Point]) -> float:
    """Return the minimum angle between incident straight-edge rays."""

    incident_graph = graph.to_undirected() if graph.is_directed() else graph
    min_angle = float("inf")
    for raw_node in incident_graph.nodes():
        node = int(raw_node)
        center = positions.get(int(node))
        if center is None:
            continue
        vectors: List[Tuple[float, float]] = []
        for raw_neighbor in sorted(incident_graph.neighbors(raw_node), key=lambda value: int(value)):
            neighbor = int(raw_neighbor)
            neighbor_point = positions.get(int(neighbor))
            if neighbor_point is None:
                continue
            dx = float(neighbor_point[0]) - float(center[0])
            dy = float(neighbor_point[1]) - float(center[1])
            norm = float(math.hypot(dx, dy))
            if norm <= 1e-6:
                continue
            vectors.append((float(dx / norm), float(dy / norm)))
        for index, left in enumerate(vectors):
            for right in vectors[index + 1 :]:
                dot = max(-1.0, min(1.0, float((left[0] * right[0]) + (left[1] * right[1]))))
                angle = math.degrees(math.acos(dot))
                min_angle = min(float(min_angle), float(angle))
    return float(min_angle)


def _raw_layout_for_variant(
    graph_sample: GraphTopologySample,
    *,
    layout_variant: str,
    layout_seed: int,
) -> Tuple[Dict[int, Point], str]:
    """Resolve abstract coordinates for one requested layout variant."""

    graph = graph_sample.graph
    requested = str(layout_variant)
    if requested == "shell":
        return _shell_layout(graph), "shell"
    if requested == "spring":
        return _spring_layout(graph, seed=int(layout_seed)), "spring"
    if requested == "grid_jitter":
        return _grid_jitter_layout(graph, seed=int(layout_seed)), "grid_jitter"
    if requested == "layered":
        return _layered_layout(graph), "layered"
    if requested == "component_clustered":
        return _component_clustered_layout(graph, seed=int(layout_seed)), "component_clustered"
    if requested == "path_spine":
        return _path_spine_layout(graph_sample), "path_spine"
    if requested == "radial_tree":
        return _radial_tree_layout(graph_sample, seed=int(layout_seed)), "radial_tree"
    return _circular_layout(graph), "circular"


def _resolve_positions(
    graph_sample: GraphTopologySample,
    *,
    layout_variant: str,
    layout_transform_variant: str,
    content_bbox: BBox,
    node_radius_px: int,
    layout_seed: int,
    layout_fallback_variants: Sequence[str] | None = None,
) -> Tuple[Dict[int, Point], str, str]:
    """Resolve pixel node centers for one graph layout variant."""

    graph = graph_sample.graph
    actual_transform = str(layout_transform_variant)
    min_node_distance_px = float(max(18, int(node_radius_px) * 2 + 4))
    min_incident_angle_degrees = float(max(5.0, min(8.0, float(node_radius_px) * 0.25)))
    fallback_variants = tuple(str(value) for value in layout_fallback_variants) if layout_fallback_variants is not None else (
        "spring",
        "shell",
        "circular",
    )
    seed_offsets = {"spring": 97, "shell": 0, "circular": 0}
    layout_candidates: List[Tuple[str, int]] = [(str(layout_variant), int(layout_seed))]
    for fallback_variant in fallback_variants:
        if str(fallback_variant) == str(layout_variant):
            continue
        layout_candidates.append((str(fallback_variant), int(layout_seed) + int(seed_offsets.get(str(fallback_variant), 0))))

    best_positions: Dict[int, Point] | None = None
    best_layout = "circular"
    best_score: Tuple[float, float, float, float] | None = None
    for candidate_layout, candidate_seed in layout_candidates:
        raw_positions, actual_layout = _raw_layout_for_variant(
            graph_sample,
            layout_variant=str(candidate_layout),
            layout_seed=int(candidate_seed),
        )
        transformed = _transform_raw_layout(raw_positions, layout_transform_variant=actual_transform)
        positions = _scale_layout_to_content(
            transformed,
            content_bbox=tuple(int(value) for value in content_bbox),
            node_radius_px=int(node_radius_px),
        )
        node_distance = float(_min_node_distance(positions))
        incident_angle = float(_min_incident_edge_angle_degrees(graph, positions))
        angle_score = 180.0 if math.isinf(float(incident_angle)) else float(incident_angle)
        score = (
            1.0 if node_distance >= min_node_distance_px else 0.0,
            1.0 if angle_score >= min_incident_angle_degrees else 0.0,
            float(angle_score),
            float(node_distance),
        )
        if best_score is None or score > best_score:
            best_score = tuple(float(value) for value in score)
            best_positions = dict(positions)
            best_layout = str(actual_layout)
        if node_distance >= min_node_distance_px and angle_score >= min_incident_angle_degrees:
            return positions, str(actual_layout), actual_transform
    if best_positions is None:
        fallback_positions = _scale_layout_to_content(
            _transform_raw_layout(_circular_layout(graph), layout_transform_variant=actual_transform),
            content_bbox=tuple(int(value) for value in content_bbox),
            node_radius_px=int(node_radius_px),
        )
        return fallback_positions, "circular", actual_transform
    return dict(best_positions), str(best_layout), actual_transform


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


def _point_in_bbox(point: Point, bbox: BBox) -> bool:
    """Return whether one pixel point lies inside one axis-aligned bbox."""

    x, y = int(point[0]), int(point[1])
    x0, y0, x1, y1 = [int(value) for value in bbox]
    return bool(x0 <= x <= x1 and y0 <= y <= y1)


def _bbox_intersects_bbox(left: BBox, right: BBox) -> bool:
    """Return whether two axis-aligned bboxes overlap."""

    lx0, ly0, lx1, ly1 = [int(value) for value in left]
    rx0, ry0, rx1, ry1 = [int(value) for value in right]
    return not (lx1 < rx0 or rx1 < lx0 or ly1 < ry0 or ry1 < ly0)


def _segment_intersects_bbox(segment: Tuple[Point, Point], bbox: BBox) -> bool:
    """Return whether one line segment intersects one axis-aligned bbox."""

    start, end = segment
    if _point_in_bbox(start, bbox) or _point_in_bbox(end, bbox):
        return True
    x0, y0, x1, y1 = [int(value) for value in bbox]
    box_edges = (
        ((int(x0), int(y0)), (int(x1), int(y0))),
        ((int(x1), int(y0)), (int(x1), int(y1))),
        ((int(x1), int(y1)), (int(x0), int(y1))),
        ((int(x0), int(y1)), (int(x0), int(y0))),
    )
    return any(_segments_intersect(segment, edge) for edge in box_edges)


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


def _quadratic_bezier_point(start: Point, control: Point, end: Point, t_value: float) -> Tuple[float, float]:
    """Evaluate one quadratic Bezier point."""

    t = min(1.0, max(0.0, float(t_value)))
    inv = 1.0 - t
    x = (inv * inv * float(start[0])) + (2.0 * inv * t * float(control[0])) + (t * t * float(end[0]))
    y = (inv * inv * float(start[1])) + (2.0 * inv * t * float(control[1])) + (t * t * float(end[1]))
    return (float(x), float(y))


def _quadratic_bezier_tangent(start: Point, control: Point, end: Point, t_value: float) -> Tuple[float, float]:
    """Return the normalized tangent for one quadratic Bezier point."""

    t = min(1.0, max(0.0, float(t_value)))
    dx = (2.0 * (1.0 - t) * (float(control[0]) - float(start[0]))) + (2.0 * t * (float(end[0]) - float(control[0])))
    dy = (2.0 * (1.0 - t) * (float(control[1]) - float(start[1]))) + (2.0 * t * (float(end[1]) - float(control[1])))
    norm = float(math.hypot(dx, dy))
    if norm <= 1e-6:
        fallback_dx = float(end[0]) - float(start[0])
        fallback_dy = float(end[1]) - float(start[1])
        fallback_norm = float(math.hypot(fallback_dx, fallback_dy))
        if fallback_norm <= 1e-6:
            return (1.0, 0.0)
        return (float(fallback_dx / fallback_norm), float(fallback_dy / fallback_norm))
    return (float(dx / norm), float(dy / norm))


def _resolve_arc_control_candidates(
    *,
    start: Point,
    end: Point,
    content_bbox: BBox,
    edge_key: Tuple[str, str],
) -> Tuple[Point, ...]:
    """Resolve deterministic arc control points for an edge, outward first."""

    x0, y0 = float(start[0]), float(start[1])
    x1, y1 = float(end[0]), float(end[1])
    dx = float(x1 - x0)
    dy = float(y1 - y0)
    norm = float(math.hypot(dx, dy))
    if norm <= 1e-6:
        point = (int(round(x0)), int(round(y0)))
        return (point,)
    mid_x = 0.5 * float(x0 + x1)
    mid_y = 0.5 * float(y0 + y1)
    perp_x = float(-dy / norm)
    perp_y = float(dx / norm)
    content_center_x = 0.5 * float(int(content_bbox[0]) + int(content_bbox[2]))
    content_center_y = 0.5 * float(int(content_bbox[1]) + int(content_bbox[3]))
    outward_x = float(mid_x - content_center_x)
    outward_y = float(mid_y - content_center_y)
    dot = float((perp_x * outward_x) + (perp_y * outward_y))
    if abs(dot) <= 1e-6:
        edge_hash = sum(ord(char) for char in f"{edge_key[0]}-{edge_key[1]}")
        sign = 1.0 if int(edge_hash) % 2 == 0 else -1.0
    else:
        sign = 1.0 if dot > 0.0 else -1.0
    offset = min(76.0, max(28.0, float(norm) * 0.22))
    controls: List[Point] = []
    for candidate_sign in (sign, -sign):
        control_x = float(mid_x + (candidate_sign * perp_x * offset))
        control_y = float(mid_y + (candidate_sign * perp_y * offset))
        control = (int(round(control_x)), int(round(control_y)))
        if control not in controls:
            controls.append(control)
    return tuple(controls)


def _resolve_arc_control_point(
    *,
    start: Point,
    end: Point,
    content_bbox: BBox,
    edge_key: Tuple[str, str],
) -> Point:
    """Resolve one outward-bowed arc control point for an edge."""

    return _resolve_arc_control_candidates(
        start=start,
        end=end,
        content_bbox=content_bbox,
        edge_key=edge_key,
    )[0]


def _curve_clears_non_endpoint_nodes(
    *,
    start: Point,
    control: Point,
    end: Point,
    other_node_centers: Sequence[Point],
    node_radius_px: int,
) -> bool:
    """Return whether an arced edge stays visually clear of unrelated nodes."""

    if not other_node_centers:
        return True

    sample_count = 64
    min_clearance_px = float(max(48, int(node_radius_px) * 2 + 8))
    for index in range(1, int(sample_count)):
        x, y = _quadratic_bezier_point(
            start,
            control,
            end,
            float(index) / float(sample_count),
        )
        for node_x, node_y in other_node_centers:
            if math.hypot(float(x) - float(node_x), float(y) - float(node_y)) < min_clearance_px:
                return False
    return True


def _resolve_edge_route_controls(
    *,
    edge_labels: Sequence[Tuple[str, str]],
    label_to_node: Mapping[str, int],
    positions: Mapping[int, Point],
    content_bbox: BBox,
    edge_routing_variant: str,
    node_radius_px: int,
) -> Dict[Tuple[str, str], Point | None]:
    """Resolve optional arc controls for one graph render."""

    controls: Dict[Tuple[str, str], Point | None] = {
        (str(left), str(right)): None
        for left, right in edge_labels
    }
    if str(edge_routing_variant) != "mixed_arc" or len(edge_labels) < 3:
        return controls

    node_center_by_label = {
        str(label): tuple(int(value) for value in positions[int(node)])
        for label, node in label_to_node.items()
    }
    scored_edges: List[Tuple[float, str, str, Point]] = []
    min_curve_distance = float(max(64, int(node_radius_px) * 4))
    for left_label, right_label in edge_labels:
        start = tuple(int(value) for value in positions[int(label_to_node[str(left_label)])])
        end = tuple(int(value) for value in positions[int(label_to_node[str(right_label)])])
        distance = math.hypot(float(end[0] - start[0]), float(end[1] - start[1]))
        if distance < min_curve_distance:
            continue
        control_candidates = _resolve_arc_control_candidates(
            start=start,
            end=end,
            content_bbox=tuple(int(value) for value in content_bbox),
            edge_key=(str(left_label), str(right_label)),
        )
        other_node_centers = tuple(
            center
            for label, center in node_center_by_label.items()
            if label not in {str(left_label), str(right_label)}
        )
        selected_control = None
        for control in control_candidates:
            if _curve_clears_non_endpoint_nodes(
                start=start,
                control=tuple(int(value) for value in control),
                end=end,
                other_node_centers=other_node_centers,
                node_radius_px=int(node_radius_px),
            ):
                selected_control = tuple(int(value) for value in control)
                break
        if selected_control is None:
            continue
        scored_edges.append((float(distance), str(left_label), str(right_label), selected_control))
    if not scored_edges:
        return controls

    curve_count = min(len(scored_edges), max(1, int(round(float(len(edge_labels)) * 0.30))))
    for _, left_label, right_label, control in sorted(scored_edges, key=lambda item: (-item[0], item[1], item[2]))[
        :curve_count
    ]:
        controls[(str(left_label), str(right_label))] = tuple(int(value) for value in control)
    return controls


def _draw_edge(
    draw: ImageDraw.ImageDraw,
    *,
    start: Point,
    end: Point,
    control: Point | None = None,
    node_radius_px: int,
    edge_width_px: int,
    edge_color_rgb: Sequence[int],
    directed: bool,
    arrow_length_px: int,
    arrow_width_px: int,
) -> Tuple[Point, Point]:
    """Draw one graph edge and return the visible line segment endpoints."""

    if control is not None:
        sample_count = 48
        samples = [
            _quadratic_bezier_point(start, tuple(int(value) for value in control), end, float(index) / float(sample_count))
            for index in range(int(sample_count) + 1)
        ]
        radius = float(max(1, int(node_radius_px)))
        start_index = 0
        for index, point in enumerate(samples):
            if math.hypot(float(point[0]) - float(start[0]), float(point[1]) - float(start[1])) >= radius:
                start_index = int(index)
                break
        tip_index = int(sample_count)
        for index in range(int(sample_count), -1, -1):
            point = samples[int(index)]
            if math.hypot(float(point[0]) - float(end[0]), float(point[1]) - float(end[1])) >= radius:
                tip_index = int(index)
                break
        if tip_index <= start_index:
            return (start, end)

        tip = samples[int(tip_index)]
        tangent = _quadratic_bezier_tangent(
            start,
            tuple(int(value) for value in control),
            end,
            float(tip_index) / float(sample_count),
        )
        line_points = [
            (float(point[0]), float(point[1]))
            for point in samples[int(start_index) : int(tip_index) + 1]
        ]
        if bool(directed):
            line_end = (
                float(tip[0] - (tangent[0] * max(4, int(arrow_length_px) - 1))),
                float(tip[1] - (tangent[1] * max(4, int(arrow_length_px) - 1))),
            )
            if line_points:
                line_points[-1] = line_end
        else:
            line_end = tuple(float(value) for value in tip)
        draw.line(
            line_points,
            fill=tuple(int(v) for v in edge_color_rgb),
            width=max(1, int(edge_width_px)),
        )
        if bool(directed):
            perp_x = float(-tangent[1])
            perp_y = float(tangent[0])
            base = (
                float(tip[0] - (tangent[0] * int(arrow_length_px))),
                float(tip[1] - (tangent[1] * int(arrow_length_px))),
            )
            left = (
                float(base[0] + (perp_x * int(arrow_width_px))),
                float(base[1] + (perp_y * int(arrow_width_px))),
            )
            right = (
                float(base[0] - (perp_x * int(arrow_width_px))),
                float(base[1] - (perp_y * int(arrow_width_px))),
            )
            draw.polygon(
                [
                    (int(round(tip[0])), int(round(tip[1]))),
                    (int(round(left[0])), int(round(left[1]))),
                    (int(round(right[0])), int(round(right[1]))),
                ],
                fill=tuple(int(v) for v in edge_color_rgb),
            )
        line_start = line_points[0]
        return (
            (int(round(line_start[0])), int(round(line_start[1]))),
            (int(round(line_end[0])), int(round(line_end[1]))),
        )

    x0, y0 = float(start[0]), float(start[1])
    x1, y1 = float(end[0]), float(end[1])
    dx = float(x1 - x0)
    dy = float(y1 - y0)
    norm = float(math.hypot(dx, dy))
    if norm <= 1e-6:
        return (start, end)
    ux = float(dx / norm)
    uy = float(dy / norm)
    radius = float(max(1, int(node_radius_px)))
    line_start = (float(x0 + (ux * radius)), float(y0 + (uy * radius)))
    tip = (float(x1 - (ux * radius)), float(y1 - (uy * radius)))
    if bool(directed):
        line_end = (
            float(tip[0] - (ux * max(4, int(arrow_length_px) - 1))),
            float(tip[1] - (uy * max(4, int(arrow_length_px) - 1))),
        )
    else:
        line_end = tip
    draw.line(
        (line_start[0], line_start[1], line_end[0], line_end[1]),
        fill=tuple(int(v) for v in edge_color_rgb),
        width=max(1, int(edge_width_px)),
    )
    if bool(directed):
        perp_x = float(-uy)
        perp_y = float(ux)
        base = (
            float(tip[0] - (ux * int(arrow_length_px))),
            float(tip[1] - (uy * int(arrow_length_px))),
        )
        left = (
            float(base[0] + (perp_x * int(arrow_width_px))),
            float(base[1] + (perp_y * int(arrow_width_px))),
        )
        right = (
            float(base[0] - (perp_x * int(arrow_width_px))),
            float(base[1] - (perp_y * int(arrow_width_px))),
        )
        draw.polygon(
            [
                (int(round(tip[0])), int(round(tip[1]))),
                (int(round(left[0])), int(round(left[1]))),
                (int(round(right[0])), int(round(right[1]))),
            ],
            fill=tuple(int(v) for v in edge_color_rgb),
        )
    return (
        (int(round(line_start[0])), int(round(line_start[1]))),
        (int(round(line_end[0])), int(round(line_end[1]))),
    )


def _draw_edge_boxed_label(
    draw: ImageDraw.ImageDraw,
    *,
    box: BBox,
    text: str,
    font_size_px: int,
    box_fill_rgb: Sequence[int],
    box_border_rgb: Sequence[int],
    text_rgb: Sequence[int],
) -> BBox:
    """Draw one boxed edge label inside the provided bbox."""

    font = load_font(max(14, int(font_size_px)), bold=True)
    resolved_font_size = float(getattr(font, "size", font_size_px))
    stroke_width = max(1, int(round(resolved_font_size * 0.12)))
    center = (0.5 * float(box[0] + box[2]), 0.5 * float(box[1] + box[3]))
    draw.rounded_rectangle(
        box,
        radius=max(6, int(round((min(int(box[2] - box[0]), int(box[3] - box[1])) * 0.22)))),
        fill=tuple(int(value) for value in box_fill_rgb),
        outline=tuple(int(value) for value in box_border_rgb),
        width=max(2, int(round(resolved_font_size * 0.10))),
    )
    draw_text_centered(
        draw,
        text=text,
        center=center,
        font=font,
        fill=tuple(int(value) for value in text_rgb),
        stroke_fill=tuple(int(value) for value in box_fill_rgb),
        stroke_width=int(stroke_width),
    )
    return tuple(int(value) for value in box)


def _draw_edge_weight_label(
    draw: ImageDraw.ImageDraw,
    *,
    box: BBox,
    weight: int,
    font_size_px: int,
    box_fill_rgb: Sequence[int],
    box_border_rgb: Sequence[int],
    text_rgb: Sequence[int],
) -> BBox:
    """Draw one boxed edge-weight label inside the provided bbox."""

    return _draw_edge_boxed_label(
        draw,
        box=tuple(int(value) for value in box),
        text=str(int(weight)),
        font_size_px=int(font_size_px),
        box_fill_rgb=tuple(int(value) for value in box_fill_rgb),
        box_border_rgb=tuple(int(value) for value in box_border_rgb),
        text_rgb=tuple(int(value) for value in text_rgb),
    )


def _resolve_edge_boxed_label_box(
    draw: ImageDraw.ImageDraw,
    *,
    segment: Tuple[Point, Point],
    text: str,
    font_size_px: int,
    offset_px: int,
    padding_px: int,
    content_bbox: BBox,
    other_segments: Sequence[Tuple[Point, Point]],
    reserved_boxes: Sequence[BBox],
    node_bboxes: Sequence[BBox],
    side_seed: int,
) -> BBox:
    """Choose one readable edge-label bbox that avoids edge and node collisions."""

    start, end = segment
    x0, y0 = float(start[0]), float(start[1])
    x1, y1 = float(end[0]), float(end[1])
    dx = float(x1 - x0)
    dy = float(y1 - y0)
    norm = float(math.hypot(dx, dy))
    mid_x = 0.5 * float(x0 + x1)
    mid_y = 0.5 * float(y0 + y1)
    if float(norm) <= 1e-6:
        norm_x, norm_y = 0.0, -1.0
    else:
        norm_x = float(-dy / norm)
        norm_y = float(dx / norm)

    font = load_font(max(14, int(font_size_px)), bold=True)
    label_text = str(text)
    stroke_width = max(1, int(round(float(getattr(font, "size", font_size_px)) * 0.10)))
    raw_bbox = draw.textbbox((0, 0), label_text, font=font, stroke_width=int(stroke_width))
    text_width = max(1, int(raw_bbox[2] - raw_bbox[0]))
    text_height = max(1, int(raw_bbox[3] - raw_bbox[1]))
    pad = max(2, int(padding_px))
    half_w = float((text_width / 2.0) + pad)
    half_h = float((text_height / 2.0) + pad)
    required_clearance = float(abs(norm_x) * half_w) + float(abs(norm_y) * half_h) + float(max(4, pad))

    preferred_signs = (1, -1) if int(side_seed) % 2 == 0 else (-1, 1)
    t_positions = (0.50, 0.42, 0.58, 0.34, 0.66, 0.26, 0.74)
    offset_scales = (1.0, 1.35, 1.7, 2.1, 2.5, 3.0)
    content = tuple(int(value) for value in content_bbox)

    best_box: BBox | None = None
    best_score: tuple[float, float, float, float, float] | None = None
    for sign_value in preferred_signs:
        sign = float(sign_value)
        for offset_scale in offset_scales:
            for t_value in t_positions:
                base_x = float(x0 + (float(dx) * float(t_value)))
                base_y = float(y0 + (float(dy) * float(t_value)))
                normal_distance = max(float(offset_px) * float(offset_scale), float(required_clearance))
                center = (
                    float(base_x + (sign * float(norm_x) * float(normal_distance))),
                    float(base_y + (sign * float(norm_y) * float(normal_distance))),
                )
                box = (
                    int(round(center[0] - half_w)),
                    int(round(center[1] - half_h)),
                    int(round(center[0] + half_w)),
                    int(round(center[1] + half_h)),
                )
                out_of_bounds = (
                    max(0, int(content[0] - box[0]))
                    + max(0, int(content[1] - box[1]))
                    + max(0, int(box[2] - content[2]))
                    + max(0, int(box[3] - content[3]))
                )
                own_segment_crossings = int(_segment_intersects_bbox(segment, box))
                segment_crossings = sum(1 for other_segment in other_segments if _segment_intersects_bbox(other_segment, box))
                node_overlaps = sum(1 for node_bbox in node_bboxes if _bbox_intersects_bbox(node_bbox, box))
                label_overlaps = sum(1 for reserved in reserved_boxes if _bbox_intersects_bbox(reserved, box))
                score = (
                    float(own_segment_crossings),
                    float(segment_crossings),
                    float(node_overlaps + label_overlaps),
                    float(out_of_bounds),
                    float(normal_distance + abs(float(t_value) - 0.5)),
                )
                if best_score is None or score < best_score:
                    best_score = score
                    best_box = tuple(int(value) for value in box)
                    if score[:4] == (0.0, 0.0, 0.0, 0.0):
                        return tuple(int(value) for value in best_box)
    if best_box is None:
        raise ValueError("failed to resolve one edge label box")
    return tuple(int(value) for value in best_box)


def _resolve_edge_weight_label_box(
    draw: ImageDraw.ImageDraw,
    *,
    segment: Tuple[Point, Point],
    weight: int,
    font_size_px: int,
    offset_px: int,
    padding_px: int,
    content_bbox: BBox,
    other_segments: Sequence[Tuple[Point, Point]],
    reserved_boxes: Sequence[BBox],
    node_bboxes: Sequence[BBox],
    side_seed: int,
) -> BBox:
    """Choose one readable weight-label bbox that avoids edge and node collisions."""

    return _resolve_edge_boxed_label_box(
        draw,
        segment=tuple(segment),
        text=str(int(weight)),
        font_size_px=int(font_size_px),
        offset_px=int(offset_px),
        padding_px=int(padding_px),
        content_bbox=tuple(int(value) for value in content_bbox),
        other_segments=tuple(other_segments),
        reserved_boxes=tuple(reserved_boxes),
        node_bboxes=tuple(node_bboxes),
        side_seed=int(side_seed),
    )


def _node_label_box(
    *,
    radius: int,
    node_shape_variant: str,
    outline_width: int,
) -> Tuple[float, float]:
    """Return one conservative text-fit box inside a node glyph."""

    inner_diameter = max(4.0, float((2 * int(radius)) - (2 * max(1, int(outline_width))) - 6))
    shape = str(node_shape_variant)
    if shape == "rounded_square":
        scale = 0.84
    elif shape == "hexagon":
        scale = 0.74
    else:
        scale = 0.68
    side = float(inner_diameter) * float(scale)
    return (float(side), float(side))


def _resolve_node_label_font(
    draw: ImageDraw.ImageDraw,
    *,
    node_labels: Sequence[str],
    render_params: GraphRenderParams,
) -> Tuple[ImageFont.ImageFont, int]:
    """Resolve one fitted node-label font and its stroke width.

    We fit against the longest rendered label so the whole graph uses one
    stable font size while still accommodating multi-character labels such as
    `10` inside compact node glyphs.
    """

    sample_label = max((str(label) for label in node_labels), key=len, default="A")
    max_width, max_height = _node_label_box(
        radius=int(render_params.node_radius_px),
        node_shape_variant=str(render_params.node_shape_variant),
        outline_width=int(render_params.node_border_width_px),
    )
    fitted_font = fit_font_to_box(
        draw,
        text=str(sample_label),
        max_width=float(max_width),
        max_height=float(max_height),
        bold=True,
        min_size_px=10,
        max_size_px=int(render_params.label_font_size_px),
        fill_ratio=0.94,
    )
    stroke_width = max(1, int(round(float(getattr(fitted_font, "size", render_params.label_font_size_px)) * 0.10)))
    return fitted_font, int(stroke_width)


def render_graph_scene(
    *,
    graph_sample: GraphTopologySample,
    layout_variant: str,
    layout_transform_variant: str,
    render_params: GraphRenderParams,
    layout_seed: int,
    scene_title: str = "Graph",
    directed: bool = False,
    base_image: Image.Image | None = None,
    edge_weights_by_label: Mapping[Tuple[str, str], int] | None = None,
    edge_weight_label_font_size_px: int | None = None,
    edge_weight_label_offset_px: int = 12,
    edge_weight_label_padding_px: int = 4,
    edge_text_labels_by_label: Mapping[Tuple[str, str], str] | None = None,
    edge_text_label_font_size_px: int | None = None,
    edge_text_label_offset_px: int = 12,
    edge_text_label_padding_px: int = 5,
    node_style_by_label: Mapping[str, Mapping[str, Any]] | None = None,
    edge_style_by_label: Mapping[Tuple[str, str], Mapping[str, Any]] | None = None,
    layout_fallback_variants: Sequence[str] | None = None,
) -> RenderedGraphScene:
    """Render one labeled single-panel node-link graph scene."""

    panel_geometry = _resolve_panel_geometry(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        outer_margin_px=int(render_params.outer_margin_px),
        panel_padding_px=int(render_params.panel_padding_px),
        title_font_size_px=int(render_params.panel_title_font_size_px),
    )
    if isinstance(render_params.information_scene_style, Mapping):
        panel_geometry["information_scene_style"] = dict(render_params.information_scene_style)
    information_style_meta = render_params.information_scene_style if isinstance(render_params.information_scene_style, Mapping) else None
    information_background_meta: Dict[str, Any] | None = None
    if information_style_meta is not None:
        try:
            information_style = information_scene_style_from_metadata(information_style_meta)
            image, information_background_meta = make_information_scene_background(
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
                style=information_style,
                instance_seed=int(layout_seed),
                namespace="graph.node_link.information_scene_background",
            )
            fill_background = False
        except Exception:
            if base_image is None:
                image = Image.new("RGB", (int(render_params.canvas_width), int(render_params.canvas_height)))
                fill_background = True
            else:
                image = base_image.convert("RGB").copy()
                fill_background = False
    elif base_image is None:
        image = Image.new("RGB", (int(render_params.canvas_width), int(render_params.canvas_height)))
        fill_background = True
    else:
        image = base_image.convert("RGB").copy()
        fill_background = False
    if information_background_meta is not None:
        panel_geometry["information_scene_background_meta"] = dict(information_background_meta)
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
        graph_sample,
        layout_variant=str(layout_variant),
        layout_transform_variant=str(layout_transform_variant),
        content_bbox=content_bbox,
        node_radius_px=int(render_params.node_radius_px),
        layout_seed=int(layout_seed),
        layout_fallback_variants=layout_fallback_variants,
    )

    label_to_node = {str(label): int(node) for node, label in zip(graph_sample.graph.nodes(), graph_sample.node_labels)}
    edge_weight_lookup = {
        (str(left), str(right)): int(weight)
        for (left, right), weight in (edge_weights_by_label or {}).items()
    }
    edge_text_label_lookup = {
        (str(left), str(right)): str(text)
        for (left, right), text in (edge_text_labels_by_label or {}).items()
    }
    actual_edge_routing_variant = (
        str(render_params.edge_routing_variant)
        if str(render_params.edge_routing_variant) in SUPPORTED_EDGE_ROUTING_VARIANTS
        else "straight"
    )
    node_bbox_lookup = {
        str(label): (
            int(positions[int(node)][0] - int(render_params.node_radius_px)),
            int(positions[int(node)][1] - int(render_params.node_radius_px)),
            int(positions[int(node)][0] + int(render_params.node_radius_px)),
            int(positions[int(node)][1] + int(render_params.node_radius_px)),
        )
        for node, label in zip(graph_sample.graph.nodes(), graph_sample.node_labels)
    }
    edge_route_controls = _resolve_edge_route_controls(
        edge_labels=tuple((str(left), str(right)) for left, right in graph_sample.edge_labels),
        label_to_node=label_to_node,
        positions=positions,
        content_bbox=content_bbox,
        edge_routing_variant=str(actual_edge_routing_variant),
        node_radius_px=int(render_params.node_radius_px),
    )
    edge_styles = {
        (str(left), str(right)): dict(style)
        for (left, right), style in (edge_style_by_label or {}).items()
    }
    edge_segments: List[Tuple[Tuple[str, str], Tuple[Point, Point]]] = []
    rendered_edges: List[RenderedGraphEdge] = []
    for left_label, right_label in graph_sample.edge_labels:
        left_node = int(label_to_node[str(left_label)])
        right_node = int(label_to_node[str(right_label)])
        start = tuple(int(value) for value in positions[left_node])
        end = tuple(int(value) for value in positions[right_node])
        control = edge_route_controls.get((str(left_label), str(right_label)))
        edge_style = edge_styles.get((str(left_label), str(right_label)), {})
        edge_color_rgb = tuple(int(v) for v in edge_style.get("edge_color_rgb", render_params.edge_color_rgb))
        edge_width_px = int(edge_style.get("edge_width_px", render_params.edge_width_px))
        segment = _draw_edge(
            draw,
            start=start,
            end=end,
            control=control,
            node_radius_px=int(render_params.node_radius_px),
            edge_width_px=max(1, int(edge_width_px)),
            edge_color_rgb=edge_color_rgb,
            directed=bool(directed),
            arrow_length_px=int(render_params.arrow_length_px),
            arrow_width_px=int(render_params.arrow_width_px),
        )
        edge_segments.append(((str(left_label), str(right_label)), segment))
        rendered_edges.append(
            RenderedGraphEdge(
                edge_id=f"edge_{str(left_label)}_{str(right_label)}",
                node_u_label=str(left_label),
                node_v_label=str(right_label),
                directed=bool(directed),
                segment_px=segment,
                route_variant="arc" if control is not None else "straight",
                control_px=tuple(int(value) for value in control) if control is not None else None,
                color_name=str(edge_style["color_name"]) if edge_style.get("color_name") is not None else None,
                edge_color_rgb=tuple(int(value) for value in edge_color_rgb),
            )
        )

    reserved_edge_label_boxes: List[BBox] = []
    labeled_edges: List[RenderedGraphEdge] = []
    all_segments = [tuple(segment) for _, segment in edge_segments]
    for edge in rendered_edges:
        edge_text_label = edge_text_label_lookup.get((str(edge.node_u_label), str(edge.node_v_label)))
        edge_text_label_bbox = None
        if edge_text_label is not None:
            side_seed = sum(ord(char) for char in f"{edge.node_u_label}-{edge.node_v_label}-label")
            edge_text_label_bbox = _resolve_edge_boxed_label_box(
                draw,
                segment=tuple(edge.segment_px),
                text=str(edge_text_label),
                font_size_px=int(
                    edge_text_label_font_size_px
                    if edge_text_label_font_size_px is not None
                    else max(13, int(render_params.label_font_size_px) - 4)
                ),
                offset_px=int(edge_text_label_offset_px),
                padding_px=int(edge_text_label_padding_px),
                content_bbox=content_bbox,
                other_segments=tuple(
                    segment for segment in all_segments if tuple(segment) != tuple(edge.segment_px)
                ),
                reserved_boxes=tuple(reserved_edge_label_boxes),
                node_bboxes=tuple(node_bbox_lookup.values()),
                side_seed=int(side_seed),
            )
            reserved_edge_label_boxes.append(tuple(int(value) for value in edge_text_label_bbox))
            _draw_edge_boxed_label(
                draw,
                box=tuple(int(value) for value in edge_text_label_bbox),
                text=str(edge_text_label),
                font_size_px=int(
                    edge_text_label_font_size_px
                    if edge_text_label_font_size_px is not None
                    else max(13, int(render_params.label_font_size_px) - 4)
                ),
                box_fill_rgb=tuple(int(v) for v in render_params.panel_fill_rgb),
                box_border_rgb=tuple(int(v) for v in render_params.panel_border_rgb),
                text_rgb=tuple(int(v) for v in render_params.title_color_rgb),
            )

        edge_weight = edge_weight_lookup.get((str(edge.node_u_label), str(edge.node_v_label)))
        weight_label_bbox = None
        if edge_weight is not None:
            side_seed = sum(ord(char) for char in f"{edge.node_u_label}-{edge.node_v_label}")
            weight_label_bbox = _resolve_edge_weight_label_box(
                draw,
                segment=tuple(edge.segment_px),
                weight=int(edge_weight),
                font_size_px=int(
                    edge_weight_label_font_size_px
                    if edge_weight_label_font_size_px is not None
                    else max(12, int(render_params.label_font_size_px) - 4)
                ),
                offset_px=int(edge_weight_label_offset_px),
                padding_px=int(edge_weight_label_padding_px),
                content_bbox=content_bbox,
                other_segments=tuple(
                    segment for segment in all_segments if tuple(segment) != tuple(edge.segment_px)
                ),
                reserved_boxes=tuple(reserved_edge_label_boxes),
                node_bboxes=tuple(node_bbox_lookup.values()),
                side_seed=int(side_seed),
            )
            reserved_edge_label_boxes.append(tuple(int(value) for value in weight_label_bbox))
            _draw_edge_weight_label(
                draw,
                box=tuple(int(value) for value in weight_label_bbox),
                weight=int(edge_weight),
                font_size_px=int(
                    edge_weight_label_font_size_px
                    if edge_weight_label_font_size_px is not None
                    else max(12, int(render_params.label_font_size_px) - 4)
                ),
                box_fill_rgb=tuple(int(v) for v in render_params.panel_fill_rgb),
                box_border_rgb=tuple(int(v) for v in render_params.panel_border_rgb),
                text_rgb=tuple(int(v) for v in render_params.title_color_rgb),
            )
        labeled_edges.append(
            RenderedGraphEdge(
                edge_id=str(edge.edge_id),
                node_u_label=str(edge.node_u_label),
                node_v_label=str(edge.node_v_label),
                directed=bool(edge.directed),
                segment_px=tuple(edge.segment_px),
                route_variant=str(edge.route_variant),
                control_px=tuple(int(value) for value in edge.control_px) if edge.control_px is not None else None,
                weight=int(edge_weight) if edge_weight is not None else None,
                weight_label_bbox_xyxy=tuple(int(value) for value in weight_label_bbox) if weight_label_bbox is not None else None,
                edge_label=str(edge_text_label) if edge_text_label is not None else None,
                edge_label_bbox_xyxy=tuple(int(value) for value in edge_text_label_bbox) if edge_text_label_bbox is not None else None,
                color_name=str(edge.color_name) if edge.color_name is not None else None,
                edge_color_rgb=tuple(int(value) for value in edge.edge_color_rgb) if edge.edge_color_rgb is not None else None,
            )
        )
    rendered_edges = labeled_edges

    label_font, label_stroke_width = _resolve_node_label_font(
        draw,
        node_labels=tuple(str(label) for label in graph_sample.node_labels),
        render_params=render_params,
    )
    rendered_nodes: List[RenderedGraphNode] = []
    radius = int(render_params.node_radius_px)
    node_styles = {str(key): dict(value) for key, value in (node_style_by_label or {}).items()}
    for node, label in zip(graph_sample.graph.nodes(), graph_sample.node_labels):
        center = tuple(int(value) for value in positions[int(node)])
        node_style = node_styles.get(str(label), {})
        fill_rgb = tuple(int(v) for v in node_style.get("fill_rgb", render_params.node_fill_rgb))
        border_rgb = tuple(int(v) for v in node_style.get("border_rgb", render_params.node_border_rgb))
        label_text_rgb = tuple(int(v) for v in node_style.get("label_text_rgb", render_params.label_text_rgb))
        label_stroke_rgb = tuple(int(v) for v in node_style.get("label_stroke_rgb", render_params.label_stroke_rgb))
        if node_style.get("halo_rgb") is not None:
            halo_pad = int(node_style.get("halo_pad_px", 6))
            halo_width = int(node_style.get("halo_width_px", 3))
            halo_bbox = (
                int(center[0] - radius - halo_pad),
                int(center[1] - radius - halo_pad),
                int(center[0] + radius + halo_pad),
                int(center[1] + radius + halo_pad),
            )
            draw.ellipse(
                halo_bbox,
                outline=tuple(int(v) for v in node_style.get("halo_rgb", render_params.title_color_rgb)),
                width=max(1, int(halo_width)),
            )
        bbox = _draw_node_shape(
            draw,
            center=center,
            radius=int(radius),
            node_shape_variant=str(render_params.node_shape_variant),
            fill_rgb=fill_rgb,
            outline_rgb=border_rgb,
            outline_width=int(render_params.node_border_width_px),
        )
        draw_text_centered(
            draw,
            text=str(label),
            center=(float(center[0]), float(center[1])),
            font=label_font,
            fill=label_text_rgb,
            stroke_fill=label_stroke_rgb,
            stroke_width=int(label_stroke_width),
        )
        rendered_nodes.append(
            RenderedGraphNode(
                label=str(label),
                degree=int(graph_sample.degrees_by_label[str(label)]),
                center_xy=center,
                bbox_xyxy=tuple(int(value) for value in bbox),
                neighbors=tuple(str(value) for value in graph_sample.adjacency_by_label[str(label)]),
                successors=tuple(str(value) for value in graph_sample.successors_by_label[str(label)]),
                predecessors=tuple(str(value) for value in graph_sample.predecessors_by_label[str(label)]),
                color_name=str(node_style["color_name"]) if node_style.get("color_name") is not None else None,
                fill_rgb=tuple(int(value) for value in fill_rgb),
                border_rgb=tuple(int(value) for value in border_rgb),
                label_text_rgb=tuple(int(value) for value in label_text_rgb),
                label_stroke_rgb=tuple(int(value) for value in label_stroke_rgb),
            )
        )

    return RenderedGraphScene(
        image=image,
        panel_geometry={str(key): value for key, value in panel_geometry.items()},
        nodes=tuple(rendered_nodes),
        edges=tuple(rendered_edges),
        layout_variant=str(actual_layout_variant),
        layout_transform_variant=str(actual_layout_transform_variant),
        edge_routing_variant=str(actual_edge_routing_variant),
        crossing_count=_count_edge_crossings(edge_segments),
        resolved_label_font_size_px=int(getattr(label_font, "size", int(render_params.label_font_size_px))),
        resolved_label_stroke_width_px=int(label_stroke_width),
    )


__all__ = [
    "GraphRenderParams",
    "RenderedGraphEdge",
    "RenderedGraphNode",
    "RenderedGraphScene",
    "SUPPORTED_EDGE_ROUTING_VARIANTS",
    "SUPPORTED_LAYOUT_TRANSFORM_VARIANTS",
    "SUPPORTED_NODE_SHAPE_VARIANTS",
    "projected_edge_label_bbox_evidence",
    "render_graph_scene",
]
