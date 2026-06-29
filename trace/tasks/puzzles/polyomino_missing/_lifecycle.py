"""Neutral lifecycle helpers for polyomino missing-piece public tasks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, Mapping

from PIL import Image

from trace.core.visual.noise import apply_post_image_noise
from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.puzzles.shared.scene_style import (
    make_puzzle_scene_background,
    resolve_puzzle_scene_style,
)
from trace.tasks.puzzles.shared.visual_defaults import load_puzzle_noise_defaults
from trace.tasks.base import TaskOutput
from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts
from trace.tasks.shared.mcq import option_label_for_index
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import option_and_missing_region_annotation
from .shared.defaults import (
    resolve_answer_label,
    resolve_custom_render_params,
    resolve_option_count,
    resolve_render_params,
    resolve_scene_variant,
)
from .shared.output import build_trace_payload
from .shared.prompts import build_prompt
from .shared.rendering import render_polyomino_missing_scene
from .shared.state import SCENE_ID, RenderedPolyominoMissingScene


_NOISE_DEFAULTS = load_puzzle_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


@dataclass(frozen=True)
class PolyominoSceneArtifacts:
    """Rendered scene, prompt, and annotation artifacts for one public task."""

    image: Image.Image
    prompt: str
    prompt_variants: dict[str, str]
    prompt_meta: dict[str, Any]
    prompt_artifacts: PromptTraceArtifacts
    rendered_scene: RenderedPolyominoMissingScene
    render_params: Any
    background_meta: dict[str, Any]
    scene_style_meta: dict[str, Any]
    post_noise_meta: dict[str, Any]
    annotation_artifacts: AnnotationArtifacts


@dataclass(frozen=True)
class PolyominoOptionAxes:
    """Resolved presentation and answer axes for one option-label instance."""

    scene_variant: str
    scene_variant_probabilities: dict[str, float]
    option_count: int
    option_count_range: tuple[int, int]
    option_count_probabilities: dict[str, float]
    option_labels: tuple[str, ...]
    answer_label: str
    answer_label_probabilities: dict[str, float]


DatasetFactory = Callable[[int, Mapping[str, Any], PolyominoOptionAxes], Mapping[str, Any]]
TaskFieldFactory = Callable[[PolyominoOptionAxes, Mapping[str, Any]], Mapping[str, Any]]


def resolve_polyomino_option_axes(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    namespace_base: str,
    option_count_min_key: str,
    option_count_max_key: str,
    option_count_fallback_min: int,
    option_count_fallback_max: int,
    option_count_context: str,
    option_count_choices_key: str | None = None,
) -> PolyominoOptionAxes:
    """Resolve common visual/answer axes without owning task semantics."""

    axes_rng = spawn_rng(int(instance_seed), f"{str(namespace_base)}.axes")
    scene_variant, scene_variant_probabilities = resolve_scene_variant(
        params=params,
        generation_defaults=generation_defaults,
        instance_seed=int(instance_seed),
        namespace_base=str(namespace_base),
    )
    option_count, option_count_range, option_count_probabilities = resolve_option_count(
        axes_rng,
        params=params,
        generation_defaults=generation_defaults,
        min_key=str(option_count_min_key),
        max_key=str(option_count_max_key),
        choices_key=option_count_choices_key,
        fallback_min=int(option_count_fallback_min),
        fallback_max=int(option_count_fallback_max),
        context=str(option_count_context),
    )
    option_labels = tuple(option_label_for_index(index) for index in range(int(option_count)))
    answer_label, answer_label_probabilities = resolve_answer_label(
        axes_rng,
        labels=option_labels,
    )
    return PolyominoOptionAxes(
        scene_variant=str(scene_variant),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        option_count=int(option_count),
        option_count_range=(int(option_count_range[0]), int(option_count_range[1])),
        option_count_probabilities=dict(option_count_probabilities),
        option_labels=tuple(str(label) for label in option_labels),
        answer_label=str(answer_label),
        answer_label_probabilities=dict(answer_label_probabilities),
    )


def run_polyomino_option_task(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
    namespace_base: str,
    option_count_min_key: str,
    option_count_max_key: str,
    option_count_fallback_min: int,
    option_count_fallback_max: int,
    option_count_context: str,
    prompt_task_key: str,
    prompt_query_key: str,
    dataset_factory: DatasetFactory,
    task_field_factory: TaskFieldFactory,
    question_format: str,
    view_family: str,
    option_count_choices_key: str | None = None,
) -> TaskOutput:
    """Run common scene plumbing around task-owned objective hooks."""

    last_error: Exception | None = None
    for attempt_index in range(max(1, int(max_attempts))):
        attempt_seed = int(instance_seed) + int(attempt_index)
        try:
            axes = resolve_polyomino_option_axes(
                instance_seed=int(attempt_seed),
                params=params,
                generation_defaults=generation_defaults,
                namespace_base=str(namespace_base),
                option_count_min_key=str(option_count_min_key),
                option_count_max_key=str(option_count_max_key),
                option_count_choices_key=option_count_choices_key,
                option_count_fallback_min=int(option_count_fallback_min),
                option_count_fallback_max=int(option_count_fallback_max),
                option_count_context=str(option_count_context),
            )
            dataset = dict(dataset_factory(int(attempt_seed), params, axes))
            dataset["scene_variant"] = str(axes.scene_variant)
            artifacts = prepare_polyomino_scene(
                instance_seed=int(attempt_seed),
                params=params,
                rendering_defaults=rendering_defaults,
                prompt_defaults=prompt_defaults,
                dataset=dataset,
                scene_variant=str(axes.scene_variant),
                prompt_task_key=str(prompt_task_key),
                prompt_query_key=str(prompt_query_key),
                namespace_base=str(namespace_base),
            )
            answer_gt = TypedValue(type="option_letter", value=str(axes.answer_label))
            task_fields = {
                "query_id": str(selected_branch),
                "query_id_probabilities": dict(branch_probabilities),
                "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                "option_count": int(axes.option_count),
                "option_count_range": list(axes.option_count_range),
                "option_count_probabilities": dict(axes.option_count_probabilities),
                "answer_option_label_probabilities": dict(
                    axes.answer_label_probabilities
                ),
                "max_attempts": int(max_attempts),
                **dict(task_field_factory(axes, dataset)),
            }
            trace_payload = build_trace_payload(
                dataset=dataset,
                rendered_scene=artifacts.rendered_scene,
                render_params=artifacts.render_params,
                prompt_meta=artifacts.prompt_meta,
                task_fields=task_fields,
                background_meta=artifacts.background_meta,
                scene_style_meta=artifacts.scene_style_meta,
                post_noise_meta=artifacts.post_noise_meta,
                projected_annotation=artifacts.annotation_artifacts.projected_annotation,
                question_format=str(question_format),
                view_family=str(view_family),
            )
            trace_payload["query_spec"] = build_prompt_query_spec(
                prompt_artifacts=artifacts.prompt_artifacts,
                query_id=str(selected_branch),
                params=task_fields,
            )
            return TaskOutput(
                prompt=artifacts.prompt,
                prompt_variants=artifacts.prompt_variants,
                answer_gt=answer_gt,
                annotation_gt=artifacts.annotation_artifacts.annotation_gt,
                image=artifacts.image,
                image_id="img0",
                trace_payload=trace_payload,
                task_versions=default_task_versions(),
                scene_id=SCENE_ID,
                query_id=str(selected_branch),
            )
        except (RuntimeError, ValueError) as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise RuntimeError("polyomino missing-piece task failed")


def prepare_polyomino_scene(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    dataset: Mapping[str, Any],
    scene_variant: str,
    prompt_task_key: str,
    prompt_query_key: str,
    namespace_base: str,
) -> PolyominoSceneArtifacts:
    """Render one scene and derive prompt/annotation artifacts."""

    render_params = resolve_render_params(
        params,
        rendering_defaults=rendering_defaults,
        instance_seed=int(instance_seed),
    )
    scene_style, scene_style_meta = resolve_puzzle_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{str(namespace_base)}.background",
    )
    render_params = replace(
        render_params,
        panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
        option_panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
        option_shape_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
        shape_fill_rgb=tuple(int(value) for value in scene_style.mark_rgb),
        border_color_rgb=tuple(int(value) for value in scene_style.grid_rgb),
        text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
        text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
    )
    custom_render_params = resolve_custom_render_params(
        params,
        rendering_defaults=rendering_defaults,
        instance_seed=int(instance_seed),
    )
    custom_render_params = replace(
        custom_render_params,
        highlight_fill_rgb=tuple(int(value) for value in scene_style.step_fill_rgb),
        empty_cell_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
        board_grid_rgb=tuple(int(value) for value in scene_style.grid_rgb),
        marked_cell_rgb=tuple(int(value) for value in scene_style.mark_rgb),
        target_cell_rgb=tuple(int(value) for value in scene_style.step_fill_rgb),
    )
    background, background_meta = make_puzzle_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=scene_style,
    )
    rendered_scene = render_polyomino_missing_scene(
        background,
        scene_variant=str(scene_variant),
        dataset=dataset,
        render_params=render_params,
        custom_params=custom_render_params,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=_NOISE_DEFAULTS,
    )
    prompt, prompt_variants, prompt_meta, prompt_artifacts = build_prompt(
        prompt_defaults,
        scene_variant=str(scene_variant),
        prompt_task_key=str(prompt_task_key),
        prompt_query_key=str(prompt_query_key),
        instance_seed=int(instance_seed),
    )
    annotation_artifacts = option_and_missing_region_annotation(
        rendered_scene=rendered_scene,
        selected_option_panel_id=str(dataset["correct_option_panel_id"]),
    )
    return PolyominoSceneArtifacts(
        image=image,
        prompt=prompt,
        prompt_variants=prompt_variants,
        prompt_meta=prompt_meta,
        prompt_artifacts=prompt_artifacts,
        rendered_scene=rendered_scene,
        render_params=render_params,
        background_meta=dict(background_meta),
        scene_style_meta=dict(scene_style_meta),
        post_noise_meta=dict(post_noise_meta),
        annotation_artifacts=annotation_artifacts,
    )


__all__ = [
    "PolyominoOptionAxes",
    "PolyominoSceneArtifacts",
    "prepare_polyomino_scene",
    "resolve_polyomino_option_axes",
    "run_polyomino_option_task",
]
