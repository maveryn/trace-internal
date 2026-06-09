"""Count nodes satisfying binary-tree structural predicates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
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
    SUPPORTED_BINARY_TREE_COUNT_QUERY_IDS,
    SUPPORTED_BINARY_TREE_SCENE_VARIANTS,
    projected_binary_tree_bbox_annotation,
    render_binary_tree_scene,
    sample_binary_tree_for_count_query,
    target_labels_for_count_query,
)
from ..shared.complexity import (
    build_graph_complexity,
    normalize_int_with_bounds,
    resolve_graph_complexity_weights,
)
from ..shared.fixed_query_task import FixedGraphQueryTaskMixin, MergedGraphQueryTaskMixin
from ..shared.graph_scene import SUPPORTED_NODE_SHAPE_VARIANTS
from ..shared.graph_sampling import SUPPORTED_NODE_LINK_LABEL_VARIANTS
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import resolve_graph_named_variant, resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "graph_binary_tree_node_property_count_source"
SCENE_ID = "binary_tree"
BINARY_TREE_CHILD_STRUCTURE_NODE_COUNT_TASK_ID = "task_graph__binary_tree__child_structure_node_count"
BINARY_TREE_DEPTH_LEVEL_NODE_COUNT_TASK_ID = "task_graph__binary_tree__depth_level_node_count"
CHILD_STRUCTURE_QUERY_IDS: Tuple[str, ...] = (
    "internal_node_count",
    "leaf_node_count",
    "single_child_node_count",
    "two_child_node_count",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for binary-tree node counting."""

    node_count_min: int = 7
    node_count_max: int = 13
    target_count_min: int = 1
    target_count_max: int = 6
    internal_count_min: int = 3
    internal_count_max: int = 7
    depth_min: int = 1
    depth_max: int = 4
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
    """Resolved query and style axes for one binary-tree count instance."""

    query_id: str
    scene_variant: str
    target_count: int
    target_depth: int | None
    label_variant: str
    node_shape_variant: str
    node_color_name: str
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    target_depth_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="counting")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="counting", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _support_for_query(query_id: str) -> Tuple[int, ...]:
    lower = int(group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min))
    upper = int(group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max))
    node_count_min = int(group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min))
    node_count_max = int(group_default(_GEN_DEFAULTS, "node_count_max", _DEFAULTS.node_count_max))
    if str(query_id) == "leaf_node_count":
        return tuple(range(max(2, lower), int(upper) + 1))
    if str(query_id) == "two_child_node_count":
        return tuple(range(max(1, lower), int(upper) + 1))
    if str(query_id) == "internal_node_count":
        internal_min = int(group_default(_GEN_DEFAULTS, "internal_count_min", _DEFAULTS.internal_count_min))
        internal_max = int(group_default(_GEN_DEFAULTS, "internal_count_max", _DEFAULTS.internal_count_max))
        return tuple(
            internal_count
            for internal_count in range(int(internal_min), int(internal_max) + 1)
            if any(
                int(node_count_min) <= (int(internal_count) + int(two_child_count) + 1) <= int(node_count_max)
                for two_child_count in range(1, int(internal_count) + 1)
            )
        )
    return tuple(range(max(1, lower), int(upper) + 1))


