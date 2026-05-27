"""Shared adjacency-list and adjacency-matrix scenes for graph-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ...shared.drawing import draw_rounded_rect
from ...shared.text_rendering import draw_text_centered, fit_font_to_box, load_font
from .label_assets import default_graph_label_bucket_weights, resolve_graph_node_labels


SCENE_ID = "adjacency"
SUPPORTED_ADJACENCY_REPRESENTATION_VARIANTS: Tuple[str, ...] = (
    "adjacency_list_panel",
    "adjacency_matrix_panel",
)


@dataclass(frozen=True)
class AdjacencyLabelSet:
    """Resolved graph labels plus provenance metadata."""

    labels: Tuple[str, ...]
    label_variant: str
    label_source_kind: str
    label_bucket: str
    label_manifest: str
    label_filter: Mapping[str, Any]
    label_bucket_probabilities: Mapping[str, float]


@dataclass(frozen=True)
class AdjacencyGraphSample:
    """Symbolic graph represented by an adjacency list or matrix."""

    labels: Tuple[str, ...]
    directed: bool
    adjacency: Mapping[str, Tuple[str, ...]]
    edges: Tuple[Tuple[str, str], ...]
    weights: Mapping[Tuple[str, str], int]
    components: Tuple[Tuple[str, ...], ...] = ()
    mst_edges: Tuple[Tuple[str, str], ...] = ()
    mst_weight: int = 0


@dataclass(frozen=True)
class AdjacencyRepresentationRender:
    """Rendered adjacency representation and pixel evidence anchors."""

    image: Image.Image
    representation_variant: str
    panel_bbox: List[float]
    node_label_bboxes: Mapping[str, List[float]]
    row_label_bboxes: Mapping[str, List[float]]
    column_label_bboxes: Mapping[str, List[float]]
    cell_bboxes: Mapping[str, List[float]]
    panel_geometry: Mapping[str, Any]
    style_meta: Mapping[str, Any]


def canonical_undirected_edge(left: str, right: str) -> Tuple[str, str]:
    """Return one deterministic undirected edge key."""

    a = str(left)
    b = str(right)
    return (a, b) if a <= b else (b, a)


def matrix_cell_key(row_label: str, column_label: str) -> str:
    """Return stable string key for a rendered matrix cell."""

    return f"{str(row_label)}||{str(column_label)}"


def resolve_adjacency_labels(
    *,
    instance_seed: int,
    task_id: str,
    label_variant: str,
    node_count: int,
    max_chars: int,
    min_chars: int | None = None,
    bucket_weights: Mapping[str, float] | None = None,
) -> AdjacencyLabelSet:
    """Resolve compact node labels for adjacency panels."""

    resolved = resolve_graph_node_labels(
        spawn_rng(int(instance_seed), f"{str(task_id)}.labels"),
        label_variant=str(label_variant),
        object_count=int(node_count),
        max_chars=int(max_chars),
        min_chars=min_chars,
        bucket_weights=bucket_weights or default_graph_label_bucket_weights(),
        sequential_numbers=True,
    )
    return AdjacencyLabelSet(
        labels=tuple(str(label) for label in resolved.labels),
        label_variant=str(resolved.label_variant),
        label_source_kind=str(resolved.label_source_kind),
        label_bucket=str(resolved.label_bucket),
        label_manifest=str(resolved.label_manifest),
        label_filter=dict(resolved.label_filter),
        label_bucket_probabilities=dict(resolved.label_bucket_probabilities),
    )


def _edge_set_from_adjacency(adjacency: Mapping[str, Sequence[str]], *, directed: bool) -> Tuple[Tuple[str, str], ...]:
    edges: set[Tuple[str, str]] = set()
    for source, targets in adjacency.items():
        for target in targets:
            if bool(directed):
                edges.add((str(source), str(target)))
            else:
                edges.add(canonical_undirected_edge(str(source), str(target)))
    return tuple(sorted(edges))


def bfs_visit_order(adjacency: Mapping[str, Sequence[str]], source: str) -> Tuple[str, ...]:
    """Return BFS order using the neighbor order shown in the adjacency list."""

    start = str(source)
    visited = {start}
    queue = [start]
    order: List[str] = []
    while queue:
        node = queue.pop(0)
        order.append(str(node))
        for neighbor in adjacency.get(str(node), ()):
            label = str(neighbor)
            if label in visited:
                continue
            visited.add(label)
            queue.append(label)
    return tuple(order)


def dfs_visit_order(adjacency: Mapping[str, Sequence[str]], source: str) -> Tuple[str, ...]:
    """Return recursive DFS preorder using the shown neighbor order."""

    visited: set[str] = set()
    order: List[str] = []

    def _visit(node: str) -> None:
        visited.add(str(node))
        order.append(str(node))
        for neighbor in adjacency.get(str(node), ()):
            label = str(neighbor)
            if label not in visited:
                _visit(label)

    _visit(str(source))
    return tuple(order)


def sample_reachable_directed_adjacency(
    *,
    instance_seed: int,
    task_id: str,
    labels: Sequence[str],
    source_label: str,
    extra_edge_count: int,
) -> AdjacencyGraphSample:
    """Sample a directed graph where every node is reachable from source."""

    rng = spawn_rng(int(instance_seed), f"{str(task_id)}.reachable_digraph")
    label_order = tuple(str(label) for label in labels)
    source = str(source_label)
    remaining = [label for label in label_order if label != source]
    rng.shuffle(remaining)
    reached = [source]
    edges: set[Tuple[str, str]] = set()
    for label in remaining:
        parent = str(rng.choice(reached))
        edges.add((parent, str(label)))
        reached.append(str(label))
    all_pairs = [(left, right) for left in label_order for right in label_order if left != right]
    rng.shuffle(all_pairs)
    for edge in all_pairs:
        if len(edges) >= (len(label_order) - 1) + int(extra_edge_count):
            break
        edges.add((str(edge[0]), str(edge[1])))
    adjacency_lists: Dict[str, List[str]] = {label: [] for label in label_order}
    for left, right in sorted(edges):
        adjacency_lists[str(left)].append(str(right))
    for targets in adjacency_lists.values():
        rng.shuffle(targets)
    adjacency = {label: tuple(targets) for label, targets in adjacency_lists.items()}
    return AdjacencyGraphSample(
        labels=label_order,
        directed=True,
        adjacency=adjacency,
        edges=_edge_set_from_adjacency(adjacency, directed=True),
        weights={},
    )


def _partition_labels(labels: Sequence[str], component_count: int, rng) -> Tuple[Tuple[str, ...], ...]:
    shuffled = [str(label) for label in labels]
    rng.shuffle(shuffled)
    count = max(1, min(int(component_count), len(shuffled)))
    groups: List[List[str]] = [[] for _ in range(count)]
    for index, label in enumerate(shuffled):
        groups[int(index % count)].append(str(label))
    return tuple(tuple(group) for group in groups if group)


def sample_component_adjacency(
    *,
    instance_seed: int,
    task_id: str,
    labels: Sequence[str],
    component_count: int,
    directed: bool,
    extra_edge_count: int,
) -> AdjacencyGraphSample:
    """Sample an undirected component graph or directed SCC graph."""

    rng = spawn_rng(int(instance_seed), f"{str(task_id)}.components.{int(component_count)}.{bool(directed)}")
    label_order = tuple(str(label) for label in labels)
    components = _partition_labels(label_order, int(component_count), rng)
    adjacency_lists: Dict[str, List[str]] = {label: [] for label in label_order}
    edges: set[Tuple[str, str]] = set()

    for component in components:
        nodes = list(component)
        if len(nodes) <= 1:
            continue
        if bool(directed):
            for index, source in enumerate(nodes):
                target = nodes[(index + 1) % len(nodes)]
                edges.add((str(source), str(target)))
            if len(nodes) > 2:
                edges.add((str(nodes[0]), str(nodes[2])))
        else:
            for left, right in zip(nodes, nodes[1:]):
                edges.add(canonical_undirected_edge(str(left), str(right)))
            possible = [canonical_undirected_edge(a, b) for idx, a in enumerate(nodes) for b in nodes[idx + 1 :]]
            rng.shuffle(possible)
            for edge in possible[: max(0, int(extra_edge_count))]:
                edges.add(edge)

    if bool(directed) and len(components) >= 2:
        for left_component, right_component in zip(components, components[1:]):
            edges.add((str(left_component[0]), str(right_component[0])))

    for left, right in sorted(edges):
        adjacency_lists[str(left)].append(str(right))
        if not bool(directed):
            adjacency_lists[str(right)].append(str(left))
    for targets in adjacency_lists.values():
        rng.shuffle(targets)

    return AdjacencyGraphSample(
        labels=label_order,
        directed=bool(directed),
        adjacency={label: tuple(targets) for label, targets in adjacency_lists.items()},
        edges=_edge_set_from_adjacency(adjacency_lists, directed=bool(directed)),
        weights={},
        components=tuple(tuple(node for node in component) for component in components),
    )


def sample_weighted_matrix_mst_adjacency(
    *,
    instance_seed: int,
    task_id: str,
    labels: Sequence[str],
    extra_edge_count: int,
    edge_weight_min: int,
    edge_weight_max: int,
) -> AdjacencyGraphSample:
    """Sample a connected weighted graph with a unique obvious MST."""

    rng = spawn_rng(int(instance_seed), f"{str(task_id)}.weighted_matrix_mst")
    label_order = tuple(str(label) for label in labels)
    shuffled = list(label_order)
    rng.shuffle(shuffled)
    tree_edges: List[Tuple[str, str]] = []
    connected = [shuffled[0]]
    for label in shuffled[1:]:
        parent = str(rng.choice(connected))
        tree_edges.append(canonical_undirected_edge(parent, str(label)))
        connected.append(str(label))

    low_max = max(int(edge_weight_min), min(int(edge_weight_max), int(edge_weight_min) + 4))
    tree_weights = {edge: int(rng.randint(int(edge_weight_min), int(low_max))) for edge in tree_edges}
    max_tree_weight = max(tree_weights.values()) if tree_weights else int(edge_weight_min)
    non_tree_min = min(int(edge_weight_max), int(max_tree_weight) + 2)
    if int(non_tree_min) > int(edge_weight_max):
        non_tree_min = int(edge_weight_max)

    possible = [
        canonical_undirected_edge(left, right)
        for idx, left in enumerate(label_order)
        for right in label_order[idx + 1 :]
        if canonical_undirected_edge(left, right) not in set(tree_edges)
    ]
    rng.shuffle(possible)
    extra_edges = possible[: max(0, int(extra_edge_count))]
    weights: Dict[Tuple[str, str], int] = dict(tree_weights)
    for edge in extra_edges:
        weights[edge] = int(rng.randint(int(non_tree_min), int(edge_weight_max)))

    adjacency_lists: Dict[str, List[str]] = {label: [] for label in label_order}
    for left, right in sorted(weights):
        adjacency_lists[str(left)].append(str(right))
        adjacency_lists[str(right)].append(str(left))
    for targets in adjacency_lists.values():
        targets.sort(key=lambda label: label_order.index(str(label)))

    return AdjacencyGraphSample(
        labels=label_order,
        directed=False,
        adjacency={label: tuple(targets) for label, targets in adjacency_lists.items()},
        edges=tuple(sorted(weights)),
        weights=dict(weights),
        mst_edges=tuple(sorted(tree_edges)),
        mst_weight=int(sum(tree_weights.values())),
    )


def _draw_text_bbox(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    bbox: Sequence[float],
    font_size_px: int,
    fill: Sequence[int],
    stroke_fill: Sequence[int],
    bold: bool = True,
) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=max(1.0, float(x1 - x0 - 4)),
        max_height=max(1.0, float(y1 - y0 - 4)),
        bold=bool(bold),
        min_size_px=8,
        max_size_px=int(font_size_px),
        fill_ratio=0.90,
    )
    draw_text_centered(
        draw,
        text=str(text),
        center=(0.5 * (x0 + x1), 0.5 * (y0 + y1)),
        font=font,
        fill=tuple(int(v) for v in fill),
        stroke_fill=tuple(int(v) for v in stroke_fill),
        stroke_width=1,
    )
    return [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)]


def _panel_style() -> Dict[str, Tuple[int, int, int]]:
    return {
        "panel_fill": (255, 255, 255),
        "panel_border": (197, 207, 222),
        "grid": (205, 214, 228),
        "header_fill": (229, 236, 248),
        "header_text": (45, 55, 72),
        "cell_text": (36, 43, 57),
        "muted_text": (110, 119, 134),
        "accent_fill": (66, 116, 245),
        "accent_text": (255, 255, 255),
    }


def render_adjacency_list_panel(
    *,
    sample: AdjacencyGraphSample,
    base_image: Image.Image,
    title: str,
    subtitle: str,
    font_size_px: int = 20,
) -> AdjacencyRepresentationRender:
    """Render an adjacency-list panel."""

    image = base_image.copy()
    draw = ImageDraw.Draw(image)
    style = _panel_style()
    width, height = image.size
    panel_bbox = [36.0, 34.0, float(width - 36), float(height - 34)]
    draw_rounded_rect(draw, tuple(panel_bbox), radius=20, fill=style["panel_fill"], outline=style["panel_border"], width=2)
    title_font = load_font(24, bold=True)
    body_font = load_font(16, bold=False)
    draw.text((62, 52), str(title), fill=style["header_text"], font=title_font)
    draw.text((62, 84), str(subtitle), fill=style["muted_text"], font=body_font)

    labels = tuple(str(label) for label in sample.labels)
    row_h = min(56, max(40, int((height - 140) / max(1, len(labels)))))
    y0 = 120
    x_label0 = 70
    label_w = 88
    x_neighbors0 = x_label0 + label_w + 38
    node_bboxes: Dict[str, List[float]] = {}
    row_bboxes: Dict[str, List[float]] = {}
    for row_index, label in enumerate(labels):
        top = float(y0 + (row_index * row_h))
        bottom = float(top + row_h - 8)
        row_bbox = [float(x_label0 - 14), float(top), float(width - 70), float(bottom)]
        row_bboxes[str(label)] = [round(value, 3) for value in row_bbox]
        draw_rounded_rect(draw, tuple(row_bbox), radius=10, fill=(248, 250, 253), outline=(225, 231, 240), width=1)
        label_bbox = [float(x_label0), float(top + 6), float(x_label0 + label_w), float(bottom - 6)]
        draw_rounded_rect(draw, tuple(label_bbox), radius=14, fill=style["accent_fill"], outline=(35, 74, 166), width=1)
        node_bboxes[str(label)] = _draw_text_bbox(
            draw,
            text=str(label),
            bbox=label_bbox,
            font_size_px=int(font_size_px),
            fill=style["accent_text"],
            stroke_fill=(25, 62, 150),
        )
        colon_font = load_font(int(font_size_px), bold=True)
        draw_text_centered(
            draw,
            text=":",
            center=(float(x_label0 + label_w + 18), 0.5 * (label_bbox[1] + label_bbox[3])),
            font=colon_font,
            fill=style["header_text"],
            stroke_fill=style["panel_fill"],
            stroke_width=0,
        )
        cursor = float(x_neighbors0)
        targets = tuple(str(target) for target in sample.adjacency.get(str(label), ()))
        if not targets:
            none_bbox = [cursor, float(top + 6), cursor + 72.0, float(bottom - 6)]
            _draw_text_bbox(
                draw,
                text="none",
                bbox=none_bbox,
                font_size_px=max(14, int(font_size_px) - 2),
                fill=style["muted_text"],
                stroke_fill=style["panel_fill"],
                bold=False,
            )
            continue
        for target in targets:
            chip_w = max(48.0, min(96.0, 22.0 + (12.0 * len(str(target)))))
            chip_bbox = [cursor, float(top + 6), cursor + chip_w, float(bottom - 6)]
            draw_rounded_rect(draw, tuple(chip_bbox), radius=12, fill=(239, 244, 252), outline=(197, 207, 222), width=1)
            _draw_text_bbox(
                draw,
                text=str(target),
                bbox=chip_bbox,
                font_size_px=max(13, int(font_size_px) - 2),
                fill=style["cell_text"],
                stroke_fill=(239, 244, 252),
                bold=True,
            )
            cursor += chip_w + 10.0

    return AdjacencyRepresentationRender(
        image=image,
        representation_variant="adjacency_list_panel",
        panel_bbox=list(panel_bbox),
        node_label_bboxes=dict(node_bboxes),
        row_label_bboxes=dict(node_bboxes),
        column_label_bboxes={},
        cell_bboxes={},
        panel_geometry={
            "canvas_size": [int(width), int(height)],
            "panel_bbox": list(panel_bbox),
            "row_bboxes": dict(row_bboxes),
        },
        style_meta={"panel_style": "adjacency_list_card"},
    )


def render_adjacency_matrix_panel(
    *,
    sample: AdjacencyGraphSample,
    base_image: Image.Image,
    title: str,
    subtitle: str,
    weighted: bool,
    font_size_px: int = 19,
) -> AdjacencyRepresentationRender:
    """Render an adjacency matrix or weighted adjacency matrix."""

    image = base_image.copy()
    draw = ImageDraw.Draw(image)
    style = _panel_style()
    width, height = image.size
    panel_bbox = [34.0, 30.0, float(width - 34), float(height - 30)]
    draw_rounded_rect(draw, tuple(panel_bbox), radius=20, fill=style["panel_fill"], outline=style["panel_border"], width=2)
    title_font = load_font(24, bold=True)
    body_font = load_font(16, bold=False)
    draw.text((60, 48), str(title), fill=style["header_text"], font=title_font)
    draw.text((60, 80), str(subtitle), fill=style["muted_text"], font=body_font)

    labels = tuple(str(label) for label in sample.labels)
    n = len(labels)
    available_w = float(width - 120)
    available_h = float(height - 145)
    cell = int(max(34, min(62, available_w / float(n + 1), available_h / float(n + 1))))
    grid_w = cell * (n + 1)
    grid_h = cell * (n + 1)
    left = int(round((width - grid_w) / 2))
    top = 120
    row_bboxes: Dict[str, List[float]] = {}
    col_bboxes: Dict[str, List[float]] = {}
    cell_bboxes: Dict[str, List[float]] = {}

    for row in range(n + 1):
        for col in range(n + 1):
            x0 = float(left + (col * cell))
            y0 = float(top + (row * cell))
            bbox = [x0, y0, x0 + cell, y0 + cell]
            fill = style["header_fill"] if row == 0 or col == 0 else (255, 255, 255)
            draw.rectangle(tuple(bbox), fill=fill, outline=style["grid"], width=1)
            if row == 0 and col == 0:
                continue
            if row == 0:
                label = labels[col - 1]
                col_bboxes[str(label)] = [round(value, 3) for value in bbox]
                _draw_text_bbox(
                    draw,
                    text=str(label),
                    bbox=bbox,
                    font_size_px=int(font_size_px),
                    fill=style["header_text"],
                    stroke_fill=style["header_fill"],
                )
                continue
            if col == 0:
                label = labels[row - 1]
                row_bboxes[str(label)] = [round(value, 3) for value in bbox]
                _draw_text_bbox(
                    draw,
                    text=str(label),
                    bbox=bbox,
                    font_size_px=int(font_size_px),
                    fill=style["header_text"],
                    stroke_fill=style["header_fill"],
                )
                continue
            row_label = labels[row - 1]
            col_label = labels[col - 1]
            cell_bboxes[matrix_cell_key(row_label, col_label)] = [round(value, 3) for value in bbox]
            if row_label == col_label:
                text = "-"
                text_fill = style["muted_text"]
            else:
                edge_key = (str(row_label), str(col_label)) if sample.directed else canonical_undirected_edge(row_label, col_label)
                if bool(weighted):
                    text = str(sample.weights.get(edge_key, ""))
                else:
                    text = "1" if edge_key in set(sample.edges) else "0"
                text_fill = style["cell_text"] if text not in {"", "0"} else style["muted_text"]
            _draw_text_bbox(
                draw,
                text=str(text),
                bbox=bbox,
                font_size_px=max(13, int(font_size_px)),
                fill=text_fill,
                stroke_fill=(255, 255, 255),
                bold=True,
            )

    return AdjacencyRepresentationRender(
        image=image,
        representation_variant="adjacency_matrix_panel",
        panel_bbox=list(panel_bbox),
        node_label_bboxes=dict(row_bboxes),
        row_label_bboxes=dict(row_bboxes),
        column_label_bboxes=dict(col_bboxes),
        cell_bboxes=dict(cell_bboxes),
        panel_geometry={
            "canvas_size": [int(width), int(height)],
            "panel_bbox": list(panel_bbox),
            "matrix_origin_px": [int(left), int(top)],
            "cell_size_px": int(cell),
        },
        style_meta={"panel_style": "weighted_adjacency_matrix" if bool(weighted) else "adjacency_matrix"},
    )


__all__ = [
    "SCENE_ID",
    "SUPPORTED_ADJACENCY_REPRESENTATION_VARIANTS",
    "AdjacencyGraphSample",
    "AdjacencyLabelSet",
    "AdjacencyRepresentationRender",
    "bfs_visit_order",
    "canonical_undirected_edge",
    "dfs_visit_order",
    "matrix_cell_key",
    "render_adjacency_list_panel",
    "render_adjacency_matrix_panel",
    "resolve_adjacency_labels",
    "sample_component_adjacency",
    "sample_reachable_directed_adjacency",
    "sample_weighted_matrix_mst_adjacency",
]
