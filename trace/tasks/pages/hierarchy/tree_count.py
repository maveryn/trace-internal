"""Diagrams hierarchy task that returns rooted-tree integer counts."""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Tuple

from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.diagram.common import projected_diagram_bbox_evidence
from ..shared.diagram.complexity import (
    build_diagrams_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_diagrams_complexity_weights,
)
from ..shared.diagram.hierarchy_common import (
    HierarchyDefaults,
    SUPPORTED_DIAGRAM_HIERARCHY_TREE_COUNT_SCENE_VARIANTS,
    SUPPORTED_DIAGRAM_HIERARCHY_TREE_COUNT_QUERY_IDS,
    build_hierarchy_tree_count_dataset,
    resolve_hierarchy_render_params,
    resolve_hierarchy_tree_count_scene_variant,
    resolve_hierarchy_tree_count_query_id,
)
from ..shared.diagram.hierarchy_scene import render_hierarchy_scene
from ..shared.diagram.visual_defaults import load_diagrams_background_defaults, load_diagrams_noise_defaults
from ..shared.public_query_task import rewrite_pages_query_output


TASK_ID = "task_pages__hierarchy__tree_count"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = SUPPORTED_DIAGRAM_HIERARCHY_TREE_COUNT_QUERY_IDS
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_DIAGRAM_HIERARCHY_TREE_COUNT_SCENE_VARIANTS
_REASONING_LOAD_BASE_BY_VARIANT = {
    "subtree_descendant_count": 0.58,
    "subtree_leaf_count": 0.64,
    "path_length_between_two_nodes": 0.62,
}
_SCENE_LOAD_BY_VARIANT = {"rooted_tree": 0.16}

_DEFAULTS = HierarchyDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "hierarchy")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_diagrams_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_diagrams_background_defaults(task_group="hierarchy")
POST_IMAGE_NOISE_DEFAULTS = load_diagrams_noise_defaults(task_group="hierarchy", apply_prob=0.0)


def _build_prompt_json_examples(*, query_id: str) -> tuple[str, str]:
    """Return prompt JSON examples that match the active tree-count query id."""

    examples = {
        "subtree_descendant_count": (
            [[256, 316, 368, 374], [196, 462, 308, 520], [374, 462, 486, 520], [374, 608, 486, 666]],
            4,
        ),
        "subtree_leaf_count": (
            [[188, 610, 300, 668], [366, 610, 478, 668], [544, 610, 656, 668]],
            3,
        ),
        "path_length_between_two_nodes": (
            [
                [226, 690, 338, 748],
                [384, 560, 496, 618],
                [542, 430, 654, 488],
                [700, 560, 812, 618],
                [858, 690, 970, 748],
            ],
            4,
        ),
    }
    evidence_bbox, answer_value = examples[str(query_id)]
    answer_and_evidence = {"evidence": evidence_bbox, "answer": int(answer_value)}
    answer_only = {"answer": int(answer_value)}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


