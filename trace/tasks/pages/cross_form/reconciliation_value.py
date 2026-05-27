"""Cross-form document reconciliation task with numeric answers."""

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
from ..shared.common import projected_document_bbox_evidence
from ..shared.complexity import (
    build_pages_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_pages_complexity_weights,
)
from ..shared.reconciliation_common import (
    ReconciliationDefaults,
    SUPPORTED_DOCUMENT_RECONCILIATION_SCENE_VARIANTS,
    SUPPORTED_DOCUMENT_RECONCILIATION_QUERY_VARIANTS,
    build_cross_form_reconciliation_dataset,
    resolve_reconciliation_render_params,
    resolve_reconciliation_scene_variant,
    resolve_reconciliation_query_variant,
)
from ..shared.reconciliation_scene import render_reconciliation_scene
from ..shared.public_query_task import rewrite_pages_query_output
from ..shared.visual_defaults import load_pages_background_defaults, load_pages_noise_defaults


TASK_ID = "task_pages__paired_forms__reconciliation_value"
_SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = SUPPORTED_DOCUMENT_RECONCILIATION_QUERY_VARIANTS
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_DOCUMENT_RECONCILIATION_SCENE_VARIANTS
_REASONING_LOAD_BASE_BY_VARIANT = {
    "sum_absolute_quantity_differences": 0.00,
    "total_amount_delta": 0.50,
    "shortfall_minus_overage_value": 1.00,
}
_SCENE_LOAD_BY_VARIANT = {"purchase_receipt_pair": 0.34}

_DEFAULTS = ReconciliationDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "cross_form")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_pages_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_pages_background_defaults(task_group="cross_form")
POST_IMAGE_NOISE_DEFAULTS = load_pages_noise_defaults(task_group="cross_form", apply_prob=0.0)


def _build_prompt_json_examples(*, query_variant: str) -> tuple[str, str]:
    """Return stable JSON examples that match the active reconciliation variant."""

    examples = {
        "total_amount_delta": (
            [
                [120, 330, 180, 352],
                [380, 330, 430, 352],
                [890, 330, 950, 352],
                [1160, 330, 1210, 352],
                [500, 330, 555, 352],
            ],
            864,
        ),
        "shortfall_minus_overage_value": (
            [
                [120, 420, 180, 442],
                [380, 420, 430, 442],
                [890, 420, 950, 442],
                [1160, 420, 1210, 442],
                [500, 420, 555, 442],
            ],
            324,
        ),
        "sum_absolute_quantity_differences": (
            [
                [120, 510, 180, 532],
                [380, 510, 430, 532],
                [890, 510, 950, 532],
                [1160, 510, 1210, 532],
            ],
            42,
        ),
    }
    evidence_bboxes, answer_value = examples[str(query_variant)]
    answer_and_evidence = {"evidence": evidence_bboxes, "answer": int(answer_value)}
    answer_only = {"answer": int(answer_value)}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


