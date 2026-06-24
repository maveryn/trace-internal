"""Private lifecycle plumbing for isometric harbor count tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.shared.config_defaults import required_group_defaults
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.output import bbox_set_projection, isometric_harbor_render_spec, isometric_harbor_scene_ir
from .shared.prompts import build_isometric_harbor_prompt_artifacts
from .shared.rendering import SCENE_ID
from .shared.sampling import CountTaskSampleSpec
from .shared.spatial_primitives import rounded_bbox
from .shared.state import IsoHarborEntity, IsoHarborScene


@dataclass(frozen=True)
class HarborCountPlan:
    """Public-owned hooks for one harbor count objective."""

    public_id: str
    operation: str
    required_prompt_keys: tuple[str, ...]
    sample_spec: Callable[[int, Mapping[str, Any]], CountTaskSampleSpec]
    prompt_slots: Callable[[Mapping[str, Any], CountTaskSampleSpec], Mapping[str, Any]]
    scene_builder: Callable[[int, CountTaskSampleSpec], IsoHarborScene]
    entity_selector: Callable[[IsoHarborScene, CountTaskSampleSpec], Sequence[IsoHarborEntity]]
    render_map: Callable[[IsoHarborScene, CountTaskSampleSpec, tuple[str, ...]], Mapping[str, Any]]
    identity_fields: Callable[[CountTaskSampleSpec], Mapping[str, Any]]
    extra_query_params: Callable[[CountTaskSampleSpec], Mapping[str, Any]]
    scene_validator: Callable[[IsoHarborScene, CountTaskSampleSpec], None] | None = None


def sorted_harbor_boats(
    scene: IsoHarborScene,
    *,
    predicate: Callable[[IsoHarborEntity], bool],
) -> tuple[IsoHarborEntity, ...]:
    """Return countable boat witnesses in stable annotation order."""

    return tuple(
        sorted(
            (
                entity
                for entity in scene.entities
                if str(entity.object_type) == "boat" and bool(predicate(entity))
            ),
            key=lambda entity: (float(entity.bbox_xyxy[1]), float(entity.bbox_xyxy[0]), str(entity.entity_id)),
        )
    )


def run_harbor_count_lifecycle(
    *,
    plan: HarborCountPlan,
    domain: str,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Render one harbor scene, bind task-owned witnesses, and package `TaskOutput`."""

    sample = plan.sample_spec(int(instance_seed), dict(params))
    checked_prompt_defaults = required_group_defaults(
        prompt_defaults,
        list(plan.required_prompt_keys),
        context=f"prompt defaults for {plan.public_id}",
    )
    last_error: Exception | None = None
    scene: IsoHarborScene | None = None
    counted_entities: tuple[IsoHarborEntity, ...] = ()
    for attempt in range(max(1, int(max_attempts))):
        try:
            scene_seed = int(instance_seed) + int(attempt) * 1009
            scene = plan.scene_builder(scene_seed, sample)
            counted_entities = tuple(plan.entity_selector(scene, sample))
            if len(counted_entities) != int(sample.target_count):
                raise ValueError(f"count {len(counted_entities)} did not match target_count {sample.target_count}")
            if plan.scene_validator is not None:
                plan.scene_validator(scene, sample)
            break
        except Exception as exc:
            last_error = exc
            scene = None
            counted_entities = ()
    if scene is None:
        raise RuntimeError(f"could not generate harbor task instance: {last_error}") from last_error

    annotation_value = [rounded_bbox(entity.bbox_xyxy) for entity in counted_entities]
    counted_entity_ids = tuple(str(entity.entity_id) for entity in counted_entities)
    prompt_artifacts = build_isometric_harbor_prompt_artifacts(
        domain=str(domain),
        scene_id=SCENE_ID,
        prompt_defaults=checked_prompt_defaults,
        prompt_query_key=str(sample.prompt_query_key),
        slots=dict(plan.prompt_slots(checked_prompt_defaults, sample)),
        instance_seed=int(instance_seed),
    )
    identity_fields = dict(plan.identity_fields(sample))
    extra_query_params = dict(plan.extra_query_params(sample))
    query_params = {
        "query_id": str(sample.selected_key),
        "prompt_query_key": str(sample.prompt_query_key),
        "query_id_probabilities": dict(sample.query_probabilities),
        "target_count": int(sample.target_count),
        "target_count_probabilities": dict(sample.target_count_probabilities),
        "answer_count_support": list(sample.answer_count_support),
        "answer_count_probabilities": dict(sample.answer_count_probabilities),
        "answer_count": int(len(counted_entities)),
        "counted_entity_ids": list(counted_entity_ids),
        "canvas_profile": str(sample.canvas_profile),
        "canvas_profile_probabilities": dict(sample.canvas_profile_probabilities),
        **identity_fields,
        **extra_query_params,
    }
    trace_payload = {
        "scene_ir": isometric_harbor_scene_ir(
            domain=str(domain),
            scene_id=SCENE_ID,
            scene=scene,
            relations={
                "operation": str(plan.operation),
                **identity_fields,
                "answer_count": int(len(counted_entities)),
                "counted_entity_ids": list(counted_entity_ids),
                "counted_entity_bboxes_px": [list(bbox) for bbox in annotation_value],
            },
        ),
        "query_spec": {
            "task_id": str(plan.public_id),
            "query_id": str(sample.selected_key),
            "prompt_query_key": str(sample.prompt_query_key),
            "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": query_params,
        },
        "render_spec": isometric_harbor_render_spec(scene, scene_id=SCENE_ID),
        "render_map": dict(plan.render_map(scene, sample, counted_entity_ids)),
        "execution_trace": {
            "query_id": str(sample.selected_key),
            "prompt_query_key": str(sample.prompt_query_key),
            "scene_id": SCENE_ID,
            "answer": int(len(counted_entities)),
            **identity_fields,
            "counted_entity_ids": list(counted_entity_ids),
            "renderer": dict(scene.trace),
        },
        "witness_symbolic": {
            "answer_count": int(len(counted_entities)),
            **identity_fields,
            "counted_entity_ids": list(counted_entity_ids),
            "counted_entity_bboxes": [list(bbox) for bbox in annotation_value],
        },
        "projected_annotation": bbox_set_projection(annotation_value),
    }
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        answer_gt=TypedValue(type="integer", value=int(len(counted_entities))),
        annotation_gt=TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_value]),
        image=scene.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(sample.selected_key),
    )


__all__ = ["HarborCountPlan", "run_harbor_count_lifecycle", "sorted_harbor_boats"]
