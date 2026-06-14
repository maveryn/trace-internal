"""Neutral render lifecycle for the named-field icons scene."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Tuple

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.icons.shared.icon_task_rendering import resolve_icon_render_params
from trace.tasks.icons.shared.procedural_named_icon_field_scene import (
    NamedIconFieldSpec,
    RenderedNamedIconFieldScene,
    named_icon_bboxes_for_shape,
    render_procedural_named_icon_field_scene,
    resolve_named_icon_fill_style_support,
)

from .shared.annotations import (
    bbox_set_from_bboxes,
    boolean_annotation_bboxes,
    counterfactual_annotation_bboxes,
)
from .shared.defaults import BOOLEAN_DEFAULTS, COUNTERFACTUAL_DEFAULTS, SHAPE_COUNT_DEFAULTS
from .shared.metrics import (
    boolean_counted_instance_ids,
    boolean_query_expression,
    counterfactual_counted_instance_ids,
)
from .shared.output import (
    build_boolean_query_metadata,
    build_boolean_trace_payload,
    build_counterfactual_query_metadata,
    build_counterfactual_trace_payload,
    build_shape_count_query_metadata,
    build_shape_count_trace_payload,
    shape_counted_instance_ids,
)
from .shared.output import render_slot_params
from .shared.prompts import (
    build_boolean_prompt_artifacts,
    build_counterfactual_prompt_artifacts,
    build_shape_count_prompt_artifacts,
)
from .shared.rendering import (
    build_boolean_scene_specs,
    build_counterfactual_scene_specs,
    build_shape_count_scene_specs,
)
from .shared.sampling import (
    color_support,
    sample_boolean_spec,
    sample_counterfactual_spec,
    sample_shape_count_spec,
    shape_support,
)


@dataclass(frozen=True)
class NamedFieldRenderedAttempt:
    """Rendered named-field scene plus the symbolic sample used to create it."""

    sample: Any
    scene: RenderedNamedIconFieldScene
    render_params: Mapping[str, Any]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    slot_padding_px: int
    slot_jitter_px: int
    stack_gap_px: int


SceneSpecBuilder = Callable[
    [Any, Mapping[str, Any], Any],
    tuple[Any, tuple[NamedIconFieldSpec, ...], Tuple[Tuple[int, int, int], ...]],
]


def render_named_field_attempts(
    *,
    run_namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    fallback_defaults: Any,
    max_attempts: int,
    build_scene_specs: SceneSpecBuilder,
) -> NamedFieldRenderedAttempt:
    """Run the shared named-field render/retry loop for one task-owned plan."""

    render_defaults = dict(rendering_defaults)
    render_params = resolve_icon_render_params(
        params=params,
        render_defaults=render_defaults,
        fallback_defaults=fallback_defaults,
        instance_seed=int(instance_seed),
    )
    slot_padding_px, slot_jitter_px, stack_gap_px = render_slot_params(params, render_defaults, fallback_defaults)

    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            scene_rng = spawn_rng(int(instance_seed), f"{run_namespace}.scene", int(attempt))
            sample, icon_specs, sampled_palette_rgb = build_scene_specs(scene_rng, render_params, attempt)
            scene = render_procedural_named_icon_field_scene(
                rng=scene_rng,
                instance_seed=int(instance_seed),
                task_id=str(run_namespace),
                icon_specs=icon_specs,
                render_params=render_params,
                layout_modes=(str(sample.arrangement_mode),),
                slot_padding_px=int(slot_padding_px),
                slot_jitter_px=int(slot_jitter_px),
                stack_gap_px=int(stack_gap_px),
            )
            return NamedFieldRenderedAttempt(
                sample=sample,
                scene=scene,
                render_params=dict(render_params),
                sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in sampled_palette_rgb),
                slot_padding_px=int(slot_padding_px),
                slot_jitter_px=int(slot_jitter_px),
                stack_gap_px=int(stack_gap_px),
            )
        except Exception as exc:  # pragma: no cover - exercised through smoke tests.
            last_error = exc
    raise RuntimeError(f"could not generate {run_namespace}: {last_error}") from last_error


def run_shape_count_named_field_task(
    *,
    task_id: str,
    domain: str,
    scene_id: str,
    query_id: str,
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    prompt_defaults_map: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Run the repeated lifecycle for a public direct shape-count task."""

    task_params = dict(params)

    def build_scene_specs(scene_rng, render_params, _attempt):
        sample = sample_shape_count_spec(
            run_namespace=str(task_id),
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=generation_defaults,
            render_defaults=rendering_defaults,
        )
        icon_specs, sampled_palette_rgb = build_shape_count_scene_specs(
            run_namespace=str(task_id),
            sample=sample,
            instance_seed=int(instance_seed),
            render_params=render_params,
            rng=scene_rng,
        )
        return sample, icon_specs, sampled_palette_rgb

    rendered = render_named_field_attempts(
        run_namespace=str(task_id),
        instance_seed=int(instance_seed),
        params=task_params,
        rendering_defaults=rendering_defaults,
        fallback_defaults=SHAPE_COUNT_DEFAULTS,
        max_attempts=int(max_attempts),
        build_scene_specs=build_scene_specs,
    )
    sample = rendered.sample
    scene = rendered.scene
    annotation_bboxes = named_icon_bboxes_for_shape(scene.instances, shape_id=str(sample.target_shape_id))
    if len(annotation_bboxes) != int(sample.target_count):
        raise RuntimeError("rendered named-shape count did not match target count")
    annotation_artifacts = bbox_set_from_bboxes(annotation_bboxes)
    prompt_artifacts, prompt_defaults = build_shape_count_prompt_artifacts(
        domain=str(domain),
        run_namespace=str(task_id),
        prompt_defaults_map=prompt_defaults_map,
        sample=sample,
        instance_seed=int(instance_seed),
    )
    counted_instance_ids = shape_counted_instance_ids(sample, scene.instances)
    query_metadata = build_shape_count_query_metadata(
        sample=sample,
        params=task_params,
        gen_defaults=generation_defaults,
        shape_support=shape_support(task_params, generation_defaults),
    )
    trace_payload = build_shape_count_trace_payload(
        sample=sample,
        scene=scene,
        render_params=rendered.render_params,
        sampled_palette_rgb=rendered.sampled_palette_rgb,
        prompt_defaults=prompt_defaults,
        prompt_artifacts=prompt_artifacts,
        annotation_artifacts=annotation_artifacts,
        counted_instance_ids=counted_instance_ids,
        query_metadata=query_metadata,
        public_query_id=str(query_id),
        slot_padding_px=rendered.slot_padding_px,
        slot_jitter_px=rendered.slot_jitter_px,
        stack_gap_px=rendered.stack_gap_px,
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=TypedValue(type="integer", value=int(sample.target_count)),
        annotation_gt=TypedValue(type=str(annotation_artifacts["annotation_type"]), value=list(annotation_artifacts["annotation_value"])),
        image=scene.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=str(scene_id),
        query_id=str(query_id),
        prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
    )


