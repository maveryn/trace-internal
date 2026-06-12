"""Count quadrilaterals of a requested type."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from .shared.consolidated_runtime import build_counting_output

TASK_ID = 'task_geometry__graph_paper__quadrilateral_type_count'
SCENE_ID = "graph_paper"
QUERY_ID = 'quadrilateral_type_count'
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
ALLOWED_SCENE_VARIANTS: Tuple[str, ...] = ('quadrilateral',)


@register_task
class GeometryCountingQuadrilateralTypeCountTask:
    """Count quadrilaterals of a requested type."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, _query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
        )
        output = build_counting_output(
            instance_seed=int(instance_seed),
            params=task_params,
            query_id=str(query_id),
            allowed_scene_variants=ALLOWED_SCENE_VARIANTS,
            max_attempts=int(max_attempts),
        )
        final_output = TaskOutput(
            prompt=str(output.prompt),
            answer_gt=output.answer_gt,
            annotation_gt=output.annotation_gt,
            image=output.image,
            image_id=str(output.image_id),
            trace_payload=dict(output.trace_payload),
            task_versions=dict(output.task_versions),
            query_id=str(output.query_id),
            prompt_variants=dict(output.prompt_variants),
        )
        return final_output
