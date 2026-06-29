"""Scene-private lifecycle plumbing for Sudoku public task files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from trace.core.seed import spawn_rng
from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.puzzles.shared.visual_defaults import load_puzzle_noise_defaults
from trace.tasks.shared.config_defaults import (
    load_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.config_defaults import required_group_defaults
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import (
    bbox_set_for_coords,
    bbox_set_map_for_marked_cell_context,
)
from .shared.output import build_sudoku_trace_payload, text_style_metadata
from .shared.prompts import (
    object_description_for_scene_variant,
    render_sudoku_prompt_artifacts,
    unit_scope_text,
)
from .shared.rendering import RenderedSudokuScene, render_sudoku_visual_artifacts
from .shared.sampling import (
    SudokuAxes,
    SudokuDefaults,
    build_sudoku_solution,
    resolve_sudoku_axes,
    resolve_sudoku_render_params,
)
from .shared.state import Board, SCENE_ID, SudokuSample


@dataclass(frozen=True)
class SudokuAnnotationBinding:
    """Task-owned annotation projection result consumed by lifecycle plumbing."""

    annotation_kind: str
    annotation_value: Any
    entity_ids: Any


@dataclass(frozen=True)
class SudokuTaskRuntime:
    """Public task metadata required by neutral Sudoku lifecycle plumbing."""

    source_id: str
    support_key: str
    include_unit_type: bool
    prompt_query_key: str
    attempt_namespace: str


SampleBuilder = Callable[..., SudokuSample]


def _bind_sudoku_annotation(
    rendered_scene: RenderedSudokuScene,
    sample: SudokuSample,
) -> SudokuAnnotationBinding:
    """Project sample-selected Sudoku cell witnesses into public annotation."""

    cell_bboxes = rendered_scene.render_map["cell_bboxes_px"]
    if sample.marked_cell is not None:
        projected, entity_ids = bbox_set_map_for_marked_cell_context(
            cell_bboxes,
            marked_cell=sample.marked_cell,
            constraint_coords=sample.annotation_coords[1:],
        )
        return SudokuAnnotationBinding(
            annotation_kind="bbox_set_map",
            annotation_value=projected["bbox_set_map"],
            entity_ids=entity_ids,
        )
    projected, entity_ids = bbox_set_for_coords(cell_bboxes, sample.annotation_coords)
    return SudokuAnnotationBinding(
        annotation_kind="bbox_set",
        annotation_value=projected["bbox_set"],
        entity_ids=entity_ids,
    )


def run_sudoku_lifecycle(
    *,
    source_id: str,
    selected_query_id: str,
    query_probabilities: Mapping[str, float],
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    defaults: SudokuDefaults,
    support_key: str,
    fallback_support: Sequence[int],
    include_unit_type: bool,
    prompt_query_key: str,
    prompt_required_keys: Sequence[str],
    attempt_namespace: str,
    build_sample: SampleBuilder,
    noise_defaults: Mapping[str, Any],
    instance_seed: int,
    max_attempts: int,
) -> TaskOutput:
    """Run neutral Sudoku rendering/retry plumbing around task-owned hooks."""

    axes = resolve_sudoku_axes(
        params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace_root=str(attempt_namespace),
        support_key=str(support_key),
        fallback_support=fallback_support,
        include_unit_type=bool(include_unit_type),
    )
    render_params = resolve_sudoku_render_params(
        params,
        render_defaults=render_defaults,
        instance_seed=int(instance_seed),
        defaults=defaults,
    )

    sample: SudokuSample | None = None
    last_error: Exception | None = None
    for attempt_index in range(max(1, int(max_attempts))):
        rng = spawn_rng(
            int(instance_seed),
            f"{attempt_namespace}.attempt.{int(attempt_index)}",
        )
        try:
            solution = build_sudoku_solution(rng)
            sample = build_sample(
                rng=rng,
                solution=solution,
                axes=axes,
                defaults=defaults,
            )
            break
        except ValueError as exc:
            last_error = exc
    if sample is None:
        raise RuntimeError(
            f"{source_id} failed to generate a valid Sudoku sample after "
            f"{max_attempts} attempts"
        ) from last_error

    visual = render_sudoku_visual_artifacts(
        sample=sample,
        style_variant=str(axes.style_variant),
        render_params=render_params,
        instance_seed=int(instance_seed),
        params=dict(params),
        noise_defaults=dict(noise_defaults),
    )
    annotation = _bind_sudoku_annotation(visual.rendered_scene, sample)
    prompt_defaults_resolved = required_group_defaults(
        prompt_defaults,
        tuple(str(key) for key in prompt_required_keys),
        context=f"prompt defaults for {source_id}",
    )
    object_description = object_description_for_scene_variant(
        prompt_defaults_resolved,
        str(axes.scene_variant),
    )
    prompt_artifacts = render_sudoku_prompt_artifacts(
        prompt_defaults=prompt_defaults_resolved,
        prompt_query_key=str(prompt_query_key),
        object_description=str(object_description),
        unit_scope_text=unit_scope_text(
            prompt_defaults_resolved,
            sample.highlighted_unit_type,
        ),
        instance_seed=int(instance_seed),
    )
    query_params = {
        "query_id_probabilities": dict(query_probabilities),
        "prompt_query_key": str(prompt_query_key),
        "scene_variant": str(axes.scene_variant),
        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
        "style_variant": str(axes.style_variant),
        "style_variant_probabilities": dict(axes.style_variant_probabilities),
        "target_answer": int(sample.answer),
        "target_answer_support": [int(value) for value in axes.target_answer_support],
        "target_answer_probabilities": dict(axes.target_answer_probabilities),
        "visible_count": int(sample.visible_count),
    }
    if sample.highlighted_unit_type is not None:
        query_params.update(
            {
                "unit_type": sample.highlighted_unit_type,
                "unit_index": sample.highlighted_unit_index,
                "unit_type_probabilities": dict(axes.unit_type_probabilities or {}),
            }
        )
    prompt_spec_payload = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query_id),
        params=query_params,
    )
    trace_payload = build_sudoku_trace_payload(
        sample=sample,
        rendered_scene=visual.rendered_scene,
        image=visual.image,
        prompt_artifacts=prompt_artifacts,
        prompt_spec_payload=prompt_spec_payload,
        execution_fields={"query_id": str(selected_query_id)},
        annotation_type=str(annotation.annotation_kind),
        annotation_value=annotation.annotation_value,
        annotation_entity_ids=annotation.entity_ids,
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        panel_style_meta=visual.panel_style_meta,
        text_style_meta=text_style_metadata(str(render_params.font_family)),
        background_meta=visual.background_meta,
        post_noise_meta=visual.post_noise_meta,
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_gt=TypedValue(type="integer", value=int(sample.answer)),
        annotation_gt=TypedValue(
            type=str(annotation.annotation_kind),
            value=annotation.annotation_value,
        ),
        image=visual.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(selected_query_id),
    )


def run_sudoku_single_query_lifecycle(
    *,
    runtime: SudokuTaskRuntime,
    params: Mapping[str, Any],
    build_sample: SampleBuilder,
    instance_seed: int,
    max_attempts: int,
) -> TaskOutput:
    """Select the fixed Sudoku branch, then run neutral scene lifecycle plumbing."""

    defaults = SudokuDefaults()
    gen_defaults, render_defaults, prompt_defaults = (
        load_scene_generation_rendering_prompt_defaults(
            "puzzles",
            SCENE_ID,
            task_id=str(runtime.source_id),
        )
    )
    fallback_support = getattr(defaults, str(runtime.support_key))
    prompt_required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        "object_description_sparse_grid",
        "object_description_filled_grid",
    )
    if bool(runtime.include_unit_type):
        prompt_required_keys = (
            *prompt_required_keys,
            "unit_scope_text_row",
            "unit_scope_text_column",
            "unit_scope_text_box",
        )
    noise_defaults = load_puzzle_noise_defaults(
        scene_id=SCENE_ID,
        apply_prob=0.5,
    )
    selected_query, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=(SINGLE_QUERY_ID,),
        default_query_id=SINGLE_QUERY_ID,
        task_id=str(runtime.source_id),
        namespace=f"{runtime.attempt_namespace}.query",
    )
    return run_sudoku_lifecycle(
        source_id=str(runtime.source_id),
        selected_query_id=str(selected_query),
        query_probabilities=query_probabilities,
        params=task_params,
        gen_defaults=gen_defaults,
        render_defaults=render_defaults,
        prompt_defaults=prompt_defaults,
        defaults=defaults,
        support_key=str(runtime.support_key),
        fallback_support=fallback_support,
        include_unit_type=bool(runtime.include_unit_type),
        prompt_query_key=str(runtime.prompt_query_key),
        prompt_required_keys=prompt_required_keys,
        attempt_namespace=str(runtime.attempt_namespace),
        build_sample=build_sample,
        noise_defaults=noise_defaults,
        instance_seed=int(instance_seed),
        max_attempts=int(max_attempts),
    )


__all__ = [
    "RenderedSudokuScene",
    "SudokuAnnotationBinding",
    "SudokuTaskRuntime",
    "run_sudoku_lifecycle",
    "run_sudoku_single_query_lifecycle",
]
