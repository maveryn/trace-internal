"""Count visible turning points on a plotted function."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from .shared.graphing.count_common import TURNING_POINT_COUNT, _SCENE_DEFAULTS
from .shared.graphing.count_runtime import build_count_artifacts, count_query

TASK_ID = "task_geometry__function_graph__extremum_count_turning_point_count"
SCENE_ID = "function_graph"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (TURNING_POINT_COUNT,)


@register_task
class GeometryGraphingTurningPointCountTask:
    """Count visible points where the plotted graph changes direction."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=TURNING_POINT_COUNT,
            task_id=TASK_ID,
        )
        query = count_query(
            instance_seed=int(instance_seed),
            params=task_params,
            query_id=str(query_id),
            query_id_probabilities=query_probabilities,
        )
        artifacts = build_count_artifacts(
            instance_seed=int(instance_seed),
            params=task_params,
            query=query,
        )
        return TaskOutput(
            prompt=str(artifacts.prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(artifacts.rendered_scene.answer_value)),
            annotation_gt=TypedValue(
                type=str(artifacts.rendered_scene.annotation_type),
                value=list(artifacts.rendered_scene.annotation_value),
            ),
            image=artifacts.image,
            image_id="img0",
            trace_payload=artifacts.trace_payload,
            task_versions=artifacts.task_versions,
            query_id=str(query.query_id),
            prompt_variants=dict(artifacts.prompt_artifacts.prompt_variants),
        )
