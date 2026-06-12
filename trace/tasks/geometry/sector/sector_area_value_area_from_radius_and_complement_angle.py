"""Compute sector area using a complementary angle relation."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from .shared.runtime import SCENE_ID, SectorFormulaRuntime


TASK_ID = "task_geometry__sector__sector_area_value_area_from_radius_and_complement_angle"
QUERY_ID = "area_from_radius_and_complement_angle"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
REASONING_KIND = "sector_measure"


@register_task
class GeometrySectorAreaFromRadiusAndComplementAngleTask:
    """Compute sector area using a complementary angle relation."""

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
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        artifact = SectorFormulaRuntime().generate_artifact(
            int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
            runtime_namespace=TASK_ID,
            query_id=str(query_id),
            query_probabilities=query_id_probabilities,
            reasoning_kind=REASONING_KIND,
        )
        answer_gt = TypedValue(type="number", value=float(artifact.answer))
        annotation_gt = TypedValue(type="bbox_set", value=list(artifact.annotation_value))
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


__all__ = ["GeometrySectorAreaFromRadiusAndComplementAngleTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
