"""Public objective for the composite-shape rectilinear scene."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.core.scene_config import get_scene_defaults

from ...base import TaskOutput
from ...registry import register_task
from ..shared.composite_measurement_cases import (
    _COMPOSITE_AREA_CASES,
    _COMPOSITE_PERIMETER_CASES,
    _cases_for_query,
)
from ..shared.composite_measurement_task import _CompositeMeasurementBaseTask


SCENE_ID = "composite_shape"
TASK_ID = "task_geometry__composite_shape__tabbed_rectilinear_perimeter"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ('tabbed_rectilinear_perimeter',)


@register_task
class GeometryCompositeShapeTabbedRectilinearPerimeterTask(_CompositeMeasurementBaseTask):
    """Compute the perimeter of a tabbed rectilinear composite shape."""

    task_id = TASK_ID
    domain = "geometry"
    public_scene_id = SCENE_ID
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    scene_kind = "geometry_rectilinear_composite_shape"
    reasoning_kind = "composite_perimeter"
    cases = _cases_for_query(_COMPOSITE_PERIMETER_CASES, "tabbed_rectilinear_perimeter")
    defaults_map = get_scene_defaults("geometry", SCENE_ID)
    defaults_are_scene_aligned = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        if self.task_id != TASK_ID:
            raise ValueError(f"unexpected task id: {self.task_id}")
        task_params = dict(params)
        output = super().generate(
            int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
        )
        return output


__all__ = ["GeometryCompositeShapeTabbedRectilinearPerimeterTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
