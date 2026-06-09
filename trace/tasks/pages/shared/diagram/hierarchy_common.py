"""Shared dataset builders and render defaults for hierarchy-diagram tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.render_variation import resolve_layout_jitter
from .common import (
    resolve_diagrams_axis_variant,
    resolve_diagrams_int_param,
    resolve_diagrams_rgb_triple,
    sample_diagram_short_names,
)


SUPPORTED_DIAGRAM_HIERARCHY_SCENE_VARIANTS: Tuple[str, ...] = ("org_chart",)
SUPPORTED_DIAGRAM_HIERARCHY_QUERY_IDS: Tuple[str, ...] = (
    "parent_of_node",
    "lowest_common_ancestor_of_two_nodes",
)
SUPPORTED_DIAGRAM_HIERARCHY_TREE_COUNT_SCENE_VARIANTS: Tuple[str, ...] = ("rooted_tree",)
SUPPORTED_DIAGRAM_HIERARCHY_TREE_COUNT_QUERY_IDS: Tuple[str, ...] = (
    "subtree_descendant_count",
    "subtree_leaf_count",
    "path_length_between_two_nodes",
)

_TITLE_OPTIONS: Tuple[str, ...] = (
    "Organization Chart",
    "Team Structure",
    "Department Hierarchy",
    "Company Structure",
    "Org Overview",
)
_TREE_TITLE_OPTIONS: Tuple[str, ...] = (
    "Rooted Tree",
    "Tree Structure",
    "Parent-Child Tree",
    "Node Hierarchy",
    "Tree Diagram",
)
_TEMPLATES: Tuple[Dict[str, object], ...] = (
    {
        "template_id": "balanced_three_divisions",
        "root_node_id": "node_0",
        "children_by_parent": {
            "node_0": ["node_1", "node_2", "node_3"],
            "node_1": ["node_4", "node_5"],
            "node_2": ["node_6", "node_7"],
            "node_3": ["node_8", "node_9"],
        },
    },
    {
        "template_id": "mixed_depth_branch",
        "root_node_id": "node_0",
        "children_by_parent": {
            "node_0": ["node_1", "node_2", "node_3"],
            "node_1": ["node_4", "node_5"],
            "node_2": ["node_6"],
            "node_6": ["node_7", "node_8"],
            "node_3": ["node_9", "node_10"],
        },
    },
    {
        "template_id": "deep_escalation_branch",
        "root_node_id": "node_0",
        "children_by_parent": {
            "node_0": ["node_1", "node_2", "node_3"],
            "node_1": ["node_4", "node_5"],
            "node_2": ["node_6"],
            "node_6": ["node_7"],
            "node_7": ["node_8", "node_9"],
            "node_3": ["node_10"],
        },
    },
    {
        "template_id": "dual_pillars",
        "root_node_id": "node_0",
        "children_by_parent": {
            "node_0": ["node_1", "node_2"],
            "node_1": ["node_3", "node_4", "node_5"],
            "node_2": ["node_6", "node_7"],
            "node_7": ["node_8", "node_9"],
        },
    },
)


@dataclass(frozen=True)
class HierarchyDefaults:
    """Default generation bounds for hierarchy ancestor-label tasks."""

    org_template_count: int = len(_TEMPLATES)


@dataclass(frozen=True)
class HierarchyRenderParams:
    """Resolved rendering knobs for one hierarchy-diagram scene."""

    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    title_font_size_px: int
    title_band_height_px: int
    node_width_px: int
    node_height_px: int
    node_corner_radius_px: int
    node_border_width_px: int
    connector_width_px: int
    connector_branch_gap_px: int
    label_font_size_px: int
    root_fill_rgb: Tuple[int, int, int]
    node_fill_rgb: Tuple[int, int, int]
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    title_color_rgb: Tuple[int, int, int]
    node_border_rgb: Tuple[int, int, int]
    label_color_rgb: Tuple[int, int, int]
    label_stroke_rgb: Tuple[int, int, int]
    connector_color_rgb: Tuple[int, int, int]
    layout_jitter_meta: Dict[str, Any]


def resolve_hierarchy_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active hierarchy scene variant."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_HIERARCHY_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_hierarchy_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active hierarchy query id."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_HIERARCHY_QUERY_IDS,
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def resolve_hierarchy_tree_count_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active generic tree-count hierarchy scene variant."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_HIERARCHY_TREE_COUNT_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_hierarchy_tree_count_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active generic tree-count hierarchy query id."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_HIERARCHY_TREE_COUNT_QUERY_IDS,
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def resolve_hierarchy_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    instance_seed: int | None = None,
) -> HierarchyRenderParams:
    """Resolve rendering params for hierarchy scenes."""

    def _int(key: str, fallback: int) -> int:
        return resolve_diagrams_int_param(
            params,
            render_defaults,
            key,
            fallback,
            instance_seed=instance_seed,
            namespace="pages.hierarchy",
        )

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return resolve_diagrams_rgb_triple(
            params,
            render_defaults,
            key,
            fallback,
            instance_seed=instance_seed,
            namespace="pages.hierarchy",
        )

    layout_jitter_meta = resolve_layout_jitter(
        params,
        render_defaults,
        instance_seed=instance_seed,
        namespace="pages.hierarchy.layout",
    )

    return HierarchyRenderParams(
        canvas_width=_int("canvas_width", 1280),
        canvas_height=_int("canvas_height", 880),
        outer_margin_px=_int("outer_margin_px", 52),
        panel_padding_px=_int("panel_padding_px", 28),
        panel_corner_radius_px=_int("panel_corner_radius_px", 30),
        title_font_size_px=_int("title_font_size_px", 32),
        title_band_height_px=_int("title_band_height_px", 78),
        node_width_px=_int("node_width_px", 164),
        node_height_px=_int("node_height_px", 72),
        node_corner_radius_px=_int("node_corner_radius_px", 20),
        node_border_width_px=_int("node_border_width_px", 3),
        connector_width_px=_int("connector_width_px", 5),
        connector_branch_gap_px=_int("connector_branch_gap_px", 22),
        label_font_size_px=_int("label_font_size_px", 24),
        root_fill_rgb=_triple("root_fill_rgb", (236, 244, 255)),
        node_fill_rgb=_triple("node_fill_rgb", (246, 248, 252)),
        panel_fill_rgb=_triple("panel_fill_rgb", (252, 252, 255)),
        panel_border_rgb=_triple("panel_border_rgb", (88, 98, 112)),
        title_color_rgb=_triple("title_color_rgb", (34, 40, 48)),
        node_border_rgb=_triple("node_border_rgb", (77, 90, 109)),
        label_color_rgb=_triple("label_color_rgb", (29, 34, 41)),
        label_stroke_rgb=_triple("label_stroke_rgb", (255, 255, 255)),
        connector_color_rgb=_triple("connector_color_rgb", (95, 104, 118)),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def _title(*, rng) -> str:
    """Sample one short hierarchy scene title."""

    return str(_TITLE_OPTIONS[int(rng.randrange(len(_TITLE_OPTIONS)))])


def _tree_title(*, rng) -> str:
    """Sample one short generic rooted-tree scene title."""

    return str(_TREE_TITLE_OPTIONS[int(rng.randrange(len(_TREE_TITLE_OPTIONS)))])


def _all_node_ids(root_node_id: str, children_by_parent: Mapping[str, Sequence[str]]) -> List[str]:
    """Return ordered node ids for one hierarchy template."""

    ordered: List[str] = [str(root_node_id)]
    seen = {str(root_node_id)}
    for parent_id, children in children_by_parent.items():
        parent_key = str(parent_id)
        if parent_key not in seen:
            ordered.append(parent_key)
            seen.add(parent_key)
        for child_id in children:
            child_key = str(child_id)
            if child_key not in seen:
                ordered.append(child_key)
                seen.add(child_key)
    return ordered


def _parent_map(children_by_parent: Mapping[str, Sequence[str]]) -> Dict[str, str]:
    """Build the reverse parent lookup for one tree template."""

    parent_by_child: Dict[str, str] = {}
    for parent_id, children in children_by_parent.items():
        for child_id in children:
            parent_by_child[str(child_id)] = str(parent_id)
    return parent_by_child


def _depth_map(root_node_id: str, children_by_parent: Mapping[str, Sequence[str]]) -> Dict[str, int]:
    """Compute node depths in one rooted hierarchy."""

    depths = {str(root_node_id): 0}
    stack = [str(root_node_id)]
    while stack:
        node_id = stack.pop()
        base_depth = int(depths[node_id])
        for child_id in children_by_parent.get(str(node_id), []):
            child_key = str(child_id)
            depths[child_key] = int(base_depth + 1)
            stack.append(child_key)
    return depths


def _ancestors(node_id: str, parent_by_child: Mapping[str, str]) -> List[str]:
    """Return one node's ancestor chain starting from the node itself."""

    chain = [str(node_id)]
    cursor = str(node_id)
    while cursor in parent_by_child:
        cursor = str(parent_by_child[cursor])
        chain.append(cursor)
    return chain


