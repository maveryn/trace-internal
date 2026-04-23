"""Diagrams flow task that returns the next labeled step in a process diagram."""

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
from ..shared.common import projected_diagram_bbox_evidence
from ..shared.complexity import (
    build_diagrams_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_diagrams_complexity_weights,
)
from ..shared.flow_common import (
    FlowDefaults,
    FLOW_PROCESS_LABEL_LENGTH_BOUNDS,
    SUPPORTED_DIAGRAM_FLOW_SCENE_VARIANTS,
    SUPPORTED_DIAGRAM_FLOW_TASK_VARIANTS,
    build_flow_next_step_dataset,
    resolve_flow_render_params,
    resolve_flow_scene_variant,
    resolve_flow_task_variant,
)
from ..shared.flow_scene import render_flow_scene
from ..shared.visual_defaults import load_diagrams_background_defaults, load_diagrams_noise_defaults


TASK_ID = "task_diagrams_flow_next_step_label"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = SUPPORTED_DIAGRAM_FLOW_TASK_VARIANTS
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_DIAGRAM_FLOW_SCENE_VARIANTS
_REASONING_LOAD_BASE_BY_VARIANT = {
    "direct_next_step": 0.24,
    "branch_next_step": 0.34,
}
_SCENE_LOAD_BY_VARIANT = {
    "flowchart": 0.11,
    "swimlane": 0.18,
}

_DEFAULTS = FlowDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("diagrams", "flow")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_diagrams_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
_COMPONENT_COUNT_BOUNDS = (
    min(
        (2 * int(_DEFAULTS.direct_node_count_min)) - 1,
        12,
    ),
    max(
        (2 * int(_DEFAULTS.direct_node_count_max)) - 1 + int(_DEFAULTS.lane_count),
        12 + int(_DEFAULTS.lane_count),
    ),
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_diagrams_background_defaults(task_group="flow")
POST_IMAGE_NOISE_DEFAULTS = load_diagrams_noise_defaults(task_group="flow", apply_prob=0.0)


def _build_prompt_json_examples(*, task_variant: str) -> tuple[str, str]:
    """Return prompt JSON examples that match the active flow-query variant."""

    answer_value = "Approve Order" if str(task_variant) == "direct_next_step" else "Fix Record"
    answer_and_evidence = {"evidence": [[624, 228, 838, 312]], "answer": str(answer_value)}
    answer_only = {"answer": str(answer_value)}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


@register_task
class DiagramsFlowNextStepLabelTask:
    """Return the exact visible next-step label in one process flow diagram."""

    task_id = TASK_ID
    domain = "diagrams"
    task_group = "flow"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = resolve_flow_task_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_variant, scene_variant_probabilities = resolve_flow_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_flow_next_step_dataset(
            task_variant=str(task_variant),
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        render_params = resolve_flow_render_params(params, render_defaults=_RENDER_DEFAULTS)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_flow_scene(
            background,
            scene_variant=str(scene_variant),
            scene_title=str(dataset["scene_title"]),
            lane_specs=list(dataset["lane_specs"]),
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
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "evidence_hint_direct_next_step",
                "evidence_hint_branch_next_step",
                "object_description_flowchart",
                "object_description_swimlane",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(task_variant=str(task_variant))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(task_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(scene_variant)}"]),
                "question_text": str(dataset["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(task_variant)}"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_node_bbox_id = str(dataset["answer_node_bbox_id"])
        evidence_projection = projected_diagram_bbox_evidence(rendered_scene.node_bbox_map, [str(answer_node_bbox_id)])
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        answer_value = str(dataset["answer_node_label"])
        answer_gt = TypedValue(type="string", value=str(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        component_scan = normalize_int_with_bounds(
            int(dataset["topology_node_count"]) + int(dataset["topology_edge_count"]) + int(dataset["lane_count"]),
            _COMPONENT_COUNT_BOUNDS,
        )
        lane_scan = normalize_int_with_bounds(int(dataset["lane_count"]), [0, 3])
        output_burden = normalize_int_with_bounds(int(dataset["answer_label_length"]), FLOW_PROCESS_LABEL_LENGTH_BOUNDS)
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)])
            + (0.12 * float(component_scan))
            + (0.08 * float(lane_scan))
            + (0.06 * float(output_burden))
        )
        complexity = build_diagrams_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": clamp_unit_interval((0.78 * float(component_scan)) + (0.22 * float(lane_scan))),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
                "output_burden": float(output_burden),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"diagram_flow_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "answer_node_id": str(dataset["answer_node_id"]),
                    "answer_node_bbox_id": str(answer_node_bbox_id),
                    "view_family": str(dataset["view_family"]),
                },
            },
            "query_spec": {
                "task_variant": str(task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "task_variant_probabilities": dict(task_variant_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "topology_node_count": int(dataset["topology_node_count"]),
                    "topology_edge_count": int(dataset["topology_edge_count"]),
                    "lane_count": int(dataset["lane_count"]),
                    "answer_label_length": int(dataset["answer_label_length"]),
                    "query_branch_label": dataset["query_branch_label"],
                },
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "geometry_seed": int(instance_seed),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "node_width_px": int(render_params.node_width_px),
                "node_height_px": int(render_params.node_height_px),
                "decision_diameter_px": int(render_params.decision_diameter_px),
                "edge_width_px": int(render_params.edge_width_px),
                "lane_gutter_width_px": int(render_params.lane_gutter_width_px),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "lane_bboxes_px": dict(rendered_scene.lane_bbox_map),
                "lane_label_bboxes_px": dict(rendered_scene.lane_label_bbox_map),
                "node_bboxes_px": dict(rendered_scene.node_bbox_map),
                "node_label_bboxes_px": dict(rendered_scene.node_label_bbox_map),
                "edge_label_bboxes_px": dict(rendered_scene.edge_label_bbox_map),
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "scene_title": str(dataset["scene_title"]),
                "question_text": str(dataset["question_text"]),
                "topology_node_count": int(dataset["topology_node_count"]),
                "topology_edge_count": int(dataset["topology_edge_count"]),
                "lane_count": int(dataset["lane_count"]),
                "lane_specs": [dict(spec) for spec in dataset["lane_specs"]],
                "node_specs": [dict(spec) for spec in dataset["node_specs"]],
                "edge_specs": [dict(spec) for spec in dataset["edge_specs"]],
                "query_node_id": str(dataset["query_node_id"]),
                "query_node_label": str(dataset["query_node_label"]),
                "query_branch_label": dataset["query_branch_label"],
                "answer_node_id": str(dataset["answer_node_id"]),
                "answer_node_label": str(answer_value),
                "answer_label_length": int(dataset["answer_label_length"]),
                "answer_node_bbox_id": str(answer_node_bbox_id),
                "supporting_node_bbox_ids": [str(answer_node_bbox_id)],
            },
            "witness_symbolic": {
                "type": "id_set",
                "ids": [str(dataset["answer_node_id"])],
            },
            "projected_evidence": dict(evidence_projection),
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(task_variant),
        )


__all__ = ["DiagramsFlowNextStepLabelTask"]
