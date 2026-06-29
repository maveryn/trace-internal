"""Neutral rendering and output plumbing for overlay public tasks."""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any, Callable, Dict, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.puzzles.shared.scene_style import (
    make_puzzle_scene_background,
    resolve_puzzle_scene_style,
)
from trace.tasks.puzzles.shared.unit_size_jitter import with_puzzle_unit_size_jitter
from trace.tasks.puzzles.shared.visual_defaults import load_puzzle_noise_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import option_choice_bbox
from .shared.defaults import resolve_render_params, resolve_scene_variant
from .shared.output import build_trace_payload
from .shared.prompts import build_overlay_prompt_artifacts
from .shared.rendering import render_puzzle_overlay_scene
from .shared.sampling import solver_trace
from .shared.state import DOMAIN, OverlayDataset, SCENE_ID

_NOISE_DEFAULTS = load_puzzle_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)
INTERNAL_QUERY_ID = "overlay_union_same_grid"


def retry_overlay_generation(
    *,
    build_case: Callable[[int, Mapping[str, Any], int], TaskOutput],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Retry task-local construction when semantic constraints reject a seed."""

    last_error: Exception | None = None
    for attempt_index in range(max(1, int(max_attempts))):
        try:
            return build_case(
                instance_seed=int(instance_seed) + int(attempt_index),
                params=params,
                max_attempts=int(max_attempts),
            )
        except ValueError as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise RuntimeError("overlay generation failed without a captured error")


def resolve_overlay_public_branch(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    task_id: str,
    namespace: str,
) -> tuple[str, dict[str, float], Mapping[str, Any]]:
    """Resolve the no-branch public query id and return sanitized params."""

    selected_branch, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=(SINGLE_QUERY_ID,),
        default_query_id=SINGLE_QUERY_ID,
        task_id=str(task_id),
        namespace=f"{namespace}.branch",
    )
    if str(selected_branch) != SINGLE_QUERY_ID:
        raise ValueError(f"unsupported overlay public branch: {selected_branch}")
    return str(selected_branch), dict(branch_probabilities), task_params


def object_description_for_scene(scene_variant: str) -> str:
    """Return concise scene wording for one overlay visual treatment."""

    descriptions = {
        "overlay_strip": (
            "a transparent-sheet overlay puzzle with two aligned source sheets "
            "above labeled result options"
        ),
        "overlay_card": (
            "a card-style transparent-sheet overlay puzzle with two aligned "
            "source sheets above labeled result options"
        ),
        "overlay_outline": (
            "an outline-style transparent-sheet overlay puzzle with two aligned "
            "source sheets above labeled result options"
        ),
    }
    return descriptions.get(str(scene_variant), descriptions["overlay_strip"])


def prepare_overlay_visual_case(
    *,
    dataset: OverlayDataset,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    instance_seed: int,
    scene_variant: str,
    prompt_task_key: str,
    prompt_query_key: str,
    namespace: str,
) -> Dict[str, Any]:
    """Render a sampled overlay dataset and matching prompt artifacts."""

    render_params = resolve_render_params(
        params,
        rendering_defaults,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    scene_style, scene_style_meta = resolve_puzzle_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.background",
    )
    render_params = replace(
        render_params,
        panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
        paper_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
        paper_shadow_rgb=tuple(int(value) for value in scene_style.background_accent_rgb),
        border_color_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
        text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
        text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
        mark_fill_rgb=tuple(int(value) for value in scene_style.mark_rgb),
        mark_outline_rgb=tuple(int(value) for value in scene_style.grid_rgb),
        instruction_fill_rgb=tuple(int(value) for value in scene_style.panel_accent_rgb),
    )
    background, background_meta = make_puzzle_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=scene_style,
    )
    rendered_scene = render_puzzle_overlay_scene(
        background,
        scene_variant=str(scene_variant),
        grid_size=int(dataset.grid_size),
        left_mark_specs=dataset.left_mark_specs,
        right_mark_specs=dataset.right_mark_specs,
        option_specs=dataset.option_specs,
        render_params=render_params,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=_NOISE_DEFAULTS,
    )
    prompt_defaults, prompt_artifacts = build_overlay_prompt_artifacts(
        prompt_task_key=str(prompt_task_key),
        prompt_query_key=str(prompt_query_key),
        dynamic_slots={
            "object_description": object_description_for_scene(str(scene_variant)),
        },
        instance_seed=int(instance_seed),
    )
    return {
        "image": image,
        "rendered_scene": rendered_scene,
        "render_params": render_params,
        "scene_variant": str(scene_variant),
        "background_meta": dict(background_meta),
        "scene_style_meta": dict(scene_style_meta),
        "post_noise_meta": dict(post_noise_meta),
        "prompt_defaults": dict(prompt_defaults),
        "prompt_artifacts": prompt_artifacts,
    }


def render_spec_from_visual(visual: Mapping[str, Any]) -> Dict[str, Any]:
    """Build the common render-spec trace section from rendered visual metadata."""

    render_params = visual["render_params"]
    rendered_scene = visual["rendered_scene"]
    return {
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "coord_space": "pixel",
        "scene_variant": str(visual["scene_variant"]),
        "background_style": dict(visual["background_meta"]),
        "scene_style": {
            **dict(visual["scene_style_meta"]),
            "mark_shape": str(render_params.mark_shape),
            "mark_shape_probabilities": dict(render_params.mark_shape_probabilities),
        },
        "post_image_noise": dict(visual["post_noise_meta"]),
        "scene_bbox_px": list(rendered_scene.scene_bbox_px),
        "layout": "transparent_sheet_overlay_with_visual_options",
        "unit_size_jitter": dict(render_params.unit_size_jitter),
    }


def overlay_render_map(*, rendered_scene: Any, render_params: Any) -> Dict[str, Any]:
    """Build the common pixel render map for one rendered overlay scene."""

    return with_puzzle_unit_size_jitter(
        {
            "image_id": "img0",
            "scene_bbox_px": list(rendered_scene.scene_bbox_px),
            "reference_panel_bbox_px": list(rendered_scene.reference_panel_bbox_px),
            "source_sheet_bboxes_px": {
                str(key): list(value)
                for key, value in rendered_scene.source_sheet_bbox_map.items()
            },
            "option_choice_bboxes_px": {
                str(key): list(value)
                for key, value in rendered_scene.option_choice_bbox_map.items()
            },
            "annotation_source": "option_choice_bboxes_px",
        },
        render_params.unit_size_jitter,
    )


def build_overlay_result_label_case(
    *,
    task_id: str,
    namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    prompt_task_key: str,
    prompt_query_key: str,
    dataset_builder: Callable[..., OverlayDataset],
    validate_dataset: Callable[[OverlayDataset], None],
) -> TaskOutput:
    """Run neutral overlay option-label plumbing for a task-owned dataset."""

    selected_branch, branch_probabilities, task_params = resolve_overlay_public_branch(
        instance_seed=int(instance_seed),
        params=params,
        task_id=str(task_id),
        namespace=str(namespace),
    )
    scene_variant, scene_variant_probabilities = resolve_scene_variant(
        params=task_params,
        generation_defaults=generation_defaults,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    dataset = dataset_builder(
        params=task_params,
        instance_seed=int(instance_seed),
        generation_defaults=generation_defaults,
        namespace=str(namespace),
    )
    validate_dataset(dataset)
    visual = prepare_overlay_visual_case(
        dataset=dataset,
        params=task_params,
        rendering_defaults=rendering_defaults,
        instance_seed=int(instance_seed),
        scene_variant=str(scene_variant),
        prompt_task_key=str(prompt_task_key),
        prompt_query_key=str(prompt_query_key),
        namespace=str(namespace),
    )
    rendered_scene = visual["rendered_scene"]
    annotation_gt, projected_annotation, witness_symbolic = option_choice_bbox(
        rendered_scene.option_choice_bbox_map,
        dataset.correct_option_choice_id,
    )
    answer_gt = TypedValue(type="option_letter", value=str(dataset.answer_option_label))
    prompt_artifacts = visual["prompt_artifacts"]
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_branch),
        params={
            "query_id_probabilities": dict(branch_probabilities),
            "prompt_query_key": str(prompt_query_key),
            "internal_query_id": INTERNAL_QUERY_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "grid_size": int(dataset.grid_size),
            "option_count": int(dataset.option_count),
            "mark_shape": str(visual["render_params"].mark_shape),
        },
    )
    render_map = overlay_render_map(
        rendered_scene=rendered_scene,
        render_params=visual["render_params"],
    )
    execution_trace = {
        "query_id": str(selected_branch),
        "internal_query_id": INTERNAL_QUERY_ID,
        "scene_id": SCENE_ID,
        "scene_variant": str(scene_variant),
        "scene_variant_probabilities": dict(scene_variant_probabilities),
        "question_format": "overlay_union_mcq",
        "view_family": "transparent_sheet_overlay_mcq",
        "grid_size": int(dataset.grid_size),
        "grid_size_range": list(dataset.grid_size_range),
        "option_count": int(dataset.option_count),
        "option_count_range": list(dataset.option_count_range),
        "sheet_mark_count_range": list(dataset.sheet_mark_count_range),
        "overlap_count_range": list(dataset.overlap_count_range),
        "left_cells": [[int(x), int(y)] for x, y in dataset.left_cells],
        "right_cells": [[int(x), int(y)] for x, y in dataset.right_cells],
        "overlap_cells": [[int(x), int(y)] for x, y in dataset.overlap_cells],
        "union_cells": [[int(x), int(y)] for x, y in dataset.union_cells],
        "left_mark_specs": [dict(spec) for spec in dataset.left_mark_specs],
        "right_mark_specs": [dict(spec) for spec in dataset.right_mark_specs],
        "left_mark_count": int(dataset.left_mark_count),
        "right_mark_count": int(dataset.right_mark_count),
        "overlap_count": int(dataset.overlap_count),
        "union_mark_count": int(dataset.union_mark_count),
        "option_specs": [dict(option) for option in dataset.option_specs],
        "answer_option_label": str(dataset.answer_option_label),
        "correct_option_index": int(dataset.correct_option_index),
        "correct_option_choice_id": str(dataset.correct_option_choice_id),
        "valid_option_choice_ids": [str(dataset.correct_option_choice_id)],
        "annotation_policy": "scalar_bbox_selected_overlay_result_option",
        "supporting_item_ids": [str(dataset.correct_option_choice_id)],
        "supporting_annotation_source": "option_choice_bboxes_px",
        "option_count_probabilities": dict(dataset.option_count_probabilities),
        "grid_size_probabilities": dict(dataset.grid_size_probabilities),
        "correct_option_index_probabilities": dict(
            dataset.correct_option_index_probabilities
        ),
        "mark_shape": str(visual["render_params"].mark_shape),
        "mark_shape_probabilities": dict(visual["render_params"].mark_shape_probabilities),
        "query_id_probabilities": dict(branch_probabilities),
        "dataset": asdict(dataset),
        "solver_trace": {
            "internal_query_id": INTERNAL_QUERY_ID,
            **solver_trace(dataset),
        },
    }
    trace_payload = build_trace_payload(
        scene_ir={
            "scene_kind": f"puzzle_overlay_{scene_variant}",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "selected_branch": str(selected_branch),
                "semantic_rule": "result_option_equals_union_of_two_same_grid_source_sheets",
                "scene_variant": str(scene_variant),
                "answer_value": str(dataset.answer_option_label),
                "correct_option_choice_id": str(dataset.correct_option_choice_id),
                "left_cells": [[int(x), int(y)] for x, y in dataset.left_cells],
                "right_cells": [[int(x), int(y)] for x, y in dataset.right_cells],
                "union_cells": [[int(x), int(y)] for x, y in dataset.union_cells],
            },
        },
        semantic_spec=query_spec,
        render_spec=render_spec_from_visual(visual),
        render_map=render_map,
        execution_trace=execution_trace,
        witness_symbolic=witness_symbolic,
        projected_annotation=projected_annotation,
        answer_gt=answer_gt.to_dict(),
        annotation_gt=annotation_gt.to_dict(),
        prompt_defaults=visual["prompt_defaults"],
        prompt_artifacts=prompt_artifacts,
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=visual["image"],
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(selected_branch),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


__all__ = [
    "build_overlay_result_label_case",
    "object_description_for_scene",
    "overlay_render_map",
    "prepare_overlay_visual_case",
    "render_spec_from_visual",
    "resolve_overlay_public_branch",
    "retry_overlay_generation",
]
