"""Choose the missing endpoint from a visible endpoint and midpoint."""

from __future__ import annotations

from typing import Any, Dict

from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.output_metadata import default_task_versions

from .shared.coordinate.algebra_runtime import (
    MISSING_ENDPOINT_QUERY_IDS,
    build_algebra_artifacts,
)

TASK_ID = "task_geometry__coordinate_plane__missing_endpoint_label"
SCENE_ID = "coordinate_plane"
SUPPORTED_QUERY_IDS = MISSING_ENDPOINT_QUERY_IDS
SCENE_KEY = "coordinate_algebra_midpoint_scene"


@register_task
class GeometryCoordinateMissingEndpointLabelTask:
    """Choose the candidate endpoint that makes the shown point the midpoint."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        artifacts = build_algebra_artifacts(
            namespace=TASK_ID,
            config_key=TASK_ID,
            query_ids=SUPPORTED_QUERY_IDS,
            scene_key=SCENE_KEY,
            instance_seed=int(instance_seed),
            params=params,
        )
        trace_payload = dict(artifacts.trace_payload)
        trace_payload["witness_symbolic"] = {
            **dict(trace_payload.get("witness_symbolic", {})),
            "task_id": TASK_ID,
        }
        return TaskOutput(
            prompt=str(artifacts.prompt_artifacts.prompt),
            answer_gt=TypedValue(type="option_letter", value=str(artifacts.query.winner_label)),
            annotation_gt=TypedValue(type="point_set", value=artifacts.annotation_value),
            image=artifacts.rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(artifacts.query.query_id),
            prompt_variants=dict(artifacts.prompt_artifacts.prompt_variants),
        )
