"""Scene-private lifecycle plumbing for Crossing public tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.shared.annotation_artifacts import bbox_set_annotation_artifacts
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import entity_bboxes_for_ids
from .shared.defaults import SCENE_ID
from .shared.output import common_trace_params, common_trace_sections
from .shared.prompts import (
    build_crossing_prompt_artifacts,
    crossing_motion_rule_text,
    crossing_object_description,
    crossing_output_slots,
    json_examples_for_integer_answer,
)
from .shared.rendering import render_crossing_sample
from .shared.sampling import resolve_crossing_scene_axes, resolve_target_answer, sample_crossing_scene
from .shared.state import CrossingSample, CrossingSceneAxes


CrossingAttemptBuilder = Callable[[Any], CrossingSample]
CrossingAnswerBuilder = Callable[[CrossingSample], TypedValue]
CrossingEntityIdsBuilder = Callable[[CrossingSample], Sequence[str]]
CrossingMappingBuilder = Callable[[CrossingSample], Mapping[str, Any]]
CrossingObjectivePreparer = Callable[
    [int, Mapping[str, Any], str, Mapping[str, float]],
    "CrossingObjectivePlan",
]


@dataclass(frozen=True)
class CrossingObjectivePlan:
    """Task-owned objective hooks consumed by neutral Crossing lifecycle code."""

    axes: CrossingSceneAxes
    attempt_namespace: str
    construct_attempt: CrossingAttemptBuilder
    prompt_query_key: str
    prompt_dynamic_slots: CrossingMappingBuilder
    answer_gt: CrossingAnswerBuilder
    annotation_entity_ids: CrossingEntityIdsBuilder
    query_spec_params: CrossingMappingBuilder
    execution_updates: CrossingMappingBuilder


@dataclass(frozen=True)
class CrossingCountObjectiveSpec:
    """Task-owned semantic parameters for one integer-count Crossing objective."""

    prompt_query_key: str
    count_mode: str
    support_key: str
    fallback_support: tuple[int, ...]
    include_route_in_description: bool
    include_motion_rule_text: bool = False
    min_lane_count_answer_padding: int | None = None
    min_row_count_from_answer: bool = False


def prepare_count_objective_from_spec(
    *,
    task_id: str,
    spec: CrossingCountObjectiveSpec,
    instance_seed: int,
    task_params: Mapping[str, Any],
    selected_query_id: str,
    gen_defaults: Mapping[str, Any],
) -> CrossingObjectivePlan:
    """Build a Crossing count objective from task-owned semantic arguments."""

    target_answer, target_support, target_probabilities = resolve_target_answer(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=gen_defaults,
        support_key=str(spec.support_key),
        fallback_support=tuple(int(value) for value in spec.fallback_support),
        namespace=f"{task_id}.target_answer.{str(selected_query_id)}",
    )
    min_lane_count = 0
    if spec.min_lane_count_answer_padding is not None:
        min_lane_count = min(8, int(target_answer) + int(spec.min_lane_count_answer_padding))
    axes = resolve_crossing_scene_axes(
        int(instance_seed),
        params=task_params,
        gen_defaults=gen_defaults,
        min_lane_count=int(min_lane_count),
        min_row_count=int(target_answer) if bool(spec.min_row_count_from_answer) else 0,
        namespace_suffix=str(selected_query_id),
    )

    def construct_attempt(rng):
        return sample_crossing_scene(
            rng=rng,
            axes=axes,
            count_mode=str(spec.count_mode),
            target_answer=int(target_answer),
            gen_defaults=gen_defaults,
        )

    def prompt_slots(_sample) -> dict[str, Any]:
        json_example, json_example_answer_only = json_examples_for_integer_answer()
        dynamic_slots: dict[str, Any] = {
            "object_description": crossing_object_description(include_route=bool(spec.include_route_in_description)),
            **crossing_output_slots(
                prompt_query_key=str(spec.prompt_query_key),
                json_example=json_example,
                json_example_answer_only=json_example_answer_only,
            ),
        }
        if bool(spec.include_motion_rule_text):
            dynamic_slots["crossing_motion_rule_text"] = crossing_motion_rule_text()
        return dynamic_slots

    def query_spec_params(_sample) -> dict[str, Any]:
        return {
            "target_answer": int(target_answer),
            "target_answer_support": [int(value) for value in target_support],
            "target_answer_probabilities": dict(target_probabilities),
            "count_mode": str(spec.count_mode),
        }

    return CrossingObjectivePlan(
        axes=axes,
        attempt_namespace=str(task_id),
        construct_attempt=construct_attempt,
        prompt_query_key=str(spec.prompt_query_key),
        prompt_dynamic_slots=prompt_slots,
        answer_gt=lambda sample: TypedValue(type="integer", value=int(sample.answer)),
        annotation_entity_ids=lambda sample: sample.annotation_entity_ids,
        query_spec_params=query_spec_params,
        execution_updates=lambda _sample: {"target_answer": int(target_answer)},
    )


def sample_with_retries(
    *,
    task_id: str,
    instance_seed: int,
    max_attempts: int,
    attempt_namespace: str,
    construct_attempt: CrossingAttemptBuilder,
) -> CrossingSample:
    """Run task-owned Crossing construction attempts with stable retry seeds."""

    last_error: ValueError | None = None
    for attempt_index in range(max(1, int(max_attempts))):
        rng = spawn_rng(int(instance_seed), f"{attempt_namespace}.attempt.{int(attempt_index)}")
        try:
            return construct_attempt(rng)
        except ValueError as exc:
            last_error = exc
            continue
    raise RuntimeError(f"{task_id} failed to generate a valid scene after {max_attempts} attempts") from last_error


def run_crossing_lifecycle(
    *,
    task_id: str,
    domain: str,
    supported_query_ids: tuple[str, ...],
    default_query_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
    prepare_objective: CrossingObjectivePreparer,
) -> TaskOutput:
    """Run neutral Crossing query, retry, render, prompt, and output plumbing."""

    selected_query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=tuple(str(value) for value in supported_query_ids),
        default_query_id=str(default_query_id),
        task_id=str(task_id),
        namespace=f"{task_id}.query",
    )
    objective = prepare_objective(
        int(instance_seed),
        task_params,
        str(selected_query_id),
        query_probabilities,
    )
    sample = sample_with_retries(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        max_attempts=int(max_attempts),
        attempt_namespace=str(objective.attempt_namespace),
        construct_attempt=objective.construct_attempt,
    )
    rendered_context = render_crossing_sample(
        sample=sample,
        params=task_params,
        instance_seed=int(instance_seed),
    )
    annotation_bboxes = entity_bboxes_for_ids(
        rendered_context.rendered_scene,
        objective.annotation_entity_ids(sample),
    )
    annotation_artifacts = bbox_set_annotation_artifacts(annotation_bboxes)
    _prompt_defaults, prompt_artifacts = build_crossing_prompt_artifacts(
        domain=str(domain),
        prompt_query_key=str(objective.prompt_query_key),
        dynamic_slots=dict(objective.prompt_dynamic_slots(sample)),
        instance_seed=int(instance_seed),
    )
    answer_gt = objective.answer_gt(sample)
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query_id),
        params=common_trace_params(
            axes=objective.axes,
            sample=sample,
            extra_params={
                "query_id_probabilities": dict(query_probabilities),
                **dict(objective.query_spec_params(sample)),
            },
        ),
    )
    trace_payload = common_trace_sections(
        axes=objective.axes,
        sample=sample,
        rendered_context=rendered_context,
        annotation_artifacts=annotation_artifacts,
        query_spec=query_spec,
        execution_extra={
            "query_id": str(selected_query_id),
            "answer": answer_gt.value,
            **dict(objective.execution_updates(sample)),
        },
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_gt=answer_gt,
        annotation_gt=annotation_artifacts.annotation_gt,
        image=rendered_context.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(selected_query_id),
    )


__all__ = [
    "CrossingCountObjectiveSpec",
    "CrossingObjectivePlan",
    "prepare_count_objective_from_spec",
    "run_crossing_lifecycle",
    "sample_with_retries",
]
