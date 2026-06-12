"""Infer a corresponding angle measure from congruent triangles."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from .shared.triangle_congruence_runtime import ANGLE_OBJECTIVE, SCENE_ID, TriangleCongruenceCorrespondenceRuntime


TASK_ID = "task_geometry__triangle_congruence_correspondence__corresponding_angle_value"
TASK_PROMPT_KEY = "corresponding_angle_value_query"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    'angle_mark_transfer',
    'congruence_statement_angle_transfer',
    'overlapping_triangle_angle_transfer',
)


@register_task
class GeometryTriangleCongruenceCorrespondenceAngleValueTask:
    """Infer a corresponding angle measure from congruent triangles."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, _query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        artifact = TriangleCongruenceCorrespondenceRuntime().generate_artifact(
            int(instance_seed),
            params={**dict(task_params), "query_id": str(query_id)},
            max_attempts=int(max_attempts),
            public_task_id=TASK_ID,
            objective_id=ANGLE_OBJECTIVE,
            task_prompt_key=TASK_PROMPT_KEY,
            query_ids=SUPPORTED_QUERY_IDS,
        )
        final_output = TaskOutput(
            prompt=str(artifact.prompt),
            answer_gt=TypedValue(type=str(artifact.answer_type), value=artifact.answer_value),
            annotation_gt=TypedValue(type=str(artifact.annotation_type), value=artifact.annotation_value),
            image=artifact.image,
            image_id="img0",
            trace_payload=artifact.trace_payload,
            task_versions=artifact.task_versions,
            scene_id=SCENE_ID,
            query_id=str(artifact.query_id),
            prompt_variants=dict(artifact.prompt_variants),
        )
        return final_output


__all__ = ["GeometryTriangleCongruenceCorrespondenceAngleValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