@register_task
class PagesCrossFormReconciliationValueTask:
    """Compute a numeric reconciliation value across two matched document forms."""

    task_id = TASK_ID
    domain = "pages"
    task_group = "cross_form"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_variant, query_variant_probabilities = resolve_reconciliation_query_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_variant, scene_variant_probabilities = resolve_reconciliation_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_cross_form_reconciliation_dataset(
            query_variant=str(query_variant),
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        render_params = resolve_reconciliation_render_params(params, render_defaults=_RENDER_DEFAULTS, instance_seed=int(instance_seed))
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_reconciliation_scene(
            background,
            scene_title=str(dataset["scene_title"]),
            purchase_title=str(dataset["purchase_title"]),
            receiving_title=str(dataset["receiving_title"]),
            purchase_header_specs=list(dataset["purchase_header_specs"]),
            receiving_header_specs=list(dataset["receiving_header_specs"]),
            item_specs=list(dataset["item_specs"]),
            receiving_item_specs=list(dataset["receiving_item_specs"]),
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
                "evidence_hint_total_amount_delta",
                "evidence_hint_shortfall_minus_overage_value",
                "evidence_hint_sum_absolute_quantity_differences",
                "object_description_purchase_receipt_pair",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(query_variant=str(query_variant))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_purchase_receipt_pair"]),
                "question_text": str(dataset["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(query_variant)}"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_bbox_ids = [str(bbox_id) for bbox_id in dataset["evidence_bbox_ids"]]
        evidence_projection = projected_document_bbox_evidence(
            dict(rendered_scene.cell_value_bbox_map),
            evidence_bbox_ids,
        )
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        item_scan = normalize_int_with_bounds(int(dataset["item_count"]), list(dataset["item_count_range"]))
        evidence_scan = normalize_int_with_bounds(len(evidence_bbox_ids), [4, 60])
        mismatch_scan = normalize_int_with_bounds(len(dataset["mismatch_item_ids"]), [4, int(dataset["item_count"])])
        reasoning_load = clamp_unit_interval(
            (0.60 * float(_REASONING_LOAD_BASE_BY_VARIANT[str(query_variant)]))
            + (0.25 * float(evidence_scan))
            + (0.15 * float(mismatch_scan))
        )
        complexity = build_pages_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(item_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"document_reconciliation_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_variant": str(query_variant),
                    "scene_variant": str(scene_variant),
                    "answer_value": int(answer_value),
                    "view_family": str(dataset["view_family"]),
                },
            },
            "query_spec": {
                "query_variant": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": str(query_variant),
                    "scene_variant": str(scene_variant),
                    "query_variant_probabilities": dict(query_variant_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "item_count": int(dataset["item_count"]),
                    "mismatch_count_range": list(dataset["mismatch_count_range"]),
                    "direction_count_min": int(dataset["direction_count_min"]),
                    "evidence_bbox_count": int(len(evidence_bbox_ids)),
                },
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "geometry_seed": int(instance_seed),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "outer_margin_px": int(render_params.outer_margin_px),
                "panel_gap_px": int(render_params.panel_gap_px),
                "row_min_height_px": int(render_params.row_min_height_px),
                "row_max_height_px": int(render_params.row_max_height_px),
                "layout_jitter": dict(rendered_scene.layout_jitter_meta),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "panel_bboxes_px": dict(rendered_scene.panel_bboxes_px),
                "title_bboxes_px": dict(rendered_scene.title_bboxes_px),
                "header_value_bboxes_px": dict(rendered_scene.header_value_bbox_map),
                "cell_value_bboxes_px": dict(rendered_scene.cell_value_bbox_map),
                "row_bboxes_px": dict(rendered_scene.row_bbox_map),
            },
            "execution_trace": {
                "query_variant": str(query_variant),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "scene_title": str(dataset["scene_title"]),
                "question_text": str(dataset["question_text"]),
                "purchase_title": str(dataset["purchase_title"]),
                "receiving_title": str(dataset["receiving_title"]),
                "purchase_header_specs": [dict(spec) for spec in dataset["purchase_header_specs"]],
                "receiving_header_specs": [dict(spec) for spec in dataset["receiving_header_specs"]],
                "item_specs": [dict(spec) for spec in dataset["item_specs"]],
                "receiving_item_order_ids": [str(item) for item in dataset["receiving_item_order_ids"]],
                "item_count": int(dataset["item_count"]),
                "item_count_range": list(dataset["item_count_range"]),
                "quantity_range": list(dataset["quantity_range"]),
                "unit_value_range": list(dataset["unit_value_range"]),
                "discrepancy_range": list(dataset["discrepancy_range"]),
                "mismatch_count_range": list(dataset["mismatch_count_range"]),
                "direction_count_min": int(dataset["direction_count_min"]),
                "shortfall_item_ids": [str(item) for item in dataset["shortfall_item_ids"]],
                "overage_item_ids": [str(item) for item in dataset["overage_item_ids"]],
                "mismatch_item_ids": [str(item) for item in dataset["mismatch_item_ids"]],
                "answer_value": int(answer_value),
                "evidence_bbox_ids": list(evidence_bbox_ids),
                "supporting_bbox_ids": list(evidence_bbox_ids),
                "evidence_semantics": str(query_variant),
            },
            "witness_symbolic": {
                "type": "ordered_cell_bbox_ids",
                "ids": list(evidence_bbox_ids),
            },
            "projected_evidence": dict(evidence_projection),
            "background": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "answer_gt": answer_gt.to_dict(),
            "evidence_gt": evidence_gt.to_dict(),
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
            query_variant=str(query_variant),
        )
        return rewrite_pages_query_output(
            output,
            query_id=str(query_variant),
            scene_id="paired_forms",
            query_probabilities=query_variant_probabilities,
        )


__all__ = ["PagesCrossFormReconciliationValueTask"]
