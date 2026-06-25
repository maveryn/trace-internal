"""Scene-private lifecycle plumbing for slot-machine public tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import payline_segment_set_annotation
from .shared.defaults import SCENE_ID, SCENE_NAMESPACE
from .shared.output import build_slot_machine_common_trace_params, build_slot_machine_trace_payload
from .shared.prompts import build_slot_machine_prompt_artifacts
from .shared.rendering import resolve_slot_machine_render_params, render_slot_machine_scene
from .shared.sampling import resolve_slot_machine_axes
from .shared.state import SlotMachineAxes, SlotMachineScene


AttemptBuilder = Callable[[Any, SlotMachineAxes], "SlotMachineAttemptResult"]
ObjectivePreparer = Callable[
    [int, Mapping[str, Any], str, Mapping[str, float], SlotMachineAxes],
    "SlotMachineObjectivePlan",
]


@dataclass(frozen=True)
class SlotMachineAttemptResult:
    """Task-owned result of one constructed slot-machine sample."""

    scene: SlotMachineScene
    answer_gt: TypedValue
    annotation_payline_ids: tuple[str, ...]
    query_params: Mapping[str, Any]
    execution_extra: Mapping[str, Any]


@dataclass(frozen=True)
class SlotMachineObjectivePlan:
    """Prepared task-owned objective hooks for one generated instance."""

    attempt_namespace: str
    prompt_query_key: str
    query_params: Mapping[str, Any]
    prompt_dynamic_slots: Mapping[str, Any]
    construct_attempt: AttemptBuilder


def run_slot_machine_lifecycle(
    *,
    task_id: str,
    domain: str,
    supported_query_ids: Sequence[str],
    default_query_id: str,
    gen_defaults: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
    prepare_objective: ObjectivePreparer,
) -> TaskOutput:
    """Run neutral slot-machine generation after public code binds an objective."""

    selected_query, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=supported_query_ids,
        default_query_id=str(default_query_id),
        task_id=str(task_id),
        namespace=f"{SCENE_NAMESPACE}.{task_id}.query",
    )
    axes = resolve_slot_machine_axes(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=gen_defaults,
    )
    render_params = resolve_slot_machine_render_params(task_params, render_defaults)
    objective = prepare_objective(
        int(instance_seed),
        task_params,
        str(selected_query),
        dict(query_probabilities),
        axes,
    )
    prompt_defaults, prompt_artifacts = build_slot_machine_prompt_artifacts(
        domain=str(domain),
        prompt_query_key=str(objective.prompt_query_key),
        dynamic_slots=dict(objective.prompt_dynamic_slots),
        instance_seed=int(instance_seed),
    )
    query_params = build_slot_machine_common_trace_params(
        axes=axes,
        extra_params={
            "query_id_probabilities": dict(query_probabilities),
            **dict(objective.query_params),
        },
    )
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query),
        params=query_params,
    )
    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        rng = spawn_rng(int(instance_seed), f"{objective.attempt_namespace}.attempt.{attempt}")
        try:
            attempt_result = objective.construct_attempt(rng, axes)
            rendered_scene = render_slot_machine_scene(
                scene=attempt_result.scene,
                render_params=render_params,
                instance_seed=int(instance_seed),
            )
            annotation_artifacts: AnnotationArtifacts = payline_segment_set_annotation(
                rendered_scene,
                attempt_result.annotation_payline_ids,
            )
            trace_payload = build_slot_machine_trace_payload(
                axes=axes,
                scene=attempt_result.scene,
                rendered_scene=rendered_scene,
                annotation_artifacts=annotation_artifacts,
                annotation_payline_ids=attempt_result.annotation_payline_ids,
                query_spec=query_spec,
                answer_value=int(attempt_result.answer_gt.value),
                execution_extra={
                    "prompt_query_key": str(objective.prompt_query_key),
                    "prompt_bundle_id": str(prompt_defaults["bundle_id"]),
                    **dict(attempt_result.execution_extra),
                },
            )
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=attempt_result.answer_gt,
                annotation_gt=annotation_artifacts.annotation_gt,
                image=rendered_scene.image,
                image_id=f"{task_id}_{int(instance_seed)}",
                trace_payload=trace_payload,
                task_versions=default_task_versions(),
                scene_id=SCENE_ID,
                query_id=str(selected_query),
            )
        except ValueError as exc:
            last_error = exc
            continue
    raise RuntimeError(f"failed to generate {task_id} after {max_attempts} attempts") from last_error


__all__ = [
    "SlotMachineAttemptResult",
    "SlotMachineObjectivePlan",
    "run_slot_machine_lifecycle",
]
