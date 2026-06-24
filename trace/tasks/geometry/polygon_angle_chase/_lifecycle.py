"""Neutral lifecycle plumbing for polygon angle-chase public tasks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from ..shared.annotation_values import keyed_point_annotation_artifacts
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS

from .shared.defaults import DOMAIN, SCENE_DEFAULTS, SCENE_ID
from .shared.prompts import angle_chase_prompt_artifacts
from .shared.rendering import make_render_context
from .shared.state import RenderContext


ResolvePlan = Callable[..., Any]
RenderPlan = Callable[..., Any]
PromptDynamicSlots = Callable[[Any], dict[str, Any]]
TraceCommon = Callable[..., dict[str, Any]]
RenderMap = Callable[[Any], dict[str, Any]]


def run_angle_chase_entry(
    task: Any,
    instance_seed: int,
    *,
    params: dict[str, Any],
    max_attempts: int,
    task_id: str,
    resolve_plan: ResolvePlan,
    render_plan: RenderPlan,
    prompt_task_key: str,
    prompt_dynamic_slots: PromptDynamicSlots,
    trace_common: TraceCommon,
    render_map: RenderMap,
    include_scene_rotation: bool = False,
) -> TaskOutput:
    """Run common render/noise/prompt plumbing around task-owned objective hooks."""

    supported_query_ids = tuple(str(value) for value in getattr(task, "supported_query_ids"))
    selected_query, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=dict(params),
        supported_query_ids=supported_query_ids,
        default_query_id=supported_query_ids[0],
        task_id=str(task_id),
        namespace=f"{task_id}.query",
    )
    generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
        SCENE_DEFAULTS,
        task_id=str(task_id),
    )
    plan: Any | None = None
    ctx: RenderContext | None = None
    rendered: Any | None = None
    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        attempt_seed = int(instance_seed) + int(attempt)
        attempt_params = {**dict(task_params), "_render_attempt": int(attempt)}
        try:
            plan = resolve_plan(
                query_id=str(selected_query),
                instance_seed=int(attempt_seed),
                params=attempt_params,
                generation_defaults=generation_defaults,
            )
            ctx = make_render_context(int(attempt_seed), attempt_params, rendering_defaults)
            rendered = render_plan(
                query_id=str(selected_query),
                ctx=ctx,
                plan=plan,
                instance_seed=int(attempt_seed),
            )
            break
        except Exception as exc:
            last_error = exc
            continue
    if plan is None or ctx is None or rendered is None:
        raise RuntimeError(f"failed to generate {task_id}") from last_error

    image, noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_artifacts = keyed_point_annotation_artifacts(
        rendered.annotation_keyed_points,
        roles=rendered.annotation_roles,
    )
    _prompt_defaults, prompt_artifacts = angle_chase_prompt_artifacts(
        prompt_defaults=prompt_defaults,
        prompt_task_key=str(prompt_task_key),
        prompt_query_key=str(selected_query),
        dynamic_slots=prompt_dynamic_slots(plan),
        annotation_keys=rendered.annotation_roles,
        answer=int(plan.answer),
        instance_seed=int(instance_seed),
    )
    common = trace_common(plan=plan, rendered=rendered, annotation_artifacts=annotation_artifacts)
    query_params = {
        "query_id_probabilities": dict(query_probabilities),
        **dict(common.get("query_params", {})),
    }
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query),
        params=query_params,
    )
    render_spec: dict[str, Any] = {
        "task_id": str(task_id),
        "query_id": str(selected_query),
        "scene_id": SCENE_ID,
        "canvas": {"width": int(ctx.width), "height": int(ctx.height)},
        "style": {
            "technical_diagram": dict(ctx.diagram_style_meta),
            "background": dict(ctx.background_meta),
            "post_image_noise": dict(noise_meta),
        },
        "prompt": {
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
        },
    }
    if bool(include_scene_rotation):
        render_spec["single_object_scene_rotation"] = ctx.scene_transform.metadata()
    trace_payload: dict[str, Any] = {
        "scene_ir": {
            "domain": DOMAIN,
            "scene_id": SCENE_ID,
            "task_id": str(task_id),
            "query_id": str(selected_query),
            "entities": common["entities"],
            "relations": common["relations"],
        },
        "query_spec": dict(query_spec),
        "render_spec": dict(render_spec),
        "render_map": render_map(rendered),
        "execution_trace": {
            "task_id": str(task_id),
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            **dict(common["execution"]),
        },
        "witness_symbolic": {
            "task_id": str(task_id),
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            **dict(common["witness"]),
        },
        "projected_annotation": dict(annotation_artifacts.projected_annotation),
    }
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=TypedValue(type="integer", value=int(plan.answer)),
        annotation_gt=TypedValue(type=annotation_artifacts.annotation_type, value=dict(annotation_artifacts.value)),
        image=image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(selected_query),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


__all__ = ["run_angle_chase_entry"]
