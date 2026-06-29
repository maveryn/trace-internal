"""Neutral rendering and output plumbing for Tangram public tasks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Mapping

from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.puzzles.shared.scene_style import (
    make_puzzle_scene_background,
    resolve_puzzle_scene_style,
)
from trace.tasks.puzzles.shared.visual_defaults import load_puzzle_noise_defaults
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.defaults import resolve_scene_variant, resolve_tangram_render_params
from .shared.output import build_trace_payload
from .shared.prompts import build_tangram_prompt_artifacts
from .shared.rendering import render_tangram_scene
from .shared.state import DOMAIN, SCENE_ID, RenderedTangramScene, TangramSample

_NOISE_DEFAULTS = load_puzzle_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)

AnnotationBuilder = Callable[
    [RenderedTangramScene, TangramSample],
    tuple[TypedValue, dict[str, Any], dict[str, Any]],
]


def retry_tangram_generation(
    *,
    build_case: Callable[[int, Mapping[str, Any]], TaskOutput],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Retry task-local construction when semantic constraints reject a seed."""

    last_error: Exception | None = None
    for attempt_index in range(max(1, int(max_attempts))):
        try:
            return build_case(
                int(instance_seed) + int(attempt_index),
                params,
            )
        except ValueError as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise RuntimeError("Tangram generation failed without a captured error")


def build_tangram_output(
    *,
    source_id: str,
    namespace: str,
    sample: TangramSample,
    answer_gt: TypedValue,
    annotation_builder: AnnotationBuilder,
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
    task_params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    prompt_task_key: str,
    prompt_query_key: str,
    object_description: str,
    task_trace_fields: Mapping[str, Any],
    task_scene_relations: Mapping[str, Any],
    sampling_metadata: Mapping[str, Any],
    instance_seed: int,
) -> TaskOutput:
    """Render one task-owned Tangram sample and assemble output metadata."""

    scene_variant, scene_variant_probabilities = resolve_scene_variant(
        params=task_params,
        generation_defaults=generation_defaults,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    render_params = resolve_tangram_render_params(
        task_params,
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
        assembly_panel_fill_rgb=tuple(
            int(value) for value in scene_style.option_fill_rgb
        ),
        option_panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
        option_shape_fill_rgb=tuple(
            int(value) for value in scene_style.option_fill_rgb
        ),
        missing_fill_rgb=tuple(int(value) for value in scene_style.text_rgb),
        marked_outline_rgb=tuple(int(value) for value in scene_style.mark_rgb),
        border_color_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
        seam_color_rgb=tuple(int(value) for value in scene_style.grid_rgb),
        text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
        text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
        instance_seed=int(instance_seed),
    )
    background, background_meta = make_puzzle_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=scene_style,
    )
    rendered_scene = render_tangram_scene(
        background,
        sample=sample,
        scene_variant=str(scene_variant),
        render_params=render_params,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=task_params,
        default_config=_NOISE_DEFAULTS,
    )
    prompt_defaults, prompt_artifacts = build_tangram_prompt_artifacts(
        prompt_task_key=str(prompt_task_key),
        prompt_query_key=str(prompt_query_key),
        dynamic_slots={
            "object_description": str(object_description),
        },
        instance_seed=int(instance_seed),
    )
    annotation_gt, projected_annotation, witness_symbolic = annotation_builder(
        rendered_scene,
        sample,
    )
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_branch),
        params={
            "query_id_probabilities": dict(branch_probabilities),
            "prompt_query_key": str(prompt_query_key),
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "construction_mode": str(sample.construction_mode),
            "target_piece_id": str(sample.target_piece_id),
            "target_piece_ids": [str(item) for item in sample.target_piece_ids],
            "target_shape_id": str(sample.target_shape_id),
            **dict(sampling_metadata),
        },
    )
    render_spec = {
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "coord_space": "pixel",
        "scene_id": SCENE_ID,
        "scene_variant": str(scene_variant),
        "background_style": dict(background_meta),
        "scene_style": dict(scene_style_meta),
        "post_image_noise": dict(post_noise_meta),
        "scene_bbox_px": list(rendered_scene.scene_bbox_px),
        "assembly_panel_bbox_px": list(rendered_scene.assembly_panel_bbox_px),
        "assembly_bbox_px": list(rendered_scene.assembly_bbox_px),
        "text_style": {
            "option_label_font_size_px": int(render_params.option_label_font_size_px),
        },
    }
    render_map = {
        "image_id": "img0",
        "scene_bbox_px": list(rendered_scene.scene_bbox_px),
        "assembly_panel_bbox_px": list(rendered_scene.assembly_panel_bbox_px),
        "assembly_bbox_px": list(rendered_scene.assembly_bbox_px),
        "piece_bboxes_px": {
            str(key): list(value)
            for key, value in rendered_scene.piece_bbox_map.items()
        },
        "option_panel_bboxes_px": {
            str(key): list(value)
            for key, value in rendered_scene.option_panel_bbox_map.items()
        },
        "annotation_source": "piece_bboxes_px_and_option_panel_bboxes_px",
    }
    execution_trace = {
        "scene_id": SCENE_ID,
        "source_id": str(source_id),
        "query_id": str(selected_branch),
        "scene_variant": str(scene_variant),
        "scene_variant_probabilities": dict(scene_variant_probabilities),
        "construction_mode": str(sample.construction_mode),
        "target_piece_id": str(sample.target_piece_id),
        "target_piece_ids": [str(item) for item in sample.target_piece_ids],
        "target_shape_id": str(sample.target_shape_id),
        "target_shape_name": str(sample.target_shape_name),
        "answer_value": answer_gt.value,
        "query_id_probabilities": dict(branch_probabilities),
        **dict(sampling_metadata),
        **dict(task_trace_fields),
    }
    trace_payload = build_trace_payload(
        scene_ir={
            "scene_kind": "puzzle_tangram",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "scene_id": SCENE_ID,
                "selected_branch": str(selected_branch),
                "construction_mode": str(sample.construction_mode),
                "scene_variant": str(scene_variant),
                "answer_value": answer_gt.value,
                "target_piece_id": str(sample.target_piece_id),
                "target_piece_ids": [str(item) for item in sample.target_piece_ids],
                "target_shape_id": str(sample.target_shape_id),
                **dict(task_scene_relations),
            },
        },
        semantic_spec=query_spec,
        render_spec=render_spec,
        render_map=render_map,
        execution_trace=execution_trace,
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
        query_id=str(selected_branch),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


__all__ = [
    "build_tangram_output",
    "retry_tangram_generation",
]
