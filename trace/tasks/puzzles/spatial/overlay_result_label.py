"""Puzzle spatial task that chooses the combined result of two transparent sheets."""

from __future__ import annotations

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
from ..shared.common import projected_puzzle_bbox_evidence
from ..shared.complexity import (
    build_puzzle_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_puzzle_complexity_weights,
)
from ..shared.overlay_common import (
    PuzzleOverlayDefaults,
    SUPPORTED_PUZZLE_OVERLAY_TASK_VARIANTS,
    build_overlay_dataset_for_variant,
    resolve_overlay_render_params,
    resolve_overlay_scene_variant,
    resolve_overlay_task_variant,
)
from ..shared.overlay_scene import render_puzzle_overlay_scene
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "task_puzzles_spatial_overlay_result_label"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = SUPPORTED_PUZZLE_OVERLAY_TASK_VARIANTS
_REASONING_LOAD_BASE_BY_VARIANT = {"overlay_union_same_grid": 0.37}
_SCENE_LOAD_BY_VARIANT = {
    "overlay_strip": 0.14,
    "overlay_card": 0.20,
    "overlay_outline": 0.18,
}

_DEFAULTS = PuzzleOverlayDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="spatial")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="spatial", apply_prob=0.0)


@register_task
class PuzzlesSpatialOverlayResultLabelTask:
    """Choose the option that matches the union of two aligned transparent sheets."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "spatial"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = resolve_overlay_task_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_variant, scene_variant_probabilities = resolve_overlay_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_overlay_dataset_for_variant(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        render_params = resolve_overlay_render_params(params, render_defaults=_RENDER_DEFAULTS)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_puzzle_overlay_scene(
            background,
            scene_variant=str(scene_variant),
            grid_size=int(dataset["grid_size"]),
            left_mark_specs=list(dataset["left_mark_specs"]),
            right_mark_specs=list(dataset["right_mark_specs"]),
            option_specs=list(dataset["option_specs"]),
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
                "object_description_overlay_strip",
                "object_description_overlay_card",
                "object_description_overlay_outline",
                "evidence_hint_overlay_union_same_grid",
                "json_example_overlay_union_same_grid",
                "json_example_answer_only_overlay_union_same_grid",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults["evidence_hint_overlay_union_same_grid"])
        json_example = str(prompt_defaults["json_example_overlay_union_same_grid"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_overlay_union_same_grid"])

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(task_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        correct_option_choice_id = str(dataset["correct_option_choice_id"])
        evidence_projection = projected_puzzle_bbox_evidence(
            rendered_scene.option_choice_bbox_map,
            [str(correct_option_choice_id)],
        )
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_value = str(dataset["answer_option_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        sheet_scan = max(
            normalize_int_with_bounds(int(dataset["left_mark_count"]), [2, 5]),
            normalize_int_with_bounds(int(dataset["right_mark_count"]), [2, 5]),
        )
        grid_scan = normalize_int_with_bounds(int(dataset["grid_size"]), [4, 5])
        option_scan = normalize_int_with_bounds(int(dataset["option_count"]), [5, 6])
        union_scan = normalize_int_with_bounds(int(dataset["union_mark_count"]), [3, 9])
        overlap_scan = normalize_int_with_bounds(int(dataset["overlap_count"]), [1, 2])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)])
            + (0.18 * float(overlap_scan))
            + (0.12 * float(union_scan))
        )
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float((0.4 * grid_scan) + (0.35 * sheet_scan) + (0.25 * option_scan)),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_spatial_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "answer_option_label": str(answer_value),
                    "correct_option_choice_id": str(correct_option_choice_id),
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
                    "grid_size": int(dataset["grid_size"]),
                    "grid_size_range": list(dataset["grid_size_range"]),
                    "option_count": int(dataset["option_count"]),
                    "option_count_range": list(dataset["option_count_range"]),
                    "left_mark_count": int(dataset["left_mark_count"]),
                    "right_mark_count": int(dataset["right_mark_count"]),
                    "sheet_mark_count_range": list(dataset["sheet_mark_count_range"]),
                    "overlap_count": int(dataset["overlap_count"]),
                    "overlap_count_range": list(dataset["overlap_count_range"]),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "text_style": {
                    "option_label_font_size_px": int(render_params.option_label_font_size_px),
                    "combine_symbol_font_size_px": int(render_params.combine_symbol_font_size_px),
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "reference_panel_bbox_px": list(rendered_scene.reference_panel_bbox_px),
                "source_sheet_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.source_sheet_bbox_map.items()
                },
                "option_choice_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_choice_bbox_map.items()
                },
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "grid_size": int(dataset["grid_size"]),
                "grid_size_range": list(dataset["grid_size_range"]),
                "option_count": int(dataset["option_count"]),
                "option_count_range": list(dataset["option_count_range"]),
                "sheet_mark_count_range": list(dataset["sheet_mark_count_range"]),
                "overlap_count_range": list(dataset["overlap_count_range"]),
                "left_cells": [list(cell) for cell in dataset["left_cells"]],
                "right_cells": [list(cell) for cell in dataset["right_cells"]],
                "overlap_cells": [list(cell) for cell in dataset["overlap_cells"]],
                "union_cells": [list(cell) for cell in dataset["union_cells"]],
                "left_mark_specs": [dict(item) for item in dataset["left_mark_specs"]],
                "right_mark_specs": [dict(item) for item in dataset["right_mark_specs"]],
                "left_mark_count": int(dataset["left_mark_count"]),
                "right_mark_count": int(dataset["right_mark_count"]),
                "overlap_count": int(dataset["overlap_count"]),
                "union_mark_count": int(dataset["union_mark_count"]),
                "option_specs": [dict(spec) for spec in dataset["option_specs"]],
                "answer_option_label": str(answer_value),
                "correct_option_index": int(dataset["correct_option_index"]),
                "correct_option_choice_id": str(correct_option_choice_id),
                "supporting_option_choice_ids": [str(item) for item in dataset["valid_option_choice_ids"]],
                "solver_trace": dict(dataset["solver_trace"]),
                "complexity_components": dict(complexity.complexity_components),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "answer_gt": answer_gt.to_dict(),
            "evidence_gt": evidence_gt.to_dict(),
            "projected_evidence": dict(evidence_projection),
            "complexity": complexity.to_dict(),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["PuzzlesSpatialOverlayResultLabelTask"]
