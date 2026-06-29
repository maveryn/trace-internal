"""Public code-grid task for decoding a coordinate sequence."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.puzzles.shared.scene_style import (
    make_puzzle_scene_background,
    resolve_puzzle_scene_style,
)
from trace.tasks.puzzles.shared.unit_size_jitter import with_puzzle_unit_size_jitter
from trace.tasks.puzzles.shared.visual_defaults import load_puzzle_noise_defaults
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.config_defaults import (
    load_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import bbox_sequence_for_cells
from .shared.defaults import (
    resize_canvas_to_content,
    resolve_render_params,
)
from .shared.output import build_trace_payload, json_ready
from .shared.prompts import render_code_grid_prompt_artifacts
from .shared.rendering import render_code_grid_scene
from .shared.sampling import build_code_grid_dataset
from .shared.state import DOMAIN, SCENE_ID, CodeGridDataset, RenderedCodeGrid

TASK_ID = "task_puzzles__code_grid__decoded_word_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "decoded_word_label_query"
PROMPT_QUERY_KEY = "decoded_word_label"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.decoded_word_label"
_NOISE_DEFAULTS = load_puzzle_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


@register_task
class PuzzlesCodeGridDecodedWordLabelTask:
    """Decode the uppercase word from an ordered coordinate sequence."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Generate one code-grid decoded-word task instance."""

        generation_defaults, rendering_defaults, prompt_defaults = (
            load_scene_generation_rendering_prompt_defaults(
                DOMAIN,
                SCENE_ID,
                task_id=TASK_ID,
            )
        )
        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SINGLE_QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{_NAMESPACE_BASE}.query",
        )
        if str(selected_query) != SINGLE_QUERY_ID:
            raise ValueError(f"unsupported code-grid query_id: {selected_query}")

        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) + int(attempt_index)
            try:
                return _build_code_grid_output(
                    params=task_params,
                    generation_defaults=generation_defaults,
                    rendering_defaults=rendering_defaults,
                    prompt_defaults=prompt_defaults,
                    instance_seed=attempt_seed,
                    public_query_id=str(selected_query),
                    query_probabilities=dict(query_probabilities),
                    attempt_limit=int(max_attempts),
                )
            except (RuntimeError, ValueError) as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        raise RuntimeError("code-grid generation failed without a captured error")


def _build_code_grid_output(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
    public_query_id: str,
    query_probabilities: Mapping[str, float],
    attempt_limit: int,
) -> TaskOutput:
    """Build one fully rendered code-grid task output."""

    rng = spawn_rng(int(instance_seed), f"{_NAMESPACE_BASE}.sample")
    dataset = build_code_grid_dataset(
        params=params,
        generation_defaults=generation_defaults,
        rng=rng,
    )
    render_rng = spawn_rng(int(instance_seed), f"{_NAMESPACE_BASE}.layout")
    render_params = resolve_render_params(
        params,
        rendering_defaults,
        instance_seed=int(instance_seed),
    )
    render_params = resize_canvas_to_content(
        render_params,
        rows=int(dataset.rows),
        cols=int(dataset.cols),
        rng=render_rng,
    )
    scene_style, scene_style_meta = resolve_puzzle_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{_NAMESPACE_BASE}.background",
    )
    render_params = replace(
        render_params,
        panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
        grid_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
        header_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
        grid_line_rgb=tuple(int(value) for value in scene_style.grid_rgb),
        text_rgb=tuple(int(value) for value in scene_style.text_rgb),
        text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
    )
    background, background_meta = make_puzzle_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=scene_style,
    )
    rendered_scene = render_code_grid_scene(
        background,
        dataset=dataset,
        render_params=render_params,
        rng=render_rng,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=_NOISE_DEFAULTS,
    )
    prompt_artifacts = render_code_grid_prompt_artifacts(
        prompt_defaults=prompt_defaults,
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_query_key=PROMPT_QUERY_KEY,
        dynamic_slots={
            "coordinate_sequence": str(dataset.coordinate_sequence),
            "coordinate_format": str(dataset.coordinate_format),
        },
        instance_seed=int(instance_seed),
    )
    answer_gt = TypedValue(type="string", value=str(dataset.answer_value))
    annotation_gt, projected_annotation, witness_symbolic = bbox_sequence_for_cells(
        rendered_scene.item_bbox_map,
        dataset.target_cells,
    )
    return _assemble_task_output(
        dataset=dataset,
        rendered_scene=rendered_scene,
        image=image,
        prompt_artifacts=prompt_artifacts,
        render_params=render_params,
        scene_style_meta=scene_style_meta,
        background_meta=background_meta,
        post_noise_meta=post_noise_meta,
        prompt_defaults=prompt_defaults,
        public_query_id=str(public_query_id),
        query_probabilities=dict(query_probabilities),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        projected_annotation=projected_annotation,
        witness_symbolic=witness_symbolic,
        attempt_limit=int(attempt_limit),
    )


