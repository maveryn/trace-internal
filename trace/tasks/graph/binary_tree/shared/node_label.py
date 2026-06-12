"""Identify node labels in binary-tree structural relations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import hash64, spawn_rng
from .....core.scene_config import get_scene_defaults
from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.config_defaults import (
    group_default,
    split_scene_generation_rendering_prompt_defaults,
)
from ....shared.deterministic_sampling import uniform_probability_map
from .scene import (
    SUPPORTED_BINARY_TREE_SCENE_VARIANTS,
    BinaryTreeSample,
    projected_binary_tree_bbox_annotation,
    render_binary_tree_scene,
    sample_binary_tree_for_traversal_query,
)
from ...shared.graph_scene import SUPPORTED_NODE_SHAPE_VARIANTS
from ...shared.graph_sample_types import SUPPORTED_NODE_LINK_LABEL_VARIANTS
from ...shared.style import SUPPORTED_NODE_COLOR_NAMES
from ...shared.task_support import (
    format_graph_prompt_label,
    resolve_graph_named_variant,
    resolve_graph_render_params,
)
from ...shared.visual_defaults import (
    load_graph_scene_background_defaults,
    load_graph_scene_noise_defaults,
)

TASK_ID = "graph_binary_tree_node_relation_label_source"
SCENE_ID = "binary_tree"

SUPPORTED_BINARY_TREE_RELATION_QUERY_IDS: Tuple[str, ...] = (
    "parent_label",
    "left_child_label",
    "right_child_label",
    "sibling_label",
    "lowest_common_ancestor_label",
)
LOCAL_RELATIVE_NODE_QUERY_IDS: Tuple[str, ...] = (
    "parent_label",
    "left_child_label",
    "right_child_label",
    "sibling_label",
)

BINARY_TREE_RELATION_ANNOTATION_ROLES: Dict[str, Tuple[str, ...]] = {
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
    annotation_labels: Tuple[str, ...]
    query_node_ids: Tuple[str, ...]
    answer_node_id: str


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("graph", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = (
    split_scene_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=TASK_ID,
    )
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_graph_scene_noise_defaults(
    scene_id=SCENE_ID, apply_prob=0.5
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
            annotation_labels=(str(node.label), str(answer.label)),
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
            annotation_labels=(str(node.label), str(answer.label)),
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
            annotation_labels=(str(node.label), str(answer.label)),
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
            annotation_labels=(str(node.label), str(answer.label)),
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
        annotation_labels=(str(node_a.label), str(node_b.label), str(answer.label)),
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
    annotation = {
        str(role): list(box)
        for role, box in zip(
            BINARY_TREE_RELATION_ANNOTATION_ROLES[str(query_id)],
            example_boxes,
        )
    }
    return (
        json.dumps(
            {
                "annotation": annotation,
                "answer": "M",
            },
            separators=(",", ":"),
        ),
        json.dumps({"answer": "M"}, separators=(",", ":")),
    )




@dataclass(frozen=True)
class RelationRenderBundle:
    """Rendered binary-tree relation instance before public output binding."""

    query: _ResolvedQuery
    render_params: Any
    sample: BinaryTreeSample
    relation: _RelationSelection
    rendered_scene: Any
    image: Any
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    annotation_roles: Tuple[str, ...]
    annotation_keyed_bboxes: Dict[str, list[float]]
    annotation_keyed_points: Dict[str, list[float]]
    annotation_role_to_label: Dict[str, str]
    annotation_roles_by_label: Dict[str, list[str]]
    annotation_projection: Dict[str, Any]
    annotation_bboxes: list[list[float]]


def build_relation_render_bundle(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> RelationRenderBundle:
    """Sample and render one binary-tree node-label relation instance."""

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
        layout_seed=int(instance_seed),
        base_image=image,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_roles = BINARY_TREE_RELATION_ANNOTATION_ROLES[str(query.query_id)]
    annotation_projection = projected_binary_tree_bbox_annotation(rendered_scene, relation.annotation_labels)
    annotation_bboxes = [[round(float(value), 3) for value in bbox] for bbox in annotation_projection["bbox_set"]]
    if len(annotation_roles) != len(annotation_bboxes):
        raise ValueError("binary-tree relation annotation role count does not match projected annotation")
    annotation_keyed_bboxes = {str(role): list(bbox) for role, bbox in zip(annotation_roles, annotation_bboxes)}
    annotation_keyed_points = {
        str(role): list(point)
        for role, point in zip(annotation_roles, annotation_projection["pixel_point_set"])
    }
    annotation_role_to_label = {
        str(role): str(label) for role, label in zip(annotation_roles, relation.annotation_labels)
    }
    annotation_roles_by_label: Dict[str, List[str]] = {}
    for role, label in annotation_role_to_label.items():
        annotation_roles_by_label.setdefault(str(label), []).append(str(role))
    rendered_by_label = {str(node.label): node for node in rendered_scene.nodes}
    if str(relation.answer_label) not in rendered_by_label:
        raise ValueError("answer node was not rendered")
    return RelationRenderBundle(
        query=query,
        render_params=render_params,
        sample=sample,
        relation=relation,
        rendered_scene=rendered_scene,
        image=image,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        annotation_roles=tuple(str(role) for role in annotation_roles),
        annotation_keyed_bboxes={str(key): list(value) for key, value in annotation_keyed_bboxes.items()},
        annotation_keyed_points={str(key): list(value) for key, value in annotation_keyed_points.items()},
        annotation_role_to_label=dict(annotation_role_to_label),
        annotation_roles_by_label={str(key): list(value) for key, value in annotation_roles_by_label.items()},
        annotation_projection=dict(annotation_projection),
        annotation_bboxes=list(annotation_bboxes),
    )


def build_relation_trace_payload(
    *,
    bundle: RelationRenderBundle,
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts: Any,
    trace_task_id: str,
) -> Dict[str, Any]:
    """Build trace metadata for one binary-tree relation-label instance."""

    query = bundle.query
    render_params = bundle.render_params
    sample = bundle.sample
    relation = bundle.relation
    rendered_scene = bundle.rendered_scene
    node_by_id = {str(node.node_id): node for node in sample.nodes}
    node_entities = []
    for node in rendered_scene.nodes:
        sample_node = next(tree_node for tree_node in sample.nodes if str(tree_node.label) == str(node.label))
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
                "is_query_node": bool(str(sample_node.node_id) in set(relation.query_node_ids)),
                "is_answer_node": bool(str(sample_node.node_id) == str(relation.answer_node_id)),
                "is_annotation_node": bool(str(node.label) in set(relation.annotation_labels)),
                "annotation_roles": list(bundle.annotation_roles_by_label.get(str(node.label), [])),
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
            "connector_path_px": [list(point) for point in edge.connector_path_px],
            "connector_style_variant": str(edge.connector_style_variant),
        }
        for edge in rendered_scene.edges
    ]
    return {
        "scene_ir": {
            "task_id": str(trace_task_id),
            "scene_id": SCENE_ID,
            "scene_kind": "binary_tree",
            "entities": [*node_entities, *edge_entities],
            "relations": {
                "root_label": str(node_by_id[""].label),
                "query_id": str(query.query_id),
                "query_labels": list(relation.query_labels),
                "answer_label": str(relation.answer_label),
                "answer_node_id": str(relation.answer_node_id),
                "annotation_role_to_label": dict(bundle.annotation_role_to_label),
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
            "task_id": str(trace_task_id),
            "query_id": str(query.query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "query_id": str(query.query_id),
                "scene_variant": str(query.scene_variant),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                "node_count": int(sample.node_count),
                "node_count_probabilities": dict(uniform_probability_map(tuple(range(_DEFAULTS.node_count_min, _DEFAULTS.node_count_max + 1)))),
                "max_depth": int(sample.max_depth),
                "label_variant": str(query.label_variant),
                "label_variant_probabilities": dict(query.label_variant_probabilities),
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
                "connector_style_variant": str(rendered_scene.connector_style_variant),
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
                "background_meta": dict(bundle.background_meta),
                "post_image_noise_meta": dict(bundle.post_noise_meta),
            },
        },
        "render_map": {"image_id": "img0", "anchors": {}},
        "execution_trace": {
            "task_id": str(trace_task_id),
            "scene_id": SCENE_ID,
            "query_id": str(query.query_id),
            "query_labels": list(relation.query_labels),
            "answer": str(relation.answer_label),
            "answer_label": str(relation.answer_label),
            "answer_node_id": str(relation.answer_node_id),
            "annotation_roles": list(bundle.annotation_roles),
            "annotation_role_to_label": dict(bundle.annotation_role_to_label),
            "annotation_labels": list(relation.annotation_labels),
            "node_count": int(sample.node_count),
            "max_depth": int(sample.max_depth),
            "label_variant": str(sample.label_variant),
        },
        "witness_symbolic": {
            "type": "binary_tree_node_label_relation",
            "query_id": str(query.query_id),
            "query_labels": list(relation.query_labels),
            "answer_label": str(relation.answer_label),
            "annotation_role_to_label": dict(bundle.annotation_role_to_label),
        },
        "projected_annotation": {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(bundle.annotation_keyed_bboxes),
            "pixel_keyed_bbox_map": dict(bundle.annotation_keyed_bboxes),
            "keyed_point_map": dict(bundle.annotation_keyed_points),
            "pixel_keyed_point_map": dict(bundle.annotation_keyed_points),
            "bbox_sequence": list(bundle.annotation_bboxes),
            "pixel_bbox_sequence": list(bundle.annotation_bboxes),
            "pixel_point_sequence": list(bundle.annotation_projection["pixel_point_set"]),
        },
    }


__all__ = [
    "BINARY_TREE_RELATION_ANNOTATION_ROLES",
    "LOCAL_RELATIVE_NODE_QUERY_IDS",
    "RelationRenderBundle",
    "build_relation_render_bundle",
    "build_relation_trace_payload",
]
