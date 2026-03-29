"""Puzzle spatial task that counts cubes removed between two block stacks."""

from __future__ import annotations

from typing import Any, Dict, Mapping

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
from ..shared.block_stack_scene import render_puzzle_block_comparison_scene
from ..shared.common import projected_puzzle_bbox_evidence
from ..shared.complexity import (
    build_puzzle_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_puzzle_complexity_weights,
)
from ..shared.spatial_blocks_common import (
    PuzzleCubeRemovalDefaults,
    build_cube_removal_dataset_for_variant,
    resolve_block_scene_variant,
    resolve_block_stack_render_params,
    resolve_cube_removal_task_variant,
)
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "task_puzzles_spatial_cube_removal_count"
_REASONING_LOAD_BASE_BY_VARIANT = {
    "cube_removal_count": 0.38,
}
_SCENE_LOAD_BY_VARIANT = {
    "stack_strip": 0.12,
    "stack_card": 0.18,
    "stack_outline": 0.15,
}

_DEFAULTS = PuzzleCubeRemovalDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="spatial")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="spatial", apply_prob=0.0)


@register_task
class PuzzlesSpatialCubeRemovalCountTask:
    """Return the integer count of cubes removed between two shown structures."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "spatial"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = resolve_cube_removal_task_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_variant, scene_variant_probabilities = resolve_block_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_cube_removal_dataset_for_variant(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        render_params = resolve_block_stack_render_params(
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
        rendered_scene = render_puzzle_block_comparison_scene(
            background,
            scene_variant=str(scene_variant),
            original_height_rows=list(dataset["original_height_rows"]),
            original_cube_records=list(dataset["original_cube_records"]),
            remaining_height_rows=list(dataset["remaining_height_rows"]),
            remaining_cube_records=list(dataset["remaining_cube_records"]),
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
                "object_description_stack_strip",
                "object_description_stack_card",
                "object_description_stack_outline",
                "evidence_hint_cube_removal_count",
                "json_example_cube_removal_count",
                "json_example_answer_only_cube_removal_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults["evidence_hint_cube_removal_count"])
        json_example = str(prompt_defaults["json_example_cube_removal_count"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_cube_removal_count"])

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

        original_structure_bbox_id = str(dataset["original_structure_bbox_id"])
        remaining_structure_bbox_id = str(dataset["remaining_structure_bbox_id"])
        evidence_projection = projected_puzzle_bbox_evidence(
            rendered_scene.structure_bbox_map,
            [str(original_structure_bbox_id), str(remaining_structure_bbox_id)],
        )
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_value = int(dataset["removal_count"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        removal_scan = normalize_int_with_bounds(int(dataset["removal_count"]), list(dataset["removal_count_range"]))
        original_total_scan = normalize_int_with_bounds(int(dataset["original_total_cubes"]), [4, int(dataset["total_cubes_max"])])
        footprint_scan = normalize_int_with_bounds(int(dataset["row_count"] * dataset["col_count"]), [4, 16])
        changed_columns_scan = normalize_int_with_bounds(
            int(dataset["changed_column_count"]),
            [1, int(dataset["row_count"] * dataset["col_count"])],
        )
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)])
            + (0.20 * float(removal_scan))
            + (0.14 * float(changed_columns_scan))
        )
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": max(float(original_total_scan), float(footprint_scan)),
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
                    "answer_value": int(answer_value),
                    "original_structure_bbox_id": str(original_structure_bbox_id),
                    "remaining_structure_bbox_id": str(remaining_structure_bbox_id),
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
                    "row_count": int(dataset["row_count"]),
                    "col_count": int(dataset["col_count"]),
                    "original_max_height": int(dataset["original_max_height"]),
                    "original_total_cubes": int(dataset["original_total_cubes"]),
                    "remaining_total_cubes": int(dataset["remaining_total_cubes"]),
                    "removal_count": int(dataset["removal_count"]),
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
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "original_structure_bbox_px": list(rendered_scene.original_structure_bbox_px),
                "remaining_structure_bbox_px": list(rendered_scene.remaining_structure_bbox_px),
                "structure_bboxes_px": {str(key): list(value) for key, value in rendered_scene.structure_bbox_map.items()},
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "original_height_rows": [[int(value) for value in row] for row in dataset["original_height_rows"]],
                "remaining_height_rows": [[int(value) for value in row] for row in dataset["remaining_height_rows"]],
                "row_count": int(dataset["row_count"]),
                "row_count_range": list(dataset["row_count_range"]),
                "col_count": int(dataset["col_count"]),
                "col_count_range": list(dataset["col_count_range"]),
                "original_max_height": int(dataset["original_max_height"]),
                "original_max_height_range": list(dataset["original_max_height_range"]),
                "original_total_cubes": int(dataset["original_total_cubes"]),
                "remaining_total_cubes": int(dataset["remaining_total_cubes"]),
                "total_cubes_max": int(dataset["total_cubes_max"]),
                "removal_count": int(dataset["removal_count"]),
                "removal_count_range": list(dataset["removal_count_range"]),
                "changed_column_count": int(dataset["changed_column_count"]),
                "original_cube_records": [dict(record) for record in dataset["original_cube_records"]],
                "remaining_cube_records": [dict(record) for record in dataset["remaining_cube_records"]],
                "removed_cube_records": [dict(record) for record in dataset["removed_cube_records"]],
                "answer_value": int(answer_value),
                "original_structure_bbox_id": str(original_structure_bbox_id),
                "remaining_structure_bbox_id": str(remaining_structure_bbox_id),
                "task_variant_probabilities": dict(task_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "supporting_structure_ids": [str(original_structure_bbox_id), str(remaining_structure_bbox_id)],
                "solver_trace": dict(dataset["solver_trace"]),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": dict(evidence_projection),
            "answer_gt": answer_gt.to_dict(),
            "evidence_gt": evidence_gt.to_dict(),
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


__all__ = ["PuzzlesSpatialCubeRemovalCountTask"]
