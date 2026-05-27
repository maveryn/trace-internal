"""Diagrams cycle task that returns the exact visible stage label k steps before or after another stage."""

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
from ..shared.diagram.cycle_common import (
    CycleDefaults,
    SUPPORTED_DIAGRAM_CYCLE_SCENE_VARIANTS,
    SUPPORTED_DIAGRAM_CYCLE_QUERY_IDS,
    build_cycle_offset_dataset,
    normalize_cycle_query_params,
    resolve_cycle_direction,
    resolve_cycle_query_relationship,
    resolve_cycle_render_params,
    resolve_cycle_scene_variant,
    resolve_cycle_query_id,
)
from ..shared.diagram.cycle_scene import render_cycle_scene
from ..shared.diagram.visual_defaults import load_diagrams_background_defaults, load_diagrams_noise_defaults
from ..shared.public_query_task import rewrite_pages_query_output


TASK_ID = "task_pages__cycle__offset_stage_label"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = SUPPORTED_DIAGRAM_CYCLE_QUERY_IDS
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_DIAGRAM_CYCLE_SCENE_VARIANTS
_REASONING_LOAD_BASE_BY_RELATIONSHIP = {
    "after": 0.27,
    "before": 0.33,
}
_SCENE_LOAD_BY_VARIANT = {"cycle_ring": 0.12}

_DEFAULTS = CycleDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "cycle")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_diagrams_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_diagrams_background_defaults(task_group="cycle")
POST_IMAGE_NOISE_DEFAULTS = load_diagrams_noise_defaults(task_group="cycle", apply_prob=0.0)


def _build_prompt_json_examples() -> tuple[str, str]:
    """Return prompt JSON examples for the cycle offset-stage task."""

    answer_value = "Mina"
    evidence_bbox = [[747, 242, 869, 300]]
    answer_and_evidence = {"evidence": evidence_bbox, "answer": str(answer_value)}
    answer_only = {"answer": str(answer_value)}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


@register_task
class PagesCycleOffsetStageLabelTask:
    """Return the exact visible stage k steps before or after a queried stage in one directed cycle."""

    task_id = TASK_ID
    domain = "pages"
    task_group = "cycle"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        params = normalize_cycle_query_params(params)
        query_id, query_id_probabilities = resolve_cycle_query_id(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        query_relationship, query_relationship_probabilities = resolve_cycle_query_relationship(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_variant, scene_variant_probabilities = resolve_cycle_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        cycle_direction, cycle_direction_probabilities = resolve_cycle_direction(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_cycle_offset_dataset(
            query_id=str(query_id),
            query_relationship=str(query_relationship),
            scene_variant=str(scene_variant),
            cycle_direction=str(cycle_direction),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        render_params = resolve_cycle_render_params(params, render_defaults=_RENDER_DEFAULTS, instance_seed=int(instance_seed))
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_cycle_scene(
            background,
            scene_title=str(dataset["scene_title"]),
            stage_specs=list(dataset["stage_specs"]),
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
                "evidence_hint_offset_stage_label",
                "object_description_cycle_ring",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_cycle_ring"]),
                "question_text": str(dataset["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint_offset_stage_label"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_stage_bbox_id = str(dataset["answer_stage_bbox_id"])
        evidence_projection = projected_diagram_bbox_evidence(rendered_scene.stage_bbox_map, [str(answer_stage_bbox_id)])
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        answer_value = str(dataset["answer_stage_label"])
        answer_gt = TypedValue(type="string", value=str(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        stage_scan = normalize_int_with_bounds(int(dataset["stage_count"]), [5, 12])
        step_scan = normalize_int_with_bounds(int(dataset["step_count"]), [2, 11])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BASE_BY_RELATIONSHIP[str(query_relationship)])
            + (0.12 * float(stage_scan))
            + (0.20 * float(step_scan))
        )
        complexity = build_diagrams_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(stage_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"diagram_cycle_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "query_relationship": str(query_relationship),
                    "direction": str(dataset["direction"]),
                    "answer_stage_id": str(dataset["answer_stage_id"]),
                    "answer_stage_bbox_id": str(answer_stage_bbox_id),
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
                    "query_relationship": str(query_relationship),
                    "query_relationship_probabilities": dict(query_relationship_probabilities),
                    "cycle_direction": str(cycle_direction),
                    "cycle_direction_probabilities": dict(cycle_direction_probabilities),
                    "stage_count": int(dataset["stage_count"]),
                    "step_count": int(dataset["step_count"]),
                    "query_relationship": str(dataset["query_relationship"]),
                },
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "geometry_seed": int(instance_seed),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "node_width_px": int(render_params.node_width_px),
                "node_height_px": int(render_params.node_height_px),
                "ring_radius_x_px": int(render_params.ring_radius_x_px),
                "ring_radius_y_px": int(render_params.ring_radius_y_px),
                "edge_width_px": int(render_params.edge_width_px),
                "layout_jitter": dict(rendered_scene.layout_jitter_meta),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "stage_bboxes_px": dict(rendered_scene.stage_bbox_map),
                "stage_label_bboxes_px": dict(rendered_scene.stage_label_bbox_map),
                "edge_bboxes_px": dict(rendered_scene.edge_bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "scene_title": str(dataset["scene_title"]),
                "question_text": str(dataset["question_text"]),
                "direction": str(dataset["direction"]),
                "stage_count": int(dataset["stage_count"]),
                "step_count": int(dataset["step_count"]),
                "query_relationship": str(dataset["query_relationship"]),
                "query_stage_id": str(dataset["query_stage_id"]),
                "query_stage_label": str(dataset["query_stage_label"]),
                "query_stage_index": int(dataset["query_stage_index"]),
                "answer_stage_id": str(dataset["answer_stage_id"]),
                "answer_stage_label": str(answer_value),
                "answer_stage_bbox_id": str(answer_stage_bbox_id),
                "answer_stage_index": int(dataset["answer_stage_index"]),
                "stage_specs": [dict(spec) for spec in dataset["stage_specs"]],
                "edge_specs": [dict(spec) for spec in dataset["edge_specs"]],
                "supporting_stage_bbox_ids": [str(answer_stage_bbox_id)],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(dataset["answer_stage_id"])],
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
        query_id = f"{query_relationship}_offset_stage_label"
        return rewrite_pages_query_output(
            output,
            query_id=query_id,
            scene_id="cycle",
            query_probabilities={
                f"{key}_offset_stage_label": float(value)
                for key, value in query_relationship_probabilities.items()
            },
        )


__all__ = ["PagesCycleOffsetStageLabelTask"]
