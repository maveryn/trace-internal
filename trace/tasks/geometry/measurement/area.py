"""Single-object geometry area measurement task."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from ...registry import register_task
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.conic_geometry import CircleInstance, EllipseInstance
from ..shared.graph_paper import resolve_graph_cell_capacity
from ..shared.polygon_geometry import (
    PolygonInstance,
    feasible_triangle_area_values,
    sample_triangle_instance_with_area_on_graph_paper,
    triangle_integer_edge_specs_for_area,
)
from .defaults import MEASUREMENT_SHARED_DEFAULTS
from .shape_measure_base import GeometryShapeMeasureBase


@register_task
class GeometryAreaMeasure2DTask(GeometryShapeMeasureBase):
    """Measure 2D area for one polygon/ellipse on graph paper."""

    task_id = "task_geometry_measurement_area"
    scene_kind = "geometry_2d_area_measurement"
    query_template_id = "geometry_2d_area_measure_v1"
    answer_component_key = "area_square_units"
    supported_shape_variants = ("triangle", "quadrilateral", "ellipse")

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

    def _resolve_polygon_target_answer(
        self,
        *,
        instance_seed: int,
        params: Mapping[str, Any],
        variant_kind: str,
        answer_min: int | None,
        answer_max: int | None,
        gen_defaults: Mapping[str, Any],
        render_defaults: Mapping[str, Any],
    ) -> Tuple[int | None, Dict[str, float], List[int], int]:
        """Select triangle-area targets from exact feasible support before layout."""

        if str(variant_kind) != "triangle":
            return super()._resolve_polygon_target_answer(
                instance_seed=int(instance_seed),
                params=params,
                variant_kind=str(variant_kind),
                answer_min=answer_min,
                answer_max=answer_max,
                gen_defaults=gen_defaults,
                render_defaults=render_defaults,
            )
        _explicit_graph_cells, graph_cells_max = resolve_graph_cell_capacity(
            params=params,
            render_defaults=render_defaults,
            fallback_min=int(MEASUREMENT_SHARED_DEFAULTS.graph_cells_min),
            fallback_max=int(MEASUREMENT_SHARED_DEFAULTS.graph_cells_max),
        )
        max_span_units = max(3, int(graph_cells_max) - 2)
        feasible_answers = list(
            feasible_triangle_area_values(
                max_span_units=int(max_span_units),
                area_min=(None if answer_min is None else int(answer_min)),
                area_max=(None if answer_max is None else int(answer_max)),
            )
        )
        if not feasible_answers:
            raise ValueError("no feasible triangle area values for requested answer bounds and graph-cell limits")
        probabilities = {str(value): (1.0 / float(len(feasible_answers))) for value in feasible_answers}
        sampling_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.{variant_kind}.target_answer",
        )
        selected_answer = int(feasible_answers[int(sampling_index) % len(feasible_answers)])
        triangle_specs = triangle_integer_edge_specs_for_area(
            area_square_units=int(selected_answer),
            max_span_units=int(max_span_units),
        )
        required_graph_cells = min(
            max(int(base_units), int(apex_x_units), int(height_units))
            for base_units, apex_x_units, height_units in triangle_specs
        ) + 2
        return int(selected_answer), probabilities, [int(value) for value in feasible_answers], int(required_graph_cells)

    def _sample_polygon_instance(
        self,
        rng,
        *,
        variant_kind: str,
        target_answer_scalar: int | None,
        context,
        gen_defaults: Mapping[str, Any],
    ) -> PolygonInstance:
        """Use constructive triangle-area sampling when the task targets triangle area."""

        if str(variant_kind) == "triangle" and target_answer_scalar is not None:
            return sample_triangle_instance_with_area_on_graph_paper(
                rng,
                area_square_units=int(target_answer_scalar),
                canvas_size=int(context.canvas_size),
                graph_spacing=int(context.graph_spacing),
                graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
                padding_units=0,
                max_attempts=12,
            )
        return super()._sample_polygon_instance(
            rng,
            variant_kind=str(variant_kind),
            target_answer_scalar=target_answer_scalar,
            context=context,
            gen_defaults=gen_defaults,
        )

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
