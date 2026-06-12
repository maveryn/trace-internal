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
TASK_ID = "task_geometry__composite_shape__composite_area_value"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ('rectangle_minus_triangle_area', 'l_shape_area')


@register_task
class GeometryMeasurementCompositeAreaValueTask(_CompositeMeasurementBaseTask):
    """Compute a composite shaded area by subtraction/decomposition."""

    task_id = TASK_ID
    domain = "geometry"
    public_scene_id = SCENE_ID
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    scene_kind = "geometry_rectilinear_composite_shape"
    reasoning_kind = "composite_area"
    cases = _COMPOSITE_AREA_CASES
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


__all__ = ["GeometryMeasurementCompositeAreaValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