def _descendants(node_id: str, children_by_parent: Mapping[str, Sequence[str]]) -> List[str]:
    """Return all descendants of one node in deterministic DFS order."""

    collected: List[str] = []

    def _walk(parent_id: str) -> None:
        for child_id in children_by_parent.get(str(parent_id), []):
            child_key = str(child_id)
            collected.append(child_key)
            _walk(child_key)

    _walk(str(node_id))
    return collected


def _leaf_descendants(node_id: str, children_by_parent: Mapping[str, Sequence[str]]) -> List[str]:
    """Return leaf descendants of one node in deterministic DFS order."""

    return [
        str(candidate)
        for candidate in _descendants(str(node_id), children_by_parent)
        if str(candidate) not in children_by_parent
    ]


def _lowest_common_ancestor(node_a: str, node_b: str, parent_by_child: Mapping[str, str]) -> str:
    """Return the lowest common ancestor of two hierarchy nodes."""

    ancestors_b = set(_ancestors(str(node_b), parent_by_child))
    for candidate in _ancestors(str(node_a), parent_by_child):
        if str(candidate) in ancestors_b:
            return str(candidate)
    raise ValueError("hierarchy nodes must share at least one ancestor")


def _path_between_nodes(node_a: str, node_b: str, parent_by_child: Mapping[str, str]) -> List[str]:
    """Return the ordered node path from `node_a` to `node_b` in one rooted tree."""

    ancestors_a = _ancestors(str(node_a), parent_by_child)
    ancestors_b = _ancestors(str(node_b), parent_by_child)
    index_by_b = {str(node_id): int(index) for index, node_id in enumerate(ancestors_b)}
    for index_a, candidate in enumerate(ancestors_a):
        candidate_key = str(candidate)
        if candidate_key in index_by_b:
            index_b = int(index_by_b[candidate_key])
            upward = [str(node_id) for node_id in ancestors_a[: index_a + 1]]
            downward = [str(node_id) for node_id in reversed(ancestors_b[:index_b])]
            return [*upward, *downward]
    raise ValueError("tree nodes must share at least one ancestor")