def _assemble_task_output(
    *,
    dataset: CodeGridDataset,
    rendered_scene: RenderedCodeGrid,
    image,
    prompt_artifacts,
    render_params,
    scene_style_meta: Mapping[str, Any],
    background_meta: Mapping[str, Any],
    post_noise_meta: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    public_query_id: str,
    query_probabilities: Mapping[str, float],
    answer_gt: TypedValue,
    annotation_gt: TypedValue,
    projected_annotation: Mapping[str, Any],
    witness_symbolic: Mapping[str, Any],
    attempt_limit: int,
) -> TaskOutput:
    """Assemble final TaskOutput with task-owned answer and annotation."""

    query_params = {
        "query_id": str(public_query_id),
        "query_id_probabilities": dict(query_probabilities),
        "prompt_query_key": PROMPT_QUERY_KEY,
        "scene_id": SCENE_ID,
        "grid_rows": int(dataset.rows),
        "grid_cols": int(dataset.cols),
        "grid_size_range": list(dataset.grid_size_range),
        "coordinate_sequence": str(dataset.coordinate_sequence),
        "coordinate_tokens": list(dataset.coordinate_tokens),
        "coordinate_format": str(dataset.coordinate_format),
        "coordinate_format_probabilities": dict(
            dataset.coordinate_format_probabilities
        ),
        "target_answer_support": list(dataset.answer_support),
    }
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(public_query_id),
        params=query_params,
    )
    render_map = with_puzzle_unit_size_jitter(
        {
            "image_id": "img0",
            "scene_bbox_px": list(rendered_scene.scene_bbox_px),
            "cell_bboxes_px": dict(rendered_scene.cell_bbox_map),
            "item_bboxes_px": dict(rendered_scene.item_bbox_map),
            "annotation_source": "item_bboxes_px",
            "layout_jitter": dict(rendered_scene.layout_jitter),
        },
        render_params.unit_size_jitter,
    )
    target_cell_records = [
        {
            "index": int(index),
            "row": int(cell[0]),
            "col": int(cell[1]),
            "coordinate": str(token),
            "letter": str(dataset.grid[int(cell[0])][int(cell[1])]),
        }
        for index, (cell, token) in enumerate(
            zip(dataset.target_cells, dataset.coordinate_tokens),
            start=1,
        )
    ]
    trace_payload = build_trace_payload(
        scene_ir={
            "scene_kind": f"puzzle_code_grid_{dataset.scene_variant}",
            "scene_id": SCENE_ID,
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "answer_value": str(answer_gt.value),
        },
        query_spec=query_spec,
        render_spec={
            "scene_id": SCENE_ID,
            "canvas_width": int(render_params.canvas_width),
            "canvas_height": int(render_params.canvas_height),
            "coord_space": "pixel",
            "scene_variant": str(dataset.scene_variant),
            "scene_variant_probabilities": dict(dataset.scene_variant_probabilities),
            "scene_style": dict(scene_style_meta),
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "scene_bbox_px": list(rendered_scene.scene_bbox_px),
            "layout_jitter": dict(rendered_scene.layout_jitter),
            "unit_size_jitter": dict(render_params.unit_size_jitter),
        },
        render_map=render_map,
        execution_trace={
            **dict(query_params),
            "dataset": json_ready(dataset),
            "grid": [list(row) for row in dataset.grid],
            "target_word": str(dataset.target_word),
            "target_cells": target_cell_records,
            "answer_value": str(answer_gt.value),
            "annotation_policy": "bbox_sequence_decode_cells_in_coordinate_order",
            "supporting_annotation_source": "item_bboxes_px",
            "max_attempts": int(attempt_limit),
        },
        witness_symbolic=witness_symbolic,
        projected_annotation=projected_annotation,
        answer_gt=answer_gt.to_dict(),
        annotation_gt=annotation_gt.to_dict(),
        prompt_defaults=prompt_defaults,
        prompt_artifacts=prompt_artifacts,
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(public_query_id),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


__all__ = ["PuzzlesCodeGridDecodedWordLabelTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
