"""Single-object geometry perimeter measurement task."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from ...registry import register_task
from ...shared.config_defaults import group_default
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.conic_geometry import CircleInstance, EllipseInstance
from ..shared.graph_paper import resolve_graph_cell_capacity
from ..shared.polygon_geometry import (
    PolygonInstance,
    feasible_triangle_perimeter_values,
    sample_triangle_instance_with_perimeter_on_graph_paper,
    triangle_integer_edge_specs_for_perimeter,
)
from .defaults import MEASUREMENT_SHARED_DEFAULTS
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

    def _circle_answer_coefficient_scale(self) -> int:
        """Return circle circumference coefficient scale for `kπ` answers."""
        return 2

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
        """Select triangle-perimeter targets from exact feasible support before layout."""

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
            feasible_triangle_perimeter_values(
                max_span_units=int(max_span_units),
                perimeter_min=(None if answer_min is None else int(answer_min)),
                perimeter_max=(None if answer_max is None else int(answer_max)),
            )
        )
        if not feasible_answers:
            raise ValueError("no feasible triangle perimeter values for requested answer bounds and graph-cell limits")
        probabilities = {str(value): (1.0 / float(len(feasible_answers))) for value in feasible_answers}
        sampling_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.{variant_kind}.target_answer",
        )
        selected_answer = int(feasible_answers[int(sampling_index) % len(feasible_answers)])
        triangle_specs = triangle_integer_edge_specs_for_perimeter(
            perimeter_units=int(selected_answer),
            max_span_units=int(max_span_units),
        )
        required_graph_cells = min(
            max(int(base_units), int(apex_x_units), int(height_units))
            for base_units, apex_x_units, height_units in triangle_specs
        ) + 2
        return int(selected_answer), probabilities, [int(value) for value in feasible_answers], int(required_graph_cells)

    def _resolve_circle_target_answer(
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
        """Select one circumference coefficient before scene layout."""

        if str(variant_kind) != "circle":
            return super()._resolve_circle_target_answer(
                instance_seed=int(instance_seed),
                params=params,
                variant_kind=str(variant_kind),
                answer_min=answer_min,
                answer_max=answer_max,
                gen_defaults=gen_defaults,
                render_defaults=render_defaults,
            )
        radius_min = int(group_default(gen_defaults, "circle_radius_min", MEASUREMENT_SHARED_DEFAULTS.circle_radius_min))
        radius_max = int(group_default(gen_defaults, "circle_radius_max", MEASUREMENT_SHARED_DEFAULTS.circle_radius_max))
        _explicit_graph_cells, graph_cells_max = resolve_graph_cell_capacity(
            params=params,
            render_defaults=render_defaults,
            fallback_min=int(MEASUREMENT_SHARED_DEFAULTS.graph_cells_min),
            fallback_max=int(MEASUREMENT_SHARED_DEFAULTS.graph_cells_max),
        )
        feasible_coefficients: List[int] = []
        for radius_units in range(int(radius_min), int(radius_max) + 1):
            coefficient = int(2 * int(radius_units))
            if answer_min is not None and int(coefficient) < int(answer_min):
                continue
            if answer_max is not None and int(coefficient) > int(answer_max):
                continue
            if int((2 * int(radius_units)) + 2) > int(graph_cells_max):
                continue
            feasible_coefficients.append(int(coefficient))
        if not feasible_coefficients:
            raise ValueError("no feasible circle circumference coefficients for requested bounds and graph-cell limits")
        probabilities = {str(value): (1.0 / float(len(feasible_coefficients))) for value in feasible_coefficients}
        sampling_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.{variant_kind}.target_answer",
        )
        selected_answer = int(feasible_coefficients[int(sampling_index) % len(feasible_coefficients)])
        required_graph_cells = int(selected_answer) + 2
        return int(selected_answer), probabilities, [int(value) for value in feasible_coefficients], int(required_graph_cells)

    def _sample_polygon_instance(
        self,
        rng,
        *,
        variant_kind: str,
        target_answer_scalar: int | None,
        context,
        gen_defaults: Mapping[str, Any],
    ) -> PolygonInstance:
        """Use constructive triangle-perimeter sampling when the task targets triangle perimeter."""

        if str(variant_kind) == "triangle" and target_answer_scalar is not None:
            return sample_triangle_instance_with_perimeter_on_graph_paper(
                rng,
                perimeter_units=int(target_answer_scalar),
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