def _resolve_int_bound_pair(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    context: str,
) -> Tuple[int, int]:
    """Resolve one inclusive integer bound pair from task params/defaults."""

    lower = int(resolve_diagrams_int_param(params, gen_defaults, str(min_key), int(fallback_min)))
    upper = int(resolve_diagrams_int_param(params, gen_defaults, str(max_key), int(fallback_max)))
    if lower > upper:
        raise ValueError(f"{min_key} must be <= {max_key} in {context}")
    return int(lower), int(upper)


def _variant_local_index(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    query_id: str,
    namespace: str,
) -> int:
    """Return a deterministic local index for balancing support inside one variant."""

    return resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{query_id}.{namespace}",
    )


def _select_from_support(
    *,
    support: Sequence[int],
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    query_id: str,
    namespace: str,
    offset: int = 0,
) -> int:
    """Select one integer from a finite support with variant-local balancing."""

    values = [int(value) for value in support]
    if not values:
        raise ValueError(f"empty integer support for {namespace}")
    selection_index = _variant_local_index(
        params=params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        query_id=str(query_id),
        namespace=str(namespace),
    )
    return int(values[int(selection_index + int(offset)) % len(values)])


def _hierarchy_template(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, object]:
    """Resolve one hierarchy template deterministically."""

    template_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.hierarchy_template",
        )
        % len(_TEMPLATES)
    )
    return dict(_TEMPLATES[template_index])


def _label_map(
    *,
    node_ids: Sequence[str],
    rng,
) -> Dict[str, str]:
    """Assign unique short human-name labels across one org chart."""

    sampled_names = sample_diagram_short_names(count=len(node_ids), rng=rng)
    return {
        str(node_id): str(label)
        for node_id, label in zip([str(node_id) for node_id in node_ids], sampled_names)
    }


class _TreeBuilder:
    """Small deterministic builder for rooted tree query fixtures."""

    def __init__(self) -> None:
        self.children_by_parent: Dict[str, List[str]] = {}
        self.node_ids: List[str] = ["node_0"]
        self.depths: Dict[str, int] = {"node_0": 0}

    def add_child(self, parent_id: str) -> str:
        """Append one child below `parent_id` and return its node id."""

        node_id = f"node_{len(self.node_ids)}"
        parent_key = str(parent_id)
        self.children_by_parent.setdefault(parent_key, []).append(str(node_id))
        self.node_ids.append(str(node_id))
        self.depths[str(node_id)] = int(self.depths[parent_key] + 1)
        return str(node_id)

    def add_chain(self, parent_id: str, *, edge_count: int) -> List[str]:
        """Append a chain below `parent_id` and return the new nodes in order."""

        chain: List[str] = []
        cursor = str(parent_id)
        for _ in range(int(edge_count)):
            cursor = self.add_child(cursor)
            chain.append(str(cursor))
        return chain


