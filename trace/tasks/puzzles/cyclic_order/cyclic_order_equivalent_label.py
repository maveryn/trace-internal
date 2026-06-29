"""Public cyclic-order equivalent-loop label task."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.puzzles.shared.scene_style import (
    make_puzzle_scene_background,
    resolve_puzzle_scene_style,
)
from trace.tasks.puzzles.shared.visual_defaults import load_puzzle_noise_defaults
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import option_bbox_annotation
from .shared.output import build_trace_payload
from .shared.prompts import build_cyclic_order_prompt_artifacts
from .shared.rendering import render_cyclic_order_scene
from .shared.rules import token_sequences_are_rotation_equivalent
from .shared.sampling import (
    build_cyclic_order_dataset,
    resolve_loop_path_style,
    resolve_render_params,
    resolve_scene_variant,
    resolve_token_render_style,
)
from .shared.state import (
    DEFAULTS,
    DOMAIN,
    SCENE_ID,
    TOKEN_STYLE_PROMPT_INSTRUCTION,
)


TASK_ID = "task_puzzles__cyclic_order__cyclic_order_equivalent_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "cyclic_order_equivalent_label_query"
PROMPT_QUERY_KEY = SINGLE_QUERY_ID
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}"
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)
_NOISE_DEFAULTS = load_puzzle_noise_defaults(scene_id=SCENE_ID, apply_prob=0.15)


@register_task
class PuzzlesCyclicOrderEquivalentLabelTask:
    """Identify the only option loop with the same cyclic order as the reference."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> TaskOutput:
        """Generate a cyclic-order option-label task with scalar bbox annotation."""

        last_error: Exception | None = None
        attempts = max(1, int(max_attempts))
        for attempt_index in range(attempts):
            try:
                return _generate_once(
                    instance_seed=int(instance_seed) + int(attempt_index),
                    params=params,
                )
            except ValueError as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        raise RuntimeError("cyclic-order generation failed without a captured error")


