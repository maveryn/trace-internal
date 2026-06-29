"""Neutral rendering and output plumbing for paper-fold public tasks."""

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
from .shared.defaults import (
    resolve_fold_axis,
    resolve_render_params,
    resolve_scene_variant,
)
from .shared.output import build_trace_payload
from .shared.prompts import build_paper_fold_prompt_artifacts
from .shared.rendering import (
    FOLD_RESULT_SUPERSAMPLE_SCALE,
    render_puzzle_fold_result_scene,
)
from .shared.sampling import sample_paper_fold_dataset, solver_trace
from .shared.state import DOMAIN, PaperFoldDataset, SCENE_ID

_NOISE_DEFAULTS = load_puzzle_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)
INTERNAL_GRAMMAR_ID = "single_axis_mark_projection"


def retry_paper_fold_generation(
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
    raise RuntimeError("paper-fold generation failed without a captured error")


def resolve_paper_fold_public_branch(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[str, dict[str, float], Mapping[str, Any]]:
    """Resolve the no-branch public query id and return sanitized params."""

    selected_branch, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=(SINGLE_QUERY_ID,),
        default_query_id=SINGLE_QUERY_ID,
        namespace=f"{namespace}.branch",
    )
    if str(selected_branch) != SINGLE_QUERY_ID:
        raise ValueError(f"unsupported paper-fold public branch: {selected_branch}")
    return str(selected_branch), dict(branch_probabilities), task_params


def object_description_for_scene(scene_variant: str) -> str:
    """Return concise scene wording for one paper-fold treatment."""

    descriptions = {
        "fold_strip": "a paper-folding puzzle with a fold diagram above labeled result options",
        "fold_card": "a card-style paper-folding puzzle with a fold diagram above labeled result options",
        "fold_outline": "an outline-style paper-folding puzzle with a fold diagram above labeled result options",
    }
    return descriptions.get(str(scene_variant), descriptions["fold_strip"])


def prepare_paper_fold_visual_case(
    *,
    dataset: PaperFoldDataset,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    instance_seed: int,
    scene_variant: str,
    prompt_task_key: str,
    prompt_query_key: str,
    namespace: str,
) -> Dict[str, Any]:
    """Render a sampled paper-fold dataset and matching prompt artifacts."""

    render_params = resolve_render_params(
        params,
        rendering_defaults,
        instance_seed=int(instance_seed),
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
        fold_line_rgb=tuple(int(value) for value in scene_style.grid_rgb),
        grid_line_rgb=tuple(int(value) for value in scene_style.notebook_line_rgb),
        arrow_rgb=tuple(int(value) for value in scene_style.mark_rgb),
        instruction_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
    )
    background, background_meta = make_puzzle_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=scene_style,
    )
    rendered_scene = render_puzzle_fold_result_scene(
        background,
        scene_variant=str(scene_variant),
        fold_axis=str(dataset.fold_axis),
        fold_direction=str(dataset.fold_direction),
        grid_size=int(dataset.grid_size),
        original_mark_specs=dataset.original_mark_specs,
        option_specs=dataset.option_specs,
        result_grid_cols=int(dataset.result_grid_cols),
        result_grid_rows=int(dataset.result_grid_rows),
        render_params=render_params,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=_NOISE_DEFAULTS,
    )
    prompt_defaults, prompt_artifacts = build_paper_fold_prompt_artifacts(
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
        "scene_style": dict(visual["scene_style_meta"]),
        "post_image_noise": dict(visual["post_noise_meta"]),
        "scene_bbox_px": list(rendered_scene.scene_bbox_px),
        "layout": "single_fold_reference_with_visual_options",
        "unit_size_jitter": dict(render_params.unit_size_jitter),
        "text_style": {
            "option_label_font_size_px": int(render_params.option_label_font_size_px),
        },
        "antialias_supersample_scale": int(FOLD_RESULT_SUPERSAMPLE_SCALE),
    }


def paper_fold_render_map(*, rendered_scene: Any, render_params: Any) -> Dict[str, Any]:
    """Build the common pixel render map for one rendered paper-fold scene."""

    return with_puzzle_unit_size_jitter(
        {
            "image_id": "img0",
            "scene_bbox_px": list(rendered_scene.scene_bbox_px),
            "reference_panel_bbox_px": list(rendered_scene.reference_panel_bbox_px),
            "reference_paper_bbox_px": list(rendered_scene.reference_paper_bbox_px),
            "option_choice_bboxes_px": {
                str(key): list(value)
                for key, value in rendered_scene.option_choice_bbox_map.items()
            },
            "annotation_source": "option_choice_bboxes_px",
        },
        render_params.unit_size_jitter,
    )


