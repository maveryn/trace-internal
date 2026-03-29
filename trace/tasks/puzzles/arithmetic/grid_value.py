"""Puzzle arithmetic task with one explicit unknown cell in a rule-induction grid."""

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
    PuzzleArithmeticGridDefaults,
    SUPPORTED_PUZZLE_GRID_SCENE_VARIANTS,
    build_arithmetic_grid_dataset_for_variant,
    projected_puzzle_bbox_evidence,
    resolve_grid_render_params,
    resolve_puzzle_axis_variant,
)
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.grid_scene import render_puzzle_grid_scene
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "task_puzzles_arithmetic_grid_value"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "sum_rule_missing",
    "difference_rule_missing",
    "product_rule_missing",
)
_REASONING_LOAD_BASE_BY_VARIANT = {
    "sum_rule_missing": 0.28,
    "difference_rule_missing": 0.4,
    "product_rule_missing": 0.56,
}
_SCENE_LOAD_BY_VARIANT = {
    "grid_strip": 0.16,
    "grid_card": 0.24,
    "grid_outline": 0.2,
}

_DEFAULTS = PuzzleArithmeticGridDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "arithmetic")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="arithmetic")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="arithmetic", apply_prob=0.0)


def _resolve_task_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic arithmetic-grid puzzle variant."""

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
    """Resolve the visual arithmetic-grid scene variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_GRID_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


@register_task
class PuzzlesArithmeticGridValueTask:
    """Return the integer that should fill the explicit unknown cell in one arithmetic puzzle grid."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "arithmetic"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = _resolve_task_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = build_arithmetic_grid_dataset_for_variant(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )

        render_params = resolve_grid_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_puzzle_grid_scene(
            background,
            scene_variant=str(scene_variant),
            grid_rows=list(dataset["grid_rows"]),
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
                "object_description_grid_strip",
                "object_description_grid_card",
                "object_description_grid_outline",
                "evidence_hint_sum_rule_missing",
                "evidence_hint_difference_rule_missing",
                "evidence_hint_product_rule_missing",
                "json_example_sum_rule_missing",
                "json_example_difference_rule_missing",
                "json_example_product_rule_missing",
                "json_example_answer_only_sum_rule_missing",
                "json_example_answer_only_difference_rule_missing",
                "json_example_answer_only_product_rule_missing",
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

        query_cell_id = str(dataset["query_cell_id"])
        evidence_projection = projected_puzzle_bbox_evidence(rendered_scene.cell_bbox_map, [str(query_cell_id)])
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_grid_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "answer_value": int(answer_value),
                    "query_cell_id": str(query_cell_id),
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
                    "row_count": int(dataset["row_count"]),
                    "row_count_range": list(dataset["row_count_range"]),
                    "col_count": int(dataset["col_count"]),
                    "cell_count": int(dataset["cell_count"]),
                    "cell_count_range": list(dataset["cell_count_range"]),
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
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "cell_bboxes_px": {str(key): list(value) for key, value in rendered_scene.cell_bbox_map.items()},
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "answer_value": int(answer_value),
                "query_cell_id": str(query_cell_id),
                "grid_rows": [[dict(cell) for cell in row] for row in dataset["grid_rows"]],
                "row_values": [[int(value) for value in row] for row in dataset["row_values"]],
                "visible_example_rows": [[int(value) for value in row] for row in dataset["visible_example_rows"]],
                "solver_trace": dict(dataset["solver_trace"]),
                "row_count": int(dataset["row_count"]),
                "row_count_range": list(dataset["row_count_range"]),
                "col_count": int(dataset["col_count"]),
                "cell_count": int(dataset["cell_count"]),
                "cell_count_range": list(dataset["cell_count_range"]),
                "query_row_index": int(dataset["query_row_index"]),
                "query_col_index": int(dataset["query_col_index"]),
                "answer_range": list(dataset["answer_range"]),
                "max_visible_value": int(dataset["max_visible_value"]),
                "task_variant_probabilities": dict(task_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "supporting_cell_ids": [str(query_cell_id)],
                "question_format": "unknown_cell_grid",
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }

        operand_hidden_bonus = 0.12 if int(dataset["query_col_index"]) in {0, 1} else 0.0
        reasoning_load = min(
            1.0,
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)])
            + (0.15 * float(normalize_int_with_bounds(int(dataset["row_count"]), list(dataset["row_count_range"]))))
            + float(operand_hidden_bonus),
        )

        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(dataset["cell_count"]), list(dataset["cell_count_range"])),
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


__all__ = ["PuzzlesArithmeticGridValueTask"]
