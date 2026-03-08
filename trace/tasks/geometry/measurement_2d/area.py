"""Single-object geometry area measurement task."""

from __future__ import annotations

from typing import Any, Mapping

from ...registry import register_task
from ..shared.conic_geometry import CircleInstance, EllipseInstance
from ..shared.polygon_geometry import PolygonInstance
from .shape_measure_base import GeometryShapeMeasureBase


@register_task
class GeometryAreaMeasure2DTask(GeometryShapeMeasureBase):
    """Measure 2D area for one polygon/ellipse on graph paper."""

    task_id = "task_geometry_measurement_2d_area"
    scene_kind = "geometry_2d_area_measurement"
    query_template_id = "geometry_2d_area_measure_v1"
    answer_component_key = "area_square_units"
    supported_shape_variants = ("triangle", "quadrilateral", "pentagon", "ellipse")

    def _answer_scalar_from_polygon_instance(self, instance: PolygonInstance) -> int:
        """Return polygon area answer value."""
        return int(instance.area_square_units)

    def _answer_scalar_from_ellipse_instance(self, instance: EllipseInstance) -> int:
        """Return ellipse area `k` coefficient for `kπ`."""
        return int(instance.area_pi_coefficient)

    def _answer_scalar_from_circle_instance(self, instance: CircleInstance) -> int:
        """Return circle area `k` coefficient for `kπ` when reused."""
        return int(instance.area_pi_coefficient)

    def _pi_variants(self) -> set[str]:
        """Return shape variants that emit π-expression answers."""
        return {"ellipse"}

    def _circle_answer_coefficient_scale(self) -> int:
        """Return circle area coefficient scale for `kπ` answers."""
        return 1

    def _resolve_required_graph_cells(
        self,
        *,
        variant_kind: str,
        answer_min: int | None,
        answer_max: int | None,
        gen_defaults: Mapping[str, Any],
    ) -> int:
        """Apply area-task-specific minimum graph-cell rules."""
        required = int(
            super()._resolve_required_graph_cells(
                variant_kind=str(variant_kind),
                answer_min=answer_min,
                answer_max=answer_max,
                gen_defaults=gen_defaults,
            )
        )
        if str(variant_kind) != "triangle" or answer_min is None:
            return int(required)
        minimum = int(answer_min)
        if minimum <= 6:
            return int(required)
        if minimum <= 12:
            return max(int(required), 8)
        if minimum <= 24:
            return max(int(required), 10)
        raise ValueError("no feasible triangle area values for requested answer_min")

    def _complexity_score(
        self,
        *,
        variant_kind: str,
        answer_scalar: int,
        polygon_sides: int | None,
    ) -> float:
        """Compute area-task complexity from shape variant + answer magnitude."""
        variant = str(variant_kind)
        if polygon_sides is None:
            side_component = 1.0 if variant == "ellipse" else 0.0
        else:
            side_component = min(1.0, (float(int(polygon_sides)) - 3.0) / 2.0)
        area_component = min(1.0, float(answer_scalar) / 32.0)
        return max(0.0, min(1.0, 0.34 + (0.36 * side_component) + (0.30 * area_component)))
