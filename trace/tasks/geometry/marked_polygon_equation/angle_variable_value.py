"""Solve a variable from equal-angle polygon markings."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import run_marked_equation_task
from .shared.construction import (
    Builder,
    equilateral_median_right_angle_variable,
    isosceles_base_angle_variable,
    marked_equal_angles_variable,
)
from .shared.sampling import select_case_variant, select_construction_family

TASK_ID = "task_geometry__marked_polygon_equation__angle_variable_value"
SUPPORTED_QUERY_IDS: tuple[str, ...] = ("single",)
CONSTRUCTION_OPTIONS: tuple[tuple[str, Builder], ...] = (
    ("marked_equal_angles_variable", marked_equal_angles_variable),
    ("isosceles_triangle_base_angle_variable", isosceles_base_angle_variable),
    ("equilateral_median_right_angle_variable", equilateral_median_right_angle_variable),
)


def _build_case(instance_seed: int, params: Mapping[str, Any]):
    """Select the equal-angle construction family and bind one algebraic case."""

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
class GeometryMarkedPolygonEquationAngleVariableValueTask:
    """Task-owned equal-angle variable objective for marked polygon equations."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_marked_equation_task(
            task_id=TASK_ID,
            supported_queries=SUPPORTED_QUERY_IDS,
            build_case=_build_case,
            reasoning_steps=1,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


__all__ = ["GeometryMarkedPolygonEquationAngleVariableValueTask"]
