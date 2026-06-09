"""Return the label at a position in a binary-tree traversal order."""

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
    SUPPORTED_BINARY_TREE_SCENE_VARIANTS,
    SUPPORTED_BINARY_TREE_TRAVERSAL_QUERY_IDS,
    projected_binary_tree_bbox_annotation,
    render_binary_tree_scene,
    sample_binary_tree_for_traversal_query,
    traversal_labels_for_query,
)
from ..shared.complexity import (
    build_graph_complexity,
    normalize_int_with_bounds,
    resolve_graph_complexity_weights,
)
from ..shared.graph_scene import SUPPORTED_NODE_SHAPE_VARIANTS
from ..shared.graph_sampling import SUPPORTED_NODE_LINK_LABEL_VARIANTS
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import resolve_graph_named_variant, resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__binary_tree__traversal_kth_label"
SCENE_ID = "binary_tree"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for binary-tree traversal-order tasks."""

    node_count_min: int = 7
    node_count_max: int = 13
    traversal_position_min: int = 2
    traversal_position_max: int = 10
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
    """Resolved query and style axes for one binary-tree traversal instance."""

    query_id: str
    scene_variant: str
    traversal_position: int
    label_variant: str
    node_shape_variant: str
    node_color_name: str
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    traversal_position_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "order")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="order")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="order", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    variant_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_id")
    query_id, query_probs = resolve_graph_named_variant(
        variant_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        supported=SUPPORTED_BINARY_TREE_TRAVERSAL_QUERY_IDS,
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
    lower = int(group_default(_GEN_DEFAULTS, "traversal_position_min", _DEFAULTS.traversal_position_min))
    upper = int(group_default(_GEN_DEFAULTS, "traversal_position_max", _DEFAULTS.traversal_position_max))
    support = tuple(range(int(lower), int(upper) + 1))
    explicit_position = params.get("traversal_position")
    if explicit_position is not None:
        traversal_position = int(explicit_position)
        if int(traversal_position) not in set(support):
            raise ValueError("traversal_position is outside configured support")
    else:
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:traversal_position",
        )
        traversal_position = int(support[int(selection_index % len(support))])
    return _ResolvedQuery(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        traversal_position=int(traversal_position),
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        node_color_name=str(node_color_name),
        query_id_probabilities=dict(query_probs),
        scene_variant_probabilities=dict(scene_probs),
        traversal_position_probabilities=uniform_probability_map(support, selected=int(traversal_position) if explicit_position is not None else None),
        label_variant_probabilities=dict(label_probs),
        node_shape_variant_probabilities=dict(shape_probs),
        node_color_name_probabilities=dict(color_probs),
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    return (
        json.dumps(
            {
                "annotation": [[156, 124, 204, 172], [250, 250, 298, 298], [470, 430, 520, 480]],
                "answer": "M",
            },
            separators=(",", ":"),
        ),
        json.dumps({"answer": "M"}, separators=(",", ":")),
    )


def _build_complexity(*, sample, traversal_position: int) -> Any:
    node_norm = normalize_int_with_bounds(int(sample.node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max))
    depth_norm = normalize_int_with_bounds(int(sample.max_depth), (2, _DEFAULTS.max_depth))
    position_norm = normalize_int_with_bounds(int(traversal_position), (_DEFAULTS.traversal_position_min, _DEFAULTS.traversal_position_max))
    return build_graph_complexity(
        weights=_COMPLEXITY_WEIGHTS,
        components={
            "topology_reasoning": (0.45 * position_norm) + (0.35 * depth_norm) + (0.20 * node_norm),
            "visual_scan": (0.70 * node_norm) + (0.30 * depth_norm),
            "ambiguity": (0.60 * position_norm) + (0.40 * depth_norm),
            "clutter": (0.65 * node_norm) + (0.35 * depth_norm),
        },
    )


@register_task
class GraphOrderBinaryTreeTraversalLabelTask:
    """Return the node label at a requested position in a binary-tree traversal."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "order"

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
        node_count_min = max(
            int(group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min)),
            int(query.traversal_position),
        )
        sample = sample_binary_tree_for_traversal_query(
            int(instance_seed),
            node_count_min=int(node_count_min),
            node_count_max=int(group_default(_GEN_DEFAULTS, "node_count_max", _DEFAULTS.node_count_max)),
            max_depth=int(group_default(_GEN_DEFAULTS, "max_depth", _DEFAULTS.max_depth)),
            label_variant=str(query.label_variant),
            label_max_chars=int(group_default(_GEN_DEFAULTS, "label_max_chars", _DEFAULTS.label_max_chars)),
            max_attempts=max(1, int(max_attempts)),
        )
        traversal_labels = traversal_labels_for_query(sample, str(query.query_id))
        if int(query.traversal_position) > len(traversal_labels):
            raise ValueError("sampled binary tree is smaller than requested traversal position")
        answer_value = str(traversal_labels[int(query.traversal_position) - 1])
        annotation_labels = tuple(str(label) for label in traversal_labels[: int(query.traversal_position)])

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
        annotation_projection = projected_binary_tree_bbox_annotation(rendered_scene, annotation_labels)
        annotation_bboxes = [[round(float(value), 3) for value in bbox] for bbox in annotation_projection["bbox_sequence"]]
        answer_gt = TypedValue(type="string", value=str(answer_value))
        annotation_gt = TypedValue(type="bbox_sequence", value=list(annotation_bboxes))

        prompt_defaults = dict(_PROMPT_DEFAULTS)
        json_example, json_example_answer_only = _build_prompt_json_examples()
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
                "traversal_position": str(query.traversal_position),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[annotation_hint_key]),
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
                    "is_answer_node": bool(str(node.label) == str(answer_value)),
                    "is_in_annotation_prefix": bool(str(node.label) in set(annotation_labels)),
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
                    "traversal_position": int(query.traversal_position),
                    "answer_label": str(answer_value),
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
                    "traversal_position": int(query.traversal_position),
                    "traversal_position_probabilities": dict(query.traversal_position_probabilities),
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
                "answer": str(answer_value),
                "annotation_labels": list(annotation_labels),
                "traversal_position": int(query.traversal_position),
                "node_count": int(sample.node_count),
                "max_depth": int(sample.max_depth),
                "label_variant": str(sample.label_variant),
            },
            "witness_symbolic": {
                "type": "node_label_sequence",
                "labels": list(annotation_labels),
                "query_id": str(query.query_id),
                "answer_label": str(answer_value),
            },
            "projected_annotation": {
                "type": "bbox_sequence",
                "bbox_sequence": list(annotation_bboxes),
                "pixel_bbox_sequence": list(annotation_bboxes),
                "pixel_point_sequence": list(annotation_projection["pixel_point_sequence"]),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample=sample, traversal_position=int(query.traversal_position)),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphOrderBinaryTreeTraversalLabelTask"]
