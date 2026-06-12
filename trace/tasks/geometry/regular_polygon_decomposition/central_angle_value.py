"""Find a central angle in a regular-polygon decomposition."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from .shared.runtime import ANGLE_OBJECTIVE_KEY, RegularPolygonDecompositionRuntime, SCENE_ID


TASK_ID = "task_geometry__regular_polygon_decomposition__central_angle_value"
SUPPORTED_QUERY_IDS = (
    'single_wedge_central_angle',
    'marked_wedges_central_angle',
)
DEFAULT_QUERY_ID = "single_wedge_central_angle"
TASK_KEY = "central_angle_value_query"
ANSWER_HINT_KEY = "answer_hint_integer_degrees"


@register_task
class GeometryRegularPolygonDecompositionCentralAngleTask:
    """Find a central angle in a regular-polygon decomposition."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_id_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=DEFAULT_QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        artifact = RegularPolygonDecompositionRuntime().generate_artifact(
            int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
            runtime_namespace=TASK_ID,
            query_id=str(query_id),
            query_probabilities=query_id_probabilities,
            objective_key=ANGLE_OBJECTIVE_KEY,
            task_key=TASK_KEY,
            answer_hint_key=ANSWER_HINT_KEY,
        )
        answer_gt = TypedValue(type=str(artifact.answer_type), value=artifact.answer)
        annotation_gt = TypedValue(type="keyed_point_map", value=dict(artifact.annotation_value))
        return TaskOutput(
            prompt=str(artifact.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=artifact.image,
            image_id="img0",
            trace_payload=artifact.trace_payload,
            task_versions=artifact.task_versions,
            scene_id=SCENE_ID,
            query_id=str(artifact.query_id),
            prompt_variants=dict(artifact.prompt_variants),
        )


__all__ = ["GeometryRegularPolygonDecompositionCentralAngleTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
