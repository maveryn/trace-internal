"""Legacy analytical measurement geometry value tasks.

Remaining public tasks in this module still use legacy measurement scene-package
routing while their scenes are migrated to scene packages. Shared rendering,
case construction, and generation logic live in geometry shared modules.
"""

from __future__ import annotations

from typing import Any, Dict

from ...base import TaskOutput
from ...registry import register_task
from trace.core.scene_config import get_scene_defaults
from ..shared.composite_measurement_cases import (
    _ANGLE_BISECTOR_SEGMENT_CASES,
    _CENTROID_MEDIAN_SEGMENT_CASES,
    _COMPOSITE_AREA_CASES,
    _COMPOSITE_PERIMETER_CASES,
    _PARALLEL_SECTION_SCALE_CASES,
    _PYTHAGOREAN_CASES,
    _SIMILARITY_CASES,
    _cases_for_query,
)

SCENE_ID = "triangle_relations"
SUPPORTED_QUERY_IDS = ('angle_bisector_base_length', )
from ..shared.composite_measurement_task import _CompositeMeasurementBaseTask












@register_task
class GeometryAngleBisectorBaseLengthTask(_CompositeMeasurementBaseTask):
    """Infer the whole base length from an angle-bisector split."""

    task_id = "task_geometry__triangle_relations__angle_bisector_segment_value_angle_bisector_base_length"
    public_scene_id = "triangle_relations"
    scene_id = public_scene_id
    defaults_map = get_scene_defaults("geometry", SCENE_ID)
    defaults_are_scene_aligned = True
    prompts_are_scene_aligned = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    scene_kind = "geometry_triangle_special_segment"
    reasoning_kind = "angle_bisector_segment"
    cases = _cases_for_query(_ANGLE_BISECTOR_SEGMENT_CASES, "angle_bisector_base_length")

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        generation_seed = int(instance_seed)
        task_params = dict(params)
        attempt_budget = int(max_attempts)
        output = super().generate(generation_seed, params=task_params, max_attempts=attempt_budget)
        return output













