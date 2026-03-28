"""Puzzle arithmetic task with one explicit unknown slot in an equation scene."""

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
from ..shared.arithmetic_common import (
    PuzzleArithmeticDefaults,
    SUPPORTED_PUZZLE_ARITHMETIC_SCENE_VARIANTS,
    adjust_render_params_for_equation_rows,
    build_arithmetic_equation_dataset_for_variant,
    projected_puzzle_bbox_evidence,
    resolve_arithmetic_render_params,
    resolve_puzzle_axis_variant,
)
from ..shared.arithmetic_scene import render_puzzle_arithmetic_scene
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "task_puzzles_arithmetic_equation_value"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "result_unknown",
    "operand_unknown",
)
_REASONING_LOAD_BASE_BY_VARIANT = {
    "result_unknown": 0.28,
    "operand_unknown": 0.48,
}
_SCENE_LOAD_BY_VARIANT = {
    "equation_strip": 0.15,
    "equation_card": 0.25,
    "equation_outline": 0.2,
}

_DEFAULTS = PuzzleArithmeticDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "arithmetic")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="arithmetic")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="arithmetic", apply_prob=0.0)


def _resolve_task_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic arithmetic puzzle variant."""

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


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the visual arithmetic puzzle scene variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_ARITHMETIC_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


@register_task
class PuzzlesArithmeticEquationValueTask:
    """Return the integer that should fill the explicit unknown slot in one arithmetic puzzle."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "arithmetic"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = _resolve_task_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = build_arithmetic_equation_dataset_for_variant(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )

        render_params = resolve_arithmetic_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
        )
        render_params = adjust_render_params_for_equation_rows(
            render_params,
            equation_rows=list(dataset["equation_rows"]),
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_puzzle_arithmetic_scene(
            background,
            scene_variant=str(scene_variant),
            equation_rows=list(dataset["equation_rows"]),
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
                "object_description_equation_strip",
                "object_description_equation_card",
                "object_description_equation_outline",
                "evidence_hint_result_unknown",
                "evidence_hint_operand_unknown",
                "json_example_result_unknown",
                "json_example_operand_unknown",
                "json_example_answer_only_result_unknown",
                "json_example_answer_only_operand_unknown",
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

        query_slot_id = str(dataset["query_slot_id"])
        evidence_projection = projected_puzzle_bbox_evidence(rendered_scene.slot_bbox_map, [str(query_slot_id)])
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_arithmetic_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "answer_value": int(answer_value),
                    "query_slot_id": str(query_slot_id),
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
                    "slot_count": int(dataset["slot_count"]),
                    "slot_count_range": list(dataset["slot_count_range"]),
                    "operand_count": int(dataset["operand_count"]),
                    "operand_count_range": list(dataset["operand_count_range"]),
                    "step_count": int(dataset["step_count"]),
                    "answer_range": list(dataset["answer_range"]),
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
                    "value_font_size_px": int(render_params.value_font_size_px),
                    "operator_font_size_px": int(render_params.operator_font_size_px),
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "slot_bboxes_px": {str(key): list(value) for key, value in rendered_scene.slot_bbox_map.items()},
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "answer_value": int(answer_value),
                "query_slot_id": str(query_slot_id),
                "equation_rows": [[dict(token) for token in row] for row in dataset["equation_rows"]],
                "solver_trace": dict(dataset["solver_trace"]),
                "slot_count": int(dataset["slot_count"]),
                "slot_count_range": list(dataset["slot_count_range"]),
                "operand_count": int(dataset["operand_count"]),
                "operand_count_range": list(dataset["operand_count_range"]),
                "step_count": int(dataset["step_count"]),
                "answer_range": list(dataset["answer_range"]),
                "max_visible_value": int(dataset["max_visible_value"]),
                "task_variant_probabilities": dict(task_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "supporting_slot_ids": [str(query_slot_id)],
                "question_format": "unknown_slot_equation",
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }

        operator_symbols = [str(symbol) for symbol in dataset["solver_trace"]["operator_symbols"]]
        operator_variety_norm = (
            (len(set(operator_symbols)) - 1) / 2.0
            if operator_symbols
            else 0.0
        )
        multiply_load = 0.15 if "×" in set(operator_symbols) else 0.0
        reasoning_load = min(
            1.0,
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)])
            + (0.15 * float(normalize_int_with_bounds(int(dataset["operand_count"]), [2, 5])))
            + (0.1 * float(operator_variety_norm))
            + float(multiply_load),
        )

        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(dataset["slot_count"]), list(dataset["slot_count_range"])),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )
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


__all__ = ["PuzzlesArithmeticEquationValueTask"]
