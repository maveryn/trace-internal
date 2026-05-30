"""Shared pipe-junction graph sampler and renderer."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

import networkx as nx
from PIL import Image, ImageDraw

from ...shared.font_assets import font_asset_version, get_font_family_record
from ...shared.graph_algorithms import bfs_dist_count_by_adjacency, reconstruct_unique_shortest_path_by_adjacency
from ...shared.text_legibility import (
    draw_centered_readable_text,
    resolve_readable_text_style,
    text_legibility_summary_from_records,
)
from ...shared.text_rendering import fit_font_to_box, load_font
from .graph_sampling import canonicalize_graph_edge_label, graph_label_sort_key
from .graph_scene import (
    BBox,
    GraphRenderParams,
    Point,
    apply_graph_content_layout_jitter,
    draw_graph_context_text_blocks,
    draw_graph_context_text_chips,
)
from .label_assets import resolve_graph_node_labels


GridCell = Tuple[int, int]
NodeEdge = Tuple[int, int]
LabelEdge = Tuple[str, str]

SUPPORTED_PIPE_GRID_SHAPE_VARIANTS: Tuple[str, ...] = ("3x4", "3x5", "4x4", "4x5")
SUPPORTED_PIPE_LABEL_VARIANTS: Tuple[str, ...] = ("letters", "numbers")
PIPE_VISUAL_STYLE_IDS: Tuple[str, ...] = (
    "industrial_steel",
    "copper_plumbing",
    "teal_plant",
    "blueprint_tubes",
)


@dataclass(frozen=True)
class PipeJunctionNetworkSample:
    """Trace-ready sampled pipe-junction network."""

    graph: nx.Graph
    node_labels: Tuple[str, ...]
    label_by_node: Dict[int, str]
    node_by_label: Dict[str, int]
    node_grid_cells: Dict[int, GridCell]
    open_edges: Tuple[NodeEdge, ...]
    blocked_edges: Tuple[NodeEdge, ...]
    open_edge_labels: Tuple[LabelEdge, ...]
    blocked_edge_labels: Tuple[LabelEdge, ...]
    adjacency_by_label: Dict[str, Tuple[str, ...]]
    degrees_by_label: Dict[str, int]
    query_label: str = ""
    source_label: str = ""
    goal_label: str = ""
    target_labels: Tuple[str, ...] = ()
    target_edges: Tuple[LabelEdge, ...] = ()
    target_shortest_path_length: int = 0
    target_reachable_count: int = 0
    target_bridge_count: int = 0
    query_distance: int = 0
    target_exact_distance_count: int = 0
    grid_shape_variant: str = ""
    label_variant: str = ""
    label_source_kind: str = ""
    label_bucket: str = ""
    label_manifest: str = ""
    label_filter: Mapping[str, Any] | None = None
    label_bucket_probabilities: Mapping[str, float] | None = None


@dataclass(frozen=True)
class RenderedPipeJunctionNode:
    """One rendered pipe junction."""

    label: str
    open_degree: int
    grid_cell: GridCell
    center_xy: Point
    bbox_xyxy: BBox
    open_neighbors: Tuple[str, ...]


@dataclass(frozen=True)
class RenderedPipeJunctionEdge:
    """One rendered open or blocked pipe segment."""

    edge_id: str
    node_u_label: str
    node_v_label: str
    pipe_state: str
    segment_px: Tuple[Point, Point]


@dataclass(frozen=True)
class RenderedPipeJunctionScene:
    """Full pipe-junction render output."""

    image: Image.Image
    panel_geometry: Dict[str, Any]
    nodes: Tuple[RenderedPipeJunctionNode, ...]
    edges: Tuple[RenderedPipeJunctionEdge, ...]
    grid_shape_variant: str
    resolved_label_font_size_px: int
    resolved_label_stroke_width_px: int
    open_pipe_width_px: int
    blocked_pipe_width_px: int


def parse_pipe_grid_shape(grid_shape_variant: str) -> Tuple[int, int]:
    """Parse one ``RxC`` grid-shape variant."""

    text = str(grid_shape_variant).strip().lower()
    if "x" not in text:
        raise ValueError(f"unsupported pipe grid shape: {grid_shape_variant}")
    left, right = text.split("x", 1)
    rows = int(left)
    cols = int(right)
    if rows <= 1 or cols <= 1:
        raise ValueError(f"unsupported pipe grid shape: {grid_shape_variant}")
    return int(rows), int(cols)


def feasible_pipe_node_counts(*, node_count_min: int, node_count_max: int, grid_shape_variant: str) -> Tuple[int, ...]:
    """Return node counts that fit in the requested pipe grid shape."""

    rows, cols = parse_pipe_grid_shape(str(grid_shape_variant))
    maximum = min(int(node_count_max), int(rows * cols))
    minimum = int(node_count_min)
    if int(minimum) > int(maximum):
        return ()
    return tuple(range(int(minimum), int(maximum) + 1))


def projected_pipe_node_point_evidence(
    rendered_scene: RenderedPipeJunctionScene,
    labels: Sequence[str],
) -> Dict[str, Any]:
    """Project ordered junction labels into pixel point/bbox evidence."""

    node_by_label = {str(node.label): node for node in rendered_scene.nodes}
    point_map: Dict[str, list[float]] = {}
    point_set: list[list[float]] = []
    bbox_set: list[list[float]] = []
    for label in [str(value) for value in labels]:
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


def projected_pipe_edge_pair_evidence(
    rendered_scene: RenderedPipeJunctionScene,
    edges: Sequence[Sequence[str]],
) -> Dict[str, Any]:
    """Project edge endpoint labels into node-center point-pair evidence."""

    node_by_label = {str(node.label): node for node in rendered_scene.nodes}
    point_pair_set: list[list[list[float]]] = []
    for edge in edges:
        endpoints = [str(value) for value in edge]
        if len(endpoints) != 2:
            continue
        left_node = node_by_label.get(endpoints[0])
        right_node = node_by_label.get(endpoints[1])
        if left_node is None or right_node is None:
            continue
        point_pair_set.append(
            [
                [float(left_node.center_xy[0]), float(left_node.center_xy[1])],
                [float(right_node.center_xy[0]), float(right_node.center_xy[1])],
            ]
        )
    return {"point_pair_set": point_pair_set}


def _canonical_node_edge(left: int, right: int) -> NodeEdge:
    """Return one canonical integer node edge."""

    a = int(left)
    b = int(right)
    return (a, b) if a < b else (b, a)


def _sort_node_edges(edges: Sequence[NodeEdge]) -> Tuple[NodeEdge, ...]:
    """Sort canonical integer node edges."""

    return tuple(sorted((_canonical_node_edge(left, right) for left, right in edges), key=lambda edge: (edge[0], edge[1])))


def _grid_cells(rows: int, cols: int) -> Tuple[GridCell, ...]:
    """Return row-major grid cells."""

    return tuple((int(row), int(col)) for row in range(int(rows)) for col in range(int(cols)))


def _sample_connected_cells(
    rng: random.Random,
    *,
    rows: int,
    cols: int,
    node_count: int,
) -> Tuple[GridCell, ...]:
    """Sample one connected subset of grid cells."""

    all_cells = set(_grid_cells(int(rows), int(cols)))
    if int(node_count) > len(all_cells):
        raise ValueError("node_count exceeds pipe grid capacity")

    start = rng.choice(tuple(sorted(all_cells)))
    selected = {start}
    while len(selected) < int(node_count):
        frontier: set[GridCell] = set()
        for row, col in selected:
            for candidate in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                if candidate in all_cells and candidate not in selected:
                    frontier.add(candidate)
        if not frontier:
            raise ValueError("failed to grow connected pipe-cell subset")
        selected.add(rng.choice(tuple(sorted(frontier))))
    return tuple(sorted(selected))


def _candidate_edges_for_cells(cells_by_node: Mapping[int, GridCell]) -> Tuple[NodeEdge, ...]:
    """Return all 4-neighbor candidate pipe edges among selected cells."""

    items = list(cells_by_node.items())
    edges: list[NodeEdge] = []
    for index, (left_node, left_cell) in enumerate(items):
        for right_node, right_cell in items[index + 1 :]:
            distance = abs(int(left_cell[0]) - int(right_cell[0])) + abs(int(left_cell[1]) - int(right_cell[1]))
            if int(distance) == 1:
                edges.append(_canonical_node_edge(int(left_node), int(right_node)))
    return _sort_node_edges(edges)


def _candidate_adjacency(nodes: Sequence[int], candidate_edges: Sequence[NodeEdge]) -> Dict[int, Tuple[int, ...]]:
    """Build adjacency from candidate node edges."""

    adjacency: Dict[int, list[int]] = {int(node): [] for node in nodes}
    for left, right in candidate_edges:
        adjacency[int(left)].append(int(right))
        adjacency[int(right)].append(int(left))
    return {int(node): tuple(sorted(values)) for node, values in adjacency.items()}


def _random_spanning_tree_edges(
    rng: random.Random,
    *,
    nodes: Sequence[int],
    candidate_edges: Sequence[NodeEdge],
) -> Tuple[NodeEdge, ...]:
    """Sample one spanning tree over a connected candidate graph."""

    ordered_nodes = tuple(sorted(int(node) for node in nodes))
    if not ordered_nodes:
        return ()
    edge_pool = _sort_node_edges(candidate_edges)
    visited = {int(rng.choice(ordered_nodes))}
    tree_edges: list[NodeEdge] = []
    while len(visited) < len(ordered_nodes):
        frontier = [
            edge
            for edge in edge_pool
            if (edge[0] in visited and edge[1] not in visited) or (edge[1] in visited and edge[0] not in visited)
        ]
        if not frontier:
            raise ValueError("candidate graph is not connected")
        edge = rng.choice(frontier)
        tree_edges.append(edge)
        visited.add(int(edge[0]))
        visited.add(int(edge[1]))
    return _sort_node_edges(tree_edges)


def _connected_node_subset(
    rng: random.Random,
    *,
    nodes: Sequence[int],
    candidate_edges: Sequence[NodeEdge],
    subset_size: int,
) -> Tuple[int, ...]:
    """Sample one connected subset of nodes from the candidate graph."""

    ordered_nodes = tuple(sorted(int(node) for node in nodes))
    if int(subset_size) > len(ordered_nodes):
        raise ValueError("subset_size exceeds node count")
    adjacency = _candidate_adjacency(ordered_nodes, candidate_edges)
    start = int(rng.choice(ordered_nodes))
    selected = {int(start)}
    while len(selected) < int(subset_size):
        frontier = sorted({int(neighbor) for node in selected for neighbor in adjacency.get(int(node), ()) if int(neighbor) not in selected})
        if not frontier:
            raise ValueError("failed to sample connected node subset")
        selected.add(int(rng.choice(frontier)))
    return tuple(sorted(selected))


def _induced_edges(candidate_edges: Sequence[NodeEdge], nodes: Sequence[int]) -> Tuple[NodeEdge, ...]:
    """Return candidate edges induced by a node subset."""

    node_set = {int(node) for node in nodes}
    return _sort_node_edges((left, right) for left, right in candidate_edges if int(left) in node_set and int(right) in node_set)


def _add_random_open_edges(
    graph: nx.Graph,
    rng: random.Random,
    *,
    candidate_edges: Sequence[NodeEdge],
    max_extra_edges: int,
) -> int:
    """Add random candidate non-tree edges and return how many were added."""

    available = [edge for edge in _sort_node_edges(candidate_edges) if not graph.has_edge(int(edge[0]), int(edge[1]))]
    rng.shuffle(available)
    added = 0
    for left, right in available[: max(0, int(max_extra_edges))]:
        graph.add_edge(int(left), int(right))
        added += 1
    return int(added)


def _sample_blocked_edges(
    rng: random.Random,
    *,
    candidate_edges: Sequence[NodeEdge],
    open_edges: Sequence[NodeEdge],
    min_count: int = 1,
    max_count: int = 5,
) -> Tuple[NodeEdge, ...]:
    """Sample visible blocked pipe edges from non-open candidate edges."""

    open_set = set(_sort_node_edges(open_edges))
    available = [edge for edge in _sort_node_edges(candidate_edges) if edge not in open_set]
    if not available:
        return ()
    upper = min(len(available), max(0, int(max_count)))
    lower = min(upper, max(0, int(min_count)))
    count = int(rng.randint(int(lower), int(upper))) if int(upper) >= int(lower) else 0
    rng.shuffle(available)
    return _sort_node_edges(available[:count])


def _open_adjacency_by_node(graph: nx.Graph) -> Dict[int, Tuple[int, ...]]:
    """Return deterministic open-pipe adjacency by node id."""

    return {int(node): tuple(sorted(int(value) for value in graph.neighbors(int(node)))) for node in sorted(graph.nodes())}


def _label_edge(label_by_node: Mapping[int, str], edge: NodeEdge) -> LabelEdge:
    """Convert one integer edge to a canonical label edge."""

    return canonicalize_graph_edge_label(str(label_by_node[int(edge[0])]), str(label_by_node[int(edge[1])]), directed=False)


def _build_pipe_sample(
    rng: random.Random,
    *,
    graph: nx.Graph,
    node_grid_cells: Mapping[int, GridCell],
    candidate_edges: Sequence[NodeEdge],
    blocked_edges: Sequence[NodeEdge] | None = None,
    label_variant: str,
    grid_shape_variant: str,
    label_by_node_override: Mapping[int, str] | None = None,
    query_label: str = "",
    source_label: str = "",
    goal_label: str = "",
    target_labels: Sequence[str] = (),
    target_edges: Sequence[LabelEdge] = (),
    target_shortest_path_length: int = 0,
    target_reachable_count: int = 0,
    target_bridge_count: int = 0,
    query_distance: int = 0,
    target_exact_distance_count: int = 0,
) -> PipeJunctionNetworkSample:
    """Build the labeled trace sample wrapper for one pipe graph."""

    node_ids = tuple(sorted(int(node) for node in graph.nodes()))
    if isinstance(label_by_node_override, Mapping):
        label_by_node = {int(node): str(label_by_node_override[int(node)]) for node in node_ids}
        label_variant = str(label_variant)
        label_source_kind = str(label_variant)
        label_bucket = ""
        label_manifest = ""
        label_filter: Mapping[str, Any] = {}
        label_bucket_probabilities: Mapping[str, float] = {}
    else:
        resolved_labels = resolve_graph_node_labels(
            rng,
            label_variant=str(label_variant),
            object_count=len(node_ids),
            max_chars=4,
            sequential_numbers=False,
        )
        node_labels = tuple(str(label) for label in resolved_labels.labels)
        label_variant = str(resolved_labels.label_variant)
        label_source_kind = str(resolved_labels.label_source_kind)
        label_bucket = str(resolved_labels.label_bucket)
        label_manifest = str(resolved_labels.label_manifest)
        label_filter = dict(resolved_labels.label_filter)
        label_bucket_probabilities = dict(resolved_labels.label_bucket_probabilities)
        label_by_node = {int(node): str(label) for node, label in zip(node_ids, node_labels)}
    node_by_label = {str(label): int(node) for node, label in label_by_node.items()}
    open_edges = _sort_node_edges((int(left), int(right)) for left, right in graph.edges())
    blocked = _sort_node_edges(blocked_edges or ())
    open_edge_labels = tuple(sorted((_label_edge(label_by_node, edge) for edge in open_edges), key=lambda pair: (graph_label_sort_key(pair[0]), graph_label_sort_key(pair[1]))))
    blocked_edge_labels = tuple(sorted((_label_edge(label_by_node, edge) for edge in blocked), key=lambda pair: (graph_label_sort_key(pair[0]), graph_label_sort_key(pair[1]))))
    adjacency_by_label = {
        str(label_by_node[int(node)]): tuple(sorted((str(label_by_node[int(neighbor)]) for neighbor in graph.neighbors(int(node))), key=graph_label_sort_key))
        for node in node_ids
    }
    degrees_by_label = {str(label_by_node[int(node)]): int(graph.degree(int(node))) for node in node_ids}
    return PipeJunctionNetworkSample(
        graph=graph.copy(),
        node_labels=tuple(str(label_by_node[int(node)]) for node in node_ids),
        label_by_node=dict(label_by_node),
        node_by_label=dict(node_by_label),
        node_grid_cells={int(node): tuple(int(value) for value in node_grid_cells[int(node)]) for node in node_ids},
        open_edges=tuple(open_edges),
        blocked_edges=tuple(blocked),
        open_edge_labels=tuple(open_edge_labels),
        blocked_edge_labels=tuple(blocked_edge_labels),
        adjacency_by_label=dict(adjacency_by_label),
        degrees_by_label=dict(degrees_by_label),
        query_label=str(query_label),
        source_label=str(source_label),
        goal_label=str(goal_label),
        target_labels=tuple(str(label) for label in target_labels),
        target_edges=tuple((str(left), str(right)) for left, right in target_edges),
        target_shortest_path_length=int(target_shortest_path_length),
        target_reachable_count=int(target_reachable_count),
        target_bridge_count=int(target_bridge_count),
        query_distance=int(query_distance),
        target_exact_distance_count=int(target_exact_distance_count),
        grid_shape_variant=str(grid_shape_variant),
        label_variant=str(label_variant),
        label_source_kind=str(label_source_kind),
        label_bucket=str(label_bucket),
        label_manifest=str(label_manifest),
        label_filter=dict(label_filter),
        label_bucket_probabilities=dict(label_bucket_probabilities),
    )


def _new_node_graph(node_count: int) -> nx.Graph:
    """Return an empty graph over node ids."""

    graph = nx.Graph()
    graph.add_nodes_from(range(int(node_count)))
    return graph


def _sample_grid_support(
    rng: random.Random,
    *,
    node_count: int,
    grid_shape_variant: str,
) -> Tuple[Dict[int, GridCell], Tuple[NodeEdge, ...]]:
    """Sample selected grid cells and their candidate edges."""

    rows, cols = parse_pipe_grid_shape(str(grid_shape_variant))
    cells = _sample_connected_cells(rng, rows=int(rows), cols=int(cols), node_count=int(node_count))
    cells_by_node = {int(index): tuple(int(value) for value in cell) for index, cell in enumerate(cells)}
    candidate_edges = _candidate_edges_for_cells(cells_by_node)
    candidate_graph = _new_node_graph(int(node_count))
    candidate_graph.add_edges_from(candidate_edges)
    if int(node_count) > 1 and not nx.is_connected(candidate_graph):
        raise ValueError("sampled pipe cells are not candidate-connected")
    return dict(cells_by_node), tuple(candidate_edges)


def sample_pipe_shortest_path_network(
    rng: random.Random,
    *,
    node_count: int,
    target_shortest_path_length: int,
    grid_shape_variant: str,
    label_variant: str,
    max_attempts: int = 500,
) -> PipeJunctionNetworkSample:
    """Sample a pipe network with a unique shortest open route of a target length."""

    for _ in range(max(1, int(max_attempts))):
        cells_by_node, candidate_edges = _sample_grid_support(rng, node_count=int(node_count), grid_shape_variant=str(grid_shape_variant))
        graph = _new_node_graph(int(node_count))
        graph.add_edges_from(_random_spanning_tree_edges(rng, nodes=tuple(range(int(node_count))), candidate_edges=candidate_edges))
        adjacency = _open_adjacency_by_node(graph)
        pairs: list[Tuple[int, int, Tuple[int, ...]]] = []
        for source in sorted(graph.nodes()):
            dist_start, count_start = bfs_dist_count_by_adjacency(adjacency, start=int(source))
            for goal in sorted(graph.nodes()):
                if int(source) >= int(goal):
                    continue
                if int(dist_start.get(int(goal), -1)) != int(target_shortest_path_length):
                    continue
                if int(count_start.get(int(goal), 0)) != 1:
                    continue
                dist_goal, _ = bfs_dist_count_by_adjacency(adjacency, start=int(goal))
                path = reconstruct_unique_shortest_path_by_adjacency(
                    adjacency,
                    start=int(source),
                    goal=int(goal),
                    dist_start=dist_start,
                    dist_goal=dist_goal,
                )
                if path is not None:
                    pairs.append((int(source), int(goal), tuple(int(node) for node in path)))
        if not pairs:
            continue
        source_node, goal_node, path_nodes = rng.choice(pairs)

        available = [edge for edge in _sort_node_edges(candidate_edges) if not graph.has_edge(edge[0], edge[1])]
        rng.shuffle(available)
        for left, right in available[:3]:
            graph.add_edge(int(left), int(right))
            adjacency = _open_adjacency_by_node(graph)
            dist_start, count_start = bfs_dist_count_by_adjacency(adjacency, start=int(source_node))
            dist_goal, _ = bfs_dist_count_by_adjacency(adjacency, start=int(goal_node))
            path = reconstruct_unique_shortest_path_by_adjacency(
                adjacency,
                start=int(source_node),
                goal=int(goal_node),
                dist_start=dist_start,
                dist_goal=dist_goal,
            )
            if (
                int(dist_start.get(int(goal_node), -1)) != int(target_shortest_path_length)
                or int(count_start.get(int(goal_node), 0)) != 1
                or path is None
                or tuple(int(node) for node in path) != tuple(path_nodes)
            ):
                graph.remove_edge(int(left), int(right))

        blocked_edges = _sample_blocked_edges(rng, candidate_edges=candidate_edges, open_edges=tuple(graph.edges()), min_count=1, max_count=5)
        provisional = _build_pipe_sample(
            rng,
            graph=graph,
            node_grid_cells=cells_by_node,
            candidate_edges=candidate_edges,
            blocked_edges=blocked_edges,
            label_variant=str(label_variant),
            grid_shape_variant=str(grid_shape_variant),
        )
        path_labels = tuple(str(provisional.label_by_node[int(node)]) for node in path_nodes)
        return _build_pipe_sample(
            rng,
            graph=graph,
            node_grid_cells=cells_by_node,
            candidate_edges=candidate_edges,
            blocked_edges=blocked_edges,
            label_variant=str(label_variant),
            grid_shape_variant=str(grid_shape_variant),
            label_by_node_override=provisional.label_by_node,
            source_label=path_labels[0],
            goal_label=path_labels[-1],
            target_labels=path_labels,
            target_shortest_path_length=int(target_shortest_path_length),
        )
    raise ValueError("failed to sample pipe shortest-path network")


def sample_pipe_reachable_network(
    rng: random.Random,
    *,
    node_count: int,
    target_reachable_count: int,
    grid_shape_variant: str,
    label_variant: str,
    max_attempts: int = 500,
) -> PipeJunctionNetworkSample:
    """Sample a pipe network with one open reachable component of target size."""

    if int(target_reachable_count) >= int(node_count):
        raise ValueError("reachable-count task needs at least one unreachable junction")
    for _ in range(max(1, int(max_attempts))):
        cells_by_node, candidate_edges = _sample_grid_support(rng, node_count=int(node_count), grid_shape_variant=str(grid_shape_variant))
        try:
            reachable_nodes = _connected_node_subset(
                rng,
                nodes=tuple(range(int(node_count))),
                candidate_edges=candidate_edges,
                subset_size=int(target_reachable_count),
            )
        except ValueError:
            continue
        reachable_set = {int(node) for node in reachable_nodes}
        graph = _new_node_graph(int(node_count))
        reachable_edges = _induced_edges(candidate_edges, reachable_nodes)
        graph.add_edges_from(_random_spanning_tree_edges(rng, nodes=reachable_nodes, candidate_edges=reachable_edges))
        _add_random_open_edges(graph, rng, candidate_edges=reachable_edges, max_extra_edges=2)

        remaining_nodes = [node for node in range(int(node_count)) if int(node) not in reachable_set]
        remaining_edges = _induced_edges(candidate_edges, remaining_nodes)
        for edge in remaining_edges:
            if rng.random() < 0.35:
                graph.add_edge(int(edge[0]), int(edge[1]))

        query_node = int(rng.choice(reachable_nodes))
        adjacency = _open_adjacency_by_node(graph)
        dist, _ = bfs_dist_count_by_adjacency(adjacency, start=int(query_node))
        observed = tuple(sorted(int(node) for node in dist.keys()))
        if len(observed) != int(target_reachable_count) or set(observed) != reachable_set:
            continue
        blocked_edges = _sample_blocked_edges(rng, candidate_edges=candidate_edges, open_edges=tuple(graph.edges()), min_count=2, max_count=6)
        provisional = _build_pipe_sample(
            rng,
            graph=graph,
            node_grid_cells=cells_by_node,
            candidate_edges=candidate_edges,
            blocked_edges=blocked_edges,
            label_variant=str(label_variant),
            grid_shape_variant=str(grid_shape_variant),
        )
        target_labels = tuple(sorted((str(provisional.label_by_node[int(node)]) for node in observed), key=graph_label_sort_key))
        query_label = str(provisional.label_by_node[int(query_node)])
        return _build_pipe_sample(
            rng,
            graph=graph,
            node_grid_cells=cells_by_node,
            candidate_edges=candidate_edges,
            blocked_edges=blocked_edges,
            label_variant=str(label_variant),
            grid_shape_variant=str(grid_shape_variant),
            label_by_node_override=provisional.label_by_node,
            query_label=query_label,
            target_labels=target_labels,
            target_reachable_count=int(target_reachable_count),
        )
    raise ValueError("failed to sample pipe reachable-count network")


def sample_pipe_bridge_network(
    rng: random.Random,
    *,
    node_count: int,
    target_bridge_count: int,
    grid_shape_variant: str,
    label_variant: str,
    max_attempts: int = 800,
) -> PipeJunctionNetworkSample:
    """Sample a connected pipe network with a target number of open bridge pipes."""

    def _search_exact_bridge_graph(
        base_graph: nx.Graph,
        available_edges: Sequence[NodeEdge],
        *,
        target_count: int,
    ) -> nx.Graph | None:
        """Return a graph formed by adding support edges with exactly target bridges."""

        start_count = len(tuple(nx.bridges(base_graph)))
        if int(start_count) == int(target_count):
            return base_graph.copy()
        if int(start_count) < int(target_count):
            return None

        shuffled_edges = [(int(left), int(right)) for left, right in available_edges]
        rng.shuffle(shuffled_edges)
        frontier: list[tuple[int, int, nx.Graph, tuple[NodeEdge, ...]]] = [
            (abs(int(start_count) - int(target_count)), int(start_count), base_graph.copy(), tuple(shuffled_edges))
        ]
        seen: set[tuple[NodeEdge, ...]] = {tuple(sorted(tuple(edge) for edge in base_graph.edges()))}
        expansion_budget = 400
        while frontier and expansion_budget > 0:
            frontier.sort(key=lambda item: (int(item[0]), int(item[1]), len(item[3])))
            _gap, current_count, graph_state, remaining_edges = frontier.pop(0)
            expansion_budget -= 1
            candidate_edges = list(remaining_edges)
            rng.shuffle(candidate_edges)
            for edge in candidate_edges:
                candidate = graph_state.copy()
                candidate.add_edge(int(edge[0]), int(edge[1]))
                new_count = len(tuple(nx.bridges(candidate)))
                if int(new_count) < int(target_count) or int(new_count) >= int(current_count):
                    continue
                if int(new_count) == int(target_count):
                    return candidate
                next_remaining = tuple(candidate_edge for candidate_edge in remaining_edges if tuple(candidate_edge) != tuple(edge))
                state_key = tuple(sorted(tuple(sorted(edge_key)) for edge_key in candidate.edges()))
                if state_key in seen:
                    continue
                seen.add(state_key)
                frontier.append(
                    (
                        abs(int(new_count) - int(target_count)),
                        int(new_count),
                        candidate,
                        next_remaining,
                    )
                )
        return None

    for _ in range(max(1, int(max_attempts))):
        cells_by_node, candidate_edges = _sample_grid_support(rng, node_count=int(node_count), grid_shape_variant=str(grid_shape_variant))
        graph = _new_node_graph(int(node_count))
        tree_edges = _sort_node_edges(_random_spanning_tree_edges(rng, nodes=tuple(range(int(node_count))), candidate_edges=candidate_edges))
        graph.add_edges_from(tree_edges)
        available = [edge for edge in _sort_node_edges(candidate_edges) if edge not in set(tree_edges)]

        target_count = int(target_bridge_count)
        exact_graph = _search_exact_bridge_graph(graph, available, target_count=int(target_count))
        if exact_graph is None:
            continue
        graph = exact_graph
        remaining = [edge for edge in available if not graph.has_edge(int(edge[0]), int(edge[1]))]
        current_count = len(tuple(nx.bridges(graph)))

        if int(current_count) == int(target_count) and remaining:
            stable_edges: list[tuple[int, int]] = []
            for edge in remaining:
                candidate = graph.copy()
                candidate.add_edge(int(edge[0]), int(edge[1]))
                if len(tuple(nx.bridges(candidate))) == int(target_count):
                    stable_edges.append((int(edge[0]), int(edge[1])))
            rng.shuffle(stable_edges)
            for edge in stable_edges[: rng.randint(0, min(2, len(stable_edges)))]:
                graph.add_edge(int(edge[0]), int(edge[1]))

        bridge_edges = _sort_node_edges((int(left), int(right)) for left, right in nx.bridges(graph))
        if len(bridge_edges) != int(target_bridge_count):
            continue
        blocked_edges = _sample_blocked_edges(rng, candidate_edges=candidate_edges, open_edges=tuple(graph.edges()), min_count=1, max_count=5)
        provisional = _build_pipe_sample(
            rng,
            graph=graph,
            node_grid_cells=cells_by_node,
            candidate_edges=candidate_edges,
            blocked_edges=blocked_edges,
            label_variant=str(label_variant),
            grid_shape_variant=str(grid_shape_variant),
        )
        target_edges = tuple(sorted((_label_edge(provisional.label_by_node, edge) for edge in bridge_edges), key=lambda pair: (graph_label_sort_key(pair[0]), graph_label_sort_key(pair[1]))))
        return _build_pipe_sample(
            rng,
            graph=graph,
            node_grid_cells=cells_by_node,
            candidate_edges=candidate_edges,
            blocked_edges=blocked_edges,
            label_variant=str(label_variant),
            grid_shape_variant=str(grid_shape_variant),
            label_by_node_override=provisional.label_by_node,
            target_edges=target_edges,
            target_bridge_count=int(target_bridge_count),
        )
    raise ValueError("failed to sample pipe bridge-count network")


def sample_pipe_exact_distance_network(
    rng: random.Random,
    *,
    node_count: int,
    query_distance: int,
    target_exact_distance_count: int,
    grid_shape_variant: str,
    label_variant: str,
    max_attempts: int = 800,
) -> PipeJunctionNetworkSample:
    """Sample a pipe network with a target number of nodes exactly k open pipes away."""

    for _ in range(max(1, int(max_attempts))):
        cells_by_node, candidate_edges = _sample_grid_support(rng, node_count=int(node_count), grid_shape_variant=str(grid_shape_variant))
        graph = _new_node_graph(int(node_count))
        graph.add_edges_from(_random_spanning_tree_edges(rng, nodes=tuple(range(int(node_count))), candidate_edges=candidate_edges))
        available_extra = max(0, min(4, len(candidate_edges) - (int(node_count) - 1)))
        _add_random_open_edges(graph, rng, candidate_edges=candidate_edges, max_extra_edges=rng.randint(0, available_extra))
        adjacency = _open_adjacency_by_node(graph)
        matching_sources: list[Tuple[int, Tuple[int, ...]]] = []
        for source in sorted(graph.nodes()):
            dist, _ = bfs_dist_count_by_adjacency(adjacency, start=int(source))
            exact_nodes = tuple(sorted(int(node) for node, distance in dist.items() if int(distance) == int(query_distance)))
            if len(exact_nodes) == int(target_exact_distance_count):
                matching_sources.append((int(source), exact_nodes))
        if not matching_sources:
            continue
        query_node, exact_nodes = rng.choice(matching_sources)
        blocked_edges = _sample_blocked_edges(rng, candidate_edges=candidate_edges, open_edges=tuple(graph.edges()), min_count=1, max_count=5)
        provisional = _build_pipe_sample(
            rng,
            graph=graph,
            node_grid_cells=cells_by_node,
            candidate_edges=candidate_edges,
            blocked_edges=blocked_edges,
            label_variant=str(label_variant),
            grid_shape_variant=str(grid_shape_variant),
        )
        query_label = str(provisional.label_by_node[int(query_node)])
        target_labels = tuple(sorted((str(provisional.label_by_node[int(node)]) for node in exact_nodes), key=graph_label_sort_key))
        return _build_pipe_sample(
            rng,
            graph=graph,
            node_grid_cells=cells_by_node,
            candidate_edges=candidate_edges,
            blocked_edges=blocked_edges,
            label_variant=str(label_variant),
            grid_shape_variant=str(grid_shape_variant),
            label_by_node_override=provisional.label_by_node,
            query_label=query_label,
            target_labels=target_labels,
            query_distance=int(query_distance),
            target_exact_distance_count=int(target_exact_distance_count),
        )
    raise ValueError("failed to sample pipe exact-distance network")


def _resolve_pipe_panel_geometry(render_params: GraphRenderParams) -> Dict[str, Any]:
    """Resolve the single-panel pipe scene geometry."""

    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    margin = int(render_params.outer_margin_px)
    panel = (margin, margin, width - margin, height - margin)
    title_band_height = max(40, int(round(float(render_params.panel_title_font_size_px) * 1.8)))
    title_band = (panel[0], panel[1], panel[2], panel[1] + title_band_height)
    content = (
        panel[0] + int(render_params.panel_padding_px),
        title_band[3] + max(12, int(render_params.panel_padding_px // 2)),
        panel[2] - int(render_params.panel_padding_px),
        panel[3] - int(render_params.panel_padding_px),
    )
    return {
        "canvas_size": [int(width), int(height)],
        "scene_panel_xyxy": [int(value) for value in panel],
        "title_band_xyxy": [int(value) for value in title_band],
        "scene_content_xyxy": [int(value) for value in content],
    }


def _draw_panel(
    image: Image.Image,
    *,
    panel_geometry: Mapping[str, Any],
    render_params: GraphRenderParams,
    scene_title: str,
    layout_seed: int,
) -> None:
    """Draw panel chrome for the pipe graph."""

    draw = ImageDraw.Draw(image)
    panel = tuple(int(value) for value in panel_geometry["scene_panel_xyxy"])
    draw.rounded_rectangle(
        panel,
        radius=max(0, int(render_params.panel_corner_radius_px)),
        fill=tuple(int(value) for value in render_params.panel_fill_rgb),
        outline=tuple(int(value) for value in render_params.panel_border_rgb),
        width=2,
    )
    title_band = tuple(int(value) for value in panel_geometry["title_band_xyxy"])
    title_style = resolve_readable_text_style(
        instance_seed=int(layout_seed),
        namespace="graph.pipe_network.panel_title_text",
        role="graph_panel_title_text",
        surface_rgbs=(tuple(int(value) for value in render_params.panel_fill_rgb),),
        preferred_rgbs=(tuple(int(value) for value in render_params.title_color_rgb),),
        min_contrast_ratio=4.5,
        min_lab_distance=28.0,
    )
    draw_centered_readable_text(
        draw,
        text=str(scene_title),
        center=(0.5 * float(title_band[0] + title_band[2]), 0.5 * float(title_band[1] + title_band[3])),
        font=load_font(
            int(render_params.panel_title_font_size_px),
            bold=True,
            font_family=str(render_params.font_family or ""),
        ),
        style=title_style,
        stroke_width=2,
    )


def _clamp_channel(value: float) -> int:
    """Clamp one color channel to an integer RGB value."""

    return max(0, min(255, int(round(float(value)))))


def _mix_rgb(left: Sequence[int], right: Sequence[int], amount: float) -> Tuple[int, int, int]:
    """Linearly mix two RGB colors."""

    t = max(0.0, min(1.0, float(amount)))
    return tuple(
        _clamp_channel((float(left[index]) * (1.0 - t)) + (float(right[index]) * t))
        for index in range(3)
    )


def _resolve_pipe_visual_style(*, render_params: GraphRenderParams, layout_seed: int) -> Dict[str, Any]:
    """Resolve a deterministic physical-pipe visual style."""

    rng = random.Random((int(layout_seed) ^ 0x5A17C0DE) & 0xFFFFFFFF)
    style_id = PIPE_VISUAL_STYLE_IDS[int(rng.randrange(len(PIPE_VISUAL_STYLE_IDS)))]
    style_map: Dict[str, Dict[str, Tuple[int, int, int]]] = {
        "industrial_steel": {
            "board_fill_rgb": (239, 242, 245),
            "board_grid_rgb": (215, 222, 229),
            "tube_shadow_rgb": (98, 107, 116),
            "tube_outline_rgb": (54, 64, 74),
            "tube_fill_rgb": (151, 165, 177),
            "tube_highlight_rgb": (232, 237, 242),
            "blocked_outline_rgb": (100, 104, 111),
            "blocked_fill_rgb": (185, 188, 193),
            "blocked_highlight_rgb": (243, 244, 246),
            "blocked_marker_rgb": (182, 65, 55),
            "fitting_shadow_rgb": (117, 124, 132),
            "fitting_outer_rgb": (58, 68, 78),
            "fitting_ring_rgb": (122, 137, 150),
            "fitting_inner_rgb": (238, 242, 246),
            "bolt_rgb": (45, 53, 61),
        },
        "copper_plumbing": {
            "board_fill_rgb": (249, 244, 235),
            "board_grid_rgb": (224, 210, 192),
            "tube_shadow_rgb": (118, 76, 51),
            "tube_outline_rgb": (99, 57, 35),
            "tube_fill_rgb": (190, 111, 65),
            "tube_highlight_rgb": (249, 190, 124),
            "blocked_outline_rgb": (111, 87, 75),
            "blocked_fill_rgb": (187, 178, 170),
            "blocked_highlight_rgb": (248, 241, 233),
            "blocked_marker_rgb": (154, 54, 48),
            "fitting_shadow_rgb": (127, 85, 59),
            "fitting_outer_rgb": (110, 62, 38),
            "fitting_ring_rgb": (187, 111, 67),
            "fitting_inner_rgb": (255, 241, 222),
            "bolt_rgb": (86, 48, 30),
        },
        "teal_plant": {
            "board_fill_rgb": (237, 246, 244),
            "board_grid_rgb": (204, 224, 220),
            "tube_shadow_rgb": (60, 102, 101),
            "tube_outline_rgb": (30, 74, 76),
            "tube_fill_rgb": (62, 148, 143),
            "tube_highlight_rgb": (197, 239, 232),
            "blocked_outline_rgb": (90, 104, 107),
            "blocked_fill_rgb": (177, 191, 191),
            "blocked_highlight_rgb": (242, 250, 248),
            "blocked_marker_rgb": (174, 66, 58),
            "fitting_shadow_rgb": (70, 116, 113),
            "fitting_outer_rgb": (31, 78, 79),
            "fitting_ring_rgb": (66, 145, 139),
            "fitting_inner_rgb": (230, 250, 246),
            "bolt_rgb": (25, 58, 60),
        },
        "blueprint_tubes": {
            "board_fill_rgb": (226, 238, 250),
            "board_grid_rgb": (181, 203, 226),
            "tube_shadow_rgb": (51, 83, 121),
            "tube_outline_rgb": (28, 58, 96),
            "tube_fill_rgb": (74, 128, 183),
            "tube_highlight_rgb": (213, 235, 255),
            "blocked_outline_rgb": (77, 92, 113),
            "blocked_fill_rgb": (166, 181, 201),
            "blocked_highlight_rgb": (236, 244, 252),
            "blocked_marker_rgb": (178, 66, 62),
            "fitting_shadow_rgb": (55, 87, 124),
            "fitting_outer_rgb": (33, 67, 106),
            "fitting_ring_rgb": (82, 139, 194),
            "fitting_inner_rgb": (236, 247, 255),
            "bolt_rgb": (23, 50, 82),
        },
    }
    resolved = dict(style_map[str(style_id)])
    resolved["fitting_ring_rgb"] = _mix_rgb(
        resolved["fitting_ring_rgb"],
        tuple(int(value) for value in render_params.node_fill_rgb),
        0.22,
    )
    treatment_rng = random.Random((int(layout_seed) ^ 0x3D71B0A9) & 0xFFFFFFFF)
    if str(style_id) == "blueprint_tubes":
        treatment_support = ("plain_panel", "plate_seams", "blueprint_grid")
    else:
        treatment_support = ("plain_panel", "plate_seams", "perforated_panel")
    board_treatment = str(treatment_support[int(treatment_rng.randrange(len(treatment_support)))])
    return {
        "style_id": str(style_id),
        "board_treatment": str(board_treatment),
        **{key: tuple(int(channel) for channel in value) for key, value in resolved.items()},
    }


def _pipe_style_metadata(style: Mapping[str, Any]) -> Dict[str, Any]:
    """Return JSON-friendly pipe style metadata."""

    out: Dict[str, Any] = {
        "style_id": str(style.get("style_id", "")),
        "board_treatment": str(style.get("board_treatment", "")),
    }
    for key, value in style.items():
        if key in {"style_id", "board_treatment"}:
            continue
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            out[str(key)] = [int(channel) for channel in value[:3]]
    return out


def _draw_pipe_board_background(
    draw: ImageDraw.ImageDraw,
    *,
    content_bbox: Sequence[int],
    style: Mapping[str, Any],
) -> None:
    """Draw the physical board that the pipe network sits on."""

    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    fill = tuple(int(value) for value in style["board_fill_rgb"])
    grid = tuple(int(value) for value in style["board_grid_rgb"])
    draw.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=fill, outline=_mix_rgb(grid, (40, 48, 58), 0.18), width=2)
    treatment = str(style.get("board_treatment", "plain_panel"))
    if treatment == "blueprint_grid":
        step = 56
        for x in range(x0 + step, x1, step):
            draw.line((x, y0 + 8, x, y1 - 8), fill=grid, width=1)
        for y in range(y0 + step, y1, step):
            draw.line((x0 + 8, y, x1 - 8, y), fill=grid, width=1)
    elif treatment == "plate_seams":
        seam = _mix_rgb(grid, (40, 48, 58), 0.22)
        for fraction in (0.34, 0.67):
            x = int(round(float(x0) + (float(x1 - x0) * fraction)))
            draw.line((x, y0 + 18, x, y1 - 18), fill=seam, width=2)
        y = int(round(float(y0) + (float(y1 - y0) * 0.52)))
        draw.line((x0 + 18, y, x1 - 18, y), fill=seam, width=2)
    elif treatment == "perforated_panel":
        dot_fill = _mix_rgb(grid, (45, 52, 60), 0.35)
        spacing = 62
        radius = 2
        for y in range(y0 + 38, y1 - 18, spacing):
            for x in range(x0 + 38, x1 - 18, spacing):
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=dot_fill)
    screw_radius = 4
    for sx, sy in (
        (x0 + 15, y0 + 15),
        (x1 - 15, y0 + 15),
        (x0 + 15, y1 - 15),
        (x1 - 15, y1 - 15),
    ):
        draw.ellipse(
            (sx - screw_radius, sy - screw_radius, sx + screw_radius, sy + screw_radius),
            fill=_mix_rgb(grid, (45, 52, 60), 0.40),
            outline=_mix_rgb(grid, (0, 0, 0), 0.25),
            width=1,
        )


def _grid_cell_centers(
    *,
    grid_shape_variant: str,
    content_bbox: Sequence[int],
    node_radius_px: int,
) -> Dict[GridCell, Point]:
    """Return pixel centers for every grid cell."""

    rows, cols = parse_pipe_grid_shape(str(grid_shape_variant))
    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    inset = max(8, int(node_radius_px) + 10)
    usable_x0 = x0 + inset
    usable_y0 = y0 + inset
    usable_x1 = x1 - inset
    usable_y1 = y1 - inset
    centers: Dict[GridCell, Point] = {}
    for row in range(int(rows)):
        for col in range(int(cols)):
            x = usable_x0 + ((usable_x1 - usable_x0) * (float(col) / float(max(1, int(cols) - 1))))
            y = usable_y0 + ((usable_y1 - usable_y0) * (float(row) / float(max(1, int(rows) - 1))))
            centers[(int(row), int(col))] = (int(round(x)), int(round(y)))
    return centers


def _trim_segment_to_node_radius(start: Point, end: Point, *, radius: int) -> Tuple[Point, Point]:
    """Trim one pipe segment so it meets node boundaries."""

    x0, y0 = float(start[0]), float(start[1])
    x1, y1 = float(end[0]), float(end[1])
    dx = float(x1 - x0)
    dy = float(y1 - y0)
    norm = float(math.hypot(dx, dy))
    if norm <= 1e-6:
        return (start, end)
    ux = float(dx / norm)
    uy = float(dy / norm)
    trim = float(max(1, int(radius) - 1))
    return (
        (int(round(x0 + (ux * trim))), int(round(y0 + (uy * trim)))),
        (int(round(x1 - (ux * trim))), int(round(y1 - (uy * trim)))),
    )


def _draw_blocked_pipe_marker(
    draw: ImageDraw.ImageDraw,
    *,
    segment: Tuple[Point, Point],
    color_rgb: Sequence[int],
    width_px: int,
) -> None:
    """Draw a clear X-shaped blocked-pipe marker at segment midpoint."""

    start, end = segment
    x0, y0 = float(start[0]), float(start[1])
    x1, y1 = float(end[0]), float(end[1])
    mx = 0.5 * (x0 + x1)
    my = 0.5 * (y0 + y1)
    dx = x1 - x0
    dy = y1 - y0
    norm = max(1.0, math.hypot(dx, dy))
    ux = dx / norm
    uy = dy / norm
    px = -dy / norm
    py = dx / norm
    half = max(16.0, min(max(22.0, float(width_px) * 3.2), norm * 0.34))
    stroke_width = max(5, int(round(float(width_px) * 0.85)))
    halo_width = stroke_width + 5
    line_pairs = (
        (
            (mx - ux * half - px * half, my - uy * half - py * half),
            (mx + ux * half + px * half, my + uy * half + py * half),
        ),
        (
            (mx - ux * half + px * half, my - uy * half + py * half),
            (mx + ux * half - px * half, my + uy * half - py * half),
        ),
    )
    for left, right in line_pairs:
        draw.line(
            (left[0], left[1], right[0], right[1]),
            fill=(248, 250, 252),
            width=halo_width,
        )
    for left, right in line_pairs:
        draw.line(
            (left[0], left[1], right[0], right[1]),
            fill=tuple(int(value) for value in color_rgb),
            width=stroke_width,
        )


def _offset_segment(segment: Tuple[Point, Point], *, offset_px: float) -> Tuple[Point, Point]:
    """Offset one pipe segment perpendicular to its direction."""

    start, end = segment
    dx = float(end[0] - start[0])
    dy = float(end[1] - start[1])
    norm = max(1.0, math.hypot(dx, dy))
    px = -dy / norm
    py = dx / norm
    return (
        (int(round(float(start[0]) + (px * float(offset_px)))), int(round(float(start[1]) + (py * float(offset_px))))),
        (int(round(float(end[0]) + (px * float(offset_px)))), int(round(float(end[1]) + (py * float(offset_px))))),
    )


def _draw_pipe_tube(
    draw: ImageDraw.ImageDraw,
    *,
    segment: Tuple[Point, Point],
    width_px: int,
    outline_rgb: Sequence[int],
    fill_rgb: Sequence[int],
    highlight_rgb: Sequence[int],
    shadow_rgb: Sequence[int],
) -> None:
    """Draw one thick cylindrical-looking pipe tube."""

    start, end = segment
    tube_width = max(10, int(width_px))
    outer_width = int(tube_width + max(6, round(tube_width * 0.34)))
    shadow_segment = _offset_segment((start, end), offset_px=max(2.0, float(tube_width) * 0.15))
    draw.line(
        (shadow_segment[0][0], shadow_segment[0][1], shadow_segment[1][0], shadow_segment[1][1]),
        fill=tuple(int(value) for value in shadow_rgb),
        width=outer_width + 4,
    )
    draw.line((start[0], start[1], end[0], end[1]), fill=tuple(int(value) for value in outline_rgb), width=outer_width)
    draw.line((start[0], start[1], end[0], end[1]), fill=tuple(int(value) for value in fill_rgb), width=tube_width)
    highlight_segment = _offset_segment((start, end), offset_px=-max(2.0, float(tube_width) * 0.18))
    draw.line(
        (highlight_segment[0][0], highlight_segment[0][1], highlight_segment[1][0], highlight_segment[1][1]),
        fill=tuple(int(value) for value in highlight_rgb),
        width=max(3, int(round(float(tube_width) * 0.18))),
    )


def _draw_blocked_valve_marker(
    draw: ImageDraw.ImageDraw,
    *,
    segment: Tuple[Point, Point],
    style: Mapping[str, Any],
    width_px: int,
) -> None:
    """Draw a valve/plate marker for one blocked pipe."""

    start, end = segment
    mx = int(round(0.5 * float(start[0] + end[0])))
    my = int(round(0.5 * float(start[1] + end[1])))
    dx = abs(int(end[0] - start[0]))
    dy = abs(int(end[1] - start[1]))
    half_long = max(18, int(round(float(width_px) * 1.05)))
    half_short = max(8, int(round(float(width_px) * 0.42)))
    if dx >= dy:
        valve_box = (mx - half_short, my - half_long, mx + half_short, my + half_long)
    else:
        valve_box = (mx - half_long, my - half_short, mx + half_long, my + half_short)
    marker = tuple(int(value) for value in style["blocked_marker_rgb"])
    outline = _mix_rgb(marker, (20, 20, 20), 0.38)
    draw.rounded_rectangle(valve_box, radius=6, fill=marker, outline=outline, width=3)
    _draw_blocked_pipe_marker(
        draw,
        segment=segment,
        color_rgb=(248, 250, 252),
        width_px=max(4, int(round(float(width_px) * 0.42))),
    )


def _draw_pipe_fitting(
    draw: ImageDraw.ImageDraw,
    *,
    center: Point,
    radius: int,
    style: Mapping[str, Any],
) -> Tuple[int, int, int, int]:
    """Draw one flanged pipe junction fitting."""

    cx, cy = int(center[0]), int(center[1])
    outer_radius = int(radius)
    shadow_offset = max(2, int(round(float(outer_radius) * 0.10)))
    shadow = tuple(int(value) for value in style["fitting_shadow_rgb"])
    outer = tuple(int(value) for value in style["fitting_outer_rgb"])
    ring = tuple(int(value) for value in style["fitting_ring_rgb"])
    inner = tuple(int(value) for value in style["fitting_inner_rgb"])
    bolt = tuple(int(value) for value in style["bolt_rgb"])
    shadow_box = (
        cx - outer_radius + shadow_offset,
        cy - outer_radius + shadow_offset,
        cx + outer_radius + shadow_offset,
        cy + outer_radius + shadow_offset,
    )
    bbox = (cx - outer_radius, cy - outer_radius, cx + outer_radius, cy + outer_radius)
    draw.ellipse(shadow_box, fill=shadow)
    draw.ellipse(bbox, fill=outer, outline=_mix_rgb(outer, (0, 0, 0), 0.35), width=2)
    ring_inset = max(4, int(round(float(outer_radius) * 0.18)))
    ring_box = (
        cx - outer_radius + ring_inset,
        cy - outer_radius + ring_inset,
        cx + outer_radius - ring_inset,
        cy + outer_radius - ring_inset,
    )
    draw.ellipse(ring_box, fill=ring, outline=_mix_rgb(ring, (0, 0, 0), 0.22), width=2)
    inner_radius = max(13, int(round(float(outer_radius) * 0.58)))
    inner_box = (cx - inner_radius, cy - inner_radius, cx + inner_radius, cy + inner_radius)
    draw.ellipse(inner_box, fill=inner, outline=_mix_rgb(ring, (0, 0, 0), 0.35), width=2)
    bolt_radius = max(2, int(round(float(outer_radius) * 0.08)))
    bolt_ring_radius = max(inner_radius + 4, int(round(float(outer_radius) * 0.78)))
    for angle_index in range(8):
        theta = (math.tau * float(angle_index)) / 8.0
        bx = int(round(float(cx) + (math.cos(theta) * float(bolt_ring_radius))))
        by = int(round(float(cy) + (math.sin(theta) * float(bolt_ring_radius))))
        draw.ellipse(
            (bx - bolt_radius, by - bolt_radius, bx + bolt_radius, by + bolt_radius),
            fill=bolt,
            outline=_mix_rgb(bolt, (255, 255, 255), 0.25),
            width=1,
        )
    return bbox


def _pipe_text_legibility_records(
    render_params: GraphRenderParams,
    *,
    layout_seed: int,
    style: Mapping[str, Any],
) -> Tuple[Dict[str, Any], ...]:
    """Return pipe-network required text styles for panel metadata."""

    existing_records: list[Dict[str, Any]] = []
    if isinstance(render_params.text_legibility, Mapping):
        raw_records = render_params.text_legibility.get("records")
        if isinstance(raw_records, list):
            skip_roles = {"graph_panel_title_text", "graph_node_label_text"}
            existing_records = [
                dict(record)
                for record in raw_records
                if isinstance(record, Mapping) and str(record.get("role")) not in skip_roles
            ]
    title_style = resolve_readable_text_style(
        instance_seed=int(layout_seed),
        namespace="graph.pipe_network.panel_title_text",
        role="graph_panel_title_text",
        surface_rgbs=(tuple(int(value) for value in render_params.panel_fill_rgb),),
        preferred_rgbs=(tuple(int(value) for value in render_params.title_color_rgb),),
        min_contrast_ratio=4.5,
        min_lab_distance=28.0,
    )
    junction_style = resolve_readable_text_style(
        instance_seed=int(layout_seed),
        namespace="graph.pipe_network.junction_label_text",
        role="graph_node_label_text",
        surface_rgbs=(tuple(int(value) for value in style["fitting_inner_rgb"]),),
        preferred_rgbs=(
            tuple(int(value) for value in render_params.label_text_rgb),
            tuple(int(value) for value in render_params.label_stroke_rgb),
            (255, 255, 255),
            (10, 14, 22),
        ),
        min_contrast_ratio=4.0,
        min_lab_distance=24.0,
    )
    return tuple([*existing_records, title_style.metadata(), junction_style.metadata()])


def render_pipe_network_scene(
    *,
    pipe_sample: PipeJunctionNetworkSample,
    render_params: GraphRenderParams,
    base_image: Image.Image,
    scene_title: str = "Pipe Junction Board",
    layout_seed: int = 0,
) -> RenderedPipeJunctionScene:
    """Render one sampled pipe-junction graph scene."""

    image = base_image.convert("RGB")
    draw = ImageDraw.Draw(image)
    pipe_style = _resolve_pipe_visual_style(render_params=render_params, layout_seed=int(layout_seed))
    panel_geometry = _resolve_pipe_panel_geometry(render_params)
    if isinstance(render_params.information_scene_style, Mapping):
        panel_geometry["information_scene_style"] = dict(render_params.information_scene_style)
    panel_geometry["text_legibility"] = text_legibility_summary_from_records(
        _pipe_text_legibility_records(render_params, layout_seed=int(layout_seed), style=pipe_style)
    )
    panel_geometry["pipe_visual_style"] = _pipe_style_metadata(pipe_style)
    panel_geometry["font_family"] = str(render_params.font_family or "")
    panel_geometry["font_asset"] = (
        dict(render_params.font_asset)
        if isinstance(render_params.font_asset, Mapping)
        else dict(get_font_family_record(str(render_params.font_family)).to_trace())
        if str(render_params.font_family or "").strip()
        else {}
    )
    panel_geometry["font_asset_version"] = str(render_params.font_asset_version or font_asset_version())
    panel_geometry["font_exclusion_reason"] = str(render_params.font_exclusion_reason)
    _draw_panel(
        image,
        panel_geometry=panel_geometry,
        render_params=render_params,
        scene_title=str(scene_title),
        layout_seed=int(layout_seed),
    )
    block_context_elements = list(
        draw_graph_context_text_blocks(
            image,
            panel_geometry=panel_geometry,
            render_params=render_params,
            layout_seed=int(layout_seed),
        )
    )
    chip_context_elements = draw_graph_context_text_chips(
        image,
        panel_geometry=panel_geometry,
        render_params=render_params,
        layout_seed=int(layout_seed),
    )
    panel_context_elements = list(panel_geometry.get("context_text_elements", []))
    panel_context_elements.extend([dict(element) for element in block_context_elements])
    panel_context_elements.extend([dict(element) for element in chip_context_elements])
    if panel_context_elements:
        panel_geometry["context_text_elements"] = [dict(element) for element in panel_context_elements]
    apply_graph_content_layout_jitter(
        panel_geometry,
        render_params=render_params,
        layout_seed=int(layout_seed),
    )

    content_bbox = tuple(int(value) for value in panel_geometry["scene_content_xyxy"])
    _draw_pipe_board_background(draw, content_bbox=content_bbox, style=pipe_style)
    grid_centers = _grid_cell_centers(
        grid_shape_variant=str(pipe_sample.grid_shape_variant),
        content_bbox=content_bbox,
        node_radius_px=int(render_params.node_radius_px),
    )
    node_centers = {
        int(node): grid_centers[tuple(int(value) for value in cell)]
        for node, cell in pipe_sample.node_grid_cells.items()
    }

    open_width = max(18, int(render_params.edge_width_px) * 4 + 4)
    blocked_width = max(16, int(render_params.edge_width_px) * 4)

    rendered_edges: list[RenderedPipeJunctionEdge] = []
    all_edges = [(edge, "blocked") for edge in pipe_sample.blocked_edges] + [(edge, "open") for edge in pipe_sample.open_edges]
    for edge, pipe_state in all_edges:
        left, right = int(edge[0]), int(edge[1])
        start, end = _trim_segment_to_node_radius(
            node_centers[int(left)],
            node_centers[int(right)],
            radius=int(render_params.node_radius_px),
        )
        if str(pipe_state) == "blocked":
            _draw_pipe_tube(
                draw,
                segment=(start, end),
                width_px=int(blocked_width),
                outline_rgb=pipe_style["blocked_outline_rgb"],
                fill_rgb=pipe_style["blocked_fill_rgb"],
                highlight_rgb=pipe_style["blocked_highlight_rgb"],
                shadow_rgb=pipe_style["fitting_shadow_rgb"],
            )
            _draw_blocked_valve_marker(
                draw,
                segment=(start, end),
                style=pipe_style,
                width_px=int(blocked_width),
            )
        else:
            _draw_pipe_tube(
                draw,
                segment=(start, end),
                width_px=int(open_width),
                outline_rgb=pipe_style["tube_outline_rgb"],
                fill_rgb=pipe_style["tube_fill_rgb"],
                highlight_rgb=pipe_style["tube_highlight_rgb"],
                shadow_rgb=pipe_style["tube_shadow_rgb"],
            )
        label_edge = _label_edge(pipe_sample.label_by_node, _canonical_node_edge(left, right))
        rendered_edges.append(
            RenderedPipeJunctionEdge(
                edge_id=f"pipe_{label_edge[0]}_{label_edge[1]}_{pipe_state}",
                node_u_label=str(label_edge[0]),
                node_v_label=str(label_edge[1]),
                pipe_state=str(pipe_state),
                segment_px=(tuple(start), tuple(end)),
            )
        )

    rendered_nodes: list[RenderedPipeJunctionNode] = []
    fitting_radius = max(
        int(render_params.node_radius_px) + 7,
        int(round(float(render_params.node_radius_px) * 1.35)),
    )
    label_inner_radius = max(14, int(round(float(fitting_radius) * 0.58)))
    label_font = fit_font_to_box(
        draw,
        text=max(pipe_sample.node_labels, key=len),
        max_width=max(10, int(label_inner_radius * 1.65)),
        max_height=max(10, int(label_inner_radius * 1.20)),
        max_size_px=int(render_params.label_font_size_px),
        min_size_px=11,
        bold=True,
        font_family=str(render_params.font_family or ""),
    )
    resolved_font_size = int(getattr(label_font, "size", render_params.label_font_size_px))
    stroke_width = max(1, int(round(float(resolved_font_size) * 0.10)))
    label_style = resolve_readable_text_style(
        instance_seed=int(layout_seed),
        namespace="graph.pipe_network.junction_label_text",
        role="graph_node_label_text",
        surface_rgbs=(tuple(int(value) for value in pipe_style["fitting_inner_rgb"]),),
        preferred_rgbs=(
            tuple(int(value) for value in render_params.label_text_rgb),
            tuple(int(value) for value in render_params.label_stroke_rgb),
            (255, 255, 255),
            (10, 14, 22),
        ),
        min_contrast_ratio=4.0,
        min_lab_distance=24.0,
    )
    for node in sorted(pipe_sample.graph.nodes()):
        label = str(pipe_sample.label_by_node[int(node)])
        center = tuple(int(value) for value in node_centers[int(node)])
        bbox = _draw_pipe_fitting(draw, center=center, radius=int(fitting_radius), style=pipe_style)
        draw_centered_readable_text(
            draw,
            text=label,
            center=(float(center[0]), float(center[1])),
            font=label_font,
            style=label_style,
            stroke_width=int(stroke_width),
        )
        open_neighbors = tuple(
            sorted((str(pipe_sample.label_by_node[int(neighbor)]) for neighbor in pipe_sample.graph.neighbors(int(node))), key=graph_label_sort_key)
        )
        rendered_nodes.append(
            RenderedPipeJunctionNode(
                label=label,
                open_degree=int(pipe_sample.graph.degree(int(node))),
                grid_cell=tuple(int(value) for value in pipe_sample.node_grid_cells[int(node)]),
                center_xy=center,
                bbox_xyxy=tuple(int(value) for value in bbox),
                open_neighbors=open_neighbors,
            )
        )

    return RenderedPipeJunctionScene(
        image=image,
        panel_geometry=dict(panel_geometry),
        nodes=tuple(rendered_nodes),
        edges=tuple(rendered_edges),
        grid_shape_variant=str(pipe_sample.grid_shape_variant),
        resolved_label_font_size_px=int(resolved_font_size),
        resolved_label_stroke_width_px=int(stroke_width),
        open_pipe_width_px=int(open_width),
        blocked_pipe_width_px=int(blocked_width),
    )


__all__ = [
    "PipeJunctionNetworkSample",
    "RenderedPipeJunctionEdge",
    "RenderedPipeJunctionNode",
    "RenderedPipeJunctionScene",
    "SUPPORTED_PIPE_GRID_SHAPE_VARIANTS",
    "SUPPORTED_PIPE_LABEL_VARIANTS",
    "feasible_pipe_node_counts",
    "parse_pipe_grid_shape",
    "projected_pipe_edge_pair_evidence",
    "projected_pipe_node_point_evidence",
    "render_pipe_network_scene",
    "sample_pipe_bridge_network",
    "sample_pipe_exact_distance_network",
    "sample_pipe_reachable_network",
    "sample_pipe_shortest_path_network",
]
