"""Single-object geometry perimeter measurement task."""

from __future__ import annotations

from ...registry import register_task
from ..shared.conic_geometry import CircleInstance, EllipseInstance
from ..shared.polygon_geometry import PolygonInstance
from .shape_measure_base import GeometryShapeMeasureBase


@register_task
class GeometryPerimeterMeasure2DTask(GeometryShapeMeasureBase):
    """Measure 2D perimeter/circumference for one polygon/circle on graph paper."""

    task_id = "task_geometry_measurement_perimeter"
    scene_kind = "geometry_2d_perimeter_measurement"
    query_template_id = "geometry_2d_perimeter_measure_v1"
    answer_component_key = "perimeter_units"
    supported_shape_variants = ("triangle", "quadrilateral", "circle")

    def _answer_scalar_from_polygon_instance(self, instance: PolygonInstance) -> int:
        """Return polygon perimeter answer value."""
        return int(instance.perimeter_units)

    def _answer_scalar_from_ellipse_instance(self, instance: EllipseInstance) -> int:
        """Raise because ellipse perimeter is intentionally out of scope."""
        raise ValueError(
            "ellipse perimeter answers are intentionally excluded; "
            "use circle variant for π-based perimeter measurement"
        )

    def _answer_scalar_from_circle_instance(self, instance: CircleInstance) -> int:
        """Return circle circumference `k` coefficient for `kπ`."""
        return int(instance.circumference_pi_coefficient)

    def _pi_variants(self) -> set[str]:
        """Return shape variants that emit π-expression answers."""
        return {"circle"}

    def _complexity_score(
        self,
        *,
        variant_kind: str,
        answer_scalar: int,
        polygon_sides: int | None,
    ) -> float:
        """Compute perimeter-task complexity from shape variant + answer magnitude."""
        variant = str(variant_kind)
        if polygon_sides is None:
            side_component = 1.0 if variant == "circle" else 0.0
        else:
            side_component = min(1.0, (float(int(polygon_sides)) - 3.0) / 2.0)
        perimeter_component = min(1.0, float(answer_scalar) / 24.0)
        return max(0.0, min(1.0, 0.36 + (0.34 * side_component) + (0.30 * perimeter_component)))
