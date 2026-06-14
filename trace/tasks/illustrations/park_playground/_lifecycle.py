"""Neutral render lifecycle helpers for park/playground tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...shared.config_defaults import required_group_defaults
from ...shared.output_metadata import default_task_versions
from .shared.output import park_render_spec, park_scene_ir
from .shared.prompts import build_park_prompt_artifacts
from .shared.rendering import render_park_playground_scene
from .shared.sampling import render_params, setting_weights, style_weights
from .shared.state import ParkEquipmentSpec, ParkPersonSpec, RenderedParkPlaygroundScene


def render_scene_with_retries(
    *,
    namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    fallback_width: int,
    fallback_height: int,
    fallback_scale: int,
    max_attempts: int,
    person_specs: Sequence[ParkPersonSpec],
    equipment_specs: Sequence[ParkEquipmentSpec] | None = None,
    required_zones: Sequence[str] = (),
) -> RenderedParkPlaygroundScene:
    """Render a scene from already-sampled semantic specs, retrying layout only."""

    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            scene_rng = spawn_rng(int(instance_seed), f"{namespace}:scene", int(attempt))
            rp = render_params(
                params,
                render_defaults,
                fallback_width=int(fallback_width),
                fallback_height=int(fallback_height),
                fallback_scale=int(fallback_scale),
            )
            return render_park_playground_scene(
                rng=scene_rng,
                person_specs=tuple(person_specs),
                equipment_specs=None if equipment_specs is None else tuple(equipment_specs),
                required_zones=tuple(str(value) for value in required_zones),
                canvas_width=int(rp["canvas_width"]),
                canvas_height=int(rp["canvas_height"]),
                render_scale=int(rp["render_scale"]),
                setting_weights=setting_weights(params, render_defaults),
                style_weights=style_weights(params, render_defaults),
            )
        except Exception as exc:  # pragma: no cover - retry surface is seed/layout dependent.
            last_error = exc
    raise RuntimeError(f"could not render park/playground scene: {last_error}") from last_error


def compose_count_result(
    *,
    task: Any,
    scene: RenderedParkPlaygroundScene,
    prompt_defaults: Mapping[str, Any],
    prompt_required_keys: Sequence[str],
    prompt_query_key: str,
    slots: Mapping[str, Any],
    instance_seed: int,
    answer: int,
    annotation_value: Sequence[Sequence[float]],
    render_map: Mapping[str, Any],
    scene_relations: Mapping[str, Any],
    query_params: Mapping[str, Any],
    execution_trace: Mapping[str, Any],
    witness_symbolic: Mapping[str, Any],
    scene_entities: Sequence[Mapping[str, Any]],
) -> TaskOutput:
    """Assemble the common count-task prompt, trace payload, and return value."""

    required_defaults = required_group_defaults(
        prompt_defaults,
        list(prompt_required_keys),
        context=f"prompt defaults for {task.task_id}",
    )
    prompt_artifacts = build_park_prompt_artifacts(
        domain=str(task.domain),
        scene_id="park_playground",
        prompt_defaults=required_defaults,
        prompt_query_key=str(prompt_query_key),
        slots=dict(slots),
        instance_seed=int(instance_seed),
    )
    trace_payload = {
        "scene_ir": park_scene_ir(
            domain=str(task.domain),
            scene_id="park_playground",
            entities=[dict(entity) for entity in scene_entities],
            relations=dict(scene_relations),
        ),
        "query_spec": {
            "task_id": str(task.task_id),
            "query_id": str(query_params["query_id"]),
            "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_params),
        },
        "render_spec": park_render_spec(scene),
        "render_map": dict(render_map),
        "execution_trace": dict(execution_trace),
        "witness_symbolic": dict(witness_symbolic),
        "projected_annotation": {"bbox_set": [list(box) for box in annotation_value]},
    }
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        answer_gt=TypedValue(type="integer", value=int(answer)),
        annotation_gt=TypedValue(type="bbox_set", value=[list(box) for box in annotation_value]),
        image=scene.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id="park_playground",
        query_id=str(query_params["query_id"]),
    )


__all__ = ["compose_count_result", "render_scene_with_retries"]
