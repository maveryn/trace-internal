"""Public objective for the composite-shape curvilinear scene."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.output_metadata import default_task_versions

from .shared.curvilinear_runtime import (
    SCENE_ID,
    CurvilinearCompositeComponents,
    generate_curvilinear_components,
)


TASK_ID = "task_geometry__composite_shape__rectangle_quarter_sector_cutout_area"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("rectangle_quarter_sector_cutout_area",)
REASONING_KIND = "area"
_SCENE_DEFAULTS = get_scene_defaults("geometry", SCENE_ID)


def _stamp_task_identity(payload: Dict[str, Any]) -> Dict[str, Any]:
    stamped = dict(payload)
    for key in ("scene_ir", "query_spec", "render_spec", "execution_trace", "witness_symbolic"):
        section = stamped.get(key)
        if isinstance(section, dict):
            section["task_id"] = TASK_ID
    return stamped




@register_task
class GeometryRectangleQuarterSectorCutoutAreaTask:
    """Compute the area of a rectangle with a quarter-sector cutout."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        task_params = dict(params)
        components = generate_curvilinear_components(
            config_key=TASK_ID,
            generation_namespace=TASK_ID,
            supported_queries=SUPPORTED_QUERY_IDS,
            reasoning_kind=REASONING_KIND,
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
        )
        trace_payload = _stamp_task_identity(dict(components.trace_payload))
        answer_gt = TypedValue(type="number", value=float(components.answer_value))
        annotation_gt = TypedValue(
            type=str(components.annotation_type),
            value=components.annotation_value,
        )
        return TaskOutput(
            prompt=str(components.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=components.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(components.query_id),
            prompt_variants=dict(components.prompt_variants),
        )


__all__ = ["GeometryRectangleQuarterSectorCutoutAreaTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
