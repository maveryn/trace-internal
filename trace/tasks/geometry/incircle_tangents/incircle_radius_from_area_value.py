"""Compute an incircle radius from triangle area and tangent labels."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from .shared.runtime import IncircleTangentRuntime, SCENE_ID, _INCIRCLE_RADIUS_QUERIES


TASK_ID = "task_geometry__incircle_tangents__incircle_radius_from_area_value"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = _INCIRCLE_RADIUS_QUERIES


def _select_query(instance_seed: int, params: Dict[str, Any]) -> tuple[str, dict[str, float], Dict[str, Any]]:
    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SUPPORTED_QUERY_IDS[0],
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )


@register_task
class GeometryIncircleRadiusFromAreaValueTask:
    """Compute incircle radius from area and tangent segment labels."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities, task_params = _select_query(int(instance_seed), params)
        artifact = IncircleTangentRuntime(
            runtime_namespace=TASK_ID,
            supported_queries=(str(query_id),),
            reasoning_kind="incircle_radius",
        ).generate(int(instance_seed), params={**task_params, "query_id": str(query_id)}, max_attempts=int(max_attempts))
        artifact.trace_payload["query_spec"]["params"]["query_id_probabilities"] = dict(query_probabilities)
        artifact.trace_payload["execution_trace"]["query_id_probabilities"] = dict(query_probabilities)
        return TaskOutput(
            prompt=str(artifact.prompt),
            answer_gt=artifact.answer_gt,
            annotation_gt=artifact.annotation_gt,
            image=artifact.image,
            image_id=str(artifact.image_id),
            trace_payload=dict(artifact.trace_payload),
            task_versions=dict(artifact.task_versions),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(artifact.prompt_variants),
        )


__all__ = ["GeometryIncircleRadiusFromAreaValueTask"]
