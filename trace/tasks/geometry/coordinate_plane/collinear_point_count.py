"""Count coordinate-plane points collinear with the reference line AB."""

from __future__ import annotations

from typing import Any, Dict

from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id

from .shared.coordinate.relation_common import COUNT_QUERY_IDS, _SCENE_DEFAULTS
from .shared.coordinate.relation_runtime import build_relation_artifacts, relation_query

TASK_ID = "task_geometry__coordinate_plane__collinear_point_count"
SCENE_ID = "coordinate_plane"
SUPPORTED_QUERY_IDS = ("collinear_count",)
SCENE_VARIANT = "line_points"


@register_task
class GeometryCoordinateCollinearPointCountTask:
    """Count dot points that lie on the same line as A and B."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
        )
        query = relation_query(
            instance_seed=int(instance_seed),
            params=task_params,
            query_id=str(query_id),
            query_id_probabilities=query_probabilities,
            scene_variant=SCENE_VARIANT,
            scene_variant_probabilities={SCENE_VARIANT: 1.0},
        )
        artifacts = build_relation_artifacts(
            instance_seed=int(instance_seed),
            params=task_params,
            query=query,
            max_attempts=int(max_attempts),
        )
        return TaskOutput(
            prompt=str(artifacts.prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=artifacts.rendered_scene.answer_value),
            annotation_gt=TypedValue(
                type=str(artifacts.rendered_scene.annotation_type),
                value=artifacts.rendered_scene.annotation_value,
            ),
            image=artifacts.image,
            image_id="img0",
            trace_payload=artifacts.trace_payload,
            task_versions=artifacts.task_versions,
            query_id=str(query.query_id),
            prompt_variants=dict(artifacts.prompt_artifacts.prompt_variants),
        )
