"""Single-object geometry polygon-perimeter measurement task."""

from __future__ import annotations

from ...registry import register_task
from .polygon_measure_base import GeometryPolygonMeasureBase


@register_task
class GeometryPolygonPerimeterMeasureTask(GeometryPolygonMeasureBase):
    """Measure polygon perimeter on graph paper."""

    task_id = "task_geometry_measurement_polygon_perimeter"
    scene_kind = "geometry_polygon_perimeter_measurement"
    query_template_id = "geometry_polygon_perimeter_measure_v1"
    answer_component_key = "perimeter_units"

    def _answer_value_from_instance(self, instance) -> int:
        """Return perimeter answer value."""
        return int(instance.perimeter_units)

    def _complexity_score(self, *, sides: int, answer_value: int) -> float:
        """Compute perimeter-task complexity from side count and perimeter size."""
        side_component = min(1.0, (float(sides) - 3.0) / 3.0)
        perimeter_component = min(1.0, float(answer_value) / 28.0)
        return max(0.0, min(1.0, 0.36 + (0.34 * side_component) + (0.30 * perimeter_component)))
