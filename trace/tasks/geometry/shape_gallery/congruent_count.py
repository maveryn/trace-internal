"""Count candidate polygons congruent to a reference polygon."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from .shared.similarity_runtime import SCENE_ID, SimilarityCountRuntime


TASK_ID = "task_geometry__shape_gallery__congruent_count"
QUERY_ID = "congruent_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


@register_task
class GeometryShapeGalleryCongruentCountTask:
    """Count candidate polygons congruent to a reference polygon."""

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
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        artifact = SimilarityCountRuntime().generate_artifact(
            int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
            runtime_namespace=TASK_ID,
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


__all__ = ["GeometryShapeGalleryCongruentCountTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
