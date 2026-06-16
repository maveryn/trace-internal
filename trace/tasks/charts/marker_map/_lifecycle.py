"""Private neutral lifecycle for marker-map chart tasks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.marker_map.shared.annotations import MarkerMapAnnotationBundle
from trace.tasks.charts.marker_map.shared.defaults import SCENE_ID
from trace.tasks.charts.marker_map.shared.output import base_query_params, build_trace_scaffold
from trace.tasks.charts.marker_map.shared.prompts import build_prompt_artifacts, dynamic_slots
from trace.tasks.charts.marker_map.shared.rendering import MarkerMapRenderResult, render_marker_map
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


@dataclass(frozen=True)
class MarkerMapBoundObjective:
    """Task-owned answer, annotation, and verifier relations after rendering."""

    answer_gt: TypedValue
    annotation: MarkerMapAnnotationBundle
    relations: Mapping[str, Any]
    witness_symbolic: Mapping[str, Any]


def marker_map_attempt_seed(instance_seed: int, attempt: int) -> int:
    """Return the neutral retry seed for marker-map scene attempts."""

    return (
        int(instance_seed)
        if int(attempt) == 0
        else int(hash64(int(instance_seed), f"{SCENE_ID}.retry", int(attempt)))
    )


def run_marker_map_lifecycle(
    *,
    task: Any,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
    default_query_id: str,
    prompt_query_key: str,
    answer_type: str,
    question_format: str,
    build_dataset: Callable[[int, Mapping[str, Any], str, Mapping[str, float]], Mapping[str, Any]],
    bind_objective: Callable[[Mapping[str, Any], MarkerMapRenderResult, str], MarkerMapBoundObjective],
) -> TaskOutput:
    """Materialize one task-owned marker-map objective with neutral retry/render plumbing."""

    selected_query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=dict(params),
        supported_query_ids=task.supported_query_ids,
        default_query_id=str(default_query_id),
        task_id=str(task.task_id),
    )
    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        attempt_seed = marker_map_attempt_seed(int(instance_seed), int(attempt))
        try:
            dataset = build_dataset(
                int(attempt_seed),
                dict(task_params),
                str(selected_query_id),
                dict(query_probabilities),
            )
            rendered: MarkerMapRenderResult = render_marker_map(
                dataset=dataset,
                params=dict(task_params),
                instance_seed=int(attempt_seed),
            )
            prompt_artifacts = build_prompt_artifacts(
                prompt_query_key=str(prompt_query_key),
                dynamic_slot_values=dynamic_slots(dataset),
                instance_seed=int(attempt_seed),
            )
            bound = bind_objective(dataset, rendered, str(selected_query_id))
            annotation_bundle = bound.annotation
            qparams = base_query_params(
                dataset=dataset,
                scene_variant=str(dataset["scene_variant"]),
                scene_variant_probabilities=dict(dataset["_scene_variant_probabilities"]),
            )
            qparams["query_id"] = str(selected_query_id)
            qparams["query_id_probabilities"] = dict(query_probabilities)
            query_spec = build_prompt_query_spec(
                prompt_artifacts=prompt_artifacts,
                query_id=str(selected_query_id),
                params=qparams,
            )
            trace_payload = build_trace_scaffold(
                dataset=dataset,
                rendered=rendered,
                scene_variant=str(dataset["scene_variant"]),
                scene_variant_probabilities=dict(dataset["_scene_variant_probabilities"]),
                query_spec=query_spec,
                question_format=str(question_format),
                answer_value=bound.answer_gt.value,
                answer_type=str(answer_type),
                annotation_type=str(annotation_bundle.annotation_type),
                annotation_region_ids=annotation_bundle.annotation_region_ids,
                projected_annotation=annotation_bundle.projected_annotation,
                relations=bound.relations,
                witness_symbolic=bound.witness_symbolic,
                annotation_refs=annotation_bundle.annotation_refs,
            )
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=bound.answer_gt,
                annotation_gt=annotation_bundle.annotation_gt,
                image=rendered.image,
                image_id="img0",
                trace_payload=trace_payload,
                task_versions=default_task_versions(),
                scene_id=SCENE_ID,
                query_id=str(selected_query_id),
            )
        except ValueError as exc:
            last_error = exc
    raise RuntimeError(f"failed to generate marker-map task: {last_error}") from last_error


__all__ = [
    "MarkerMapBoundObjective",
    "marker_map_attempt_seed",
    "run_marker_map_lifecycle",
]
