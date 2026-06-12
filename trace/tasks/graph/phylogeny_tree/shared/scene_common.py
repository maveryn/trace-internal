"""Shared rooted-cladogram sampling and rendering for graph tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from .....core.seed import hash64, spawn_rng
from ....shared.bbox_projection import round_bbox
from ....shared.text_rendering import load_font
from ....shared.text_legibility import draw_text_traced
from ...shared.graph_scene import GraphRenderParams


SUPPORTED_PHYLOGENY_SCENE_VARIANTS: Tuple[str, ...] = (
    "rectangular_cladogram",
    "diagonal_cladogram",
    "paper_cladogram",
)
PHYLOGENY_TAXON_LABEL_POOL: Tuple[str, ...] = tuple("ABCDEFGHIJKLM")


@dataclass(frozen=True)
class PhylogenyNode:
    """One node in a rooted phylogeny tree."""

    node_id: str
    parent_id: str | None
    child_ids: Tuple[str, ...]
    leaf_label: str | None
    depth: int

    @property
    def is_leaf(self) -> bool:
        return self.leaf_label is not None


@dataclass(frozen=True)
class PhylogenySample:
    """Trace-ready rooted phylogeny sample."""

    nodes: Tuple[PhylogenyNode, ...]
    root_id: str
    leaf_labels: Tuple[str, ...]
    canonical_signature: Tuple[Tuple[str, ...], ...]

    @property
    def leaf_count(self) -> int:
        return len(self.leaf_labels)

    @property
    def max_depth(self) -> int:
        return max((int(node.depth) for node in self.nodes), default=0)


@dataclass(frozen=True)
class RenderedPhylogenyNode:
    """Rendered node projection for one phylogeny diagram."""

    node_id: str
    leaf_label: str | None
    descendant_leaf_labels: Tuple[str, ...]
    center_xy: Tuple[int, int]
    bbox_xyxy: Tuple[int, int, int, int]
    label_bbox_xyxy: Tuple[int, int, int, int] | None
    is_leaf: bool


@dataclass(frozen=True)
class RenderedPhylogenyEdge:
    """Rendered parent-child branch projection."""

    edge_id: str
    parent_id: str
    child_id: str
    path_px: Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class RenderedPhylogenyScene:
    """Full render output for one phylogeny diagram."""

    image: Image.Image
    panel_geometry: Dict[str, Any]
    nodes: Tuple[RenderedPhylogenyNode, ...]
    edges: Tuple[RenderedPhylogenyEdge, ...]
    scene_variant: str
    resolved_label_font_size_px: int
    resolved_label_stroke_width_px: int
    option_panel_bboxes: Dict[str, List[float]]


def _node_map(sample: PhylogenySample) -> Dict[str, PhylogenyNode]:
    return {str(node.node_id): node for node in sample.nodes}


def _leaf_node_id_by_label(sample: PhylogenySample) -> Dict[str, str]:
    return {
        str(node.leaf_label): str(node.node_id)
        for node in sample.nodes
        if node.leaf_label is not None
    }


def descendant_leaf_labels(sample: PhylogenySample, node_id: str) -> Tuple[str, ...]:
    """Return all descendant leaf labels for one node."""

    nodes = _node_map(sample)

    def visit(current_id: str) -> List[str]:
        node = nodes[str(current_id)]
        if node.leaf_label is not None:
            return [str(node.leaf_label)]
        labels: List[str] = []
        for child_id in node.child_ids:
            labels.extend(visit(str(child_id)))
        return labels

    return tuple(sorted(visit(str(node_id))))


def canonical_phylogeny_signature(sample: PhylogenySample) -> Tuple[Tuple[str, ...], ...]:
    """Return a rooted topology signature ignoring child order and layout."""

    all_count = int(sample.leaf_count)
    clades = []
    for node in sample.nodes:
        if node.leaf_label is not None:
            continue
        leaves = tuple(descendant_leaf_labels(sample, str(node.node_id)))
        if 2 <= len(leaves) < all_count:
            clades.append(tuple(str(label) for label in leaves))
    return tuple(sorted(clades, key=lambda value: (len(value), value)))


def internal_clade_node_ids(
    sample: PhylogenySample,
    *,
    min_leaf_count: int = 2,
    max_leaf_count: int | None = None,
    include_root: bool = False,
) -> Tuple[str, ...]:
    """Return internal node ids with clade sizes inside the requested bounds."""

    upper = int(sample.leaf_count if max_leaf_count is None else max_leaf_count)
    result = []
    for node in sample.nodes:
        if node.leaf_label is not None:
            continue
        if (not include_root) and str(node.node_id) == str(sample.root_id):
            continue
        count = len(descendant_leaf_labels(sample, str(node.node_id)))
        if int(min_leaf_count) <= int(count) <= int(upper):
            result.append(str(node.node_id))
    return tuple(sorted(result))


def cherry_pairs(sample: PhylogenySample) -> Tuple[Tuple[str, str, str], ...]:
    """Return `(target_leaf, sister_leaf, parent_id)` candidates."""

    nodes = _node_map(sample)
    pairs = []
    for node in sample.nodes:
        if len(node.child_ids) != 2:
            continue
        children = [nodes[str(child_id)] for child_id in node.child_ids]
        if not all(child.leaf_label is not None for child in children):
            continue
        left_label = str(children[0].leaf_label)
        right_label = str(children[1].leaf_label)
        pairs.append((left_label, right_label, str(node.node_id)))
        pairs.append((right_label, left_label, str(node.node_id)))
    return tuple(sorted(pairs))


def mrca_node_id(sample: PhylogenySample, leaf_label_a: str, leaf_label_b: str) -> str:
    """Return the most recent common ancestor node id for two leaf labels."""

    nodes = _node_map(sample)
    leaf_to_id = _leaf_node_id_by_label(sample)
    id_a = str(leaf_to_id[str(leaf_label_a)])
    id_b = str(leaf_to_id[str(leaf_label_b)])
    ancestors_a: set[str] = set()
    current: str | None = id_a
    while current is not None:
        ancestors_a.add(str(current))
        current = nodes[str(current)].parent_id
    current = id_b
    while current is not None:
        if str(current) in ancestors_a:
            return str(current)
        current = nodes[str(current)].parent_id
    raise ValueError("phylogeny leaves have no common ancestor")


def leaf_pair_for_mrca(sample: PhylogenySample, node_id: str, rng) -> Tuple[str, str]:
    """Choose two leaves whose MRCA is exactly `node_id`."""

    nodes = _node_map(sample)
    node = nodes[str(node_id)]
    if len(node.child_ids) < 2:
        raise ValueError("MRCA candidate must have at least two child clades")
    child_groups = [
        tuple(descendant_leaf_labels(sample, str(child_id)))
        for child_id in node.child_ids
    ]
    non_empty = [group for group in child_groups if group]
    if len(non_empty) < 2:
        raise ValueError("MRCA candidate must have two non-empty child clades")
    left_group, right_group = rng.sample(non_empty, 2)
    leaf_a = str(rng.choice(list(left_group)))
    leaf_b = str(rng.choice(list(right_group)))
    if str(leaf_a) == str(leaf_b):
        raise ValueError("MRCA pair must use distinct leaves")
    return tuple(sorted((leaf_a, leaf_b)))  # type: ignore[return-value]


def _assign_depths(
    raw_nodes: Dict[str, Dict[str, Any]],
    *,
    root_id: str,
    depth: int = 0,
) -> None:
    raw_nodes[str(root_id)]["depth"] = int(depth)
    for child_id in raw_nodes[str(root_id)]["child_ids"]:
        _assign_depths(raw_nodes, root_id=str(child_id), depth=int(depth) + 1)


def sample_phylogeny_tree(
    instance_seed: int,
    *,
    leaf_count: int,
    labels: Sequence[str] | None = None,
    max_attempts: int = 200,
) -> PhylogenySample:
    """Sample one full binary rooted tree over the provided leaf labels."""

    if int(leaf_count) < 3:
        raise ValueError("phylogeny tree needs at least three leaves")
    rng = spawn_rng(int(instance_seed), "phylogeny_tree.sample")
    if labels is None:
        pool = list(PHYLOGENY_TAXON_LABEL_POOL)
        if int(leaf_count) > len(pool):
            raise ValueError("leaf_count exceeds phylogeny label pool")
        rng.shuffle(pool)
        leaf_labels = tuple(sorted(pool[: int(leaf_count)]))
    else:
        leaf_labels = tuple(str(label) for label in labels)
        if len(leaf_labels) != int(leaf_count):
            raise ValueError("labels length must match leaf_count")
        if len(set(leaf_labels)) != len(leaf_labels):
            raise ValueError("phylogeny labels must be unique")

    for attempt in range(max(1, int(max_attempts))):
        build_rng = spawn_rng(int(instance_seed), "phylogeny_tree.build", int(attempt))
        raw_nodes: Dict[str, Dict[str, Any]] = {
            f"leaf_{label}": {
                "parent_id": None,
                "child_ids": [],
                "leaf_label": str(label),
                "depth": 0,
            }
            for label in leaf_labels
        }
        clusters = [f"leaf_{label}" for label in leaf_labels]
        build_rng.shuffle(clusters)
        internal_index = 0
        while len(clusters) > 1:
            clusters.sort(key=lambda node_id: (len(_raw_descendant_labels(raw_nodes, node_id)), node_id))
            if len(clusters) >= 4 and build_rng.random() < 0.45:
                candidates = clusters[: max(3, len(clusters) // 2)]
            else:
                candidates = list(clusters)
            left_id = str(build_rng.choice(candidates))
            clusters.remove(left_id)
            candidates = [node_id for node_id in candidates if str(node_id) in set(clusters)] or list(clusters)
            right_id = str(build_rng.choice(candidates))
            clusters.remove(right_id)
            parent_id = f"internal_{internal_index}"
            internal_index += 1
            raw_nodes[parent_id] = {
                "parent_id": None,
                "child_ids": [left_id, right_id],
                "leaf_label": None,
                "depth": 0,
            }
            raw_nodes[left_id]["parent_id"] = parent_id
            raw_nodes[right_id]["parent_id"] = parent_id
            clusters.append(parent_id)
            build_rng.shuffle(clusters)
        root_id = str(clusters[0])
        _assign_depths(raw_nodes, root_id=root_id)
        nodes = tuple(
            PhylogenyNode(
                node_id=str(node_id),
                parent_id=(None if raw["parent_id"] is None else str(raw["parent_id"])),
                child_ids=tuple(str(child_id) for child_id in raw["child_ids"]),
                leaf_label=(None if raw["leaf_label"] is None else str(raw["leaf_label"])),
                depth=int(raw["depth"]),
            )
            for node_id, raw in sorted(raw_nodes.items(), key=lambda item: (int(item[1]["depth"]), str(item[0])))
        )
        sample = PhylogenySample(
            nodes=nodes,
            root_id=str(root_id),
            leaf_labels=tuple(sorted(leaf_labels)),
            canonical_signature=(),
        )
        signature = canonical_phylogeny_signature(sample)
        return PhylogenySample(
            nodes=nodes,
            root_id=str(root_id),
            leaf_labels=tuple(sorted(leaf_labels)),
            canonical_signature=tuple(signature),
        )
    raise ValueError("could not sample phylogeny tree")


def _raw_descendant_labels(raw_nodes: Mapping[str, Mapping[str, Any]], node_id: str) -> Tuple[str, ...]:
    node = raw_nodes[str(node_id)]
    if node.get("leaf_label") is not None:
        return (str(node["leaf_label"]),)
    labels: List[str] = []
    for child_id in node.get("child_ids", []):
        labels.extend(_raw_descendant_labels(raw_nodes, str(child_id)))
    return tuple(sorted(labels))


def sample_phylogeny_with_clade_size(
    instance_seed: int,
    *,
    target_size: int,
    leaf_count_min: int,
    leaf_count_max: int,
    max_attempts: int,
) -> Tuple[PhylogenySample, str]:
    """Sample a tree with one non-root clade containing exactly target_size leaves."""

    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            rng = spawn_rng(int(instance_seed), "phylogeny_tree.clade_size", int(attempt))
            low = max(int(target_size) + 1, int(leaf_count_min))
            high = max(low, int(leaf_count_max))
            leaf_count = int(rng.randint(low, high))
            sample = sample_phylogeny_tree(
                hash64(int(instance_seed), "phylogeny_tree.clade_tree", int(attempt)),
                leaf_count=int(leaf_count),
                max_attempts=50,
            )
            candidates = [
                node_id
                for node_id in internal_clade_node_ids(sample, min_leaf_count=int(target_size), max_leaf_count=int(target_size))
                if len(descendant_leaf_labels(sample, node_id)) == int(target_size)
            ]
            if not candidates:
                continue
            target_node_id = str(rng.choice(candidates))
            return sample, target_node_id
        except Exception as exc:
            last_error = exc
    raise ValueError(f"could not sample clade-size phylogeny: {last_error}")


def sample_phylogeny_with_cherry(
    instance_seed: int,
    *,
    leaf_count_min: int,
    leaf_count_max: int,
    max_attempts: int,
) -> Tuple[PhylogenySample, Tuple[str, str, str]]:
    """Sample a tree with a leaf sister pair."""

    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            rng = spawn_rng(int(instance_seed), "phylogeny_tree.cherry", int(attempt))
            sample = sample_phylogeny_tree(
                hash64(int(instance_seed), "phylogeny_tree.cherry_tree", int(attempt)),
                leaf_count=int(rng.randint(int(leaf_count_min), int(leaf_count_max))),
                max_attempts=50,
            )
            candidates = list(cherry_pairs(sample))
            if not candidates:
                continue
            return sample, tuple(str(item) for item in rng.choice(candidates))  # type: ignore[return-value]
        except Exception as exc:
            last_error = exc
    raise ValueError(f"could not sample sister-leaf phylogeny: {last_error}")


def sample_phylogeny_with_mrca_size(
    instance_seed: int,
    *,
    target_size: int,
    leaf_count_min: int,
    leaf_count_max: int,
    max_attempts: int,
) -> Tuple[PhylogenySample, str, Tuple[str, str]]:
    """Sample a tree and leaf pair whose MRCA clade has target_size leaves."""

    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            sample, node_id = sample_phylogeny_with_clade_size(
                hash64(int(instance_seed), "phylogeny_tree.mrca_tree", int(attempt)),
                target_size=int(target_size),
                leaf_count_min=int(leaf_count_min),
                leaf_count_max=int(leaf_count_max),
                max_attempts=20,
            )
            rng = spawn_rng(int(instance_seed), "phylogeny_tree.mrca_pair", int(attempt))
            leaf_pair = leaf_pair_for_mrca(sample, node_id, rng)
            if str(mrca_node_id(sample, leaf_pair[0], leaf_pair[1])) != str(node_id):
                continue
            return sample, str(node_id), tuple(str(label) for label in leaf_pair)
        except Exception as exc:
            last_error = exc
    raise ValueError(f"could not sample MRCA-size phylogeny: {last_error}")


def sample_topology_outlier_options(
    instance_seed: int,
    *,
    leaf_count_min: int,
    leaf_count_max: int,
    option_count: int = 6,
    max_attempts: int = 200,
) -> Dict[str, Any]:
    """Build six option cladograms with one rooted-topology outlier."""

    if int(option_count) != 6:
        raise ValueError("phylogeny topology options require exactly six options")
    rng = spawn_rng(int(instance_seed), "phylogeny_tree.topology_options")
    leaf_count = int(rng.randint(int(leaf_count_min), int(leaf_count_max)))
    base = sample_phylogeny_tree(
        hash64(int(instance_seed), "phylogeny_tree.topology_base", 0),
        leaf_count=int(leaf_count),
        max_attempts=50,
    )
    outlier: PhylogenySample | None = None
    for attempt in range(max(1, int(max_attempts))):
        candidate = sample_phylogeny_tree(
            hash64(int(instance_seed), "phylogeny_tree.topology_outlier", int(attempt)),
            leaf_count=int(leaf_count),
            labels=base.leaf_labels,
            max_attempts=50,
        )
        if tuple(candidate.canonical_signature) != tuple(base.canonical_signature):
            outlier = candidate
            break
    if outlier is None:
        raise ValueError("could not build topology outlier")

    correct_index = int(rng.randrange(int(option_count)))
    option_specs = []
    for index in range(int(option_count)):
        label = chr(ord("A") + int(index))
        if int(index) == int(correct_index):
            sample = outlier
            role = "outlier"
        else:
            sample = base
            role = "equivalent"
        option_specs.append(
            {
                "option_label": str(label),
                "sample": sample,
                "role": str(role),
                "canonical_signature": tuple(sample.canonical_signature),
                "layout_seed": hash64(int(instance_seed), f"phylogeny_tree.option_layout.{label}", int(index)),
            }
        )
    return {
        "base_sample": base,
        "outlier_sample": outlier,
        "option_specs": tuple(option_specs),
        "answer_option_label": chr(ord("A") + int(correct_index)),
        "correct_option_index": int(correct_index),
        "leaf_count": int(leaf_count),
    }


def _ordered_children(sample: PhylogenySample, node_id: str, *, layout_seed: int) -> Tuple[str, ...]:
    node = _node_map(sample)[str(node_id)]
    child_ids = list(node.child_ids)
    if len(child_ids) <= 1:
        return tuple(child_ids)
    key_values = [
        (hash64(int(layout_seed), f"phylogeny_child_order:{node_id}:{child_id}", 0), str(child_id))
        for child_id in child_ids
    ]
    return tuple(child_id for _key, child_id in sorted(key_values))


def _leaf_order(sample: PhylogenySample, *, layout_seed: int) -> Tuple[str, ...]:
    labels: List[str] = []

    def visit(node_id: str) -> None:
        node = _node_map(sample)[str(node_id)]
        if node.leaf_label is not None:
            labels.append(str(node.leaf_label))
            return
        for child_id in _ordered_children(sample, str(node_id), layout_seed=int(layout_seed)):
            visit(str(child_id))

    visit(str(sample.root_id))
    return tuple(labels)


def _point_bbox(center: Sequence[float], radius: float = 8.0) -> Tuple[int, int, int, int]:
    x, y = float(center[0]), float(center[1])
    r = float(radius)
    return (
        int(round(x - r)),
        int(round(y - r)),
        int(round(x + r)),
        int(round(y + r)),
    )


def _draw_text_at(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    xy: Sequence[float],
    font,
    fill: Sequence[int],
    stroke_fill: Sequence[int],
    stroke_width: int,
) -> Tuple[int, int, int, int]:
    x, y = float(xy[0]), float(xy[1])
    bbox = draw.textbbox((x, y), str(text), font=font, stroke_width=int(stroke_width))
    draw_text_traced(
        draw,
        (x, y),
        str(text),
        font=font,
        fill=tuple(int(value) for value in fill),
        stroke_fill=tuple(int(value) for value in stroke_fill),
        stroke_width=int(stroke_width),
        role="graph_phylogeny_label_text",
        required=False,
    )
    return tuple(int(round(float(value))) for value in bbox)


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Sequence[float],
    font,
    fill: Sequence[int],
    stroke_fill: Sequence[int],
    stroke_width: int,
) -> Tuple[int, int, int, int]:
    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=int(stroke_width))
    width = float(bbox[2] - bbox[0])
    height = float(bbox[3] - bbox[1])
    x = float(center[0]) - (0.5 * width) - float(bbox[0])
    y = float(center[1]) - (0.5 * height) - float(bbox[1])
    return _draw_text_at(
        draw,
        text=str(text),
        xy=(x, y),
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=int(stroke_width),
    )


def _draw_paper_lines(draw: ImageDraw.ImageDraw, bbox: Sequence[float], *, color: Sequence[int]) -> None:
    left, top, right, bottom = [float(value) for value in bbox]
    y = top + 22.0
    while y < bottom - 8.0:
        draw.line((left + 8.0, y, right - 8.0, y), fill=tuple(int(value) for value in color), width=1)
        y += 24.0


def _panel_content_bbox(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Sequence[float],
    title: str | None,
    render_params: GraphRenderParams,
    title_font,
) -> List[float]:
    left, top, right, bottom = [float(value) for value in panel_bbox]
    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=int(render_params.panel_corner_radius_px),
        fill=tuple(int(value) for value in render_params.panel_fill_rgb),
        outline=tuple(int(value) for value in render_params.panel_border_rgb),
        width=max(1, int(render_params.node_border_width_px)),
    )
    pad = float(render_params.panel_padding_px)
    title_band = 0.0
    if title:
        title_band = max(44.0, pad + 24.0)
        _draw_centered_text(
            draw,
            text=str(title),
            center=(0.5 * (left + right), top + 0.46 * title_band),
            font=title_font,
            fill=render_params.title_color_rgb,
            stroke_fill=(255, 255, 255),
            stroke_width=1,
        )
    return round_bbox((left + pad, top + title_band + 8.0, right - pad, bottom - pad))


def _layout_positions(
    sample: PhylogenySample,
    *,
    content_bbox: Sequence[float],
    layout_seed: int,
) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, Tuple[float, float]]]:
    nodes = _node_map(sample)
    left, top, right, bottom = [float(value) for value in content_bbox]
    label_space = max(42.0, min(86.0, 0.18 * (right - left)))
    tree_left = left + 18.0
    tree_right = right - label_space
    leaf_y_top = top + 18.0
    leaf_y_bottom = bottom - 18.0
    leaf_order = _leaf_order(sample, layout_seed=int(layout_seed))
    if len(leaf_order) == 1:
        leaf_y = {str(leaf_order[0]): 0.5 * (leaf_y_top + leaf_y_bottom)}
    else:
        leaf_y = {
            str(label): leaf_y_top + ((leaf_y_bottom - leaf_y_top) * float(index) / float(len(leaf_order) - 1))
            for index, label in enumerate(leaf_order)
        }
    max_depth = max(1, int(sample.max_depth))
    depth_to_x = {
        depth: tree_left + ((tree_right - tree_left) * float(depth) / float(max_depth))
        for depth in range(max_depth + 1)
    }
    centers: Dict[str, Tuple[float, float]] = {}

    def place(node_id: str) -> Tuple[float, float]:
        node = nodes[str(node_id)]
        if node.leaf_label is not None:
            center = (tree_right, float(leaf_y[str(node.leaf_label)]))
            centers[str(node_id)] = center
            return center
        child_centers = [place(str(child_id)) for child_id in _ordered_children(sample, str(node_id), layout_seed=int(layout_seed))]
        y = sum(float(center[1]) for center in child_centers) / float(len(child_centers))
        x = float(depth_to_x.get(int(node.depth), tree_left))
        centers[str(node_id)] = (x, y)
        return (x, y)

    place(str(sample.root_id))
    label_positions = {
        str(label): (tree_right + 12.0, float(leaf_y[str(label)]))
        for label in leaf_order
    }
    return centers, label_positions


def _draw_cladogram_into_panel(
    draw: ImageDraw.ImageDraw,
    *,
    sample: PhylogenySample,
    panel_bbox: Sequence[float],
    render_params: GraphRenderParams,
    scene_variant: str,
    layout_seed: int,
    title: str | None,
    marked_node_id: str | None = None,
    option_label: str | None = None,
) -> Tuple[Tuple[RenderedPhylogenyNode, ...], Tuple[RenderedPhylogenyEdge, ...], Dict[str, Any]]:
    title_font = load_font(int(render_params.panel_title_font_size_px), bold=True, font_family=str(render_params.font_family or ""))
    label_font_size = max(14, min(int(render_params.label_font_size_px), 24))
    label_font = load_font(label_font_size, bold=True, font_family=str(render_params.font_family or ""))
    content_bbox = _panel_content_bbox(
        draw,
        panel_bbox=panel_bbox,
        title=title,
        render_params=render_params,
        title_font=title_font,
    )
    if str(scene_variant) == "paper_cladogram":
        _draw_paper_lines(draw, content_bbox, color=(222, 228, 238))
    if option_label is not None:
        label_font_option = load_font(max(18, int(render_params.panel_title_font_size_px)), bold=True, font_family=str(render_params.font_family or ""))
        left, top = float(panel_bbox[0]), float(panel_bbox[1])
        _draw_centered_text(
            draw,
            text=str(option_label),
            center=(left + 30.0, top + 30.0),
            font=label_font_option,
            fill=render_params.title_color_rgb,
            stroke_fill=(255, 255, 255),
            stroke_width=1,
        )

    nodes = _node_map(sample)
    centers, label_positions = _layout_positions(sample, content_bbox=content_bbox, layout_seed=int(layout_seed))
    stroke_width = 1
    edge_width = max(2, int(render_params.edge_width_px))
    edge_rgb = tuple(int(value) for value in render_params.edge_color_rgb)
    highlight_rgb = (221, 100, 36)
    rendered_edges: List[RenderedPhylogenyEdge] = []

    def edge_path(parent_center: Tuple[float, float], child_center: Tuple[float, float]) -> Tuple[Tuple[int, int], ...]:
        px, py = parent_center
        cx, cy = child_center
        if str(scene_variant) == "diagonal_cladogram":
            return ((int(round(px)), int(round(py))), (int(round(cx)), int(round(cy))))
        mid_x = max(px + 10.0, cx)
        return (
            (int(round(px)), int(round(py))),
            (int(round(mid_x)), int(round(py))),
            (int(round(mid_x)), int(round(cy))),
            (int(round(cx)), int(round(cy))),
        )

    marked_edge_path: Tuple[Tuple[int, int], ...] | None = None
    for node in sample.nodes:
        for child_id in node.child_ids:
            path = edge_path(centers[str(node.node_id)], centers[str(child_id)])
            rendered_edges.append(
                RenderedPhylogenyEdge(
                    edge_id=f"{node.node_id}->{child_id}",
                    parent_id=str(node.node_id),
                    child_id=str(child_id),
                    path_px=tuple(path),
                )
            )
            draw.line(path, fill=edge_rgb, width=edge_width, joint="curve")
            if marked_node_id is not None and str(child_id) == str(marked_node_id):
                marked_edge_path = tuple(path)

    if marked_edge_path is not None:
        draw.line(marked_edge_path, fill=highlight_rgb, width=edge_width + 4, joint="curve")

    rendered_nodes: List[RenderedPhylogenyNode] = []
    leaf_label_bboxes: Dict[str, Tuple[int, int, int, int]] = {}
    for node in sample.nodes:
        cx, cy = centers[str(node.node_id)]
        is_leaf = node.leaf_label is not None
        label_bbox = None
        if is_leaf:
            label = str(node.leaf_label)
            lx, ly = label_positions[label]
            text_bbox = draw.textbbox((0, 0), label, font=label_font, stroke_width=stroke_width)
            text_height = float(text_bbox[3] - text_bbox[1])
            label_bbox = _draw_text_at(
                draw,
                text=label,
                xy=(lx, ly - 0.5 * text_height),
                font=label_font,
                fill=render_params.title_color_rgb,
                stroke_fill=(255, 255, 255),
                stroke_width=stroke_width,
            )
            leaf_label_bboxes[label] = label_bbox
            radius = max(3, int(edge_width))
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=edge_rgb)
        else:
            radius = max(4, int(edge_width + 1))
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=edge_rgb)
        rendered_nodes.append(
            RenderedPhylogenyNode(
                node_id=str(node.node_id),
                leaf_label=(None if node.leaf_label is None else str(node.leaf_label)),
                descendant_leaf_labels=tuple(descendant_leaf_labels(sample, str(node.node_id))),
                center_xy=(int(round(cx)), int(round(cy))),
                bbox_xyxy=_point_bbox((cx, cy), radius=max(8.0, float(edge_width + 4))),
                label_bbox_xyxy=label_bbox,
                is_leaf=bool(is_leaf),
            )
        )

    if marked_node_id is not None:
        descendant_labels = descendant_leaf_labels(sample, str(marked_node_id))
        leaf_ys = [float(centers[_leaf_node_id_by_label(sample)[str(label)]][1]) for label in descendant_labels]
        if leaf_ys:
            bracket_x = max(float(content_bbox[0]) + 18.0, min(float(content_bbox[2]) - 48.0, max(float(centers[_leaf_node_id_by_label(sample)[str(label)]][0]) for label in descendant_labels) - 22.0))
            top_y = min(leaf_ys) - 7.0
            bottom_y = max(leaf_ys) + 7.0
            draw.line((bracket_x, top_y, bracket_x, bottom_y), fill=highlight_rgb, width=edge_width + 2)
            draw.line((bracket_x, top_y, bracket_x + 12.0, top_y), fill=highlight_rgb, width=edge_width + 2)
            draw.line((bracket_x, bottom_y, bracket_x + 12.0, bottom_y), fill=highlight_rgb, width=edge_width + 2)

    metadata = {
        "content_bbox": list(content_bbox),
        "leaf_label_bboxes": {label: list(bbox) for label, bbox in leaf_label_bboxes.items()},
    }
    return tuple(rendered_nodes), tuple(rendered_edges), metadata


def render_phylogeny_tree_scene(
    *,
    sample: PhylogenySample,
    render_params: GraphRenderParams,
    scene_variant: str,
    scene_title: str,
    layout_seed: int,
    base_image: Image.Image,
    marked_node_id: str | None = None,
) -> RenderedPhylogenyScene:
    """Render one phylogeny tree into a full-size panel."""

    if str(scene_variant) not in set(SUPPORTED_PHYLOGENY_SCENE_VARIANTS):
        raise ValueError(f"unsupported phylogeny scene_variant: {scene_variant}")
    image = base_image.copy()
    draw = ImageDraw.Draw(image)
    margin = float(render_params.outer_margin_px)
    panel_bbox = round_bbox((margin, margin, float(render_params.canvas_width) - margin, float(render_params.canvas_height) - margin))
    nodes, edges, metadata = _draw_cladogram_into_panel(
        draw,
        sample=sample,
        panel_bbox=panel_bbox,
        render_params=render_params,
        scene_variant=str(scene_variant),
        layout_seed=int(layout_seed),
        title=str(scene_title),
        marked_node_id=marked_node_id,
    )
    panel_geometry = {
        "canvas_size": [int(render_params.canvas_width), int(render_params.canvas_height)],
        "panel_bbox": list(panel_bbox),
        "content_bbox": list(metadata["content_bbox"]),
    }
    return RenderedPhylogenyScene(
        image=image,
        panel_geometry=panel_geometry,
        nodes=tuple(nodes),
        edges=tuple(edges),
        scene_variant=str(scene_variant),
        resolved_label_font_size_px=max(14, min(int(render_params.label_font_size_px), 24)),
        resolved_label_stroke_width_px=1,
        option_panel_bboxes={},
    )


def render_phylogeny_option_scene(
    *,
    option_specs: Sequence[Mapping[str, Any]],
    render_params: GraphRenderParams,
    scene_variant: str,
    layout_seed: int,
    base_image: Image.Image,
) -> RenderedPhylogenyScene:
    """Render six phylogeny options into fixed A-F option panels."""

    if len(option_specs) != 6:
        raise ValueError("phylogeny option scene requires exactly six options")
    image = base_image.copy()
    draw = ImageDraw.Draw(image)
    margin_x = float(render_params.outer_margin_px)
    margin_y = float(render_params.outer_margin_px)
    gap_x = 22.0
    gap_y = 22.0
    width = float(render_params.canvas_width)
    height = float(render_params.canvas_height)
    panel_w = (width - (2.0 * margin_x) - (2.0 * gap_x)) / 3.0
    panel_h = (height - (2.0 * margin_y) - gap_y) / 2.0
    option_panel_bboxes: Dict[str, List[float]] = {}
    all_nodes: List[RenderedPhylogenyNode] = []
    all_edges: List[RenderedPhylogenyEdge] = []
    for index, spec in enumerate(option_specs):
        row = int(index // 3)
        col = int(index % 3)
        left = margin_x + (float(col) * (panel_w + gap_x))
        top = margin_y + (float(row) * (panel_h + gap_y))
        panel_bbox = round_bbox((left, top, left + panel_w, top + panel_h))
        option_label = str(spec["option_label"])
        option_panel_bboxes[option_label] = list(panel_bbox)
        nodes, edges, _metadata = _draw_cladogram_into_panel(
            draw,
            sample=spec["sample"],
            panel_bbox=panel_bbox,
            render_params=render_params,
            scene_variant=str(scene_variant),
            layout_seed=int(spec.get("layout_seed", hash64(int(layout_seed), f"option:{option_label}", int(index)))),
            title=None,
            option_label=str(option_label),
        )
        all_nodes.extend(nodes)
        all_edges.extend(edges)
    panel_geometry = {
        "canvas_size": [int(render_params.canvas_width), int(render_params.canvas_height)],
        "option_panel_bboxes": {key: list(value) for key, value in sorted(option_panel_bboxes.items())},
    }
    return RenderedPhylogenyScene(
        image=image,
        panel_geometry=panel_geometry,
        nodes=tuple(all_nodes),
        edges=tuple(all_edges),
        scene_variant=str(scene_variant),
        resolved_label_font_size_px=max(14, min(int(render_params.label_font_size_px), 24)),
        resolved_label_stroke_width_px=1,
        option_panel_bboxes={key: list(value) for key, value in sorted(option_panel_bboxes.items())},
    )


def projected_leaf_point_annotation(
    rendered_scene: RenderedPhylogenyScene,
    leaf_labels: Iterable[str],
) -> Dict[str, Any]:
    """Project leaf labels into point-set annotation using leaf terminal centers."""

    leaf_points: Dict[str, List[int]] = {}
    leaf_bboxes: Dict[str, List[int]] = {}
    for node in rendered_scene.nodes:
        if node.leaf_label is None:
            continue
        leaf_points[str(node.leaf_label)] = [int(node.center_xy[0]), int(node.center_xy[1])]
        if node.label_bbox_xyxy is not None:
            leaf_bboxes[str(node.leaf_label)] = [int(value) for value in node.label_bbox_xyxy]
    points = [leaf_points[str(label)] for label in leaf_labels]
    return {
        "point_set": [list(point) for point in points],
        "pixel_point_set": [list(point) for point in points],
        "leaf_label_bbox_map": {key: list(value) for key, value in sorted(leaf_bboxes.items())},
    }


def projected_keyed_phylogeny_annotation(
    rendered_scene: RenderedPhylogenyScene,
    *,
    role_to_node_id: Mapping[str, str],
) -> Dict[str, Any]:
    """Project keyed leaf/internal node witnesses into keyed bbox/point annotation."""

    node_by_id = {str(node.node_id): node for node in rendered_scene.nodes}
    keyed_bbox_map: Dict[str, List[int]] = {}
    keyed_point_map: Dict[str, List[int]] = {}
    for role, node_id in sorted(role_to_node_id.items()):
        node = node_by_id[str(node_id)]
        bbox = node.label_bbox_xyxy if node.label_bbox_xyxy is not None else node.bbox_xyxy
        keyed_bbox_map[str(role)] = [int(value) for value in bbox]
        keyed_point_map[str(role)] = [int(node.center_xy[0]), int(node.center_xy[1])]
    return {
        "keyed_bbox_map": dict(keyed_bbox_map),
        "pixel_keyed_bbox_map": dict(keyed_bbox_map),
        "keyed_point_map": dict(keyed_point_map),
        "pixel_keyed_point_map": dict(keyed_point_map),
    }


def phylogeny_scene_entities(
    sample: PhylogenySample,
    rendered_scene: RenderedPhylogenyScene,
) -> Tuple[Dict[str, Any], ...]:
    """Build trace scene entities for a rendered phylogeny."""

    node_by_id = _node_map(sample)
    entities: List[Dict[str, Any]] = []
    for rendered in rendered_scene.nodes:
        sample_node = node_by_id[str(rendered.node_id)]
        entities.append(
            {
                "entity_id": f"phylo_node_{rendered.node_id}",
                "entity_kind": "phylogeny_leaf" if rendered.is_leaf else "phylogeny_internal_node",
                "node_id": str(rendered.node_id),
                "leaf_label": rendered.leaf_label,
                "parent_id": sample_node.parent_id,
                "child_ids": list(sample_node.child_ids),
                "descendant_leaf_labels": list(rendered.descendant_leaf_labels),
                "depth": int(sample_node.depth),
                "center_px": list(rendered.center_xy),
                "bbox_xyxy": list(rendered.bbox_xyxy),
                "label_bbox_xyxy": (None if rendered.label_bbox_xyxy is None else list(rendered.label_bbox_xyxy)),
            }
        )
    for edge in rendered_scene.edges:
        entities.append(
            {
                "entity_id": f"phylo_edge_{edge.edge_id}",
                "entity_kind": "phylogeny_branch",
                "parent_id": str(edge.parent_id),
                "child_id": str(edge.child_id),
                "path_px": [list(point) for point in edge.path_px],
            }
        )
    return tuple(entities)


__all__ = [
    "PHYLOGENY_TAXON_LABEL_POOL",
    "SUPPORTED_PHYLOGENY_SCENE_VARIANTS",
    "PhylogenyNode",
    "PhylogenySample",
    "RenderedPhylogenyScene",
    "canonical_phylogeny_signature",
    "cherry_pairs",
    "descendant_leaf_labels",
    "internal_clade_node_ids",
    "leaf_pair_for_mrca",
    "mrca_node_id",
    "phylogeny_scene_entities",
    "projected_keyed_phylogeny_annotation",
    "projected_leaf_point_annotation",
    "render_phylogeny_option_scene",
    "render_phylogeny_tree_scene",
    "sample_phylogeny_tree",
    "sample_phylogeny_with_cherry",
    "sample_phylogeny_with_clade_size",
    "sample_phylogeny_with_mrca_size",
    "sample_topology_outlier_options",
]
