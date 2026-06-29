"""Public pipe-flow task for selecting the rotatable repair tile option."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.sampling import support_probability_map, uniform_choice_with_probabilities
from trace.core.seed import spawn_rng
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

from .shared.annotations import pipe_flow_repair_annotation
from .shared.defaults import (
    resolve_candidate_count,
    resolve_grid_size_variant,
    resolve_render_params,
    resolve_scene_variant,
)
from .shared.output import build_trace_payload
from .shared.prompts import build_prompt
from .shared.rendering import render_pipe_flow_scene
from .shared.sampling import sample_pipe_flow_dataset
from .shared.state import LABEL_POOL, SCENE_ID

TASK_ID = "task_puzzles__pipe_flow__pipe_flow_repair_tile_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "pipe_flow_repair_tile_label"
_NAMESPACE_BASE = "puzzles.pipe_flow.pipe_flow_repair_tile_label"
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = (
    load_scene_generation_rendering_prompt_defaults("puzzles", SCENE_ID, task_id=TASK_ID)
)
_NOISE_DEFAULTS = load_puzzle_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


@register_task
class PuzzlesPipeFlowRepairTileLabelTask:
    """Choose the repair option that reconnects start to finish under rotation."""

    task_id = TASK_ID
    domain = "puzzles"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> TaskOutput:
        """Generate one pipe-flow repair task with role-keyed bbox annotation."""

        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                return _generate_one(
                    instance_seed=int(instance_seed) + int(attempt_index),
                    params=params,
                    max_attempts=int(max_attempts),
                )
            except (RuntimeError, ValueError) as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        raise RuntimeError("pipe-flow generation failed without a captured error")


def _generate_one(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Resolve task-owned axes, render the scene, and bind answer/annotation."""

    selected_query_id, query_id_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SINGLE_QUERY_ID,
        task_id=TASK_ID,
        namespace=f"{_NAMESPACE_BASE}.query",
    )
    axes_rng = spawn_rng(int(instance_seed), f"{_NAMESPACE_BASE}.axes")
    grid_size_variant, grid_size_variant_probabilities = resolve_grid_size_variant(
        axes_rng,
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
    )
    scene_variant, scene_variant_probabilities = resolve_scene_variant(
        axes_rng,
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
    )
    candidate_count, candidate_count_probabilities = resolve_candidate_count(
        axes_rng,
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
    )
    answer_label, answer_label_probabilities = _resolve_answer_label(
        params=task_params,
        instance_seed=int(instance_seed),
        candidate_count=int(candidate_count),
    )
    dataset = sample_pipe_flow_dataset(
        task_params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        grid_size_variant=str(grid_size_variant),
        scene_variant=str(scene_variant),
        candidate_count=int(candidate_count),
        answer_label=str(answer_label),
    )
    _validate_pipe_flow_dataset(dataset)

    render_params = resolve_render_params(
        task_params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
    )
    scene_style, scene_style_meta = resolve_puzzle_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{_NAMESPACE_BASE}.background",
    )
    render_params = replace(
        render_params,
        panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
        cell_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
        grid_line_rgb=tuple(int(value) for value in scene_style.grid_rgb),
        pipe_rgb=tuple(int(value) for value in scene_style.mark_rgb),
        pipe_shadow_rgb=tuple(int(value) for value in scene_style.notebook_line_rgb),
        label_fill_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
        label_text_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
        text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
    )
    background, background_meta = make_puzzle_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=scene_style,
    )
    rendered_scene = render_pipe_flow_scene(
        background=background,
        dataset=dataset,
        render_params=render_params,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=task_params,
        default_config=_NOISE_DEFAULTS,
    )
    prompt, prompt_variants, prompt_meta = build_prompt(
        _PROMPT_DEFAULTS,
        scene_variant=str(dataset.scene_variant),
        prompt_query_key=PROMPT_QUERY_KEY,
        instance_seed=int(instance_seed),
    )
    annotation_artifacts = pipe_flow_repair_annotation(
        dataset=dataset,
        rendered_scene=rendered_scene,
    )
    query_params = {
        "query_id": str(selected_query_id),
        "query_id_probabilities": dict(query_id_probabilities),
        "internal_question_format": "pipe_flow_repair_tile_label",
        "scene_id": SCENE_ID,
        "scene_variant": str(dataset.scene_variant),
        "scene_variant_probabilities": dict(scene_variant_probabilities),
        "grid_size_variant": str(dataset.grid_size_variant),
        "grid_size_variant_probabilities": dict(grid_size_variant_probabilities),
        "candidate_count": int(dataset.candidate_count),
        "candidate_count_probabilities": dict(candidate_count_probabilities),
        "answer_label": str(dataset.answer_label),
        "answer_label_probabilities": dict(answer_label_probabilities),
        "rows": int(dataset.rows),
        "cols": int(dataset.cols),
        "path_length": int(len(dataset.path_cells)),
        "branch_cell_count": int(len(dataset.branch_cells)),
        "branch_terminal_count": int(len(dataset.branch_terminal_cells)),
        "rotation_allowed": True,
        "max_attempts": int(max_attempts),
    }
    trace_payload = build_trace_payload(
        dataset=dataset,
        rendered_scene=rendered_scene,
        render_params=render_params,
        prompt_meta=prompt_meta,
        task_fields=query_params,
        background_meta=background_meta,
        scene_style_meta=scene_style_meta,
        post_noise_meta=post_noise_meta,
        projected_annotation=annotation_artifacts.projected_annotation,
        question_format=PROMPT_QUERY_KEY,
    )
    trace_payload["scene_ir"]["relations"]["query_id"] = str(selected_query_id)
    trace_payload["query_spec"] = {
        "query_id": str(selected_query_id),
        "template_id": str(prompt_meta["bundle_id"]),
        "prompt_variant": dict(prompt_meta["prompt_variant"]),
        "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
        "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
        "params": dict(query_params),
    }
    return TaskOutput(
        prompt=prompt,
        prompt_variants=prompt_variants,
        answer_gt=TypedValue(type="option_letter", value=str(dataset.answer_label)),
        annotation_gt=annotation_artifacts.annotation_gt,
        image=image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(selected_query_id),
    )