def _fill_to_node_count(
    *,
    builder: _TreeBuilder,
    target_node_count: int,
    target_depth: int,
    protected_node_ids: Sequence[str],
) -> None:
    """Add non-query filler nodes without changing the protected subtree answer."""

    protected = {str(node_id) for node_id in protected_node_ids}
    while len(builder.node_ids) < int(target_node_count):
        expandable = [
            str(node_id)
            for node_id in builder.node_ids
            if str(node_id) not in protected and int(builder.depths[str(node_id)]) < int(target_depth)
        ]
        if not expandable:
            raise ValueError("tree-count filler could not find a safe parent below the target depth")
        leaf_candidates = [
            str(node_id)
            for node_id in expandable
            if str(node_id) not in builder.children_by_parent
        ]
        if leaf_candidates:
            candidates = sorted(
                leaf_candidates,
                key=lambda node_id: (-int(builder.depths[str(node_id)]), str(node_id)),
            )
        else:
            candidates = sorted(
                expandable,
                key=lambda node_id: (int(builder.depths[str(node_id)]), str(node_id)),
            )
        parent_id = candidates[0]
        builder.add_child(str(parent_id))


def _build_descendant_count_tree(
    *,
    answer_count: int,
    target_node_count: int,
    target_depth: int,
) -> Tuple[str, List[str], Dict[str, List[str]]]:
    """Build one rooted tree with exactly `answer_count` descendants below the query node."""

    builder = _TreeBuilder()
    query_node_id = builder.add_child("node_0")
    max_chain_length = max(1, int(target_depth) - 1)
    remaining = int(answer_count)
    while remaining > 0:
        chain_length = min(int(max_chain_length), int(remaining))
        builder.add_chain(str(query_node_id), edge_count=int(chain_length))
        remaining -= int(chain_length)

    annotation_node_ids = _descendants(str(query_node_id), builder.children_by_parent)
    if len(annotation_node_ids) != int(answer_count):
        raise ValueError("descendant-count tree construction produced the wrong answer")
    if max(builder.depths.values()) > int(target_depth):
        raise ValueError("descendant-count tree exceeded the target depth")

    protected = [str(query_node_id), *annotation_node_ids]
    final_node_count = max(int(target_node_count), len(builder.node_ids))
    _fill_to_node_count(
        builder=builder,
        target_node_count=int(final_node_count),
        target_depth=int(target_depth),
        protected_node_ids=protected,
    )
    return str(query_node_id), [str(node_id) for node_id in annotation_node_ids], dict(builder.children_by_parent)


def _build_leaf_count_tree(
    *,
    answer_count: int,
    target_node_count: int,
    target_depth: int,
) -> Tuple[str, List[str], Dict[str, List[str]]]:
    """Build one rooted tree with exactly `answer_count` leaf descendants below the query node."""

    builder = _TreeBuilder()
    query_node_id = builder.add_child("node_0")
    first_branch_length = max(1, int(target_depth) - 1)
    builder.add_chain(str(query_node_id), edge_count=int(first_branch_length))
    for _ in range(max(0, int(answer_count) - 1)):
        builder.add_child(str(query_node_id))

    annotation_node_ids = _leaf_descendants(str(query_node_id), builder.children_by_parent)
    if len(annotation_node_ids) != int(answer_count):
        raise ValueError("leaf-count tree construction produced the wrong answer")
    if max(builder.depths.values()) > int(target_depth):
        raise ValueError("leaf-count tree exceeded the target depth")

    protected = [str(query_node_id), *_descendants(str(query_node_id), builder.children_by_parent)]
    final_node_count = max(int(target_node_count), len(builder.node_ids))
    _fill_to_node_count(
        builder=builder,
        target_node_count=int(final_node_count),
        target_depth=int(target_depth),
        protected_node_ids=protected,
    )
    return str(query_node_id), [str(node_id) for node_id in annotation_node_ids], dict(builder.children_by_parent)


def _path_branch_lengths(
    *,
    answer_count: int,
    target_depth: int,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    query_id: str,
) -> Tuple[int, int]:
    """Choose two branch lengths whose sum is the requested path distance."""

    feasible = [
        (left_length, int(answer_count) - left_length)
        for left_length in range(1, int(answer_count))
        if max(left_length, int(answer_count) - left_length) <= int(target_depth)
    ]
    if not feasible:
        raise ValueError("path-length support is not feasible for the selected tree depth")
    selection_index = _variant_local_index(
        params=params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        query_id=str(query_id),
        namespace="path_branch_split",
    )
    return tuple(feasible[int(selection_index) % len(feasible)])


