"""Puzzle spatial task that selects the correct unfolded paper-hole pattern."""

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
from ..shared.common import projected_puzzle_bbox_evidence, resolve_puzzle_axis_variant
from ..shared.complexity import (
    build_puzzle_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_puzzle_complexity_weights,
)
from ..shared.fold_hole_common import (
    PuzzleFoldHoleDefaults,
    build_fold_hole_dataset_for_variant,
    resolve_fold_hole_render_params,
    resolve_fold_hole_scene_variant,
)
from ..shared.fold_scene import render_puzzle_fold_hole_scene
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "task_puzzles_spatial_fold_hole_label"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "single_fold_single_hole",
    "single_fold_two_holes",
    "double_fold_single_hole",
)
_REASONING_LOAD_BASE_BY_VARIANT = {
    "single_fold_single_hole": 0.26,
    "single_fold_two_holes": 0.38,
    "double_fold_single_hole": 0.46,
}
_SCENE_LOAD_BY_VARIANT = {
    "fold_strip": 0.14,
    "fold_card": 0.2,
    "fold_outline": 0.18,
}

_DEFAULTS = PuzzleFoldHoleDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="spatial")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="spatial", apply_prob=0.0)


def _resolve_task_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the requested fold-hole variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_TASK_VARIANTS,
        task_id=TASK_ID,
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


@register_task
class PuzzlesSpatialFoldHoleLabelTask:
    """Select the labeled option that correctly unfolds the folded paper."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "spatial"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = _resolve_task_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = resolve_fold_hole_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_fold_hole_dataset_for_variant(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        render_params = resolve_fold_hole_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_puzzle_fold_hole_scene(
            background,
            scene_variant=str(scene_variant),
            fold_mode=str(dataset["fold_mode"]),
            fold_axes=list(dataset["fold_axes"]),
            folded_hole_cells=list(dataset["folded_hole_cells"]),
            option_specs=list(dataset["option_specs"]),
            grid_size=int(dataset["grid_size"]),
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
                "object_description_fold_strip",
                "object_description_fold_card",
                "object_description_fold_outline",
                "evidence_hint_single_fold_single_hole",
                "evidence_hint_single_fold_two_holes",
                "evidence_hint_double_fold_single_hole",
                "json_example_single_fold_single_hole",
                "json_example_single_fold_two_holes",
                "json_example_double_fold_single_hole",
                "json_example_answer_only_single_fold_single_hole",
                "json_example_answer_only_single_fold_two_holes",
                "json_example_answer_only_double_fold_single_hole",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(task_variant)}"])
        json_example = str(prompt_defaults[f"json_example_{str(task_variant)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(task_variant)}"])

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

        correct_option_panel_id = str(dataset["correct_option_panel_id"])
        evidence_projection = projected_puzzle_bbox_evidence(
            rendered_scene.option_panel_bbox_map,
            [str(correct_option_panel_id)],
        )
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_value = str(dataset["answer_option_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        option_scan = normalize_int_with_bounds(int(dataset["option_count"]), [5, 7])
        punch_scan = normalize_int_with_bounds(int(dataset["punch_count"]), [1, 2])
        complexity_components = {
            "visual_scan": float(clamp_unit_interval((0.55 * float(option_scan)) + (0.45 * float(punch_scan)))),
            "reasoning_load": float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)]),
            "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
        }
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components=complexity_components,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_spatial_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "answer_option_label": str(answer_value),
                    "correct_option_panel_id": str(correct_option_panel_id),
                    "view_family": "fold_hole_unfold_mcq",
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
                    "option_count": int(dataset["option_count"]),
                    "grid_size": int(dataset["grid_size"]),
                    "punch_count": int(dataset["punch_count"]),
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
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "reference_panel_bbox_px": list(rendered_scene.reference_panel_bbox_px),
                "step_panel_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.step_panel_bbox_map.items()
                },
                "option_panel_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_panel_bbox_map.items()
                },
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "fold_mode": str(dataset["fold_mode"]),
                "fold_axes": list(dataset["fold_axes"]),
                "grid_size": int(dataset["grid_size"]),
                "punch_count": int(dataset["punch_count"]),
                "folded_hole_cells": [list(cell) for cell in dataset["folded_hole_cells"]],
                "unfolded_hole_cells": [list(cell) for cell in dataset["unfolded_hole_cells"]],
                "option_count": int(dataset["option_count"]),
                "option_specs": [dict(item) for item in dataset["option_specs"]],
                "answer_option_label": str(answer_value),
                "correct_option_panel_id": str(correct_option_panel_id),
                "correct_option_index": int(dataset["correct_option_index"]),
                "supporting_option_panel_ids": [str(correct_option_panel_id)],
                "solver_trace": {
                    "correct_option_label": str(answer_value),
                    "correct_option_index": int(dataset["correct_option_index"]),
                    "unfolded_hole_cells": [list(cell) for cell in dataset["unfolded_hole_cells"]],
                },
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


__all__ = ["PuzzlesSpatialFoldHoleLabelTask"]
