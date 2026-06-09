"""Puzzle topology cyclic-order equivalence task."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping

from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
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
    SUPPORTED_PUZZLE_CYCLIC_ORDER_TOKEN_RENDER_STYLES,
    SUPPORTED_PUZZLE_LOOP_PATH_STYLES,
    bead_sequences_are_rotation_equivalent,
    build_bead_equivalence_dataset_for_variant,
    resolve_bead_loop_render_params,
    resolve_bead_loop_scene_variant,
    resolve_bead_loop_query_id,
    resolve_cyclic_order_path_style,
    resolve_cyclic_order_token_render_style,
)
from ..shared.bead_loop_scene import render_puzzle_bead_loop_scene
from ..shared.common import projected_puzzle_bbox_annotation
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.fixed_query_task import FixedPuzzleQueryVariantTaskMixin
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "puzzles_topology_cyclic_order_match_internal"
CYCLIC_ORDER_EQUIVALENT_LABEL_TASK_ID = "task_puzzles__cyclic_order__cyclic_order_equivalent_label"
SCENE_ID = "cyclic_order"
_REASONING_LOAD_BASE_BY_VARIANT = {
    "cyclic_order_equivalent_label": 0.34,
}
_TOKEN_RENDER_STYLE_LOAD = {
    "colored_beads": 0.00,
    "shape_tokens": 0.04,
    "colored_shape_tokens": 0.10,
    "outline_shape_tokens": 0.08,
    "symbol_badges": 0.12,
}
_SCENE_LOAD_BY_VARIANT = {
    "necklace_board": 0.14,
    "charm_card_grid": 0.20,
    "route_loop_diagram": 0.18,
    "token_ring_outline": 0.17,
}
_LOOP_PATH_STYLE_LOAD = {
    "ellipse": 0.00,
    "rounded_rect": 0.03,
    "polygon_loop": 0.04,
    "wavy_loop": 0.06,
    "beaded_string": 0.05,
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


def _sampling_params_for_axis(
    params: Mapping[str, Any],
    *,
    explicit_keys: tuple[str, ...],
    base_divisor: int,
    offset_cycle: int | None = None,
) -> Mapping[str, Any]:
    """Return params unchanged for axis-selection call sites."""

    _ = explicit_keys, int(base_divisor), offset_cycle
    return params


class _PuzzlesTopologyCyclicOrderMatchBaseTask:
    """Compare option loops against a reference loop's cyclic token order."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "topology"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = resolve_bead_loop_query_id(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        task_axis_divisor = 1
        token_params = _sampling_params_for_axis(
            params,
            explicit_keys=("token_render_style", "bead_token_mode"),
            base_divisor=int(task_axis_divisor),
        )
        token_render_style, token_render_style_probabilities = resolve_cyclic_order_token_render_style(
            token_params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_params = _sampling_params_for_axis(
            params,
            explicit_keys=("scene_variant",),
            base_divisor=int(task_axis_divisor),
        )
        scene_variant, scene_variant_probabilities = resolve_bead_loop_scene_variant(
            scene_params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        loop_path_params = _sampling_params_for_axis(
            params,
            explicit_keys=("loop_path_style",),
            base_divisor=int(task_axis_divisor),
            offset_cycle=len(SUPPORTED_PUZZLE_CYCLIC_ORDER_TOKEN_RENDER_STYLES),
        )
        loop_path_style, loop_path_style_probabilities = resolve_cyclic_order_path_style(
            loop_path_params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        _ = int(task_axis_divisor)
        dataset_params: Mapping[str, Any] = params
        dataset = build_bead_equivalence_dataset_for_variant(
            query_id=str(query_id),
            token_render_style=str(token_render_style),
            loop_path_style=str(loop_path_style),
            params=dataset_params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        render_params = resolve_bead_loop_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.cyclic_order_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            instruction_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            border_color_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
            loop_color_rgb=tuple(int(value) for value in scene_style.grid_rgb),
            text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = render_puzzle_bead_loop_scene(
            background,
            scene_variant=str(scene_variant),
            reference_bead_specs=list(dataset["reference_bead_specs"]),
            reference_loop_shape_variant=str(dataset["reference_loop_shape_variant"]),
            reference_loop_path_style=str(dataset["reference_loop_path_style"]),
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
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_cyclic_order_equivalent_label",
                "object_description_necklace_board",
                "object_description_charm_card_grid",
                "object_description_route_loop_diagram",
                "object_description_token_ring_outline",
                "annotation_hint_cyclic_order_equivalent_label",
                "json_example_cyclic_order_equivalent_label",
                "json_example_answer_only_cyclic_order_equivalent_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        annotation_hint = str(prompt_defaults[f"annotation_hint_{str(query_id)}"])
        json_example = str(prompt_defaults[f"json_example_{str(query_id)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"])
        token_render_style_instruction = {
            "colored_beads": "Use the token colors when comparing cyclic order.",
            "shape_tokens": "Use the token shapes when comparing cyclic order.",
            "colored_shape_tokens": "Use both token color and token shape when comparing cyclic order.",
            "outline_shape_tokens": "Use the outlined token shapes when comparing cyclic order.",
            "symbol_badges": "Use both the badge symbol and badge color when comparing cyclic order.",
        }[str(token_render_style)]

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "token_render_style_instruction": str(token_render_style_instruction),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        valid_option_choice_ids = [str(value) for value in dataset["valid_option_choice_ids"]]
        annotation_projection = projected_puzzle_bbox_annotation(
            rendered_scene.option_choice_bbox_map,
            list(valid_option_choice_ids),
        )
        annotation_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in annotation_projection["bbox_set"]
        ]
        if str(query_id) == "cyclic_order_equivalent_label":
            answer_value = str(dataset["answer_option_label"])
            answer_gt = TypedValue(type="option_letter", value=str(answer_value))
        else:
            answer_value = int(dataset["valid_option_count"])
            answer_gt = TypedValue(type="integer", value=int(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        visual_scan = max(
            float(normalize_int_with_bounds(int(dataset["option_count"]), list(dataset["option_count_range"]))),
            float(normalize_int_with_bounds(int(dataset["bead_count"]), list(dataset["bead_count_range"]))),
        )
        reasoning_load = min(
            1.0,
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(query_id)])
            + float(_TOKEN_RENDER_STYLE_LOAD[str(token_render_style)])
            + float(_LOOP_PATH_STYLE_LOAD[str(loop_path_style)])
            + (
                0.18
                * float(
                    normalize_int_with_bounds(
                        int(dataset["valid_option_count"]),
                        list(dataset["valid_option_count_range"]),
                    )
                )
                if len(set(int(value) for value in dataset["valid_option_count_range"])) > 1
                else 0.0
            ),
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
                    "query_id": str(query_id),
                    "token_render_style": str(token_render_style),
                    "bead_token_mode": str(dataset["bead_token_mode"]),
                    "loop_path_style": str(loop_path_style),
                    "scene_variant": str(scene_variant),
                    "answer_value": answer_value,
                    "equivalence_rule": str(dataset["equivalence_rule"]),
                    "valid_option_choice_ids": list(valid_option_choice_ids),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "token_render_style": str(token_render_style),
                    "bead_token_mode": str(dataset["bead_token_mode"]),
                    "loop_path_style": str(loop_path_style),
                    "scene_variant": str(scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "token_render_style_probabilities": dict(token_render_style_probabilities),
                    "loop_path_style_probabilities": dict(loop_path_style_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "option_count": int(dataset["option_count"]),
                    "bead_count": int(dataset["bead_count"]),
                    "valid_option_count": int(dataset["valid_option_count"]),
                    "min_color_distance": float(dataset["min_color_distance"]),
                    "color_distance_space": str(dataset["color_distance_space"]),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "loop_path_style": str(loop_path_style),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
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
                "query_id": str(query_id),
                "token_render_style": str(token_render_style),
                "bead_token_mode": str(dataset["bead_token_mode"]),
                "loop_path_style": str(loop_path_style),
                "scene_variant": str(scene_variant),
                "query_id_probabilities": dict(query_id_probabilities),
                "token_render_style_probabilities": dict(token_render_style_probabilities),
                "loop_path_style_probabilities": dict(loop_path_style_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "equivalence_rule": str(dataset["equivalence_rule"]),
                "reference_token_sequence": [str(value) for value in dataset["reference_token_sequence"]],
                "reference_loop_shape_variant": str(dataset["reference_loop_shape_variant"]),
                "reference_loop_path_style": str(dataset["reference_loop_path_style"]),
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
                "answer_option_choice_id": None
                if dataset["answer_option_choice_id"] is None
                else str(dataset["answer_option_choice_id"]),
                "answer_option_label": None
                if dataset["answer_option_label"] is None
                else str(dataset["answer_option_label"]),
                "supporting_option_choice_ids": list(valid_option_choice_ids),
                "min_color_distance": float(dataset["min_color_distance"]),
                "color_distance_space": str(dataset["color_distance_space"]),
                "answer_value": answer_value,
                "solver_trace": dict(dataset["solver_trace"]),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(annotation_bboxes),
            },
            "projected_annotation": dict(annotation_projection),
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
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
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PuzzlesTopologyCyclicOrderEquivalentLabelTask(
    FixedPuzzleQueryVariantTaskMixin,
    _PuzzlesTopologyCyclicOrderMatchBaseTask,
):
    """Identify the unique option loop with the same cyclic token order as the reference."""

    task_id = CYCLIC_ORDER_EQUIVALENT_LABEL_TASK_ID
    fixed_query_id = "cyclic_order_equivalent_label"
    public_scene_id = SCENE_ID


__all__ = [
    "PuzzlesTopologyCyclicOrderEquivalentLabelTask",
]
