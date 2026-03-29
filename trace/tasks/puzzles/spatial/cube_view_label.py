"""Puzzle spatial task that selects a cube view consistent with one visible corner."""

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
from ..shared.cube_scene import render_puzzle_cube_scene
from ..shared.spatial_cube_common import (
    PuzzleSpatialDefaults,
    SUPPORTED_PUZZLE_CUBE_SCENE_VARIANTS,
    build_cube_view_dataset_for_variant,
    resolve_spatial_render_params,
    resolve_spatial_scene_variant,
)
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "task_puzzles_spatial_cube_view_label"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "same_cube_view",
    "impossible_cube_view",
)
_REASONING_LOAD_BASE_BY_VARIANT = {
    "same_cube_view": 0.38,
    "impossible_cube_view": 0.54,
}
_SCENE_LOAD_BY_VARIANT = {
    "cube_strip": 0.16,
    "cube_card": 0.24,
    "cube_outline": 0.2,
}

_DEFAULTS = PuzzleSpatialDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="spatial")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="spatial", apply_prob=0.0)


def _resolve_task_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic cube-view variant."""

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
class PuzzlesSpatialCubeViewLabelTask:
    """Select the labeled option cube that matches the requested view property."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "spatial"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = _resolve_task_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = resolve_spatial_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_cube_view_dataset_for_variant(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )

        render_params = resolve_spatial_render_params(
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
        rendered_scene = render_puzzle_cube_scene(
            background,
            scene_variant=str(scene_variant),
            reference_view=dict(dataset["reference_view"]),
            opposite_pair_specs=list(dataset["opposite_pair_specs"]),
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
                "object_description_cube_strip",
                "object_description_cube_card",
                "object_description_cube_outline",
                "evidence_hint_same_cube_view",
                "evidence_hint_impossible_cube_view",
                "json_example_same_cube_view",
                "json_example_impossible_cube_view",
                "json_example_answer_only_same_cube_view",
                "json_example_answer_only_impossible_cube_view",
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

        complexity_components = {
            "visual_scan": float(normalize_int_with_bounds(int(dataset["option_count"]), [4, 4])),
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
                    "view_family": "cube_view_with_opposite_face_hints",
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
                    "visible_face_count": int(dataset["visible_face_count"]),
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
                "reference_cube_bbox_px": list(rendered_scene.reference_cube_bbox_px),
                "pair_box_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.pair_box_bbox_map.items()
                },
                "option_panel_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_panel_bbox_map.items()
                },
                "option_cube_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_cube_bbox_map.items()
                },
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "question_format": "cube_view_mcq",
                "view_family": "cube_view_with_opposite_face_hints",
                "reference_view": dict(dataset["reference_view"]),
                "face_object_types": dict(dataset["face_object_types"]),
                "reference_triplet": list(dataset["reference_triplet"]),
                "opposite_pair_specs": [dict(item) for item in dataset["opposite_pair_specs"]],
                "valid_triplets": [list(item) for item in dataset["valid_triplets"]],
                "invalid_triplets": [list(item) for item in dataset["invalid_triplets"]],
                "answer_option_label": str(answer_value),
                "correct_option_index": int(dataset["correct_option_index"]),
                "correct_option_panel_id": str(correct_option_panel_id),
                "option_specs": [dict(option) for option in dataset["option_specs"]],
                "option_labels": list(dataset["option_labels"]),
                "option_count": int(dataset["option_count"]),
                "visible_face_count": int(dataset["visible_face_count"]),
                "solver_trace": dict(dataset["solver_trace"]),
                "task_variant_probabilities": dict(task_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "supporting_option_panel_ids": [str(correct_option_panel_id)],
            },
            "answer": answer_gt.to_dict(),
            "evidence": evidence_gt.to_dict(),
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
            "complexity": complexity.to_dict(),
            "task_versions": default_task_versions(),
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


__all__ = [
    "PuzzlesSpatialCubeViewLabelTask",
]