def _build_node_pair_path_tree(
    *,
    answer_count: int,
    target_node_count: int,
    target_depth: int,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    query_id: str,
) -> Tuple[str, str, List[str], Dict[str, List[str]]]:
    """Build one tree with two queried nodes exactly `answer_count` hops apart."""

    builder = _TreeBuilder()
    left_length, right_length = _path_branch_lengths(
        answer_count=int(answer_count),
        target_depth=int(target_depth),
        params=params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        query_id=str(query_id),
    )
    max_lca_depth = int(target_depth) - max(int(left_length), int(right_length))
    lca_depth = _select_from_support(
        support=range(0, int(max_lca_depth) + 1),
        params=params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        query_id=str(query_id),
        namespace="path_lca_depth",
        offset=3,
    )
    trunk_nodes = builder.add_chain("node_0", edge_count=int(lca_depth))
    lca_node_id = str(trunk_nodes[-1]) if trunk_nodes else "node_0"
    left_nodes = builder.add_chain(str(lca_node_id), edge_count=int(left_length))
    right_nodes = builder.add_chain(str(lca_node_id), edge_count=int(right_length))
    left_query_node_id = str(left_nodes[-1])
    right_query_node_id = str(right_nodes[-1])

    parent_by_child = _parent_map(builder.children_by_parent)
    annotation_node_ids = _path_between_nodes(str(left_query_node_id), str(right_query_node_id), parent_by_child)
    if len(annotation_node_ids) - 1 != int(answer_count):
        raise ValueError("node-pair path tree construction produced the wrong answer")
    if max(builder.depths.values()) > int(target_depth):
        raise ValueError("node-pair path tree exceeded the target depth")

    if max(builder.depths.values()) < int(target_depth):
        builder.add_chain("node_0", edge_count=int(target_depth))
    while len(builder.node_ids) < int(target_node_count) and not [
        node_id
        for node_id in builder.node_ids
        if str(node_id) not in set(annotation_node_ids) and int(builder.depths[str(node_id)]) < int(target_depth)
    ]:
        builder.add_child("node_0")

    final_node_count = max(int(target_node_count), len(builder.node_ids))
    _fill_to_node_count(
        builder=builder,
        target_node_count=int(final_node_count),
        target_depth=int(target_depth),
        protected_node_ids=annotation_node_ids,
    )
    parent_by_child = _parent_map(builder.children_by_parent)
    annotation_node_ids = _path_between_nodes(str(left_query_node_id), str(right_query_node_id), parent_by_child)
    return (
        str(left_query_node_id),
        str(right_query_node_id),
        [str(node_id) for node_id in annotation_node_ids],
        dict(builder.children_by_parent),
    )


def _build_parent_query(
    *,
    node_ids: Sequence[str],
    root_node_id: str,
    parent_by_child: Mapping[str, str],
    depths: Mapping[str, int],
    labels: Mapping[str, str],
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    """Build one parent-of-node hierarchy query."""

    candidates = [str(node_id) for node_id in node_ids if str(node_id) != str(root_node_id)]
    deeper_candidates = [str(node_id) for node_id in candidates if int(depths[str(node_id)]) >= 2]
    use_deeper = bool(
        deeper_candidates
        and (
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.parent_query_depth_bias",
            )
            % 4
        )
    )
    pool = deeper_candidates if use_deeper else candidates
    query_node_id = str(
        pool[
            int(
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{task_id}.parent_query_node",
                )
                % len(pool)
            )
        ]
    )
    answer_node_id = str(parent_by_child[query_node_id])
    return {
        "question_text": f"What is the parent of {labels[query_node_id]}? Return the exact label shown.",
        "query_node_ids": [str(query_node_id)],
        "query_node_labels": [str(labels[query_node_id])],
        "query_depths": [int(depths[query_node_id])],
        "answer_node_id": str(answer_node_id),
        "answer_node_label": str(labels[answer_node_id]),
        "answer_node_depth": int(depths[answer_node_id]),
        "query_relationship": "parent",
        "lca_span": 0,
    }


def _build_lca_query(
    *,
    node_ids: Sequence[str],
    root_node_id: str,
    children_by_parent: Mapping[str, Sequence[str]],
    parent_by_child: Mapping[str, str],
    depths: Mapping[str, int],
    labels: Mapping[str, str],
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    """Build one lowest-common-ancestor hierarchy query."""

    leaves = [str(node_id) for node_id in node_ids if str(node_id) not in children_by_parent and int(depths[str(node_id)]) >= 2]
    pairs: List[Tuple[str, str, str]] = []
    for left_index, left_id in enumerate(leaves):
        for right_id in leaves[left_index + 1 :]:
            ancestor = _lowest_common_ancestor(str(left_id), str(right_id), parent_by_child)
            pairs.append((str(left_id), str(right_id), str(ancestor)))
    if not pairs:
        raise ValueError("hierarchy LCA queries require at least one leaf pair")

    non_root_pairs = [pair for pair in pairs if str(pair[2]) != str(root_node_id)]
    prefer_non_root = bool(
        non_root_pairs
        and (
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.lca_non_root_bias",
            )
            % 5
        )
    )
    pair_pool = non_root_pairs if prefer_non_root else pairs
    pair_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.lca_pair",
        )
        % len(pair_pool)
    )
    left_id, right_id, answer_node_id = pair_pool[pair_index]
    left_depth = int(depths[left_id])
    right_depth = int(depths[right_id])
    answer_depth = int(depths[answer_node_id])
    span = int((left_depth - answer_depth) + (right_depth - answer_depth))
    return {
        "question_text": (
            f"What is the lowest common ancestor of {labels[left_id]} and {labels[right_id]}? "
            "Return the exact label shown."
        ),
        "query_node_ids": [str(left_id), str(right_id)],
        "query_node_labels": [str(labels[left_id]), str(labels[right_id])],
        "query_depths": [left_depth, right_depth],
        "answer_node_id": str(answer_node_id),
        "answer_node_label": str(labels[answer_node_id]),
        "answer_node_depth": answer_depth,
        "query_relationship": "lowest_common_ancestor",
        "lca_span": span,
    }