def build_paper_fold_result_label_case(
    *,
    namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    prompt_task_key: str,
    prompt_query_key: str,
    validate_dataset: Callable[[PaperFoldDataset], None],
) -> TaskOutput:
    """Run neutral paper-fold option-label plumbing for a task-owned dataset."""

    selected_branch, branch_probabilities, task_params = resolve_paper_fold_public_branch(
        instance_seed=int(instance_seed),
        params=params,
        namespace=str(namespace),
    )
    fold_axis, fold_axis_probabilities = resolve_fold_axis(
        task_params,
        generation_defaults,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    scene_variant, scene_variant_probabilities = resolve_scene_variant(
        params=task_params,
        generation_defaults=generation_defaults,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    dataset = sample_paper_fold_dataset(
        params=task_params,
        instance_seed=int(instance_seed),
        generation_defaults=generation_defaults,
        fold_axis=str(fold_axis),
        namespace=str(namespace),
    )
    validate_dataset(dataset)
    visual = prepare_paper_fold_visual_case(
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
            "internal_grammar_id": INTERNAL_GRAMMAR_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "fold_axis": str(dataset.fold_axis),
            "fold_axis_probabilities": dict(fold_axis_probabilities),
            "fold_direction": str(dataset.fold_direction),
            "grid_size": int(dataset.grid_size),
            "option_count": int(dataset.option_count),
            "mark_count": int(dataset.mark_count),
        },
    )
    render_map = paper_fold_render_map(
        rendered_scene=rendered_scene,
        render_params=visual["render_params"],
    )
    execution_trace = {
        "query_id": str(selected_branch),
        "internal_grammar_id": INTERNAL_GRAMMAR_ID,
        "scene_id": SCENE_ID,
        "scene_variant": str(scene_variant),
        "scene_variant_probabilities": dict(scene_variant_probabilities),
        "question_format": "fold_result_mcq",
        "view_family": "paper_fold_result_mcq",
        "fold_axis": str(dataset.fold_axis),
        "fold_axis_probabilities": dict(fold_axis_probabilities),
        "fold_direction": str(dataset.fold_direction),
        "grid_size": int(dataset.grid_size),
        "result_grid_cols": int(dataset.result_grid_cols),
        "result_grid_rows": int(dataset.result_grid_rows),
        "mark_count": int(dataset.mark_count),
        "mark_count_range": list(dataset.mark_count_range),
        "folded_mark_count": int(dataset.folded_mark_count),
        "kept_mark_count": int(dataset.kept_mark_count),
        "original_mark_specs": [dict(item) for item in dataset.original_mark_specs],
        "folded_result_mark_specs": [
            dict(item) for item in dataset.folded_result_mark_specs
        ],
        "option_count": int(dataset.option_count),
        "option_count_range": list(dataset.option_count_range),
        "option_specs": [dict(item) for item in dataset.option_specs],
        "answer_option_label": str(dataset.answer_option_label),
        "correct_option_choice_id": str(dataset.correct_option_choice_id),
        "correct_option_index": int(dataset.correct_option_index),
        "supporting_option_choice_ids": [str(dataset.correct_option_choice_id)],
        "annotation_policy": "scalar_bbox_selected_folded_result_option",
        "supporting_annotation_source": "option_choice_bboxes_px",
        "option_count_probabilities": dict(dataset.option_count_probabilities),
        "correct_option_index_probabilities": dict(
            dataset.correct_option_index_probabilities
        ),
        "query_id_probabilities": dict(branch_probabilities),
        "dataset": asdict(dataset),
        "solver_trace": {
            "internal_grammar_id": INTERNAL_GRAMMAR_ID,
            **solver_trace(dataset),
        },
    }
    trace_payload = build_trace_payload(
        scene_ir={
            "scene_kind": f"puzzle_paper_fold_{scene_variant}",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "selected_branch": str(selected_branch),
                "semantic_rule": "result_option_matches_single_axis_fold_projection",
                "scene_variant": str(scene_variant),
                "answer_value": str(dataset.answer_option_label),
                "correct_option_choice_id": str(dataset.correct_option_choice_id),
                "fold_axis": str(dataset.fold_axis),
                "fold_direction": str(dataset.fold_direction),
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
    "build_paper_fold_result_label_case",
    "object_description_for_scene",
    "paper_fold_render_map",
    "prepare_paper_fold_visual_case",
    "render_spec_from_visual",
    "resolve_paper_fold_public_branch",
    "retry_paper_fold_generation",
]
