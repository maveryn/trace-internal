"""Puzzle spatial task that chooses the silhouette buildable from shown pieces."""

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
from ..shared.assembly_common import (
    PuzzleAssemblyDefaults,
    SUPPORTED_PUZZLE_ASSEMBLY_TASK_VARIANTS,
    build_assembly_dataset_for_variant,
    resolve_assembly_render_params,
    resolve_assembly_scene_variant,
    resolve_assembly_task_variant,
)
from ..shared.assembly_scene import render_puzzle_assembly_scene
from ..shared.common import projected_puzzle_bbox_evidence
from ..shared.complexity import (
    build_puzzle_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_puzzle_complexity_weights,
)
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "task_puzzles_spatial_assembly_label"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = SUPPORTED_PUZZLE_ASSEMBLY_TASK_VARIANTS
_REASONING_LOAD_BASE_BY_VARIANT = {"can_be_built": 0.54}
_SCENE_LOAD_BY_VARIANT = {
    "assembly_strip": 0.16,
    "assembly_card": 0.22,
    "assembly_outline": 0.19,
}

_DEFAULTS = PuzzleAssemblyDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="spatial")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="spatial", apply_prob=0.0)


@register_task
class PuzzlesSpatialAssemblyLabelTask:
    """Choose the labeled silhouette that can be built from the shown pieces."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "spatial"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = resolve_assembly_task_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_variant, scene_variant_probabilities = resolve_assembly_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_assembly_dataset_for_variant(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        render_params = resolve_assembly_render_params(
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
        rendered_scene = render_puzzle_assembly_scene(
            background,
            scene_variant=str(scene_variant),
            piece_specs=list(dataset["piece_specs"]),
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
                "object_description_assembly_strip",
                "object_description_assembly_card",
                "object_description_assembly_outline",
                "evidence_hint_can_be_built",
                "json_example_can_be_built",
                "json_example_answer_only_can_be_built",
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

        visual_scan = 0.55 * normalize_int_with_bounds(int(dataset["piece_count"]), [3, 4]) + 0.45 * normalize_int_with_bounds(
            int(dataset["option_count"]), [5, 7]
        )
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)])
            + 0.20 * normalize_int_with_bounds(int(dataset["target_cell_count"]), [8, 11])
            + 0.10 * normalize_int_with_bounds(int(dataset["piece_count"]), [3, 4])
        )
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(visual_scan),
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
                    "correct_option_panel_id": str(correct_option_panel_id),
                    "view_family": "assembly_option_puzzle",
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
                    "piece_count": int(dataset["piece_count"]),
                    "piece_count_range": list(dataset["piece_count_range"]),
                    "option_count": int(dataset["option_count"]),
                    "option_count_range": list(dataset["option_count_range"]),
                    "target_cell_count": int(dataset["target_cell_count"]),
                    "target_cell_count_range": list(dataset["target_cell_count_range"]),
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
                "piece_card_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.piece_card_bbox_map.items()
                },
                "option_panel_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_panel_bbox_map.items()
                },
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "piece_specs": [dict(spec) for spec in dataset["piece_specs"]],
                "piece_count": int(dataset["piece_count"]),
                "piece_count_range": list(dataset["piece_count_range"]),
                "option_specs": [dict(spec) for spec in dataset["option_specs"]],
                "option_count": int(dataset["option_count"]),
                "option_count_range": list(dataset["option_count_range"]),
                "target_cells": [list(cell) for cell in dataset["target_cells"]],
                "target_bbox_dims": list(dataset["target_bbox_dims"]),
                "target_cell_count": int(dataset["target_cell_count"]),
                "target_cell_count_range": list(dataset["target_cell_count_range"]),
                "answer_option_label": str(answer_value),
                "correct_option_index": int(dataset["correct_option_index"]),
                "correct_option_panel_id": str(correct_option_panel_id),
                "supporting_option_panel_ids": [str(item) for item in dataset["valid_option_panel_ids"]],
                "question_format": "assembly_can_be_built",
                "view_family": "assembly_option_puzzle",
                "solver_trace": dict(dataset["solver_trace"]),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": dict(evidence_projection),
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


__all__ = ["PuzzlesSpatialAssemblyLabelTask"]