def build_hierarchy_ancestor_dataset(
    *,
    query_id: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    """Build one hierarchy-diagram ancestor dataset instance."""

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    template = _hierarchy_template(params=params, instance_seed=int(instance_seed), task_id=str(task_id))
    root_node_id = str(template["root_node_id"])
    children_by_parent = {
        str(parent_id): [str(child_id) for child_id in children]
        for parent_id, children in dict(template["children_by_parent"]).items()
    }
    node_ids = _all_node_ids(root_node_id, children_by_parent)
    parent_by_child = _parent_map(children_by_parent)
    depths = _depth_map(root_node_id, children_by_parent)
    labels = _label_map(node_ids=node_ids, rng=rng)

    if str(query_id) == "parent_of_node":
        query = _build_parent_query(
            node_ids=node_ids,
            root_node_id=root_node_id,
            parent_by_child=parent_by_child,
            depths=depths,
            labels=labels,
            params=params,
            instance_seed=int(instance_seed),
            task_id=str(task_id),
        )
    elif str(query_id) == "lowest_common_ancestor_of_two_nodes":
        query = _build_lca_query(
            node_ids=node_ids,
            root_node_id=root_node_id,
            children_by_parent=children_by_parent,
            parent_by_child=parent_by_child,
            depths=depths,
            labels=labels,
            params=params,
            instance_seed=int(instance_seed),
            task_id=str(task_id),
        )
    else:
        raise ValueError(f"unsupported hierarchy query id: {query_id}")

    node_specs: List[Dict[str, Any]] = []
    for node_id in node_ids:
        node_specs.append(
            {
                "node_id": str(node_id),
                "node_bbox_id": f"{node_id.replace('node', 'node_bbox')}",
                "node_label_bbox_id": f"{node_id.replace('node', 'node_label_bbox')}",
                "node_label": str(labels[node_id]),
                "parent_node_id": parent_by_child.get(str(node_id)),
                "depth": int(depths[node_id]),
                "is_leaf": str(node_id) not in children_by_parent,
            }
        )

    edge_specs: List[Dict[str, Any]] = []
    edge_index = 0
    for parent_id, children in children_by_parent.items():
        for child_id in children:
            edge_specs.append(
                {
                    "edge_id": f"edge_{edge_index}",
                    "source_node_id": str(parent_id),
                    "target_node_id": str(child_id),
                }
            )
            edge_index += 1

    leaf_count = sum(1 for node_id in node_ids if str(node_id) not in children_by_parent)
    max_depth = max(int(depth) for depth in depths.values())
    return {
        "scene_title": _title(rng=rng),
        "scene_variant": str(scene_variant),
        "query_id": str(query_id),
        "question_text": str(query["question_text"]),
        "question_format": "hierarchy_ancestor_label",
        "view_family": "org_chart_diagram",
        "template_id": str(template["template_id"]),
        "root_node_id": str(root_node_id),
        "node_specs": node_specs,
        "edge_specs": edge_specs,
        "tree_node_count": len(node_specs),
        "leaf_count": int(leaf_count),
        "tree_depth": int(max_depth),
        "query_node_ids": [str(node_id) for node_id in query["query_node_ids"]],
        "query_node_labels": [str(label) for label in query["query_node_labels"]],
        "query_depths": [int(depth) for depth in query["query_depths"]],
        "query_relationship": str(query["query_relationship"]),
        "answer_node_id": str(query["answer_node_id"]),
        "answer_node_label": str(query["answer_node_label"]),
        "answer_node_bbox_id": str(query["answer_node_id"].replace("node", "node_bbox")),
        "answer_node_depth": int(query["answer_node_depth"]),
        "lca_span": int(query["lca_span"]),
    }


def build_hierarchy_tree_count_dataset(
    *,
    query_id: str,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    """Build one generic rooted-tree counting dataset instance."""

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    query_key = str(query_id)
    if query_key not in SUPPORTED_DIAGRAM_HIERARCHY_TREE_COUNT_QUERY_IDS:
        raise ValueError(f"unsupported hierarchy tree-count query id: {query_id}")

    node_min, node_max = _resolve_int_bound_pair(
        params=params,
        gen_defaults=gen_defaults,
        min_key="tree_node_count_min",
        max_key="tree_node_count_max",
        fallback_min=16,
        fallback_max=30,
        context=str(task_id),
    )
    depth_min, depth_max = _resolve_int_bound_pair(
        params=params,
        gen_defaults=gen_defaults,
        min_key="tree_depth_min",
        max_key="tree_depth_max",
        fallback_min=4,
        fallback_max=8,
        context=str(task_id),
    )
    descendant_min, descendant_max = _resolve_int_bound_pair(
        params=params,
        gen_defaults=gen_defaults,
        min_key="subtree_descendant_count_min",
        max_key="subtree_descendant_count_max",
        fallback_min=4,
        fallback_max=18,
        context=str(task_id),
    )
    leaf_min, leaf_max = _resolve_int_bound_pair(
        params=params,
        gen_defaults=gen_defaults,
        min_key="subtree_leaf_count_min",
        max_key="subtree_leaf_count_max",
        fallback_min=2,
        fallback_max=12,
        context=str(task_id),
    )
    path_min, path_max = _resolve_int_bound_pair(
        params=params,
        gen_defaults=gen_defaults,
        min_key="path_length_between_two_nodes_min",
        max_key="path_length_between_two_nodes_max",
        fallback_min=3,
        fallback_max=2 * int(depth_max),
        context=str(task_id),
    )
    path_max = min(int(path_max), 2 * int(depth_max))
    if int(depth_min) < 1:
        raise ValueError("tree_depth_min must be at least 1")
    if int(node_min) < 2:
        raise ValueError("tree_node_count_min must be at least 2")
    if int(path_min) < 1:
        raise ValueError("path_length_between_two_nodes_min must be at least 1")
    if int(path_min) > int(path_max):
        raise ValueError("path_length_between_two_nodes_min exceeds feasible tree-depth support")

    target_node_count = _select_from_support(
        support=range(int(node_min), int(node_max) + 1),
        params=params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        query_id=query_key,
        namespace="tree_node_count",
        offset=1,
    )
    target_depth = _select_from_support(
        support=range(int(depth_min), int(depth_max) + 1),
        params=params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        query_id=query_key,
        namespace="tree_depth",
        offset=2,
    )

    if query_key == "subtree_descendant_count":
        answer_count = _select_from_support(
            support=range(int(descendant_min), int(descendant_max) + 1),
            params=params,
            instance_seed=int(instance_seed),
            task_id=str(task_id),
            query_id=query_key,
            namespace="answer_count",
        )
        query_node_id, annotation_node_ids, children_by_parent = _build_descendant_count_tree(
            answer_count=int(answer_count),
            target_node_count=int(target_node_count),
            target_depth=int(target_depth),
        )
        query_relationship = "subtree_descendant_count"
        annotation_semantics = "descendant_nodes_unordered"
    elif query_key == "subtree_leaf_count":
        answer_count = _select_from_support(
            support=range(int(leaf_min), int(leaf_max) + 1),
            params=params,
            instance_seed=int(instance_seed),
            task_id=str(task_id),
            query_id=query_key,
            namespace="answer_count",
        )
        query_node_id, annotation_node_ids, children_by_parent = _build_leaf_count_tree(
            answer_count=int(answer_count),
            target_node_count=int(target_node_count),
            target_depth=int(target_depth),
        )
        query_relationship = "subtree_leaf_count"
        annotation_semantics = "leaf_descendant_nodes_unordered"
    else:
        answer_count = _select_from_support(
            support=range(int(path_min), int(path_max) + 1),
            params=params,
            instance_seed=int(instance_seed),
            task_id=str(task_id),
            query_id=query_key,
            namespace="answer_count",
        )
        target_depth = max(int(target_depth), (int(answer_count) + 1) // 2)
        left_query_node_id, right_query_node_id, annotation_node_ids, children_by_parent = _build_node_pair_path_tree(
            answer_count=int(answer_count),
            target_node_count=int(target_node_count),
            target_depth=int(target_depth),
            params=params,
            instance_seed=int(instance_seed),
            task_id=str(task_id),
            query_id=query_key,
        )
        query_node_id = str(left_query_node_id)
        query_relationship = "path_length_between_two_nodes"
        annotation_semantics = "path_nodes_between_query_nodes_ordered"

    root_node_id = "node_0"
    node_ids = _all_node_ids(root_node_id, children_by_parent)
    if len(node_ids) < int(node_min) or len(node_ids) > int(node_max):
        raise ValueError("constructed tree node count fell outside configured bounds")
    parent_by_child = _parent_map(children_by_parent)
    depths = _depth_map(root_node_id, children_by_parent)
    max_depth = max(int(depth) for depth in depths.values())
    if max_depth < int(depth_min) or max_depth > int(depth_max):
        raise ValueError("constructed tree depth fell outside configured bounds")

    labels = _label_map(node_ids=node_ids, rng=rng)
    query_label = str(labels[str(query_node_id)])
    if query_key == "subtree_descendant_count":
        question_text = f"How many descendants does \"{query_label}\" have? Do not include \"{query_label}\" itself."
    elif query_key == "subtree_leaf_count":
        question_text = f"How many leaf nodes are in the subtree rooted at \"{query_label}\"?"
    else:
        right_query_label = str(labels[str(right_query_node_id)])
        question_text = f"How many parent-child hops are on the path between \"{query_label}\" and \"{right_query_label}\"?"

    node_specs: List[Dict[str, Any]] = []
    for node_id in node_ids:
        node_specs.append(
            {
                "node_id": str(node_id),
                "node_bbox_id": f"{node_id.replace('node', 'node_bbox')}",
                "node_label_bbox_id": f"{node_id.replace('node', 'node_label_bbox')}",
                "node_label": str(labels[node_id]),
                "parent_node_id": parent_by_child.get(str(node_id)),
                "depth": int(depths[node_id]),
                "is_leaf": str(node_id) not in children_by_parent,
            }
        )

    edge_specs: List[Dict[str, Any]] = []
    edge_index = 0
    for parent_id, children in children_by_parent.items():
        for child_id in children:
            edge_specs.append(
                {
                    "edge_id": f"edge_{edge_index}",
                    "source_node_id": str(parent_id),
                    "target_node_id": str(child_id),
                }
            )
            edge_index += 1

    descendant_node_ids = _descendants(str(query_node_id), children_by_parent)
    leaf_descendant_node_ids = _leaf_descendants(str(query_node_id), children_by_parent)
    if query_key == "path_length_between_two_nodes":
        query_node_ids = [str(query_node_id), str(right_query_node_id)]
        path_node_ids = _path_between_nodes(str(query_node_id), str(right_query_node_id), parent_by_child)
        path_lca_node_id = _lowest_common_ancestor(str(query_node_id), str(right_query_node_id), parent_by_child)
    else:
        query_node_ids = [str(query_node_id)]
        path_node_ids = _ancestors(str(query_node_id), parent_by_child)
        path_lca_node_id = str(query_node_id)
    leaf_count = sum(1 for node_id in node_ids if str(node_id) not in children_by_parent)
    annotation_node_bbox_ids = [str(node_id).replace("node", "node_bbox") for node_id in annotation_node_ids]
    return {
        "scene_title": _tree_title(rng=rng),
        "scene_variant": str(scene_variant),
        "query_id": query_key,
        "question_text": str(question_text),
        "question_format": "hierarchy_tree_count",
        "view_family": "rooted_tree_diagram",
        "template_id": f"generated_{query_key}",
        "root_node_id": str(root_node_id),
        "node_specs": node_specs,
        "edge_specs": edge_specs,
        "tree_node_count": len(node_specs),
        "leaf_count": int(leaf_count),
        "tree_depth": int(max_depth),
        "query_node_ids": [str(node_id) for node_id in query_node_ids],
        "query_node_labels": [str(labels[str(node_id)]) for node_id in query_node_ids],
        "query_depths": [int(depths[str(node_id)]) for node_id in query_node_ids],
        "query_relationship": str(query_relationship),
        "answer_count": int(answer_count),
        "annotation_node_ids": [str(node_id) for node_id in annotation_node_ids],
        "annotation_node_bbox_ids": [str(bbox_id) for bbox_id in annotation_node_bbox_ids],
        "annotation_semantics": str(annotation_semantics),
        "descendant_node_ids": [str(node_id) for node_id in descendant_node_ids],
        "descendant_count": int(len(descendant_node_ids)),
        "leaf_descendant_node_ids": [str(node_id) for node_id in leaf_descendant_node_ids],
        "leaf_descendant_count": int(len(leaf_descendant_node_ids)),
        "path_node_ids": [str(node_id) for node_id in path_node_ids],
        "path_node_labels": [str(labels[str(node_id)]) for node_id in path_node_ids],
        "path_length_between_nodes": int(len(path_node_ids) - 1),
        "path_lca_node_id": str(path_lca_node_id),
        "path_lca_node_label": str(labels[str(path_lca_node_id)]),
        "path_lca_depth": int(depths[str(path_lca_node_id)]),
    }


__all__ = [
    "HierarchyDefaults",
    "HierarchyRenderParams",
    "SUPPORTED_DIAGRAM_HIERARCHY_SCENE_VARIANTS",
    "SUPPORTED_DIAGRAM_HIERARCHY_QUERY_IDS",
    "SUPPORTED_DIAGRAM_HIERARCHY_TREE_COUNT_SCENE_VARIANTS",
    "SUPPORTED_DIAGRAM_HIERARCHY_TREE_COUNT_QUERY_IDS",
    "build_hierarchy_ancestor_dataset",
    "build_hierarchy_tree_count_dataset",
    "resolve_hierarchy_render_params",
    "resolve_hierarchy_scene_variant",
    "resolve_hierarchy_query_id",
    "resolve_hierarchy_tree_count_scene_variant",
    "resolve_hierarchy_tree_count_query_id",
]