@register_task
class PagesHierarchyTreeCountTask:
    """Return integer counts over one generic rooted tree diagram."""

    task_id = TASK_ID
    domain = "pages"
    task_group = "hierarchy"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = resolve_hierarchy_tree_count_query_id(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_variant, scene_variant_probabilities = resolve_hierarchy_tree_count_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_hierarchy_tree_count_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        render_params = resolve_hierarchy_render_params(params, render_defaults=_RENDER_DEFAULTS, instance_seed=int(instance_seed))
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_hierarchy_scene(
            background,
            scene_title=str(dataset["scene_title"]),
            root_node_id=str(dataset["root_node_id"]),
            node_specs=list(dataset["node_specs"]),
            edge_specs=list(dataset["edge_specs"]),
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "evidence_hint_subtree_descendant_count",
                "evidence_hint_subtree_leaf_count",
                "evidence_hint_path_length_between_two_nodes",
                "object_description_rooted_tree",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(query_id=str(query_id))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_rooted_tree"]),
                "question_text": str(dataset["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(query_id)}"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_node_bbox_ids = [str(bbox_id) for bbox_id in dataset["evidence_node_bbox_ids"]]
        evidence_projection = projected_diagram_bbox_evidence(rendered_scene.node_bbox_map, evidence_node_bbox_ids)
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        answer_value = int(dataset["answer_count"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        node_scan = normalize_int_with_bounds(int(dataset["tree_node_count"]), [16, 30])
        depth_scan = normalize_int_with_bounds(int(dataset["tree_depth"]), [4, 8])
        answer_scan = normalize_int_with_bounds(int(answer_value), [2, 18])
        evidence_scan = normalize_int_with_bounds(len(evidence_node_bbox_ids), [2, 19])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(query_id)])
            + (0.10 * float(node_scan))
            + (0.16 * float(depth_scan))
            + (0.14 * float(answer_scan))
            + (0.10 * float(evidence_scan))
        )
        complexity = build_diagrams_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": max(float(node_scan), float(depth_scan)),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )

        witness_type = "ordered_id_path" if str(query_id) == "path_length_between_two_nodes" else "id_set"
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"diagram_hierarchy_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "root_node_id": str(dataset["root_node_id"]),
                    "query_node_ids": [str(node_id) for node_id in dataset["query_node_ids"]],
                    "evidence_node_ids": [str(node_id) for node_id in dataset["evidence_node_ids"]],
                    "view_family": str(dataset["view_family"]),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "tree_node_count": int(dataset["tree_node_count"]),
                    "tree_depth": int(dataset["tree_depth"]),
                    "leaf_count": int(dataset["leaf_count"]),
                    "query_relationship": str(dataset["query_relationship"]),
                    "answer_count": int(answer_value),
                },
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "geometry_seed": int(instance_seed),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "node_width_px": int(render_params.node_width_px),
                "node_height_px": int(render_params.node_height_px),
                "connector_width_px": int(render_params.connector_width_px),
                "layout_jitter": dict(rendered_scene.layout_jitter_meta),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "node_bboxes_px": dict(rendered_scene.node_bbox_map),
                "node_label_bboxes_px": dict(rendered_scene.node_label_bbox_map),
                "edge_bboxes_px": dict(rendered_scene.edge_bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "scene_title": str(dataset["scene_title"]),
                "question_text": str(dataset["question_text"]),
                "template_id": str(dataset["template_id"]),
                "tree_node_count": int(dataset["tree_node_count"]),
                "tree_depth": int(dataset["tree_depth"]),
                "leaf_count": int(dataset["leaf_count"]),
                "root_node_id": str(dataset["root_node_id"]),
                "node_specs": [dict(spec) for spec in dataset["node_specs"]],
                "edge_specs": [dict(spec) for spec in dataset["edge_specs"]],
                "query_node_ids": [str(node_id) for node_id in dataset["query_node_ids"]],
                "query_node_labels": [str(label) for label in dataset["query_node_labels"]],
                "query_depths": [int(depth) for depth in dataset["query_depths"]],
                "query_relationship": str(dataset["query_relationship"]),
                "answer_count": int(answer_value),
                "evidence_node_ids": [str(node_id) for node_id in dataset["evidence_node_ids"]],
                "evidence_node_bbox_ids": [str(bbox_id) for bbox_id in evidence_node_bbox_ids],
                "evidence_semantics": str(dataset["evidence_semantics"]),
                "descendant_node_ids": [str(node_id) for node_id in dataset["descendant_node_ids"]],
                "descendant_count": int(dataset["descendant_count"]),
                "leaf_descendant_node_ids": [str(node_id) for node_id in dataset["leaf_descendant_node_ids"]],
                "leaf_descendant_count": int(dataset["leaf_descendant_count"]),
                "path_node_ids": [str(node_id) for node_id in dataset["path_node_ids"]],
                "path_node_labels": [str(label) for label in dataset["path_node_labels"]],
                "path_length_between_nodes": int(dataset["path_length_between_nodes"]),
                "path_lca_node_id": str(dataset["path_lca_node_id"]),
                "path_lca_node_label": str(dataset["path_lca_node_label"]),
                "path_lca_depth": int(dataset["path_lca_depth"]),
                "supporting_node_bbox_ids": [str(bbox_id) for bbox_id in evidence_node_bbox_ids],
            },
            "witness_symbolic": {
                "type": str(witness_type),
                "ids": [str(node_id) for node_id in dataset["evidence_node_ids"]],
            },
            "projected_evidence": dict(evidence_projection),
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }

        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
        )
        return rewrite_pages_query_output(
            output,
            query_id=str(query_id),
            scene_id="hierarchy",
            query_probabilities=query_id_probabilities,
        )


__all__ = ["PagesHierarchyTreeCountTask"]
