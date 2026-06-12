"""Compute a side length from marked polygon equations."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from .shared.runtime import MARKED_SIDE_LENGTH_TASK_KEY, MARKED_POLYGON_SCENE_ID, MarkedEquationRuntime


TASK_ID = "task_geometry__marked_polygon_equation__side_length_value"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ('isosceles_triangle_side_from_expression', 'equilateral_triangle_side_from_expression', 'marked_polygon_side_from_expression', 'equilateral_median_side_length_from_expression')


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
class GeometryMarkedPolygonEquationSideLengthValueTask:
    """Compute a side length from marked polygon equations."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = MARKED_POLYGON_SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities, task_params = _select_query(int(instance_seed), params)
        runtime = MarkedEquationRuntime(
            runtime_namespace=TASK_ID,
            case_family=MARKED_SIDE_LENGTH_TASK_KEY,
            scene_id=MARKED_POLYGON_SCENE_ID,
        )
        artifact = runtime.generate(
            int(instance_seed),
            params={**task_params, "query_id": str(query_id)},
            max_attempts=int(max_attempts),
        )
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
            scene_id=MARKED_POLYGON_SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(artifact.prompt_variants),
        )


__all__ = ["GeometryMarkedPolygonEquationSideLengthValueTask"]
