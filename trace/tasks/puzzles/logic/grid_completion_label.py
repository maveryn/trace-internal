"""Puzzle logic task that completes a missing grid cell using image options."""

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
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.logic_common import (
    PuzzleLogicDefaults,
    SUPPORTED_PUZZLE_LOGIC_SCENE_VARIANTS,
    build_logic_grid_dataset_for_variant,
    resolve_logic_render_params,
    resolve_logic_scene_variant,
)
from ..shared.logic_scene import render_puzzle_logic_scene
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "task_puzzles_logic_grid_completion_label"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "row_uniqueness",
    "column_uniqueness",
    "row_and_column_uniqueness",
)
_REASONING_LOAD_BASE_BY_VARIANT = {
    "row_uniqueness": 0.26,
    "column_uniqueness": 0.32,
    "row_and_column_uniqueness": 0.56,
}
_SCENE_LOAD_BY_VARIANT = {
    "logic_strip": 0.16,
    "logic_card": 0.24,
    "logic_outline": 0.2,
}

_DEFAULTS = PuzzleLogicDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "logic")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="logic")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="logic", apply_prob=0.0)


def _resolve_task_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic logic-grid variant."""

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
class PuzzlesLogicGridCompletionLabelTask:
    """Choose the image option that correctly completes one logic-grid puzzle."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "logic"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = _resolve_task_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = resolve_logic_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_logic_grid_dataset_for_variant(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )

        render_params = resolve_logic_render_params(
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
        rendered_scene = render_puzzle_logic_scene(
            background,
            scene_variant=str(scene_variant),
            grid_rows=list(dataset["grid_rows"]),
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
                "object_description_logic_strip",
                "object_description_logic_card",
                "object_description_logic_outline",
                "evidence_hint_row_uniqueness",
                "evidence_hint_column_uniqueness",
                "evidence_hint_row_and_column_uniqueness",
                "json_example_row_uniqueness",
                "json_example_column_uniqueness",
                "json_example_row_and_column_uniqueness",
                "json_example_answer_only_row_uniqueness",
                "json_example_answer_only_column_uniqueness",
                "json_example_answer_only_row_and_column_uniqueness",
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

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_logic_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "answer_option_label": str(answer_value),
                    "query_cell_id": str(dataset["query_cell_id"]),
                    "correct_option_panel_id": str(correct_option_panel_id),
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
                    "board_size": int(dataset["board_size"]),
                    "board_size_range": list(dataset["board_size_range"]),
                    "cell_count": int(dataset["cell_count"]),
                    "cell_count_range": list(dataset["cell_count_range"]),
                    "option_count": int(dataset["option_count"]),
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
                    "option_label_font_size_px": int(render_params.option_label_font_size_px),
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "cell_bboxes_px": {str(key): list(value) for key, value in rendered_scene.cell_bbox_map.items()},
                "option_panel_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_panel_bbox_map.items()
                },
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "query_cell_id": str(dataset["query_cell_id"]),
                "query_row_index": int(dataset["query_row_index"]),
                "query_col_index": int(dataset["query_col_index"]),
                "board_size": int(dataset["board_size"]),
                "board_size_range": list(dataset["board_size_range"]),
                "cell_count": int(dataset["cell_count"]),
                "cell_count_range": list(dataset["cell_count_range"]),
                "board_values": [[str(value) for value in row] for row in dataset["board_values"]],
                "grid_rows": [[dict(cell) for cell in row] for row in dataset["grid_rows"]],
                "symbol_pool": [str(value) for value in dataset["symbol_pool"]],
                "answer_object_type": str(dataset["answer_object_type"]),
                "answer_option_label": str(answer_value),
                "correct_option_index": int(dataset["correct_option_index"]),
                "correct_option_panel_id": str(correct_option_panel_id),
                "option_count": int(dataset["option_count"]),
                "option_specs": [dict(option) for option in dataset["option_specs"]],
                "solver_trace": dict(dataset["solver_trace"]),
                "task_variant_probabilities": dict(task_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "supporting_option_panel_ids": [str(correct_option_panel_id)],
                "question_format": "logic_grid_mcq",
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }

        board_size_norm = normalize_int_with_bounds(
            int(dataset["board_size"]),
            list(dataset["board_size_range"]),
        )
        reasoning_load = min(
            1.0,
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)]) + (0.18 * float(board_size_norm)),
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


__all__ = ["PuzzlesLogicGridCompletionLabelTask"]
