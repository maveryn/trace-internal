"""Compute trapezoid area from its extension construction and height."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from .shared.trapezoid_extension_runtime import _AREA_CASES, SCENE_ID, TrapezoidExtensionRuntime


TASK_ID = "task_geometry__trapezoid_extension__trapezoid_area_from_extension_and_height"
QUERY_ID = "trapezoid_area_from_extension_and_height"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
ANSWER_KIND = "area"


@register_task
class GeometryTrapezoidAreaFromExtensionAndHeightTask:
    """Compute trapezoid area from its extension construction and height."""

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
        cases = tuple(case for case in _AREA_CASES if case.query_id == str(query_id))
        artifact = TrapezoidExtensionRuntime().generate_artifact(
            int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
            runtime_namespace=TASK_ID,
            supported_queries=(str(query_id),),
            cases=cases,
            answer_kind=ANSWER_KIND,
        )
        return TaskOutput(
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


__all__ = ["GeometryTrapezoidAreaFromExtensionAndHeightTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
