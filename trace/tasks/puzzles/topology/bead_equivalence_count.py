"""Puzzle topology task that counts bead loops equivalent to a reference loop."""

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
from ..shared.bead_loop_common import (
    PuzzleBeadLoopDefaults,
    SUPPORTED_PUZZLE_BEAD_LOOP_TASK_VARIANTS,
    bead_sequences_are_rotation_equivalent,
    build_bead_equivalence_dataset_for_variant,
    resolve_bead_loop_render_params,
    resolve_bead_loop_scene_variant,
    resolve_bead_loop_task_variant,
)
from ..shared.bead_loop_scene import render_puzzle_bead_loop_scene
from ..shared.common import projected_puzzle_bbox_evidence
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "task_puzzles_topology_bead_equivalence_count"
_REASONING_LOAD_BASE_BY_VARIANT = {
    "color_cycle_count": 0.28,
    "shape_cycle_count": 0.34,
    "mixed_cycle_count": 0.48,
}
_SCENE_LOAD_BY_VARIANT = {
    "loop_strip": 0.14,
    "loop_card": 0.20,
    "loop_outline": 0.17,
}

_DEFAULTS = PuzzleBeadLoopDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "topology")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="topology")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="topology", apply_prob=0.0)


@register_task
class PuzzlesTopologyBeadEquivalenceCountTask:
    """Count the option loops that preserve the reference loop's cyclic bead order."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "topology"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = resolve_bead_loop_task_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_variant, scene_variant_probabilities = resolve_bead_loop_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_bead_equivalence_dataset_for_variant(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        render_params = resolve_bead_loop_render_params(
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
        rendered_scene = render_puzzle_bead_loop_scene(
            background,
            scene_variant=str(scene_variant),
            reference_bead_specs=list(dataset["reference_bead_specs"]),
            reference_loop_shape_variant=str(dataset["reference_loop_shape_variant"]),
            reference_start_angle_deg=int(dataset["reference_start_angle_deg"]),
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
                "object_description_loop_strip",
                "object_description_loop_card",
                "object_description_loop_outline",
                "evidence_hint_color_cycle_count",
                "evidence_hint_shape_cycle_count",
                "evidence_hint_mixed_cycle_count",
                "json_example_color_cycle_count",
                "json_example_shape_cycle_count",
                "json_example_mixed_cycle_count",
                "json_example_answer_only_color_cycle_count",
                "json_example_answer_only_shape_cycle_count",
                "json_example_answer_only_mixed_cycle_count",
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

        valid_option_choice_ids = [str(value) for value in dataset["valid_option_choice_ids"]]
        evidence_projection = projected_puzzle_bbox_evidence(
            rendered_scene.option_choice_bbox_map,
            list(valid_option_choice_ids),
        )
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_value = int(dataset["valid_option_count"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        visual_scan = max(
            float(normalize_int_with_bounds(int(dataset["option_count"]), list(dataset["option_count_range"]))),
            float(normalize_int_with_bounds(int(dataset["bead_count"]), list(dataset["bead_count_range"]))),
        )
        reasoning_load = min(
            1.0,
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)])
            + (0.18 * float(normalize_int_with_bounds(int(dataset["valid_option_count"]), list(dataset["valid_option_count_range"])))),
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
                "scene_kind": f"puzzle_topology_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "answer_value": int(answer_value),
                    "equivalence_rule": str(dataset["equivalence_rule"]),
                    "valid_option_choice_ids": list(valid_option_choice_ids),
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
                    "bead_count": int(dataset["bead_count"]),
                    "valid_option_count": int(dataset["valid_option_count"]),
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
                "reference_loop_bbox_px": list(rendered_scene.reference_loop_bbox_px),
                "option_choice_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_choice_bbox_map.items()
                },
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "equivalence_rule": str(dataset["equivalence_rule"]),
                "reference_token_sequence": [str(value) for value in dataset["reference_token_sequence"]],
                "reference_loop_shape_variant": str(dataset["reference_loop_shape_variant"]),
                "reference_start_angle_deg": int(dataset["reference_start_angle_deg"]),
                "option_specs": [dict(option) for option in dataset["option_specs"]],
                "option_count": int(dataset["option_count"]),
                "option_count_range": list(dataset["option_count_range"]),
                "valid_option_count": int(dataset["valid_option_count"]),
                "valid_option_count_range": list(dataset["valid_option_count_range"]),
                "bead_count": int(dataset["bead_count"]),
                "bead_count_range": list(dataset["bead_count_range"]),
                "valid_option_choice_ids": list(valid_option_choice_ids),
                "valid_option_labels": [str(value) for value in dataset["valid_option_labels"]],
                "supporting_option_choice_ids": list(valid_option_choice_ids),
                "answer_value": int(answer_value),
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

        # Sanity-check the generated option partition once before returning.
        reference_tokens = [str(value) for value in dataset["reference_token_sequence"]]
        for option in dataset["option_specs"]:
            is_equivalent = bead_sequences_are_rotation_equivalent(reference_tokens, option["token_sequence"])
            if bool(is_equivalent) != bool(option["is_valid"]):
                raise ValueError("topology bead-loop option validity drifted from the equivalence rule")

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


__all__ = ["PuzzlesTopologyBeadEquivalenceCountTask"]