def run_boolean_named_field_task(
    *,
    task_id: str,
    domain: str,
    scene_id: str,
    selected_query_key: str,
    query_probabilities: Mapping[str, float],
    prompt_query_key: str,
    predicate_kind: str,
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    prompt_defaults_map: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Run the repeated lifecycle for a public Boolean predicate count task."""

    task_params = dict(params)

    def build_scene_specs(scene_rng, render_params, _attempt):
        sample = sample_boolean_spec(
            run_namespace=str(task_id),
            prompt_query_key=str(prompt_query_key),
            predicate_kind=str(predicate_kind),
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=generation_defaults,
            render_defaults=rendering_defaults,
        )
        icon_specs, sampled_palette_rgb = build_boolean_scene_specs(
            run_namespace=str(task_id),
            sample=sample,
            instance_seed=int(instance_seed),
            render_params=render_params,
            rng=scene_rng,
        )
        return sample, icon_specs, sampled_palette_rgb

    rendered = render_named_field_attempts(
        run_namespace=str(task_id),
        instance_seed=int(instance_seed),
        params=task_params,
        rendering_defaults=rendering_defaults,
        fallback_defaults=BOOLEAN_DEFAULTS,
        max_attempts=int(max_attempts),
        build_scene_specs=build_scene_specs,
    )
    sample = rendered.sample
    scene = rendered.scene
    annotation_bboxes = boolean_annotation_bboxes(sample, scene.instances)
    if len(annotation_bboxes) != int(sample.target_answer):
        raise RuntimeError("rendered Boolean named-icon count did not match target answer")
    annotation_artifacts = bbox_set_from_bboxes(annotation_bboxes)
    prompt_artifacts, prompt_defaults = build_boolean_prompt_artifacts(
        domain=str(domain),
        run_namespace=str(task_id),
        prompt_defaults_map=prompt_defaults_map,
        sample=sample,
        instance_seed=int(instance_seed),
    )
    query_expression = boolean_query_expression(sample)
    fill_style_support = resolve_named_icon_fill_style_support(
        task_params,
        generation_defaults,
        fallback_support=BOOLEAN_DEFAULTS.named_icon_fill_style_support,
        queryable_only=False,
        queryable_fallback_support=BOOLEAN_DEFAULTS.queryable_named_icon_fill_style_support,
    )
    queryable_fill_style_support = resolve_named_icon_fill_style_support(
        task_params,
        generation_defaults,
        fallback_support=BOOLEAN_DEFAULTS.named_icon_fill_style_support,
        queryable_only=True,
        queryable_fallback_support=BOOLEAN_DEFAULTS.queryable_named_icon_fill_style_support,
    )
    counted_instance_ids = boolean_counted_instance_ids(sample, scene.instances)
    query_metadata = build_boolean_query_metadata(
        sample=sample,
        query_expression=query_expression,
        public_query_id=str(selected_query_key),
        public_query_probabilities=query_probabilities,
        shape_support=shape_support(task_params, generation_defaults),
        color_support=color_support(task_params, generation_defaults),
        fill_style_support=fill_style_support,
        queryable_fill_style_support=queryable_fill_style_support,
    )
    trace_payload = build_boolean_trace_payload(
        sample=sample,
        scene=scene,
        render_params=rendered.render_params,
        sampled_palette_rgb=rendered.sampled_palette_rgb,
        prompt_defaults=prompt_defaults,
        prompt_artifacts=prompt_artifacts,
        annotation_artifacts=annotation_artifacts,
        counted_instance_ids=counted_instance_ids,
        query_expression=query_expression,
        query_metadata=query_metadata,
        public_query_id=str(selected_query_key),
        slot_padding_px=rendered.slot_padding_px,
        slot_jitter_px=rendered.slot_jitter_px,
        stack_gap_px=rendered.stack_gap_px,
        fill_style_support=tuple(fill_style_support),
        queryable_fill_style_support=tuple(queryable_fill_style_support),
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=TypedValue(type="integer", value=int(sample.target_answer)),
        annotation_gt=TypedValue(type=str(annotation_artifacts["annotation_type"]), value=list(annotation_artifacts["annotation_value"])),
        image=scene.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=str(scene_id),
        query_id=str(selected_query_key),
        prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
    )


def run_counterfactual_named_field_task(
    *,
    task_id: str,
    domain: str,
    scene_id: str,
    selected_query_key: str,
    query_probabilities: Mapping[str, float],
    prompt_query_key: str,
    edit_kind: str,
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    prompt_defaults_map: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Run the repeated lifecycle for a public counterfactual count task."""

    task_params = dict(params)

    def build_scene_specs(scene_rng, render_params, _attempt):
        sample = sample_counterfactual_spec(
            run_namespace=str(task_id),
            prompt_query_key=str(prompt_query_key),
            edit_kind=str(edit_kind),
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=generation_defaults,
            render_defaults=rendering_defaults,
        )
        icon_specs, sampled_palette_rgb = build_counterfactual_scene_specs(
            run_namespace=str(task_id),
            sample=sample,
            instance_seed=int(instance_seed),
            render_params=render_params,
            rng=scene_rng,
        )
        return sample, icon_specs, sampled_palette_rgb

    rendered = render_named_field_attempts(
        run_namespace=str(task_id),
        instance_seed=int(instance_seed),
        params=task_params,
        rendering_defaults=rendering_defaults,
        fallback_defaults=COUNTERFACTUAL_DEFAULTS,
        max_attempts=int(max_attempts),
        build_scene_specs=build_scene_specs,
    )
    sample = rendered.sample
    scene = rendered.scene
    annotation_bboxes = counterfactual_annotation_bboxes(sample, scene.instances)
    if len(annotation_bboxes) != int(sample.target_answer):
        raise RuntimeError("rendered counterfactual named-icon count did not match target answer")
    annotation_artifacts = bbox_set_from_bboxes(annotation_bboxes)
    prompt_artifacts, prompt_defaults = build_counterfactual_prompt_artifacts(
        domain=str(domain),
        run_namespace=str(task_id),
        prompt_defaults_map=prompt_defaults_map,
        sample=sample,
        instance_seed=int(instance_seed),
    )
    counted_instance_ids = counterfactual_counted_instance_ids(sample)
    query_metadata = build_counterfactual_query_metadata(
        sample=sample,
        public_query_id=str(selected_query_key),
        public_query_probabilities=query_probabilities,
        shape_support=shape_support(task_params, generation_defaults, min_count=6),
    )
    trace_payload = build_counterfactual_trace_payload(
        sample=sample,
        scene=scene,
        render_params=rendered.render_params,
        sampled_palette_rgb=rendered.sampled_palette_rgb,
        prompt_defaults=prompt_defaults,
        prompt_artifacts=prompt_artifacts,
        annotation_artifacts=annotation_artifacts,
        counted_instance_ids=counted_instance_ids,
        query_metadata=query_metadata,
        public_query_id=str(selected_query_key),
        slot_padding_px=rendered.slot_padding_px,
        slot_jitter_px=rendered.slot_jitter_px,
        stack_gap_px=rendered.stack_gap_px,
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=TypedValue(type="integer", value=int(sample.target_answer)),
        annotation_gt=TypedValue(type=str(annotation_artifacts["annotation_type"]), value=list(annotation_artifacts["annotation_value"])),
        image=scene.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=str(scene_id),
        query_id=str(selected_query_key),
        prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
    )


__all__ = [
    "NamedFieldRenderedAttempt",
    "SceneSpecBuilder",
    "render_named_field_attempts",
    "run_boolean_named_field_task",
    "run_counterfactual_named_field_task",
    "run_shape_count_named_field_task",
]