def _depth_support_for_target(target_count: int) -> Tuple[int, ...]:
    lower = int(group_default(_GEN_DEFAULTS, "depth_min", _DEFAULTS.depth_min))
    upper = int(group_default(_GEN_DEFAULTS, "depth_max", _DEFAULTS.depth_max))
    return tuple(depth for depth in range(int(lower), int(upper) + 1) if int(target_count) <= (2 ** int(depth)))


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    variant_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_id")
    query_id, query_probs = resolve_graph_named_variant(
        variant_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        supported=SUPPORTED_BINARY_TREE_COUNT_QUERY_IDS,
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

    target_support = _support_for_query(str(query_id))
    explicit_target = params.get("target_count")
    if explicit_target is not None:
        target_count = int(explicit_target)
        if int(target_count) not in set(target_support):
            raise ValueError("target_count is outside support for the binary-tree count query")
    else:
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:target_count",
        )
        target_count = int(target_support[int(selection_index % len(target_support))])

    target_depth = None
    depth_probs: Dict[str, float] = {}
    if str(query_id) == "depth_level_node_count":
        depth_support = _depth_support_for_target(int(target_count))
        explicit_depth = params.get("target_depth")
        if explicit_depth is not None:
            target_depth = int(explicit_depth)
            if int(target_depth) not in set(depth_support):
                raise ValueError("target_depth is infeasible for the requested depth-level count")
        else:
            depth_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}:target_depth",
            )
            target_depth = int(depth_support[int(depth_index % len(depth_support))])
        depth_probs = uniform_probability_map(depth_support, selected=int(target_depth) if explicit_depth is not None else None)

    return _ResolvedQuery(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        target_count=int(target_count),
        target_depth=int(target_depth) if target_depth is not None else None,
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        node_color_name=str(node_color_name),
        query_id_probabilities=dict(query_probs),
        scene_variant_probabilities=dict(scene_probs),
        target_count_probabilities=uniform_probability_map(target_support, selected=int(target_count) if explicit_target is not None else None),
        target_depth_probabilities=dict(depth_probs),
        label_variant_probabilities=dict(label_probs),
        node_shape_variant_probabilities=dict(shape_probs),
        node_color_name_probabilities=dict(color_probs),
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    return (
        json.dumps({"annotation": [[156, 124, 204, 172], [470, 430, 520, 480]], "answer": 2}, separators=(",", ":")),
        json.dumps({"answer": 2}, separators=(",", ":")),
    )


def _build_complexity(*, sample, query: _ResolvedQuery) -> Any:
    answer_norm = normalize_int_with_bounds(int(query.target_count), (_DEFAULTS.target_count_min, _DEFAULTS.internal_count_max))
    depth_norm = normalize_int_with_bounds(int(sample.max_depth), (2, _DEFAULTS.max_depth))
    node_norm = normalize_int_with_bounds(int(sample.node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max))
    return build_graph_complexity(
        weights=_COMPLEXITY_WEIGHTS,
        components={
            "topology_reasoning": (0.45 * answer_norm) + (0.35 * depth_norm) + (0.20 * node_norm),
            "visual_scan": (0.70 * node_norm) + (0.30 * depth_norm),
            "ambiguity": 0.45 if str(query.query_id) == "depth_level_node_count" else 0.32,
            "clutter": (0.65 * node_norm) + (0.35 * depth_norm),
        },
    )


class GraphCountingBinaryTreeNodeCountTask:
    """Count binary-tree nodes satisfying a structural predicate."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "counting"

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
        sample = sample_binary_tree_for_count_query(
            int(instance_seed),
            query_id=str(query.query_id),
            target_count=int(query.target_count),
            target_depth=query.target_depth,
            node_count_min=int(group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min)),
            node_count_max=int(group_default(_GEN_DEFAULTS, "node_count_max", _DEFAULTS.node_count_max)),
            max_depth=int(group_default(_GEN_DEFAULTS, "max_depth", _DEFAULTS.max_depth)),
            label_variant=str(query.label_variant),
            label_max_chars=int(group_default(_GEN_DEFAULTS, "label_max_chars", _DEFAULTS.label_max_chars)),
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
        target_labels = target_labels_for_count_query(
            sample,
            query_id=str(query.query_id),
            target_depth=query.target_depth,
        )
        if len(target_labels) != int(query.target_count):
            raise ValueError("binary-tree count sample does not match requested target count")
        annotation_projection = projected_binary_tree_bbox_annotation(rendered_scene, target_labels)
        annotation_bboxes = [[round(float(value), 3) for value in bbox] for bbox in annotation_projection["bbox_set"]]
        answer_gt = TypedValue(type="integer", value=int(len(target_labels)))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        prompt_defaults = dict(_PROMPT_DEFAULTS)
        json_example, json_example_answer_only = _build_prompt_json_examples()
        depth_text = str(query.target_depth) if query.target_depth is not None else ""
        annotation_hint_key = f"annotation_hint_{query.query_id}"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_depth": depth_text,
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[annotation_hint_key]).format(target_depth=depth_text),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        rendered_node_by_label = {str(node.label): node for node in rendered_scene.nodes}
        node_entities = []
        for node in rendered_scene.nodes:
            child_count = int(node.left_label is not None) + int(node.right_label is not None)
            node_entities.append(
                {
                    "entity_id": f"node_{node.label}",
                    "entity_kind": "binary_tree_node",
                    "label": str(node.label),
                    "parent_label": node.parent_label,
                    "left_label": node.left_label,
                    "right_label": node.right_label,
                    "depth": int(node.depth),
                    "child_count": int(child_count),
                    "center_px": list(node.center_xy),
                    "bbox_xyxy": list(node.bbox_xyxy),
                    "is_counted": bool(str(node.label) in set(target_labels)),
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

        trace_payload = {
            "scene_ir": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "scene_kind": "binary_tree",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "root_label": str(rendered_node_by_label[sample.nodes[0].label].label),
                    "query_id": str(query.query_id),
                    "target_labels": list(target_labels),
                    "target_depth": int(query.target_depth) if query.target_depth is not None else None,
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
                "query_id": str(query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(query.scene_variant),
                    "query_id_probabilities": dict(query.query_id_probabilities),
                    "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                    "target_count": int(query.target_count),
                    "target_count_probabilities": dict(query.target_count_probabilities),
                    "target_depth": int(query.target_depth) if query.target_depth is not None else None,
                    "target_depth_probabilities": dict(query.target_depth_probabilities),
                    "node_count": int(sample.node_count),
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
                    "background_meta": dict(background_meta),
                    "post_image_noise_meta": dict(post_noise_meta),
                },
            },
            "render_map": {"image_id": "img0", "anchors": {}},
            "execution_trace": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "query_id": str(query.query_id),
                "scene_variant": str(query.scene_variant),
                "connector_style_variant": str(rendered_scene.connector_style_variant),
                "answer": int(len(target_labels)),
                "target_labels": list(target_labels),
                "target_depth": int(query.target_depth) if query.target_depth is not None else None,
                "node_count": int(sample.node_count),
                "max_depth": int(sample.max_depth),
                "label_variant": str(sample.label_variant),
            },
            "witness_symbolic": {
                "type": "node_label_set",
                "labels": list(target_labels),
                "query_id": str(query.query_id),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": list(annotation_bboxes),
                "pixel_bbox_set": list(annotation_bboxes),
                "pixel_point_set": list(annotation_projection["pixel_point_set"]),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample=sample, query=query),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GraphCountingBinaryTreeChildStructureNodeCountTask(MergedGraphQueryTaskMixin):
    """Count binary-tree nodes matching a child-structure predicate."""

    task_id = BINARY_TREE_CHILD_STRUCTURE_NODE_COUNT_TASK_ID
    domain = "graph"
    task_group = "counting"
    source_task_cls = GraphCountingBinaryTreeNodeCountTask
    supported_query_ids = CHILD_STRUCTURE_QUERY_IDS


@register_task
class GraphCountingBinaryTreeDepthLevelNodeCountTask(FixedGraphQueryTaskMixin):
    """Count binary-tree nodes at one depth level."""

    task_id = BINARY_TREE_DEPTH_LEVEL_NODE_COUNT_TASK_ID
    domain = "graph"
    task_group = "counting"
    fixed_query_id = "depth_level_node_count"
    source_task_cls = GraphCountingBinaryTreeNodeCountTask


__all__ = [
    "GraphCountingBinaryTreeChildStructureNodeCountTask",
    "GraphCountingBinaryTreeDepthLevelNodeCountTask",
]