def _generate_once(*, instance_seed: int, params: Dict[str, Any]) -> TaskOutput:
    """Construct one fully bound public task output."""

    selected_branch, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SINGLE_QUERY_ID,
        task_id=TASK_ID,
        namespace=f"{_NAMESPACE_BASE}.branch",
    )
    if str(selected_branch) != SINGLE_QUERY_ID:
        raise ValueError(f"unsupported cyclic-order branch: {selected_branch}")

    token_render_style, token_render_style_probabilities = resolve_token_render_style(
        params=task_params,
        generation_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace_base=_NAMESPACE_BASE,
    )
    scene_variant, scene_variant_probabilities = resolve_scene_variant(
        params=task_params,
        generation_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace_base=_NAMESPACE_BASE,
    )
    loop_path_style, loop_path_style_probabilities = resolve_loop_path_style(
        params=task_params,
        generation_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace_base=_NAMESPACE_BASE,
    )
    dataset = build_cyclic_order_dataset(
        token_render_style=str(token_render_style),
        loop_path_style=str(loop_path_style),
        params=task_params,
        instance_seed=int(instance_seed),
        generation_defaults=_GEN_DEFAULTS,
        defaults=DEFAULTS,
        namespace_base=_NAMESPACE_BASE,
    )
    render_params = resolve_render_params(
        task_params,
        rendering_defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
    )
    scene_style, scene_style_meta = resolve_puzzle_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{_NAMESPACE_BASE}.background",
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
    rendered_scene = render_cyclic_order_scene(
        background,
        scene_variant=str(scene_variant),
        reference_token_specs=list(dataset["reference_bead_specs"]),
        reference_loop_shape_variant=str(dataset["reference_loop_shape_variant"]),
        reference_loop_path_style=str(dataset["reference_loop_path_style"]),
        reference_start_angle_deg=int(dataset["reference_start_angle_deg"]),
        option_specs=list(dataset["option_specs"]),
        render_params=render_params,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=task_params,
        default_config=_NOISE_DEFAULTS,
    )

    answer_value = str(dataset["answer_option_label"])
    answer_gt = TypedValue(type="option_letter", value=str(answer_value))
    annotation_artifacts = option_bbox_annotation(
        rendered_scene.option_choice_bbox_map,
        str(dataset["answer_option_choice_id"]),
    )

    object_description = _object_description_for_scene(str(scene_variant))
    token_render_style_instruction = TOKEN_STYLE_PROMPT_INSTRUCTION[str(token_render_style)]
    prompt_defaults, prompt_artifacts = build_cyclic_order_prompt_artifacts(
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_query_key=PROMPT_QUERY_KEY,
        dynamic_slots={
            "object_description": str(object_description),
            "token_render_style_instruction": str(token_render_style_instruction),
        },
        instance_seed=int(instance_seed),
    )
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_branch),
        params={
            "query_id_probabilities": dict(branch_probabilities),
            "token_render_style": str(token_render_style),
            "token_render_style_probabilities": dict(token_render_style_probabilities),
            "loop_path_style": str(loop_path_style),
            "loop_path_style_probabilities": dict(loop_path_style_probabilities),
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "answer_option_label_probabilities": dict(dataset["answer_option_label_probabilities"]),
            "option_count": int(dataset["option_count"]),
            "bead_count": int(dataset["bead_count"]),
            "min_color_distance": float(dataset["min_color_distance"]),
            "color_distance_space": str(dataset["color_distance_space"]),
        },
    )

    _validate_option_partition(dataset)
    trace_payload = build_trace_payload(
        scene_ir={
            "scene_kind": f"puzzle_cyclic_order_{str(scene_variant)}",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "selected_branch": str(selected_branch),
                "token_render_style": str(token_render_style),
                "bead_token_mode": str(dataset["bead_token_mode"]),
                "loop_path_style": str(loop_path_style),
                "scene_variant": str(scene_variant),
                "answer_value": str(answer_value),
                "equivalence_rule": str(dataset["equivalence_rule"]),
                "valid_option_choice_ids": list(dataset["valid_option_choice_ids"]),
            },
        },
        prompt_defaults=prompt_defaults,
        prompt_artifacts=prompt_artifacts,
        semantic_spec=query_spec,
        render_spec={
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
        render_map={
            "image_id": "img0",
            "scene_bbox_px": list(rendered_scene.scene_bbox_px),
            "reference_loop_bbox_px": list(rendered_scene.reference_loop_bbox_px),
            "option_choice_bboxes_px": {
                str(key): list(value)
                for key, value in rendered_scene.option_choice_bbox_map.items()
            },
        },
        execution_trace={
            "query_id": str(selected_branch),
            "token_render_style": str(token_render_style),
            "bead_token_mode": str(dataset["bead_token_mode"]),
            "loop_path_style": str(loop_path_style),
            "scene_variant": str(scene_variant),
            "query_id_probabilities": dict(branch_probabilities),
            "token_render_style_probabilities": dict(token_render_style_probabilities),
            "loop_path_style_probabilities": dict(loop_path_style_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "answer_option_label_probabilities": dict(dataset["answer_option_label_probabilities"]),
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
            "bead_count": int(dataset["bead_count"]),
            "bead_count_range": list(dataset["bead_count_range"]),
            "valid_option_choice_ids": list(dataset["valid_option_choice_ids"]),
            "valid_option_labels": [str(value) for value in dataset["valid_option_labels"]],
            "answer_option_choice_id": str(dataset["answer_option_choice_id"]),
            "answer_option_label": str(dataset["answer_option_label"]),
            "supporting_option_choice_ids": list(dataset["valid_option_choice_ids"]),
            "min_color_distance": float(dataset["min_color_distance"]),
            "color_distance_space": str(dataset["color_distance_space"]),
            "answer_value": str(answer_value),
            "solver_trace": dict(dataset["solver_trace"]),
        },
        witness_symbolic={
            "type": "bbox",
            "value": list(annotation_artifacts.value),
        },
        projected_annotation=dict(annotation_artifacts.projected_annotation),
        answer_gt=answer_gt.to_dict(),
        annotation_gt=annotation_artifacts.annotation_gt.to_dict(),
    )

    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=answer_gt,
        annotation_gt=annotation_artifacts.annotation_gt,
        image=image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(selected_branch),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


def _object_description_for_scene(scene_variant: str) -> str:
    """Return concise scene wording for one cyclic-order visual style."""

    descriptions = {
        "necklace_board": "a reference token loop above six labeled option loops",
        "charm_card_grid": "a reference charm loop above six labeled option loops",
        "route_loop_diagram": "a reference route loop above six labeled option loops",
        "token_ring_outline": "a reference outlined token ring above six labeled option loops",
    }
    return descriptions.get(str(scene_variant), "a reference loop above six labeled option loops")


def _validate_option_partition(dataset: Dict[str, Any]) -> None:
    """Verify that option validity matches cyclic-order rotation equivalence."""

    reference_tokens = [str(value) for value in dataset["reference_token_sequence"]]
    for option in dataset["option_specs"]:
        is_equivalent = token_sequences_are_rotation_equivalent(
            reference_tokens,
            option["token_sequence"],
        )
        if bool(is_equivalent) != bool(option["is_valid"]):
            raise ValueError("cyclic-order option validity drifted from the equivalence rule")


__all__ = ["PuzzlesCyclicOrderEquivalentLabelTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
