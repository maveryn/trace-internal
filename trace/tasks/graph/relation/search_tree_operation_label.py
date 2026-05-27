"""Search-tree and heap operation label tasks on numeric binary trees."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.binary_tree_scene import (
    SUPPORTED_BINARY_TREE_SCENE_VARIANTS,
    BinaryTreeNode,
    BinaryTreeSample,
    projected_binary_tree_bbox_evidence,
    render_binary_tree_scene,
)
from ..shared.complexity import build_graph_complexity, normalize_int_with_bounds, resolve_graph_complexity_weights
from ..shared.graph_scene import SUPPORTED_NODE_SHAPE_VARIANTS
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import resolve_graph_named_variant, resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__binary_tree__tree_operation_label"
SCENE_ID = "binary_tree"

SUPPORTED_SEARCH_TREE_OPERATION_QUERY_VARIANTS: Tuple[str, ...] = (
    "bst_search_terminal_label",
    "bst_insert_parent_label",
    "heap_property_violation_label",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for search-tree operation tasks."""

    node_count_min: int = 7
    node_count_max: int = 13
    max_depth: int = 4
    key_min: int = 10
    key_max: int = 99
    canvas_width: int = 900
    canvas_height: int = 660
    outer_margin_px: int = 28
    panel_padding_px: int = 24
    panel_corner_radius_px: int = 20
    panel_title_font_size_px: int = 24
    node_shape_variant: str = "circle"
    node_radius_min_px: int = 20
    node_radius_max_px: int = 26
    edge_width_px: int = 4
    arrow_length_px: int = 12
    arrow_width_px: int = 7
    node_border_width_px: int = 2
    label_font_size_px: int = 20
    layout_transform_variant: str = "identity"
    node_color_name: str = "blue"
    background_color_rgb: Tuple[int, int, int] = (247, 248, 251)
    panel_fill_rgb: Tuple[int, int, int] = (255, 255, 255)
    panel_border_rgb: Tuple[int, int, int] = (205, 212, 224)
    title_color_rgb: Tuple[int, int, int] = (70, 78, 96)
    edge_color_rgb: Tuple[int, int, int] = (118, 128, 145)
    node_fill_rgb: Tuple[int, int, int] = (92, 124, 250)
    node_border_rgb: Tuple[int, int, int] = (52, 73, 144)
    label_text_rgb: Tuple[int, int, int] = (255, 255, 255)
    label_stroke_rgb: Tuple[int, int, int] = (52, 73, 144)


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved query and visual axes for one search-tree operation instance."""

    query_variant: str
    scene_variant: str
    node_count: int
    node_shape_variant: str
    node_color_name: str
    query_variant_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _OperationSelection:
    """One sampled operation query over a numeric binary tree."""

    target_key: int | None
    answer_label: str
    evidence_labels: Tuple[str, ...]
    query_node_ids: Tuple[str, ...]
    answer_node_id: str
    operation_kind: str


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="relation")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="relation", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    query_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_variant")
    query_variant, query_probs = resolve_graph_named_variant(
        query_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        supported=SUPPORTED_SEARCH_TREE_OPERATION_QUERY_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="query_variant",
    )
    scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.scene_variant")
    scene_variant, scene_probs = resolve_graph_named_variant(
        scene_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_BINARY_TREE_SCENE_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="scene_variant",
    )
    lower = int(group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min))
    upper = int(group_default(_GEN_DEFAULTS, "node_count_max", _DEFAULTS.node_count_max))
    support = tuple(range(int(lower), int(upper) + 1))
    explicit_node_count = params.get("node_count")
    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
        if int(node_count) not in set(support):
            raise ValueError("node_count is outside search-tree operation support")
    else:
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:node_count",
        )
        node_count = int(support[int(selection_index % len(support))])
    shape_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.node_shape_variant")
    node_shape_variant, shape_probs = resolve_graph_named_variant(
        shape_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="node_shape_variant",
        weights_key="node_shape_variant_weights",
        balance_flag_key="balanced_node_shape_variant_sampling",
        supported=SUPPORTED_NODE_SHAPE_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="node_shape_variant",
    )
    color_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.node_color_name")
    node_color_name, color_probs = resolve_graph_named_variant(
        color_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="node_color_name",
        weights_key="node_color_name_weights",
        balance_flag_key="balanced_node_color_name_sampling",
        supported=SUPPORTED_NODE_COLOR_NAMES,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="node_color_name",
    )
    return _ResolvedQuery(
        query_variant=str(query_variant),
        scene_variant=str(scene_variant),
        node_count=int(node_count),
        node_shape_variant=str(node_shape_variant),
        node_color_name=str(node_color_name),
        query_variant_probabilities=dict(query_probs),
        scene_variant_probabilities=dict(scene_probs),
        node_count_probabilities=dict(uniform_probability_map(support, selected=int(node_count) if explicit_node_count is not None else None)),
        node_shape_variant_probabilities=dict(shape_probs),
        node_color_name_probabilities=dict(color_probs),
    )


def _sort_node_ids(node_ids: Sequence[str]) -> Tuple[str, ...]:
    return tuple(sorted((str(node_id) for node_id in node_ids), key=lambda value: (len(value), value)))


def _sample_unique_keys(rng, *, node_count: int, key_min: int, key_max: int) -> List[int]:
    support = list(range(int(key_min), int(key_max) + 1))
    if len(support) < int(node_count) + 6:
        raise ValueError("key range is too small for search-tree operation sampling")
    rng.shuffle(support)
    return sorted(int(value) for value in support[: int(node_count)])


def _bst_insert_path(nodes: Dict[str, Dict[str, Any]], key: int, *, max_depth: int) -> bool:
    if not nodes:
        nodes[""] = {"key": int(key), "parent_id": None, "left_id": None, "right_id": None, "depth": 0}
        return True
    current_id = ""
    while True:
        current_key = int(nodes[str(current_id)]["key"])
        if int(key) == current_key:
            return False
        side = "L" if int(key) < current_key else "R"
        child_key = "left_id" if side == "L" else "right_id"
        child_id = nodes[str(current_id)][child_key]
        if child_id is None:
            node_id = f"{current_id}{side}"
            depth = len(node_id)
            if int(depth) > int(max_depth):
                return False
            nodes[node_id] = {
                "key": int(key),
                "parent_id": str(current_id),
                "left_id": None,
                "right_id": None,
                "depth": int(depth),
            }
            nodes[str(current_id)][child_key] = str(node_id)
            return True
        current_id = str(child_id)


def _sample_bst_nodes(
    instance_seed: int,
    *,
    node_count: int,
    max_depth: int,
    max_attempts: int,
) -> Dict[str, Dict[str, Any]]:
    key_min = int(group_default(_GEN_DEFAULTS, "key_min", _DEFAULTS.key_min))
    key_max = int(group_default(_GEN_DEFAULTS, "key_max", _DEFAULTS.key_max))
    for attempt in range(max(1, int(max_attempts))):
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.bst.{attempt}")
        keys = _sample_unique_keys(rng, node_count=int(node_count), key_min=key_min, key_max=key_max)
        insertion_order = list(keys)
        rng.shuffle(insertion_order)
        nodes: Dict[str, Dict[str, Any]] = {}
        failed = False
        for key in insertion_order:
            if not _bst_insert_path(nodes, int(key), max_depth=int(max_depth)):
                failed = True
                break
        if not failed and len(nodes) == int(node_count):
            return nodes
    raise ValueError("could not sample a bounded-depth BST")


def _array_index_to_node_id(index: int) -> str:
    bits = bin(int(index) + 1)[3:]
    return "".join("L" if bit == "0" else "R" for bit in bits)


def _sample_heap_nodes(
    instance_seed: int,
    *,
    node_count: int,
) -> Tuple[Dict[str, Dict[str, Any]], Tuple[str, str]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.heap")
    node_ids = [_array_index_to_node_id(index) for index in range(int(node_count))]
    base_values = {
        node_id: 12 + (len(node_id) * 18) + index
        for index, node_id in enumerate(node_ids)
    }
    non_root_ids = [node_id for node_id in node_ids if node_id]
    violation_child_id = str(rng.choice(non_root_ids))
    violation_parent_id = violation_child_id[:-1]
    base_values[violation_child_id] = int(base_values[violation_parent_id]) - 3
    used = set()
    for node_id in node_ids:
        value = int(base_values[node_id])
        while value in used:
            value += 1
        base_values[node_id] = value
        used.add(value)
    nodes: Dict[str, Dict[str, Any]] = {}
    for node_id in node_ids:
        left_id = f"{node_id}L" if f"{node_id}L" in set(node_ids) else None
        right_id = f"{node_id}R" if f"{node_id}R" in set(node_ids) else None
        nodes[node_id] = {
            "key": int(base_values[node_id]),
            "parent_id": node_id[:-1] if node_id else None,
            "left_id": left_id,
            "right_id": right_id,
            "depth": len(node_id),
        }
    violations = []
    for child_id in non_root_ids:
        parent_id = child_id[:-1]
        if int(nodes[parent_id]["key"]) > int(nodes[child_id]["key"]):
            violations.append((parent_id, child_id))
    if len(violations) != 1:
        raise ValueError("heap sampler failed to create exactly one min-heap violation")
    return nodes, tuple(violations[0])


def _make_sample(nodes: Mapping[str, Mapping[str, Any]]) -> BinaryTreeSample:
    node_ids = _sort_node_ids(tuple(nodes.keys()))
    tree_nodes = tuple(
        BinaryTreeNode(
            node_id=str(node_id),
            label=str(nodes[str(node_id)]["key"]),
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

    return BinaryTreeSample(
        nodes=tree_nodes,
        root_id="",
        label_variant="numeric_keys",
        label_source_kind="synthetic_numeric_keys",
        label_bucket="numeric_keys",
        label_manifest="synthetic_numeric_keys_v0",
        label_filter={"min": int(min(int(node.label) for node in tree_nodes)), "max": int(max(int(node.label) for node in tree_nodes))},
        label_bucket_probabilities={"numeric_keys": 1.0},
        preorder_labels=tuple(preorder("")),
        inorder_labels=tuple(inorder("")),
        postorder_labels=tuple(postorder("")),
        level_order_labels=tuple(str(node_by_id[node_id].label) for node_id in node_ids),
    )


def _bst_search_path(nodes: Mapping[str, Mapping[str, Any]], target_key: int) -> Tuple[str, ...]:
    path: List[str] = []
    current_id = ""
    while current_id in nodes:
        path.append(str(current_id))
        current_key = int(nodes[str(current_id)]["key"])
        if int(target_key) == current_key:
            break
        next_id = f"{current_id}{'L' if int(target_key) < current_key else 'R'}"
        if next_id not in nodes:
            break
        current_id = str(next_id)
    return tuple(path)


def _sample_missing_key(rng, *, nodes: Mapping[str, Mapping[str, Any]]) -> int:
    existing = {int(node["key"]) for node in nodes.values()}
    key_min = int(group_default(_GEN_DEFAULTS, "key_min", _DEFAULTS.key_min))
    key_max = int(group_default(_GEN_DEFAULTS, "key_max", _DEFAULTS.key_max))
    candidates = [key for key in range(key_min, key_max + 1) if key not in existing]
    if not candidates:
        raise ValueError("no missing key candidate")
    return int(rng.choice(candidates))


def _sample_operation(
    instance_seed: int,
    *,
    query: _ResolvedQuery,
    max_attempts: int,
) -> Tuple[BinaryTreeSample, _OperationSelection]:
    if str(query.query_variant) == "heap_property_violation_label":
        nodes, (parent_id, child_id) = _sample_heap_nodes(int(instance_seed), node_count=int(query.node_count))
        sample = _make_sample(nodes)
        parent_label = str(nodes[str(parent_id)]["key"])
        child_label = str(nodes[str(child_id)]["key"])
        return sample, _OperationSelection(
            target_key=None,
            answer_label=str(child_label),
            evidence_labels=(str(parent_label), str(child_label)),
            query_node_ids=(str(parent_id), str(child_id)),
            answer_node_id=str(child_id),
            operation_kind="min_heap_property_violation",
        )

    nodes = _sample_bst_nodes(
        int(instance_seed),
        node_count=int(query.node_count),
        max_depth=int(group_default(_GEN_DEFAULTS, "max_depth", _DEFAULTS.max_depth)),
        max_attempts=max(1, int(max_attempts)),
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.operation.{query.query_variant}")
    if str(query.query_variant) == "bst_search_terminal_label" and rng.randrange(2):
        target_key = int(rng.choice([int(node["key"]) for node in nodes.values()]))
    else:
        target_key = _sample_missing_key(rng, nodes=nodes)
    path_ids = _bst_search_path(nodes, int(target_key))
    answer_node_id = str(path_ids[-1])
    sample = _make_sample(nodes)
    labels_by_id = {str(node.node_id): str(node.label) for node in sample.nodes}
    return sample, _OperationSelection(
        target_key=int(target_key),
        answer_label=str(labels_by_id[str(answer_node_id)]),
        evidence_labels=tuple(str(labels_by_id[str(node_id)]) for node_id in path_ids),
        query_node_ids=tuple(str(node_id) for node_id in path_ids),
        answer_node_id=str(answer_node_id),
        operation_kind=str(query.query_variant),
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    return (
        json.dumps({"evidence": [[156, 124, 204, 172], [250, 250, 298, 298]], "answer": "42"}, separators=(",", ":")),
        json.dumps({"answer": "42"}, separators=(",", ":")),
    )


def _build_complexity(*, sample: BinaryTreeSample, operation: _OperationSelection, query_variant: str) -> Any:
    node_norm = normalize_int_with_bounds(int(sample.node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max))
    depth_norm = normalize_int_with_bounds(int(sample.max_depth), (2, _DEFAULTS.max_depth))
    path_norm = normalize_int_with_bounds(len(operation.evidence_labels), (2, _DEFAULTS.max_depth + 1))
    operation_load = 0.58 if str(query_variant) == "heap_property_violation_label" else 0.72
    return build_graph_complexity(
        weights=_COMPLEXITY_WEIGHTS,
        components={
            "topology_reasoning": (0.45 * operation_load) + (0.35 * path_norm) + (0.20 * depth_norm),
            "visual_scan": (0.70 * node_norm) + (0.30 * path_norm),
            "ambiguity": (0.55 * operation_load) + (0.45 * path_norm),
            "clutter": (0.65 * node_norm) + (0.35 * depth_norm),
        },
    )


@register_task
class GraphRelationSearchTreeOperationLabelTask:
    """Answer label-valued BST and heap operation queries."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query = _resolve_query(int(instance_seed), params=params)
        render_params = resolve_graph_render_params(
            params,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            node_color_name=str(query.node_color_name),
            node_shape_variant=str(query.node_shape_variant),
            edge_routing_variant="straight",
        )
        image, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        sample, operation = _sample_operation(
            int(instance_seed),
            query=query,
            max_attempts=max(1, int(max_attempts)),
        )
        scene_title = "Binary Heap" if str(query.query_variant) == "heap_property_violation_label" else "Binary Search Tree"
        rendered_scene = render_binary_tree_scene(
            sample=sample,
            render_params=render_params,
            scene_variant=str(query.scene_variant),
            scene_title=scene_title,
            base_image=image,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        evidence_projection = projected_binary_tree_bbox_evidence(rendered_scene, operation.evidence_labels)
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in evidence_projection["bbox_sequence"]]
        answer_gt = TypedValue(type="string", value=str(operation.answer_label))
        evidence_gt = TypedValue(type="bbox_sequence", value=list(evidence_bboxes))

        prompt_defaults = dict(_PROMPT_DEFAULTS)
        json_example, json_example_answer_only = _build_prompt_json_examples()
        target_key = "" if operation.target_key is None else str(operation.target_key)
        object_description_key = "object_description_heap" if str(query.query_variant) == "heap_property_violation_label" else "object_description_bst"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults.get(object_description_key, prompt_defaults["object_description"])),
                "target_key": str(target_key),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        sample_node_by_id = {str(node.node_id): node for node in sample.nodes}
        node_entities = []
        for node in rendered_scene.nodes:
            sample_node = next(tree_node for tree_node in sample.nodes if str(tree_node.label) == str(node.label))
            node_entities.append(
                {
                    "entity_id": f"node_{node.label}",
                    "entity_kind": "binary_tree_node",
                    "label": str(node.label),
                    "numeric_key": int(node.label),
                    "parent_label": node.parent_label,
                    "left_label": node.left_label,
                    "right_label": node.right_label,
                    "depth": int(node.depth),
                    "center_px": list(node.center_xy),
                    "bbox_xyxy": list(node.bbox_xyxy),
                    "is_query_path_node": bool(str(sample_node.node_id) in set(operation.query_node_ids)),
                    "is_answer_node": bool(str(sample_node.node_id) == str(operation.answer_node_id)),
                }
            )
        edge_entities = [
            {
                "entity_id": str(edge.edge_id),
                "entity_kind": "binary_tree_edge",
                "parent_label": str(edge.parent_label),
                "child_label": str(edge.child_label),
                "child_side": str(edge.child_side),
                "segment_px": [list(edge.segment_px[0]), list(edge.segment_px[1])],
            }
            for edge in rendered_scene.edges
        ]

        trace_payload = {
            "scene_ir": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "scene_kind": "search_tree_operation_diagram",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "root_label": str(sample_node_by_id[""].label),
                    "query_variant": str(query.query_variant),
                    "target_key": int(operation.target_key) if operation.target_key is not None else None,
                    "answer_label": str(operation.answer_label),
                    "answer_node_id": str(operation.answer_node_id),
                    "evidence_labels": list(operation.evidence_labels),
                    "preorder_labels": list(sample.preorder_labels),
                    "inorder_labels": list(sample.inorder_labels),
                    "postorder_labels": list(sample.postorder_labels),
                    "level_order_labels": list(sample.level_order_labels),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(rendered_scene.panel_geometry),
                },
            },
            "query_spec": {
                "task_id": TASK_ID,
                "query_id": str(query.query_variant),
                "query_variant": str(query.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(query.scene_variant),
                    "query_variant_probabilities": dict(query.query_variant_probabilities),
                    "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                    "node_count": int(sample.node_count),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "max_depth": int(sample.max_depth),
                    "node_shape_variant": str(query.node_shape_variant),
                    "node_shape_variant_probabilities": dict(query.node_shape_variant_probabilities),
                    "node_color_name": str(query.node_color_name),
                    "node_color_name_probabilities": dict(query.node_color_name_probabilities),
                    "label_source_kind": str(sample.label_source_kind),
                    "label_bucket": str(sample.label_bucket),
                    "label_manifest": str(sample.label_manifest),
                    "label_filter": dict(sample.label_filter),
                    "label_bucket_probabilities": dict(sample.label_bucket_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": list(rendered_scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(rendered_scene.panel_geometry),
                "style": {
                    "scene_variant": str(rendered_scene.scene_variant),
                    "scene_title": str(scene_title),
                    "node_color_name": str(query.node_color_name),
                    "theme_tone": str(render_params.theme_tone),
                    "panel_style_variant": str(render_params.panel_style_variant),
                    "background_color_rgb": list(render_params.background_color_rgb),
                    "panel_fill_rgb": list(render_params.panel_fill_rgb),
                    "panel_border_rgb": list(render_params.panel_border_rgb),
                    "title_color_rgb": list(render_params.title_color_rgb),
                    "edge_color_rgb": list(render_params.edge_color_rgb),
                    "node_fill_rgb": list(render_params.node_fill_rgb),
                    "node_border_rgb": list(render_params.node_border_rgb),
                    "label_text_rgb": list(render_params.label_text_rgb),
                    "label_stroke_rgb": list(render_params.label_stroke_rgb),
                    "node_shape_variant": str(render_params.node_shape_variant),
                    "node_radius_px": int(render_params.node_radius_px),
                    "edge_width_px": int(render_params.edge_width_px),
                    "node_border_width_px": int(render_params.node_border_width_px),
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "resolved_label_font_size_px": int(rendered_scene.resolved_label_font_size_px),
                    "label_stroke_width_px": int(rendered_scene.resolved_label_stroke_width_px),
                    "background_meta": dict(background_meta),
                    "post_image_noise_meta": dict(post_noise_meta),
                },
            },
            "render_map": {"image_id": "img0", "anchors": {}},
            "execution_trace": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "query_variant": str(query.query_variant),
                "query_id": str(query.query_variant),
                "operation_kind": str(operation.operation_kind),
                "target_key": int(operation.target_key) if operation.target_key is not None else None,
                "answer": str(operation.answer_label),
                "answer_label": str(operation.answer_label),
                "answer_node_id": str(operation.answer_node_id),
                "evidence_labels": list(operation.evidence_labels),
                "node_count": int(sample.node_count),
                "max_depth": int(sample.max_depth),
                "label_variant": str(sample.label_variant),
            },
            "witness_symbolic": {
                "type": "search_tree_operation_path",
                "query_variant": str(query.query_variant),
                "target_key": int(operation.target_key) if operation.target_key is not None else None,
                "answer_label": str(operation.answer_label),
                "evidence_labels": list(operation.evidence_labels),
            },
            "projected_evidence": {
                "type": "bbox_sequence",
                "bbox_sequence": list(evidence_bboxes),
                "pixel_bbox_sequence": list(evidence_bboxes),
                "pixel_point_sequence": list(evidence_projection["pixel_point_sequence"]),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample=sample, operation=operation, query_variant=str(query.query_variant)),
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(query.query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphRelationSearchTreeOperationLabelTask"]
