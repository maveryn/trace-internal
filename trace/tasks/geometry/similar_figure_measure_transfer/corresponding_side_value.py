"""Find a corresponding side length between similar figures."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from .shared.measure_transfer_runtime import SCENE_ID, MeasureTransferRuntime


TASK_ID = "task_geometry__similar_figure_measure_transfer__corresponding_side_value"
OBJECTIVE_KEY = "corresponding_side_value"
SUPPORTED_QUERY_IDS = ('direct_side_transfer', 'two_pair_side_transfer', 'nested_side_transfer')
DEFAULT_QUERY_ID = SUPPORTED_QUERY_IDS[0]


@register_task
class GeometrySimilarFigureMeasureTransferCorrespondingSideValueTask:
    """Find a corresponding side length between similar figures."""

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
            default_query_id=DEFAULT_QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        artifact = MeasureTransferRuntime().generate_artifact(
            int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
            runtime_namespace=TASK_ID,
            objective_key=OBJECTIVE_KEY,
            query_id=str(query_id),
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


__all__ = ["GeometrySimilarFigureMeasureTransferCorrespondingSideValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
