"""Diagrams schematic task that returns the callout label for one queried part."""

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
from ..shared.schematic_common import (
    SchematicDefaults,
    SUPPORTED_DIAGRAM_SCHEMATIC_SCENE_VARIANTS,
    SUPPORTED_DIAGRAM_SCHEMATIC_TASK_VARIANTS,
    build_schematic_callout_dataset,
    resolve_schematic_render_params,
    resolve_schematic_scene_variant,
    resolve_schematic_task_variant,
)
from ..shared.schematic_scene import render_schematic_scene
from ..shared.visual_defaults import load_diagrams_background_defaults, load_diagrams_noise_defaults


TASK_ID = "task_diagrams_schematic_callout_target_label"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = SUPPORTED_DIAGRAM_SCHEMATIC_TASK_VARIANTS
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_DIAGRAM_SCHEMATIC_SCENE_VARIANTS
_REASONING_LOAD_BASE_BY_VARIANT = {
    "callout_for_named_part": 0.34,
    "callout_for_highlighted_part": 0.23,
}
_SCENE_LOAD_BY_VARIANT = {"annotated_schematic": 0.17}

_DEFAULTS = SchematicDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("diagrams", "schematic")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_diagrams_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_diagrams_background_defaults(task_group="schematic")
POST_IMAGE_NOISE_DEFAULTS = load_diagrams_noise_defaults(task_group="schematic", apply_prob=0.0)


def _build_prompt_json_examples(*, task_variant: str) -> tuple[str, str]:
    """Return prompt JSON examples that match the active schematic query variant."""

    answer_value = "B" if str(task_variant) == "callout_for_named_part" else "F"
    answer_and_evidence = {"evidence": [[406, 334, 595, 445]], "answer": str(answer_value)}
    answer_only = {"answer": str(answer_value)}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


@register_task
class DiagramsSchematicCalloutTargetLabelTask:
    """Return the callout label associated with one queried schematic part."""

    task_id = TASK_ID
    domain = "diagrams"
    task_group = "schematic"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = resolve_schematic_task_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_variant, scene_variant_probabilities = resolve_schematic_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_schematic_callout_dataset(
            task_variant=str(task_variant),
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
        )
        render_params = resolve_schematic_render_params(params, render_defaults=_RENDER_DEFAULTS)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_schematic_scene(
            background,
            scene_title=str(dataset["scene_title"]),
            scene_variant=str(scene_variant),
            part_specs=list(dataset["part_specs"]),
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
                "evidence_hint_callout_for_named_part",
                "evidence_hint_callout_for_highlighted_part",
                "object_description_annotated_schematic",
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
                "object_description": str(prompt_defaults["object_description_annotated_schematic"]),
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

        answer_part_bbox_id = str(dataset["answer_part_bbox_id"])
        evidence_projection = projected_diagram_bbox_evidence(rendered_scene.part_bbox_map, [str(answer_part_bbox_id)])
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        answer_value = str(dataset["answer_callout_label"])
        answer_gt = TypedValue(type="string", value=str(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        part_scan = normalize_int_with_bounds(int(dataset["part_count"]), [5, 7])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)]) + (0.14 * float(part_scan))
        )
        complexity = build_diagrams_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": clamp_unit_interval(0.36 + (0.24 * float(part_scan))),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"diagram_schematic_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "answer_part_id": str(dataset["answer_part_id"]),
                    "answer_part_bbox_id": str(answer_part_bbox_id),
                    "answer_callout_label": str(answer_value),
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
                    "part_count": int(dataset["part_count"]),
                    "query_focus": str(dataset["query_focus"]),
                },
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "geometry_seed": int(instance_seed),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "callout_diameter_px": int(render_params.callout_diameter_px),
                "leader_width_px": int(render_params.leader_width_px),
                "part_label_font_size_px": int(render_params.part_label_font_size_px),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "chassis_bbox_px": list(rendered_scene.chassis_bbox_px),
                "part_bboxes_px": dict(rendered_scene.part_bbox_map),
                "part_label_bboxes_px": dict(rendered_scene.part_label_bbox_map),
                "callout_bboxes_px": dict(rendered_scene.callout_bbox_map),
                "callout_label_bboxes_px": dict(rendered_scene.callout_label_bbox_map),
                "leader_bboxes_px": dict(rendered_scene.leader_bbox_map),
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "scene_title": str(dataset["scene_title"]),
                "question_text": str(dataset["question_text"]),
                "part_count": int(dataset["part_count"]),
                "part_specs": [dict(spec) for spec in dataset["part_specs"]],
                "query_focus": str(dataset["query_focus"]),
                "query_part_label": dataset["query_part_label"],
                "highlight_part_id": dataset["highlight_part_id"],
                "answer_part_id": str(dataset["answer_part_id"]),
                "answer_part_label": str(dataset["answer_part_label"]),
                "answer_part_bbox_id": str(answer_part_bbox_id),
                "answer_callout_bbox_id": str(dataset["answer_callout_bbox_id"]),
                "answer_callout_label": str(answer_value),
                "supporting_part_bbox_ids": [str(answer_part_bbox_id)],
            },
            "witness_symbolic": {
                "type": "id_set",
                "ids": [str(answer_part_bbox_id)],
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


__all__ = ["DiagramsSchematicCalloutTargetLabelTask"]
