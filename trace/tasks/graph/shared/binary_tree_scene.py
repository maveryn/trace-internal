"""Shared binary-tree sampling and rendering for graph-domain tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ...shared.font_assets import font_asset_version, get_font_family_record
from ...shared.text_legibility import draw_centered_readable_text, resolve_readable_text_style
from ...shared.text_rendering import fit_font_to_box, load_font
from .graph_scene import (
    GraphRenderParams,
    SUPPORTED_NODE_SHAPE_VARIANTS,
    apply_graph_content_layout_jitter,
    draw_graph_context_text_blocks,
    draw_graph_context_text_chips,
)
from .label_assets import default_graph_label_bucket_weights, resolve_graph_node_labels


SUPPORTED_BINARY_TREE_COUNT_QUERY_IDS: Tuple[str, ...] = (
    "leaf_node_count",
    "internal_node_count",
    "single_child_node_count",
    "two_child_node_count",
    "depth_level_node_count",
)
SUPPORTED_BINARY_TREE_TRAVERSAL_QUERY_IDS: Tuple[str, ...] = (
    "preorder_kth_node_label",
    "inorder_kth_node_label",
    "postorder_kth_node_label",
    "level_order_kth_node_label",
)
SUPPORTED_BINARY_TREE_SCENE_VARIANTS: Tuple[str, ...] = (
    "classic_tree",
    "paper_tree",
    "boxed_tree",
)
SUPPORTED_BINARY_TREE_CONNECTOR_STYLE_VARIANTS: Tuple[str, ...] = (
    "diagonal_edges",
    "elbow_edges",
)


@dataclass(frozen=True)
class BinaryTreeNode:
    """One labeled node in a rooted ordered binary tree."""

    node_id: str
    label: str
    parent_id: str | None
    left_id: str | None
    right_id: str | None
    depth: int


@dataclass(frozen=True)
class BinaryTreeSample:
    """Trace-ready binary-tree structure and derived orders."""

    nodes: Tuple[BinaryTreeNode, ...]
    root_id: str
    label_variant: str
    label_source_kind: str
    label_bucket: str
    label_manifest: str
    label_filter: Dict[str, Any]
    label_bucket_probabilities: Dict[str, float]
    preorder_labels: Tuple[str, ...]
    inorder_labels: Tuple[str, ...]
    postorder_labels: Tuple[str, ...]
    level_order_labels: Tuple[str, ...]

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def max_depth(self) -> int:
        return max((int(node.depth) for node in self.nodes), default=0)


@dataclass(frozen=True)
class RenderedBinaryTreeNode:
    """Rendered node projection for one binary-tree diagram."""

    node_id: str
    label: str
    parent_label: str | None
    left_label: str | None
    right_label: str | None
    depth: int
    center_xy: Tuple[int, int]
    bbox_xyxy: Tuple[int, int, int, int]


@dataclass(frozen=True)
class RenderedBinaryTreeEdge:
    """Rendered parent-child edge projection for one binary-tree diagram."""

    edge_id: str
    parent_label: str
    child_label: str
    child_side: str
    segment_px: Tuple[Tuple[int, int], Tuple[int, int]]
    connector_path_px: Tuple[Tuple[int, int], ...]
    connector_style_variant: str


@dataclass(frozen=True)
class RenderedBinaryTreeScene:
    """Full render output for one binary-tree diagram."""

    image: Image.Image
    panel_geometry: Dict[str, Any]
    nodes: Tuple[RenderedBinaryTreeNode, ...]
    edges: Tuple[RenderedBinaryTreeEdge, ...]
    scene_variant: str
    connector_style_variant: str
    resolved_label_font_size_px: int
    resolved_label_stroke_width_px: int


def _sort_node_ids_by_level(node_ids: Sequence[str]) -> Tuple[str, ...]:
    return tuple(sorted((str(node_id) for node_id in node_ids), key=lambda value: (len(value), value)))


def _children_for_type(rng, node_type: str) -> Tuple[str, ...]:
    if str(node_type) == "two":
        return ("L", "R")
    if bool(rng.randrange(2)):
        return ("L",)
    return ("R",)


def _child_key(side: str) -> str:
    if str(side) == "L":
        return "left_id"
    if str(side) == "R":
        return "right_id"
    raise ValueError(f"unsupported binary-tree child side: {side}")


def _build_tree_from_internal_counts(
    rng,
    *,
    two_child_count: int,
    single_child_count: int,
    max_depth: int,
    max_attempts: int = 200,
) -> Tuple[Dict[str, Dict[str, Any]], str]:
    """Construct an ordered binary tree with exact internal-node type counts."""

    two_count = int(two_child_count)
    single_count = int(single_child_count)
    if two_count < 1:
        raise ValueError("binary tree construction requires at least one two-child node")
    if single_count < 0:
        raise ValueError("single_child_count must be non-negative")
    max_allowed_depth = max(2, int(max_depth))

    for _attempt in range(max(1, int(max_attempts))):
        nodes: Dict[str, Dict[str, Any]] = {
            "": {"parent_id": None, "left_id": None, "right_id": None, "depth": 0}
        }
        remaining_types: List[str] = ["two"] * max(0, two_count - 1) + ["single"] * single_count
        rng.shuffle(remaining_types)
        open_slots: List[Tuple[str, str]] = [("", "L"), ("", "R")]
        failed = False
        while remaining_types:
            feasible_slot_indices = [
                index
                for index, (parent_id, _side) in enumerate(open_slots)
                if int(nodes[str(parent_id)]["depth"]) + 1 < max_allowed_depth
            ]
            if not feasible_slot_indices:
                failed = True
                break
            slot_index = int(rng.choice(feasible_slot_indices))
            parent_id, side = open_slots.pop(slot_index)
            node_type = remaining_types.pop(0)
            node_id = f"{parent_id}{side}"
            depth = int(nodes[str(parent_id)]["depth"]) + 1
            nodes[node_id] = {"parent_id": str(parent_id), "left_id": None, "right_id": None, "depth": int(depth)}
            nodes[str(parent_id)][_child_key(str(side))] = str(node_id)
            child_sides = list(_children_for_type(rng, str(node_type)))
            rng.shuffle(child_sides)
            for child_side in child_sides:
                open_slots.append((str(node_id), str(child_side)))
            rng.shuffle(open_slots)
        if failed:
            continue

        for parent_id, side in list(open_slots):
            node_id = f"{parent_id}{side}"
            depth = int(nodes[str(parent_id)]["depth"]) + 1
            if depth > max_allowed_depth:
                failed = True
                break
            nodes[node_id] = {"parent_id": str(parent_id), "left_id": None, "right_id": None, "depth": int(depth)}
            nodes[str(parent_id)][_child_key(str(side))] = str(node_id)
        if failed:
            continue
        return nodes, ""

    raise ValueError("could not construct binary tree with requested node-type counts")


def _build_tree_for_depth_count(
    rng,
    *,
    target_depth: int,
    target_count: int,
    node_count_min: int,
    node_count_max: int,
    max_depth: int,
    compact_selection: bool = False,
) -> Tuple[Dict[str, Dict[str, Any]], str]:
    """Construct a tree with an exact number of nodes at a target depth."""

    depth = int(target_depth)
    count = int(target_count)
    if depth < 1 or count < 1:
        raise ValueError("target_depth and target_count must be positive for depth-level count")
    if count > 2 ** depth:
        raise ValueError("target_count is infeasible for the requested depth")

    positions = ["".join(bits) for bits in _binary_path_product(depth)]
    if bool(compact_selection):
        max_start = max(0, len(positions) - int(count))
        start = int(rng.randint(0, int(max_start))) if int(max_start) > 0 else 0
        selected = set(positions[int(start) : int(start) + int(count)])
    else:
        rng.shuffle(positions)
        selected = set(positions[:count])
    node_ids = {""}
    for path in selected:
        for length in range(1, len(path) + 1):
            node_ids.add(path[:length])

    if len(node_ids) > int(node_count_max):
        raise ValueError("depth target creates more nodes than node_count_max")

    max_allowed_depth = max(int(depth), int(max_depth))
    open_slots = [
        f"{node_id}{side}"
        for node_id in sorted(node_ids, key=lambda value: (len(value), value))
        for side in ("L", "R")
        if f"{node_id}{side}" not in node_ids
        and len(f"{node_id}{side}") != depth
        and len(f"{node_id}{side}") <= max_allowed_depth
    ]
    rng.shuffle(open_slots)
    target_total = int(rng.randint(max(len(node_ids), int(node_count_min)), int(node_count_max)))
    while len(node_ids) < target_total and open_slots:
        slot = str(open_slots.pop(0))
        if len(slot) == depth:
            continue
        parent_id = slot[:-1]
        if parent_id not in node_ids:
            continue
        node_ids.add(slot)
        if len(slot) < max_allowed_depth:
            child_slots = [
                f"{slot}{side}"
                for side in ("L", "R")
                if len(f"{slot}{side}") != depth and len(f"{slot}{side}") <= max_allowed_depth
            ]
            rng.shuffle(child_slots)
            open_slots.extend(child_slots)
            rng.shuffle(open_slots)

    nodes: Dict[str, Dict[str, Any]] = {
        node_id: {"parent_id": None if node_id == "" else node_id[:-1], "left_id": None, "right_id": None, "depth": len(node_id)}
        for node_id in node_ids
    }
    for node_id in list(node_ids):
        if node_id == "":
            continue
        parent_id = node_id[:-1]
        side = node_id[-1]
        nodes[str(parent_id)][_child_key(str(side))] = str(node_id)
    actual = sum(1 for node_id in node_ids if len(node_id) == depth)
    if int(actual) != int(count):
        raise ValueError("depth-level construction failed to preserve target count")
    if len(node_ids) < int(node_count_min) or len(node_ids) > int(node_count_max):
        raise ValueError("depth-level construction fell outside configured node count range")
    return nodes, ""


def _binary_path_product(length: int) -> Tuple[Tuple[str, ...], ...]:
    if int(length) <= 0:
        return ((),)
    previous = _binary_path_product(int(length) - 1)
    return tuple((*prefix, side) for prefix in previous for side in ("L", "R"))


def _assign_labels_to_tree(
    rng,
    *,
    nodes: Mapping[str, Mapping[str, Any]],
    label_variant: str,
    max_chars: int,
    min_chars: int | None = None,
    bucket_weights: Mapping[str, float] | None = None,
) -> BinaryTreeSample:
    node_ids = _sort_node_ids_by_level(tuple(nodes.keys()))
    labels = resolve_graph_node_labels(
        rng,
        label_variant=str(label_variant),
        object_count=len(node_ids),
        max_chars=int(max_chars),
        min_chars=min_chars,
        bucket_weights=bucket_weights if bucket_weights is not None else default_graph_label_bucket_weights(),
        sequential_numbers=True,
    )
    label_by_id = {str(node_id): str(label) for node_id, label in zip(node_ids, labels.labels)}

    tree_nodes = tuple(
        BinaryTreeNode(
            node_id=str(node_id),
            label=str(label_by_id[str(node_id)]),
            parent_id=str(nodes[str(node_id)]["parent_id"]) if nodes[str(node_id)].get("parent_id") is not None else None,
            left_id=str(nodes[str(node_id)]["left_id"]) if nodes[str(node_id)].get("left_id") is not None else None,
            right_id=str(nodes[str(node_id)]["right_id"]) if nodes[str(node_id)].get("right_id") is not None else None,
            depth=int(nodes[str(node_id)]["depth"]),
        )
        for node_id in node_ids
    )
    node_by_id = {str(node.node_id): node for node in tree_nodes}

    def preorder(node_id: str) -> List[str]:
        node = node_by_id[str(node_id)]
        result = [str(node.label)]
        if node.left_id is not None:
            result.extend(preorder(str(node.left_id)))
        if node.right_id is not None:
            result.extend(preorder(str(node.right_id)))
        return result

    def inorder(node_id: str) -> List[str]:
        node = node_by_id[str(node_id)]
        result: List[str] = []
        if node.left_id is not None:
            result.extend(inorder(str(node.left_id)))
        result.append(str(node.label))
        if node.right_id is not None:
            result.extend(inorder(str(node.right_id)))
        return result

    def postorder(node_id: str) -> List[str]:
        node = node_by_id[str(node_id)]
        result: List[str] = []
        if node.left_id is not None:
            result.extend(postorder(str(node.left_id)))
        if node.right_id is not None:
            result.extend(postorder(str(node.right_id)))
        result.append(str(node.label))
        return result

    level_order = [str(node_by_id[node_id].label) for node_id in node_ids]
    return BinaryTreeSample(
        nodes=tree_nodes,
        root_id="",
        label_variant=str(labels.label_variant),
        label_source_kind=str(labels.label_source_kind),
        label_bucket=str(labels.label_bucket),
        label_manifest=str(labels.label_manifest),
        label_filter=dict(labels.label_filter),
        label_bucket_probabilities=dict(labels.label_bucket_probabilities),
        preorder_labels=tuple(preorder("")),
        inorder_labels=tuple(inorder("")),
        postorder_labels=tuple(postorder("")),
        level_order_labels=tuple(level_order),
    )


def _node_type_counts(sample: BinaryTreeSample) -> Dict[str, int]:
    counts = {
        "leaf_node_count": 0,
        "internal_node_count": 0,
        "single_child_node_count": 0,
        "two_child_node_count": 0,
    }
    for node in sample.nodes:
        child_count = int(node.left_id is not None) + int(node.right_id is not None)
        if child_count == 0:
            counts["leaf_node_count"] += 1
        else:
            counts["internal_node_count"] += 1
        if child_count == 1:
            counts["single_child_node_count"] += 1
        if child_count == 2:
            counts["two_child_node_count"] += 1
    return counts


def sample_binary_tree_for_count_query(
    instance_seed: int,
    *,
    query_id: str,
    target_count: int,
    target_depth: int | None,
    node_count_min: int,
    node_count_max: int,
    max_depth: int,
    label_variant: str,
    label_max_chars: int,
    max_attempts: int = 200,
) -> BinaryTreeSample:
    """Sample a binary tree whose selected count query has the requested answer."""

    query = str(query_id)
    if query not in set(SUPPORTED_BINARY_TREE_COUNT_QUERY_IDS):
        raise ValueError(f"unsupported binary-tree count query_id: {query_id}")
    target = int(target_count)
    if target < 0:
        raise ValueError("target_count must be non-negative")
    rng = spawn_rng(int(instance_seed), f"binary_tree_count.{query}.{target}.{target_depth}")

    if query == "depth_level_node_count":
        if target_depth is None:
            raise ValueError("target_depth is required for depth_level_node_count")
        for _attempt in range(max(1, int(max_attempts))):
            try:
                nodes, _root = _build_tree_for_depth_count(
                    rng,
                    target_depth=int(target_depth),
                    target_count=int(target),
                    node_count_min=int(node_count_min),
                    node_count_max=int(node_count_max),
                    max_depth=int(max_depth),
                )
            except ValueError:
                continue
            sample = _assign_labels_to_tree(
                spawn_rng(int(instance_seed), f"binary_tree_count.labels.{query}.{_attempt}"),
                nodes=nodes,
                label_variant=str(label_variant),
                max_chars=int(label_max_chars),
            )
            actual = sum(1 for node in sample.nodes if int(node.depth) == int(target_depth))
            if int(actual) == int(target):
                return sample
        for fallback_attempt in range(32):
            try:
                nodes, _root = _build_tree_for_depth_count(
                    rng,
                    target_depth=int(target_depth),
                    target_count=int(target),
                    node_count_min=int(node_count_min),
                    node_count_max=int(node_count_max),
                    max_depth=int(max_depth),
                    compact_selection=True,
                )
            except ValueError:
                continue
            sample = _assign_labels_to_tree(
                spawn_rng(int(instance_seed), f"binary_tree_count.labels.{query}.compact.{fallback_attempt}"),
                nodes=nodes,
                label_variant=str(label_variant),
                max_chars=int(label_max_chars),
            )
            actual = sum(1 for node in sample.nodes if int(node.depth) == int(target_depth))
            if int(actual) == int(target):
                return sample
        raise ValueError("could not sample depth-level binary tree")

    for attempt in range(max(1, int(max_attempts))):
        if query == "leaf_node_count":
            two_count = max(1, target - 1)
            single_max = max(0, int(node_count_max) - ((2 * int(two_count)) + 1))
            single_min = max(0, int(node_count_min) - ((2 * int(two_count)) + 1))
            single_count = int(rng.randint(int(single_min), int(max(single_min, single_max)))) if single_max >= single_min else int(single_min)
        elif query == "two_child_node_count":
            two_count = max(1, target)
            single_max = max(0, int(node_count_max) - ((2 * int(two_count)) + 1))
            single_min = max(0, int(node_count_min) - ((2 * int(two_count)) + 1))
            single_count = int(rng.randint(int(single_min), int(max(single_min, single_max)))) if single_max >= single_min else int(single_min)
        elif query == "single_child_node_count":
            single_count = int(target)
            feasible_two = [
                two
                for two in range(1, max(2, int(node_count_max)))
                if int(node_count_min) <= ((2 * int(two)) + 1 + int(single_count)) <= int(node_count_max)
            ]
            if not feasible_two:
                raise ValueError("no feasible two-child count for requested single-child target")
            two_count = int(rng.choice(feasible_two))
        else:
            internal_count = int(target)
            feasible_two = [
                two
                for two in range(1, int(internal_count) + 1)
                if int(node_count_min) <= (int(internal_count) + int(two) + 1) <= int(node_count_max)
            ]
            if not feasible_two:
                raise ValueError("no feasible two-child count for requested internal-node target")
            two_count = int(rng.choice(feasible_two))
            single_count = int(internal_count) - int(two_count)

        try:
            nodes, _root = _build_tree_from_internal_counts(
                rng,
                two_child_count=int(two_count),
                single_child_count=int(single_count),
                max_depth=int(max_depth),
            )
        except ValueError:
            continue
        sample = _assign_labels_to_tree(
            spawn_rng(int(instance_seed), f"binary_tree_count.labels.{query}.{attempt}"),
            nodes=nodes,
            label_variant=str(label_variant),
            max_chars=int(label_max_chars),
        )
        counts = _node_type_counts(sample)
        actual = int(counts[str(query)])
        if actual == int(target):
            return sample
    raise ValueError("could not sample binary tree for count query")


def sample_binary_tree_for_traversal_query(
    instance_seed: int,
    *,
    node_count_min: int,
    node_count_max: int,
    max_depth: int,
    label_variant: str,
    label_max_chars: int,
    max_attempts: int = 200,
) -> BinaryTreeSample:
    """Sample a varied binary tree for traversal-order queries."""

    rng = spawn_rng(int(instance_seed), "binary_tree_traversal.shape")
    feasible_pairs = [
        (two, single)
        for two in range(1, max(2, int(node_count_max)))
        for single in range(0, max(1, int(node_count_max)))
        if int(node_count_min) <= ((2 * int(two)) + 1 + int(single)) <= int(node_count_max)
    ]
    if not feasible_pairs:
        raise ValueError("no feasible binary-tree traversal support")
    for attempt in range(max(1, int(max_attempts))):
        two_count, single_count = rng.choice(feasible_pairs)
        try:
            nodes, _root = _build_tree_from_internal_counts(
                rng,
                two_child_count=int(two_count),
                single_child_count=int(single_count),
                max_depth=int(max_depth),
            )
        except ValueError:
            continue
        sample = _assign_labels_to_tree(
            spawn_rng(int(instance_seed), f"binary_tree_traversal.labels.{attempt}"),
            nodes=nodes,
            label_variant=str(label_variant),
            max_chars=int(label_max_chars),
        )
        if int(sample.node_count) >= int(node_count_min) and int(sample.node_count) <= int(node_count_max):
            return sample
    raise ValueError("could not sample binary tree for traversal query")


def traversal_labels_for_query(sample: BinaryTreeSample, query_id: str) -> Tuple[str, ...]:
    """Return the ordered labels for one traversal query id."""

    query = str(query_id)
    if query == "preorder_kth_node_label":
        return tuple(sample.preorder_labels)
    if query == "inorder_kth_node_label":
        return tuple(sample.inorder_labels)
    if query == "postorder_kth_node_label":
        return tuple(sample.postorder_labels)
    if query == "level_order_kth_node_label":
        return tuple(sample.level_order_labels)
    raise ValueError(f"unsupported traversal query_id: {query_id}")


def target_labels_for_count_query(
    sample: BinaryTreeSample,
    *,
    query_id: str,
    target_depth: int | None = None,
) -> Tuple[str, ...]:
    """Return labels counted by one binary-tree count query."""

    query = str(query_id)
    labels: List[str] = []
    for node in sample.nodes:
        child_count = int(node.left_id is not None) + int(node.right_id is not None)
        if query == "leaf_node_count" and child_count == 0:
            labels.append(str(node.label))
        elif query == "internal_node_count" and child_count > 0:
            labels.append(str(node.label))
        elif query == "single_child_node_count" and child_count == 1:
            labels.append(str(node.label))
        elif query == "two_child_node_count" and child_count == 2:
            labels.append(str(node.label))
        elif query == "depth_level_node_count" and target_depth is not None and int(node.depth) == int(target_depth):
            labels.append(str(node.label))
    return tuple(labels)


def _resolve_panel_geometry(render_params: GraphRenderParams) -> Dict[str, Any]:
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    margin = int(render_params.outer_margin_px)
    panel = (margin, margin, width - margin, height - margin)
    title_band_height = max(42, int(round(float(render_params.panel_title_font_size_px) * 1.85)))
    title_band = (panel[0], panel[1], panel[2], panel[1] + title_band_height)
    content = (
        panel[0] + int(render_params.panel_padding_px),
        title_band[3] + max(14, int(render_params.panel_padding_px // 2)),
        panel[2] - int(render_params.panel_padding_px),
        panel[3] - int(render_params.panel_padding_px),
    )
    return {
        "canvas_size": [width, height],
        "panel_xyxy": [int(value) for value in panel],
        "scene_panel_xyxy": [int(value) for value in panel],
        "title_band_xyxy": [int(value) for value in title_band],
        "scene_content_xyxy": [int(value) for value in content],
    }


def _draw_node_shape(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[int, int],
    radius: int,
    shape_variant: str,
    fill_rgb: Sequence[int],
    outline_rgb: Sequence[int],
    outline_width: int,
) -> Tuple[int, int, int, int]:
    bbox = (
        int(center[0] - radius),
        int(center[1] - radius),
        int(center[0] + radius),
        int(center[1] + radius),
    )
    fill = tuple(int(value) for value in fill_rgb)
    outline = tuple(int(value) for value in outline_rgb)
    if str(shape_variant) == "rounded_square":
        draw.rounded_rectangle(
            bbox,
            radius=max(5, int(round(float(radius) * 0.32))),
            fill=fill,
            outline=outline,
            width=max(1, int(outline_width)),
        )
    elif str(shape_variant) == "hexagon":
        points = []
        for index in range(6):
            angle = math.radians(30.0 + (60.0 * float(index)))
            points.append(
                (
                    int(round(float(center[0]) + (float(radius) * math.cos(angle)))),
                    int(round(float(center[1]) + (float(radius) * math.sin(angle)))),
                )
            )
        draw.polygon(points, fill=fill, outline=outline)
        if int(outline_width) > 1:
            draw.line(points + [points[0]], fill=outline, width=max(1, int(outline_width)))
    else:
        draw.ellipse(bbox, fill=fill, outline=outline, width=max(1, int(outline_width)))
    return bbox


def _trim_segment(
    start: Tuple[int, int],
    end: Tuple[int, int],
    *,
    trim_px: int,
) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    dx = float(end[0] - start[0])
    dy = float(end[1] - start[1])
    length = math.hypot(dx, dy)
    if length <= 1e-6:
        return (tuple(start), tuple(end))
    ux = dx / length
    uy = dy / length
    return (
        (int(round(float(start[0]) + (ux * float(trim_px)))), int(round(float(start[1]) + (uy * float(trim_px))))),
        (int(round(float(end[0]) - (ux * float(trim_px)))), int(round(float(end[1]) - (uy * float(trim_px))))),
    )


def _connector_path(
    start: Tuple[int, int],
    end: Tuple[int, int],
    *,
    connector_style_variant: str,
    trim_px: int,
) -> Tuple[Tuple[int, int], ...]:
    """Return a rendered parent-child connector path outside node interiors."""

    if str(connector_style_variant) != "elbow_edges":
        segment = _trim_segment(start, end, trim_px=max(1, int(trim_px)))
        return (tuple(segment[0]), tuple(segment[1]))

    direction = 1 if int(end[1]) >= int(start[1]) else -1
    start_trim = (int(start[0]), int(start[1] + (direction * max(1, int(trim_px)))))
    end_trim = (int(end[0]), int(end[1] - (direction * max(1, int(trim_px)))))
    mid_y = int(round(0.5 * float(start_trim[1] + end_trim[1])))
    return (
        tuple(start_trim),
        (int(start_trim[0]), int(mid_y)),
        (int(end_trim[0]), int(mid_y)),
        tuple(end_trim),
    )


def _connector_style_for_scene(scene_variant: str) -> str:
    """Use worksheet-style elbow connectors on paper trees, diagonal elsewhere."""

    return "elbow_edges" if str(scene_variant) == "paper_tree" else "diagonal_edges"


def _binary_tree_positions(
    sample: BinaryTreeSample,
    *,
    content_bbox: Sequence[int],
    node_radius_px: int,
) -> Dict[str, Tuple[int, int]]:
    node_by_id = {str(node.node_id): node for node in sample.nodes}

    def inorder_ids(node_id: str) -> List[str]:
        node = node_by_id[str(node_id)]
        result: List[str] = []
        if node.left_id is not None:
            result.extend(inorder_ids(str(node.left_id)))
        result.append(str(node_id))
        if node.right_id is not None:
            result.extend(inorder_ids(str(node.right_id)))
        return result

    ordered = inorder_ids(sample.root_id)
    x0, y0, x1, y1 = (int(value) for value in content_bbox)
    width = max(1, int(x1 - x0))
    height = max(1, int(y1 - y0))
    usable_x0 = x0 + max(int(node_radius_px) + 10, 18)
    usable_x1 = x1 - max(int(node_radius_px) + 10, 18)
    if len(ordered) <= 1:
        x_by_id = {ordered[0]: int(round(0.5 * float(usable_x0 + usable_x1)))}
    else:
        step = float(max(1, usable_x1 - usable_x0)) / float(len(ordered) - 1)
        x_by_id = {node_id: int(round(float(usable_x0) + (float(index) * step))) for index, node_id in enumerate(ordered)}
    level_count = max(1, int(sample.max_depth) + 1)
    if level_count <= 1:
        y_by_depth = {0: int(round(0.5 * float(y0 + y1)))}
    else:
        step_y = float(max(1, height - (2 * int(node_radius_px)) - 16)) / float(level_count - 1)
        top_y = y0 + int(node_radius_px) + 10
        y_by_depth = {depth: int(round(float(top_y) + (float(depth) * step_y))) for depth in range(level_count)}
    return {
        str(node.node_id): (int(x_by_id[str(node.node_id)]), int(y_by_depth[int(node.depth)]))
        for node in sample.nodes
    }


def projected_binary_tree_bbox_annotation(
    rendered_scene: RenderedBinaryTreeScene,
    labels: Sequence[str],
) -> Dict[str, Any]:
    """Project ordered node labels into pixel bbox annotation."""

    requested = [str(label) for label in labels]
    node_by_label = {str(node.label): node for node in rendered_scene.nodes}
    bbox_map: Dict[str, List[float]] = {}
    bbox_set: List[List[float]] = []
    point_set: List[List[float]] = []
    for label in requested:
        node = node_by_label.get(str(label))
        if node is None:
            continue
        bbox = [float(value) for value in node.bbox_xyxy]
        center = [float(node.center_xy[0]), float(node.center_xy[1])]
        bbox_map[str(label)] = list(bbox)
        bbox_set.append(list(bbox))
        point_set.append(list(center))
    return {
        "pixel_bbox_map": bbox_map,
        "bbox_set": [list(bbox) for bbox in bbox_set],
        "pixel_bbox_set": [list(bbox) for bbox in bbox_set],
        "bbox_sequence": [list(bbox) for bbox in bbox_set],
        "pixel_bbox_sequence": [list(bbox) for bbox in bbox_set],
        "pixel_point_set": [list(point) for point in point_set],
        "pixel_point_sequence": [list(point) for point in point_set],
    }


def render_binary_tree_scene(
    *,
    sample: BinaryTreeSample,
    render_params: GraphRenderParams,
    scene_variant: str,
    scene_title: str,
    layout_seed: int = 0,
    base_image: Image.Image | None = None,
) -> RenderedBinaryTreeScene:
    """Render one top-down labeled binary-tree scene."""

    image = (
        base_image.convert("RGB").copy()
        if base_image is not None
        else Image.new("RGB", (int(render_params.canvas_width), int(render_params.canvas_height)), tuple(render_params.background_color_rgb))
    )
    draw = ImageDraw.Draw(image)
    panel_geometry = _resolve_panel_geometry(render_params)
    if isinstance(render_params.information_scene_style, Mapping):
        panel_geometry["information_scene_style"] = dict(render_params.information_scene_style)
    if isinstance(render_params.text_legibility, Mapping):
        panel_geometry["text_legibility"] = dict(render_params.text_legibility)
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
    panel = tuple(int(value) for value in panel_geometry["panel_xyxy"])
    title_band = tuple(int(value) for value in panel_geometry["title_band_xyxy"])
    panel_fill = tuple(int(value) for value in render_params.panel_fill_rgb)
    panel_border = tuple(int(value) for value in render_params.panel_border_rgb)
    resolved_layout_seed = int(layout_seed) + int(sum(ord(ch) for ch in str(scene_title)))
    draw.rounded_rectangle(
        panel,
        radius=max(6, int(render_params.panel_corner_radius_px)),
        fill=panel_fill,
        outline=panel_border,
        width=2,
    )
    title_font = load_font(
        int(render_params.panel_title_font_size_px),
        bold=True,
        font_family=str(render_params.font_family or ""),
    )
    title_style = resolve_readable_text_style(
        instance_seed=int(resolved_layout_seed + int(render_params.canvas_width) + int(render_params.canvas_height)),
        namespace="graph.binary_tree.panel_title_text",
        role="graph_panel_title_text",
        surface_rgbs=(panel_fill,),
        preferred_rgbs=(tuple(int(value) for value in render_params.title_color_rgb),),
        min_contrast_ratio=4.5,
        min_lab_distance=28.0,
    )
    draw_centered_readable_text(
        draw,
        text=str(scene_title),
        center=(0.5 * float(title_band[0] + title_band[2]), 0.5 * float(title_band[1] + title_band[3])),
        font=title_font,
        style=title_style,
        stroke_width=1,
    )

    block_context_elements = list(
        draw_graph_context_text_blocks(
            image,
            panel_geometry=panel_geometry,
            render_params=render_params,
            layout_seed=int(resolved_layout_seed),
        )
    )
    chip_context_elements = draw_graph_context_text_chips(
        image,
        panel_geometry=panel_geometry,
        render_params=render_params,
        layout_seed=int(resolved_layout_seed),
    )
    panel_context_elements = list(panel_geometry.get("context_text_elements", []))
    panel_context_elements.extend([dict(element) for element in block_context_elements])
    panel_context_elements.extend([dict(element) for element in chip_context_elements])
    if panel_context_elements:
        panel_geometry["context_text_elements"] = [dict(element) for element in panel_context_elements]

    apply_graph_content_layout_jitter(
        panel_geometry,
        render_params=render_params,
        layout_seed=int(resolved_layout_seed),
    )
    content = tuple(int(value) for value in panel_geometry["scene_content_xyxy"])
    if str(scene_variant) == "paper_tree":
        line_color = tuple(max(0, min(255, int((int(v) + 178) / 2))) for v in panel_border)
        for y in range(content[1] + 10, content[3], 34):
            draw.line((content[0], y, content[2], y), fill=line_color, width=1)
    elif str(scene_variant) == "boxed_tree":
        draw.rounded_rectangle(
            (content[0] - 8, content[1] - 8, content[2] + 8, content[3] + 8),
            radius=max(8, int(render_params.panel_corner_radius_px // 2)),
            outline=tuple(int(value) for value in render_params.panel_border_rgb),
            width=1,
        )

    positions = _binary_tree_positions(
        sample,
        content_bbox=content,
        node_radius_px=int(render_params.node_radius_px),
    )
    node_by_id = {str(node.node_id): node for node in sample.nodes}
    rendered_edges: List[RenderedBinaryTreeEdge] = []
    connector_style = _connector_style_for_scene(str(scene_variant))
    for node in sample.nodes:
        for side, child_id in (("left", node.left_id), ("right", node.right_id)):
            if child_id is None:
                continue
            start = tuple(int(value) for value in positions[str(node.node_id)])
            end = tuple(int(value) for value in positions[str(child_id)])
            path = _connector_path(
                start,
                end,
                connector_style_variant=str(connector_style),
                trim_px=max(1, int(render_params.node_radius_px) - 1),
            )
            draw.line(
                list(path),
                fill=tuple(int(value) for value in render_params.edge_color_rgb),
                width=max(1, int(render_params.edge_width_px)),
            )
            rendered_edges.append(
                RenderedBinaryTreeEdge(
                    edge_id=f"edge_{node.label}_{node_by_id[str(child_id)].label}",
                    parent_label=str(node.label),
                    child_label=str(node_by_id[str(child_id)].label),
                    child_side=str(side),
                    segment_px=(tuple(path[0]), tuple(path[-1])),
                    connector_path_px=tuple(tuple(point) for point in path),
                    connector_style_variant=str(connector_style),
                )
            )

    rendered_nodes: List[RenderedBinaryTreeNode] = []
    resolved_font_size = int(render_params.label_font_size_px)
    stroke_width = max(1, int(round(float(render_params.label_font_size_px) * 0.08)))
    shape_variant = str(render_params.node_shape_variant)
    if str(scene_variant) == "boxed_tree" and shape_variant not in SUPPORTED_NODE_SHAPE_VARIANTS:
        shape_variant = "rounded_square"
    for node in sample.nodes:
        center = tuple(int(value) for value in positions[str(node.node_id)])
        bbox = _draw_node_shape(
            draw,
            center=center,
            radius=int(render_params.node_radius_px),
            shape_variant=str(shape_variant),
            fill_rgb=tuple(int(value) for value in render_params.node_fill_rgb),
            outline_rgb=tuple(int(value) for value in render_params.node_border_rgb),
            outline_width=int(render_params.node_border_width_px),
        )
        font = fit_font_to_box(
            draw,
            text=str(node.label),
            max_width=max(8, int(bbox[2] - bbox[0]) - 6),
            max_height=max(8, int(bbox[3] - bbox[1]) - 6),
            bold=True,
            font_family=str(render_params.font_family or ""),
            min_size_px=8,
            max_size_px=int(render_params.label_font_size_px),
            fill_ratio=0.86,
        )
        resolved_font_size = min(int(resolved_font_size), int(getattr(font, "size", resolved_font_size)))
        label_style = resolve_readable_text_style(
            instance_seed=int(sum(ord(ch) for ch in str(node.label)) + int(center[0]) + (997 * int(center[1]))),
            namespace=f"graph.binary_tree.node_label_text.{str(node.label)}",
            role="graph_node_label_text",
            surface_rgbs=(tuple(int(value) for value in render_params.node_fill_rgb),),
            preferred_rgbs=(
                tuple(int(value) for value in render_params.label_text_rgb),
                tuple(int(value) for value in render_params.label_stroke_rgb),
                (255, 255, 255),
                (10, 14, 22),
            ),
            min_contrast_ratio=4.0,
            min_lab_distance=24.0,
        )
        draw_centered_readable_text(
            draw,
            text=str(node.label),
            center=(float(center[0]), float(center[1])),
            font=font,
            style=label_style,
            stroke_width=stroke_width,
        )
        parent_label = str(node_by_id[str(node.parent_id)].label) if node.parent_id is not None else None
        left_label = str(node_by_id[str(node.left_id)].label) if node.left_id is not None else None
        right_label = str(node_by_id[str(node.right_id)].label) if node.right_id is not None else None
        rendered_nodes.append(
            RenderedBinaryTreeNode(
                node_id=str(node.node_id),
                label=str(node.label),
                parent_label=parent_label,
                left_label=left_label,
                right_label=right_label,
                depth=int(node.depth),
                center_xy=tuple(center),
                bbox_xyxy=tuple(int(value) for value in bbox),
            )
        )

    return RenderedBinaryTreeScene(
        image=image,
        panel_geometry={str(key): value for key, value in panel_geometry.items()},
        nodes=tuple(rendered_nodes),
        edges=tuple(rendered_edges),
        scene_variant=str(scene_variant),
        connector_style_variant=str(connector_style),
        resolved_label_font_size_px=int(resolved_font_size),
        resolved_label_stroke_width_px=int(stroke_width),
    )


__all__ = [
    "BinaryTreeSample",
    "RenderedBinaryTreeScene",
    "SUPPORTED_BINARY_TREE_COUNT_QUERY_IDS",
    "SUPPORTED_BINARY_TREE_CONNECTOR_STYLE_VARIANTS",
    "SUPPORTED_BINARY_TREE_SCENE_VARIANTS",
    "SUPPORTED_BINARY_TREE_TRAVERSAL_QUERY_IDS",
    "projected_binary_tree_bbox_annotation",
    "render_binary_tree_scene",
    "sample_binary_tree_for_count_query",
    "sample_binary_tree_for_traversal_query",
    "target_labels_for_count_query",
    "traversal_labels_for_query",
]
