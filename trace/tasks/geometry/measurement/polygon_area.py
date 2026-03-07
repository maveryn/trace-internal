"""Single-object geometry polygon-area measurement task."""

from __future__ import annotations

from ...registry import register_task
from .polygon_measure_base import GeometryPolygonMeasureBase


@register_task
class GeometryPolygonAreaMeasureTask(GeometryPolygonMeasureBase):
    """Measure polygon area on graph paper."""

    task_id = "task_geometry_measurement_polygon_area"
    scene_kind = "geometry_polygon_area_measurement"
    query_template_id = "geometry_polygon_area_measure_v1"
    answer_component_key = "area_square_units"

    def _answer_value_from_instance(self, instance) -> int:
        """Return area answer value."""
        return int(instance.area_square_units)

    def _complexity_score(self, *, sides: int, answer_value: int) -> float:
        """Compute area-task complexity from side count and area magnitude."""
        side_component = min(1.0, (float(sides) - 3.0) / 3.0)
        area_component = min(1.0, float(answer_value) / 56.0)
        return max(0.0, min(1.0, 0.34 + (0.36 * side_component) + (0.30 * area_component)))