def _resolve_answer_label(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    candidate_count: int,
) -> tuple[str, dict[str, float]]:
    """Resolve the correct option label as a task-owned semantic operand."""

    labels = tuple(LABEL_POOL[index] for index in range(int(candidate_count)))
    explicit = params.get("answer_label")
    if explicit is not None:
        selected = str(explicit).strip().upper()
        if selected not in set(labels):
            raise ValueError(f"answer_label {selected!r} outside candidate labels")
        return selected, support_probability_map(labels, selected=selected)
    rng = spawn_rng(int(instance_seed), f"{_NAMESPACE_BASE}.answer_label")
    selected, probabilities = uniform_choice_with_probabilities(rng, labels)
    return str(selected), dict(probabilities)


def _validate_pipe_flow_dataset(dataset: Any) -> None:
    """Validate the sampled option set has exactly one labeled repair answer."""

    correct_options = [option for option in dataset.options if option.is_correct]
    if len(correct_options) != 1:
        raise ValueError("pipe-flow dataset must contain exactly one correct option")
    correct_option = correct_options[0]
    if str(correct_option.label) != str(dataset.answer_label):
        raise ValueError("pipe-flow answer label drifted from correct option")
    if str(correct_option.option_id) != str(dataset.correct_option_panel_id):
        raise ValueError("pipe-flow correct option id drifted from dataset")
    for option in dataset.options:
        if bool(option.is_correct) != bool(option.connects_after_rotation_turns):
            raise ValueError("pipe-flow option solvability does not match correctness")


__all__ = [
    "PuzzlesPipeFlowRepairTileLabelTask",
    "PROMPT_QUERY_KEY",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
