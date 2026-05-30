"""Identify node labels in binary-tree structural relations."""

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
from ...shared.config_defaults import (
    group_default,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.binary_tree_scene import (
    SUPPORTED_BINARY_TREE_SCENE_VARIANTS,
    BinaryTreeSample,
    projected_binary_tree_bbox_evidence,
    render_binary_tree_scene,
    sample_binary_tree_for_traversal_query,
)
from ..shared.complexity import (
    build_graph_complexity,
    normalize_int_with_bounds,
    resolve_graph_complexity_weights,
)
from ..shared.graph_scene import SUPPORTED_NODE_SHAPE_VARIANTS
from ..shared.graph_sampling import SUPPORTED_NODE_LINK_LABEL_VARIANTS
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import (
    format_graph_prompt_label,
    resolve_graph_named_variant,
    resolve_graph_render_params,
)
from ..shared.visual_defaults import (
    load_graph_background_defaults,
    load_graph_noise_defaults,
)

TASK_ID = "task_graph__binary_tree__node_relation_label"
SCENE_ID = "binary_tree"

SUPPORTED_BINARY_TREE_RELATION_QUERY_IDS: Tuple[str, ...] = (
    "parent_label",
    "left_child_label",
    "right_child_label",
    "sibling_label",
    "lowest_common_ancestor_label",
)

BINARY_TREE_RELATION_EVIDENCE_ROLES: Dict[str, Tuple[str, ...]] = {
    "parent_label": ("child", "parent"),
    "left_child_label": ("parent", "left_child"),
    "right_child_label": ("parent", "right_child"),
    "sibling_label": ("node", "sibling"),
    "lowest_common_ancestor_label": ("node_a", "node_b", "lowest_common_ancestor"),
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for binary-tree node-label relations."""

    node_count_min: int = 7
    node_count_max: int = 13
    max_depth: int = 4
    label_max_chars: int = 5
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
    label_variant: str = "letters"
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
    """Resolved query and style axes for one binary-tree relation instance."""

    query_id: str
    scene_variant: str
    label_variant: str
    node_shape_variant: str
    node_color_name: str
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RelationSelection:
    """One sampled binary-tree relation query."""

    query_labels: Tuple[str, ...]
    answer_label: str
    evidence_labels: Tuple[str, ...]
    query_node_ids: Tuple[str, ...]
    answer_node_id: str


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = (
    split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=TASK_ID,
    )
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="relation")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(
    task_group="relation", apply_prob=0.5
)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(
    _TASK_GROUP_DEFAULTS, task_id=TASK_ID
)


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    query_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_id")
    query_id, query_probs = resolve_graph_named_variant(
        query_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        supported=SUPPORTED_BINARY_TREE_RELATION_QUERY_IDS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="query_id",
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
    label_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.label_variant")
    label_variant, label_probs = resolve_graph_named_variant(
        label_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="label_variant",
        weights_key="label_variant_weights",
        balance_flag_key="balanced_label_variant_sampling",
        supported=SUPPORTED_NODE_LINK_LABEL_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="label_variant",
    )
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
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        node_color_name=str(node_color_name),
        query_id_probabilities=dict(query_probs),
        scene_variant_probabilities=dict(scene_probs),
        label_variant_probabilities=dict(label_probs),
        node_shape_variant_probabilities=dict(shape_probs),
        node_color_name_probabilities=dict(color_probs),
    )


def _ancestors_including_self(node_id: str) -> Tuple[str, ...]:
    return tuple(str(node_id)[:length] for length in range(len(str(node_id)), -1, -1))


def _lowest_common_ancestor(node_id_a: str, node_id_b: str) -> str:
    ancestors_a = set(_ancestors_including_self(str(node_id_a)))
    for ancestor in _ancestors_including_self(str(node_id_b)):
        if ancestor in ancestors_a:
            return str(ancestor)
    return ""


def _choose_relation(
    *,
    sample: BinaryTreeSample,
    query_id: str,
    instance_seed: int,
    attempt: int,
) -> _RelationSelection:
    node_by_id = {str(node.node_id): node for node in sample.nodes}
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.relation.{query_id}.{attempt}")
    query = str(query_id)

    if query == "parent_label":
        candidates = [node for node in sample.nodes if node.parent_id is not None]
        node = rng.choice(candidates)
        answer = node_by_id[str(node.parent_id)]
        return _RelationSelection(
            query_labels=(str(node.label),),
            answer_label=str(answer.label),
            evidence_labels=(str(node.label), str(answer.label)),
            query_node_ids=(str(node.node_id),),
            answer_node_id=str(answer.node_id),
        )

    if query == "left_child_label":
        candidates = [node for node in sample.nodes if node.left_id is not None]
        if not candidates:
            raise ValueError("no left-child candidates")
        node = rng.choice(candidates)
        answer = node_by_id[str(node.left_id)]
        return _RelationSelection(
            query_labels=(str(node.label),),
            answer_label=str(answer.label),
            evidence_labels=(str(node.label), str(answer.label)),
            query_node_ids=(str(node.node_id),),
            answer_node_id=str(answer.node_id),
        )

    if query == "right_child_label":
        candidates = [node for node in sample.nodes if node.right_id is not None]
        if not candidates:
            raise ValueError("no right-child candidates")
        node = rng.choice(candidates)
        answer = node_by_id[str(node.right_id)]
        return _RelationSelection(
            query_labels=(str(node.label),),
            answer_label=str(answer.label),
            evidence_labels=(str(node.label), str(answer.label)),
            query_node_ids=(str(node.node_id),),
            answer_node_id=str(answer.node_id),
        )

    if query == "sibling_label":
        candidates = []
        for node in sample.nodes:
            if node.parent_id is None:
                continue
            parent = node_by_id[str(node.parent_id)]
            if parent.left_id is not None and parent.right_id is not None:
                sibling_id = (
                    parent.right_id
                    if str(parent.left_id) == str(node.node_id)
                    else parent.left_id
                )
                candidates.append((node, node_by_id[str(sibling_id)]))
        if not candidates:
            raise ValueError("no sibling candidates")
        node, answer = rng.choice(candidates)
        return _RelationSelection(
            query_labels=(str(node.label),),
            answer_label=str(answer.label),
            evidence_labels=(str(node.label), str(answer.label)),
            query_node_ids=(str(node.node_id),),
            answer_node_id=str(answer.node_id),
        )

    candidates_lca = []
    nodes = list(sample.nodes)
    for index_a, node_a in enumerate(nodes):
        for node_b in nodes[index_a + 1 :]:
            lca_id = _lowest_common_ancestor(str(node_a.node_id), str(node_b.node_id))
            if lca_id in (str(node_a.node_id), str(node_b.node_id)):
                continue
            if len(str(node_a.node_id)) <= len(lca_id) or len(
                str(node_b.node_id)
            ) <= len(lca_id):
                continue
            candidates_lca.append((node_a, node_b, node_by_id[str(lca_id)]))
    if not candidates_lca:
        raise ValueError("no lowest-common-ancestor candidates")
    node_a, node_b, answer = rng.choice(candidates_lca)
    return _RelationSelection(
        query_labels=(str(node_a.label), str(node_b.label)),
        answer_label=str(answer.label),
        evidence_labels=(str(node_a.label), str(node_b.label), str(answer.label)),
        query_node_ids=(str(node_a.node_id), str(node_b.node_id)),
        answer_node_id=str(answer.node_id),
    )


def _sample_relation_tree(
    instance_seed: int,
    *,
    query: _ResolvedQuery,
    max_attempts: int,
) -> Tuple[BinaryTreeSample, _RelationSelection]:
    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            sample = sample_binary_tree_for_traversal_query(
                hash64(int(instance_seed), f"{TASK_ID}.tree", int(attempt)),
                node_count_min=int(
                    group_default(
                        _GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min
                    )
                ),
                node_count_max=int(
                    group_default(
                        _GEN_DEFAULTS, "node_count_max", _DEFAULTS.node_count_max
                    )
                ),
                max_depth=int(
                    group_default(_GEN_DEFAULTS, "max_depth", _DEFAULTS.max_depth)
                ),
                label_variant=str(query.label_variant),
                label_max_chars=int(
                    group_default(
                        _GEN_DEFAULTS, "label_max_chars", _DEFAULTS.label_max_chars
                    )
                ),
                max_attempts=max(20, int(max_attempts)),
            )
            relation = _choose_relation(
                sample=sample,
                query_id=str(query.query_id),
                instance_seed=int(instance_seed),
                attempt=int(attempt),
            )
            return sample, relation
        except Exception as exc:
            last_error = exc
    raise ValueError(f"could not sample binary-tree relation instance: {last_error}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    example_boxes = (
        [156, 124, 204, 172],
        [470, 430, 520, 480],
        [250, 250, 298, 298],
    )
    evidence = {
        str(role): list(box)
        for role, box in zip(
            BINARY_TREE_RELATION_EVIDENCE_ROLES[str(query_id)],
            example_boxes,
        )
    }
    return (
        json.dumps(
            {
                "evidence": evidence,
                "answer": "M",
            },
            separators=(",", ":"),
        ),
        json.dumps({"answer": "M"}, separators=(",", ":")),
    )


def _build_complexity(*, sample: BinaryTreeSample, query_id: str) -> Any:
    node_norm = normalize_int_with_bounds(
        int(sample.node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max)
    )
    depth_norm = normalize_int_with_bounds(
        int(sample.max_depth), (2, _DEFAULTS.max_depth)
    )
    relation_load = 1.0 if str(query_id) == "lowest_common_ancestor_label" else 0.55
    return build_graph_complexity(
        weights=_COMPLEXITY_WEIGHTS,
        components={
            "topology_reasoning": (0.50 * relation_load)
            + (0.30 * depth_norm)
            + (0.20 * node_norm),
            "visual_scan": (0.70 * node_norm) + (0.30 * depth_norm),
            "ambiguity": (
                0.62 if str(query_id) == "lowest_common_ancestor_label" else 0.38
            ),
            "clutter": (0.65 * node_norm) + (0.35 * depth_norm),
        },
    )


@register_task
class GraphRelationBinaryTreeNodeLabelTask:
    """Return labels for parent, child, sibling, and LCA binary-tree relations."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "relation"

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
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
        sample, relation = _sample_relation_tree(
            int(instance_seed),
            query=query,
            max_attempts=max(1, int(max_attempts)),
        )
        rendered_scene = render_binary_tree_scene(
            sample=sample,
            render_params=render_params,
            scene_variant=str(query.scene_variant),
            scene_title="Binary Tree",
            base_image=image,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        evidence_roles = BINARY_TREE_RELATION_EVIDENCE_ROLES[str(query.query_id)]
        evidence_projection = projected_binary_tree_bbox_evidence(
            rendered_scene, relation.evidence_labels
        )
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        if len(evidence_roles) != len(evidence_bboxes):
            raise ValueError(
                "binary-tree relation evidence role count does not match projected evidence"
            )
        evidence_keyed_bboxes = {
            str(role): list(bbox) for role, bbox in zip(evidence_roles, evidence_bboxes)
        }
        evidence_keyed_points = {
            str(role): list(point)
            for role, point in zip(
                evidence_roles, evidence_projection["pixel_point_set"]
            )
        }
        evidence_role_to_label = {
            str(role): str(label)
            for role, label in zip(evidence_roles, relation.evidence_labels)
        }
        evidence_roles_by_label: Dict[str, List[str]] = {}
        for role, label in evidence_role_to_label.items():
            evidence_roles_by_label.setdefault(str(label), []).append(str(role))
        answer_gt = TypedValue(type="string", value=str(relation.answer_label))
        evidence_gt = TypedValue(
            type="keyed_bbox_map", value=dict(evidence_keyed_bboxes)
        )

        prompt_defaults = dict(_PROMPT_DEFAULTS)
        json_example, json_example_answer_only = _build_prompt_json_examples(
            str(query.query_id)
        )
        prompt_query_labels = tuple(
            format_graph_prompt_label(
                str(label), label_variant=str(query.label_variant)
            )
            for label in relation.query_labels
        )
        slots = {
            "object_description": str(prompt_defaults["object_description"]),
            "query_label": str(prompt_query_labels[0]),
            "query_label_a": str(prompt_query_labels[0]),
            "query_label_b": (
                str(prompt_query_labels[1]) if len(prompt_query_labels) > 1 else ""
            ),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(
                prompt_defaults["json_output_contract_answer_only"]
            ),
            "evidence_hint": str(prompt_defaults[f"evidence_hint_{query.query_id}"]),
            "answer_hint": str(prompt_defaults["answer_hint"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        node_by_id = {str(node.node_id): node for node in sample.nodes}
        rendered_by_label = {str(node.label): node for node in rendered_scene.nodes}
        node_entities = []
        for node in rendered_scene.nodes:
            sample_node = next(
                tree_node
                for tree_node in sample.nodes
                if str(tree_node.label) == str(node.label)
            )
            node_entities.append(
                {
                    "entity_id": f"node_{node.label}",
                    "entity_kind": "binary_tree_node",
                    "label": str(node.label),
                    "parent_label": node.parent_label,
                    "left_label": node.left_label,
                    "right_label": node.right_label,
                    "depth": int(node.depth),
                    "center_px": list(node.center_xy),
                    "bbox_xyxy": list(node.bbox_xyxy),
                    "is_query_node": bool(
                        str(sample_node.node_id) in set(relation.query_node_ids)
                    ),
                    "is_answer_node": bool(
                        str(sample_node.node_id) == str(relation.answer_node_id)
                    ),
                    "is_evidence_node": bool(
                        str(node.label) in set(relation.evidence_labels)
                    ),
                    "evidence_roles": list(
                        evidence_roles_by_label.get(str(node.label), [])
                    ),
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
                "scene_kind": "binary_tree",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "root_label": str(node_by_id[""].label),
                    "query_id": str(query.query_id),
                    "query_labels": list(relation.query_labels),
                    "answer_label": str(relation.answer_label),
                    "answer_node_id": str(relation.answer_node_id),
                    "evidence_role_to_label": dict(evidence_role_to_label),
                    "preorder_labels": list(sample.preorder_labels),
                    "inorder_labels": list(sample.inorder_labels),
                    "postorder_labels": list(sample.postorder_labels),
                    "level_order_labels": list(sample.level_order_labels),
                },
                "frames": {
                    "pixel": {
                        "origin": [0.0, 0.0],
                        "x_positive": "right",
                        "y_positive": "down",
                    },
                    "panels": dict(rendered_scene.panel_geometry),
                },
            },
            "query_spec": {
                "task_id": TASK_ID,
                "query_id": str(query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(
                    prompt_artifacts.prompt_variant_active_key
                ),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(query.scene_variant),
                    "query_id_probabilities": dict(query.query_id_probabilities),
                    "scene_variant_probabilities": dict(
                        query.scene_variant_probabilities
                    ),
                    "node_count": int(sample.node_count),
                    "node_count_probabilities": dict(
                        uniform_probability_map(
                            tuple(
                                range(
                                    _DEFAULTS.node_count_min,
                                    _DEFAULTS.node_count_max + 1,
                                )
                            )
                        )
                    ),
                    "max_depth": int(sample.max_depth),
                    "label_variant": str(query.label_variant),
                    "label_variant_probabilities": dict(
                        query.label_variant_probabilities
                    ),
                    "node_shape_variant": str(query.node_shape_variant),
                    "node_shape_variant_probabilities": dict(
                        query.node_shape_variant_probabilities
                    ),
                    "node_color_name": str(query.node_color_name),
                    "node_color_name_probabilities": dict(
                        query.node_color_name_probabilities
                    ),
                    "label_source_kind": str(sample.label_source_kind),
                    "label_bucket": str(sample.label_bucket),
                    "label_manifest": str(sample.label_manifest),
                    "label_filter": dict(sample.label_filter),
                    "label_bucket_probabilities": dict(
                        sample.label_bucket_probabilities
                    ),
                },
            },
            "render_spec": {
                "canvas_size": list(rendered_scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(rendered_scene.panel_geometry),
                "style": {
                    "scene_variant": str(rendered_scene.scene_variant),
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
                    "resolved_label_font_size_px": int(
                        rendered_scene.resolved_label_font_size_px
                    ),
                    "label_stroke_width_px": int(
                        rendered_scene.resolved_label_stroke_width_px
                    ),
                    "background_meta": dict(background_meta),
                    "post_image_noise_meta": dict(post_noise_meta),
                },
            },
            "render_map": {"image_id": "img0", "anchors": {}},
            "execution_trace": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "query_id": str(query.query_id),
                "query_labels": list(relation.query_labels),
                "answer": str(relation.answer_label),
                "answer_label": str(relation.answer_label),
                "answer_node_id": str(relation.answer_node_id),
                "evidence_roles": list(evidence_roles),
                "evidence_role_to_label": dict(evidence_role_to_label),
                "evidence_labels": list(relation.evidence_labels),
                "node_count": int(sample.node_count),
                "max_depth": int(sample.max_depth),
                "label_variant": str(sample.label_variant),
            },
            "witness_symbolic": {
                "type": "binary_tree_node_label_relation",
                "query_id": str(query.query_id),
                "query_labels": list(relation.query_labels),
                "answer_label": str(relation.answer_label),
                "evidence_role_to_label": dict(evidence_role_to_label),
            },
            "projected_evidence": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(evidence_keyed_bboxes),
                "pixel_keyed_bbox_map": dict(evidence_keyed_bboxes),
                "keyed_point_map": dict(evidence_keyed_points),
                "pixel_keyed_point_map": dict(evidence_keyed_points),
                "bbox_sequence": list(evidence_bboxes),
                "pixel_bbox_sequence": list(evidence_bboxes),
                "pixel_point_sequence": list(evidence_projection["pixel_point_set"]),
            },
        }
        if str(relation.answer_label) not in rendered_by_label:
            raise ValueError("answer node was not rendered")
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample=sample, query_id=str(query.query_id)),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphRelationBinaryTreeNodeLabelTask"]
