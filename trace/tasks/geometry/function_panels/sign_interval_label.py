"""Select the panel whose graph has the requested sign on an interval."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from .shared.analytical.function_property_common import SIGN_INTERVAL_VARIANTS
from .shared.analytical.function_property_runtime import build_function_property_artifacts, function_property_query

TASK_ID = "task_geometry__function_panels__sign_interval_label"
SCENE_ID = "function_panels"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = tuple(SIGN_INTERVAL_VARIANTS)


@register_task
class GeometryFunctionPanelsSignIntervalLabelTask:
    """Choose the panel whose graph stays above or below the x-axis on an interval."""

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
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
        )
        query = function_property_query(
            instance_seed=int(instance_seed),
            params=task_params,
            query_id=str(query_id),
            query_id_probabilities=query_probabilities,
        )
        artifacts = build_function_property_artifacts(
            instance_seed=int(instance_seed),
            params=task_params,
            query=query,
        )
        return TaskOutput(
            prompt=str(artifacts.prompt_artifacts.prompt),
            answer_gt=TypedValue(type="option_letter", value=str(query.winner_label)),
            annotation_gt=TypedValue(type="bbox_set", value=artifacts.annotation_value),
            image=artifacts.rendered_scene.image,
            image_id="img_0",
            trace_payload=artifacts.trace_payload,
            task_versions=artifacts.task_versions,
            query_id=str(query.query_id),
            prompt_variants=dict(artifacts.prompt_artifacts.prompt_variants),
        )
