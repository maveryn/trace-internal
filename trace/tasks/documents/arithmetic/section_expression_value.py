"""Documents arithmetic task that computes one amount from visible values in a named section."""

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
from ..shared.arithmetic_common import (
    SUPPORTED_DOCUMENT_ARITHMETIC_TASK_VARIANTS,
    build_document_section_expression_dataset,
    resolve_document_arithmetic_scene_variant,
    resolve_document_arithmetic_task_variant,
)
from ..shared.common import projected_document_bbox_evidence
from ..shared.complexity import (
    build_documents_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_documents_complexity_weights,
)
from ..shared.document_common import DocumentDefaults, resolve_document_render_params
from ..shared.document_scene import render_document_scene
from ..shared.visual_defaults import load_documents_background_defaults, load_documents_noise_defaults


TASK_ID = "task_documents_arithmetic_section_expression_value"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = SUPPORTED_DOCUMENT_ARITHMETIC_TASK_VARIANTS
_REASONING_LOAD_BASE_BY_VARIANT = {
    "sum_two_amounts_in_section": 0.34,
    "difference_two_amounts_in_section": 0.38,
    "sum_minus_amount_in_section": 0.44,
}
_SCENE_LOAD_BY_VARIANT = {
    "form_sheet": 0.16,
    "invoice_sheet": 0.22,
    "receipt_sheet": 0.18,
}

_DEFAULTS = DocumentDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("documents", "arithmetic")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_documents_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_documents_background_defaults(task_group="arithmetic")
POST_IMAGE_NOISE_DEFAULTS = load_documents_noise_defaults(task_group="arithmetic", apply_prob=0.0)


def _canonical_operand_example_bboxes(*, task_variant: str) -> list[list[int]]:
    """Return stable operand-value bbox examples for prompt JSON snippets."""

    if str(task_variant) == "sum_minus_amount_in_section":
        return [
            [150, 260, 364, 294],
            [150, 320, 364, 354],
            [150, 380, 364, 414],
        ]
    return [
        [150, 260, 364, 294],
        [150, 320, 364, 354],
    ]


def _build_prompt_json_examples(*, task_variant: str) -> tuple[str, str]:
    """Return prompt JSON examples that match the active arithmetic variant."""

    answer_by_variant = {
        "sum_two_amounts_in_section": "$146.80",
        "difference_two_amounts_in_section": "$42.50",
        "sum_minus_amount_in_section": "$133.30",
    }
    answer_value = str(answer_by_variant[str(task_variant)])
    answer_and_evidence = {
        "evidence": _canonical_operand_example_bboxes(task_variant=str(task_variant)),
        "answer": str(answer_value),
    }
    answer_only = {"answer": str(answer_value)}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


@register_task
class DocumentsArithmeticSectionExpressionValueTask:
    """Compute one section-local amount expression from visible document values."""

    task_id = TASK_ID
    domain = "documents"
    task_group = "arithmetic"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = resolve_document_arithmetic_task_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_variant, scene_variant_probabilities = resolve_document_arithmetic_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_document_section_expression_dataset(
            task_variant=str(task_variant),
            scene_variant=str(scene_variant),
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        render_params = resolve_document_render_params(params, render_defaults=_RENDER_DEFAULTS)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_document_scene(
            background,
            scene_variant=str(scene_variant),
            geometry_seed=int(instance_seed),
            scene_title=str(dataset["scene_title"]),
            field_specs=list(dataset["field_specs"]),
            section_specs=list(dataset["section_specs"]),
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
                "evidence_hint",
                "object_description_form_sheet",
                "object_description_invoice_sheet",
                "object_description_receipt_sheet",
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
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_projection = projected_document_bbox_evidence(
            dict(rendered_scene.field_value_bbox_map),
            list(dataset["operand_value_bbox_ids"]),
        )
        evidence_bboxes = [list(bbox) for bbox in evidence_projection["bbox_set"]]
        answer_gt = TypedValue(type="string", value=str(dataset["result_value"]))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        field_scan = normalize_int_with_bounds(int(dataset["field_count"]), list(dataset["field_count_range"]))
        operand_scan = normalize_int_with_bounds(len(list(dataset["operand_field_ids"])), [2, 3])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)]) + (0.12 * float(operand_scan))
        )
        complexity = build_documents_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(field_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"document_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "query_section_id": str(dataset["query_section_id"]),
                    "query_section_label": str(dataset["query_section_label"]),
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
                    "field_count": int(dataset["field_count"]),
                    "field_count_range": list(dataset["field_count_range"]),
                    "operand_count": len(list(dataset["operand_field_ids"])),
                },
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "geometry_seed": int(instance_seed),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "sheet_page_width_px": int(render_params.sheet_page_width_px),
                "sheet_page_height_px": int(render_params.sheet_page_height_px),
                "receipt_page_width_px": int(render_params.receipt_page_width_px),
                "receipt_page_height_px": int(render_params.receipt_page_height_px),
                "page_shadow_offset_px": int(render_params.page_shadow_offset_px),
            },
            "render_map": {
                "page_bbox_px": list(rendered_scene.page_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "section_label_bboxes_px": dict(rendered_scene.section_label_bbox_map),
                "section_box_bboxes_px": dict(rendered_scene.section_box_bbox_map),
                "field_label_bboxes_px": dict(rendered_scene.field_label_bbox_map),
                "field_value_bboxes_px": dict(rendered_scene.field_value_bbox_map),
                "field_box_bboxes_px": dict(rendered_scene.field_box_bbox_map),
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "scene_title": str(dataset["scene_title"]),
                "question_text": str(dataset["question_text"]),
                "field_count": int(dataset["field_count"]),
                "field_specs": [dict(spec) for spec in dataset["field_specs"]],
                "section_specs": [dict(spec) for spec in dataset["section_specs"]],
                "query_section_id": str(dataset["query_section_id"]),
                "query_section_label": str(dataset["query_section_label"]),
                "operand_field_ids": list(dataset["operand_field_ids"]),
                "operand_field_labels": list(dataset["operand_field_labels"]),
                "operand_field_values": list(dataset["operand_field_values"]),
                "operand_value_bbox_ids": list(dataset["operand_value_bbox_ids"]),
                "operator_sequence": list(dataset["operator_sequence"]),
                "expression_operand_cents": list(dataset["expression_operand_cents"]),
                "result_cents": int(dataset["result_cents"]),
                "result_value": str(dataset["result_value"]),
            },
            "witness_symbolic": {
                "field_id_sequence": list(dataset["operand_field_ids"]),
                "bbox_id_sequence": list(dataset["operand_value_bbox_ids"]),
            },
            "projected_evidence": dict(evidence_projection),
            "background": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "answer_gt": answer_gt.to_dict(),
            "evidence_gt": evidence_gt.to_dict(),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id=f"{self.task_id}_image",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(task_variant),
        )


__all__ = ["DocumentsArithmeticSectionExpressionValueTask"]
