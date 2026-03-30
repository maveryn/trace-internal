"""Shared dataset builders and render defaults for hierarchy-diagram tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.name_assets import load_short_name_manifest
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.common import (
    resolve_diagrams_axis_variant,
    resolve_diagrams_int_param,
    resolve_diagrams_rgb_triple,
)


SUPPORTED_DIAGRAM_HIERARCHY_SCENE_VARIANTS: Tuple[str, ...] = ("org_chart",)
SUPPORTED_DIAGRAM_HIERARCHY_TASK_VARIANTS: Tuple[str, ...] = (
    "parent_of_node",
    "lowest_common_ancestor_of_two_nodes",
)

_TITLE_OPTIONS: Tuple[str, ...] = (
    "Organization Chart",
    "Team Structure",
    "Department Hierarchy",
    "Company Structure",
    "Org Overview",
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


def resolve_hierarchy_task_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active hierarchy task variant."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_HIERARCHY_TASK_VARIANTS,
        task_id=str(task_id),
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def resolve_hierarchy_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
) -> HierarchyRenderParams:
    """Resolve rendering params for hierarchy scenes."""

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return resolve_diagrams_rgb_triple(params, render_defaults, key, fallback)

    return HierarchyRenderParams(
        canvas_width=int(resolve_diagrams_int_param(params, render_defaults, "canvas_width", 1280)),
        canvas_height=int(resolve_diagrams_int_param(params, render_defaults, "canvas_height", 880)),
        outer_margin_px=int(resolve_diagrams_int_param(params, render_defaults, "outer_margin_px", 52)),
        panel_padding_px=int(resolve_diagrams_int_param(params, render_defaults, "panel_padding_px", 28)),
        panel_corner_radius_px=int(resolve_diagrams_int_param(params, render_defaults, "panel_corner_radius_px", 30)),
        title_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "title_font_size_px", 32)),
        title_band_height_px=int(resolve_diagrams_int_param(params, render_defaults, "title_band_height_px", 78)),
        node_width_px=int(resolve_diagrams_int_param(params, render_defaults, "node_width_px", 164)),
        node_height_px=int(resolve_diagrams_int_param(params, render_defaults, "node_height_px", 72)),
        node_corner_radius_px=int(resolve_diagrams_int_param(params, render_defaults, "node_corner_radius_px", 20)),
        node_border_width_px=int(resolve_diagrams_int_param(params, render_defaults, "node_border_width_px", 3)),
        connector_width_px=int(resolve_diagrams_int_param(params, render_defaults, "connector_width_px", 5)),
        connector_branch_gap_px=int(resolve_diagrams_int_param(params, render_defaults, "connector_branch_gap_px", 22)),
        label_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "label_font_size_px", 24)),
        root_fill_rgb=_triple("root_fill_rgb", (236, 244, 255)),
        node_fill_rgb=_triple("node_fill_rgb", (246, 248, 252)),
        panel_fill_rgb=_triple("panel_fill_rgb", (252, 252, 255)),
        panel_border_rgb=_triple("panel_border_rgb", (88, 98, 112)),
        title_color_rgb=_triple("title_color_rgb", (34, 40, 48)),
        node_border_rgb=_triple("node_border_rgb", (77, 90, 109)),
        label_color_rgb=_triple("label_color_rgb", (29, 34, 41)),
        label_stroke_rgb=_triple("label_stroke_rgb", (255, 255, 255)),
        connector_color_rgb=_triple("connector_color_rgb", (95, 104, 118)),
    )


def _sample_unique_labels(candidates: Sequence[str], *, count: int, rng) -> List[str]:
    """Sample a deterministic unique label subset from a candidate pool."""

    if int(count) > len(candidates):
        raise ValueError("requested more hierarchy labels than available candidates")
    return [str(label) for label in rng.sample(list(candidates), int(count))]


def _title(*, rng) -> str:
    """Sample one short hierarchy scene title."""

    return str(_TITLE_OPTIONS[int(rng.randrange(len(_TITLE_OPTIONS)))])


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


def _lowest_common_ancestor(node_a: str, node_b: str, parent_by_child: Mapping[str, str]) -> str:
    """Return the lowest common ancestor of two hierarchy nodes."""

    ancestors_b = set(_ancestors(str(node_b), parent_by_child))
    for candidate in _ancestors(str(node_a), parent_by_child):
        if str(candidate) in ancestors_b:
            return str(candidate)
    raise ValueError("hierarchy nodes must share at least one ancestor")


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

    sampled_names = _sample_unique_labels(load_short_name_manifest(), count=len(node_ids), rng=rng)
    return {
        str(node_id): str(label)
        for node_id, label in zip([str(node_id) for node_id in node_ids], sampled_names)
    }


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
    task_variant: str,
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

    if str(task_variant) == "parent_of_node":
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
    elif str(task_variant) == "lowest_common_ancestor_of_two_nodes":
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
        raise ValueError(f"unsupported hierarchy task variant: {task_variant}")

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
        "task_variant": str(task_variant),
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


__all__ = [
    "HierarchyDefaults",
    "HierarchyRenderParams",
    "SUPPORTED_DIAGRAM_HIERARCHY_SCENE_VARIANTS",
    "SUPPORTED_DIAGRAM_HIERARCHY_TASK_VARIANTS",
    "build_hierarchy_ancestor_dataset",
    "resolve_hierarchy_render_params",
    "resolve_hierarchy_scene_variant",
    "resolve_hierarchy_task_variant",
]
