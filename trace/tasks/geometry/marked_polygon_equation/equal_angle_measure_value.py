"""Compute an angle measure from marked equal-angle equations."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import run_marked_equation_task
from .shared.construction import Builder, isosceles_angle_from_expression, marked_equal_angle_from_expression
from .shared.sampling import select_case_variant, select_construction_family

TASK_ID = "task_geometry__marked_polygon_equation__equal_angle_measure_value"
SUPPORTED_QUERY_IDS: tuple[str, ...] = ("single",)
CONSTRUCTION_OPTIONS: tuple[tuple[str, Builder], ...] = (
    ("marked_equal_angle_from_expression", marked_equal_angle_from_expression),
    ("isosceles_triangle_angle_from_expression", isosceles_angle_from_expression),
)


def _build_case(instance_seed: int, params: Mapping[str, Any]):
    """Select the equal-angle measure construction and bind one algebraic case."""

    family_name, builder, family_probabilities, task_params = select_construction_family(
        options=CONSTRUCTION_OPTIONS,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.construction_family",
    )
    variant_index = select_case_variant(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{family_name}.case",
    )
    return builder(int(variant_index)), int(variant_index), dict(family_probabilities), task_params


@register_task
class GeometryMarkedPolygonEquationEqualAngleMeasureValueTask:
    """Task-owned equal-angle measure objective for marked polygon equations."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_marked_equation_task(
            task_id=TASK_ID,
            supported_queries=SUPPORTED_QUERY_IDS,
            build_case=_build_case,
            reasoning_steps=2,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


__all__ = ["GeometryMarkedPolygonEquationEqualAngleMeasureValueTask"]
