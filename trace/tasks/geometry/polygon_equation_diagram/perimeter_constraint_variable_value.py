"""Solve a variable from side expressions and a visible total perimeter."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import run_polygon_equation_task
from .shared.sampling import sample_perimeter_constraint_relation
from .shared.state import PolygonEquationCase

TASK_ID = "task_geometry__polygon_equation_diagram__perimeter_constraint_variable_value"
SUPPORTED_QUERY_IDS: tuple[str, ...] = ("single",)


def _build_case(*, instance_seed: int, params: Mapping[str, Any], generation_defaults: Mapping[str, Any]):
    relation = sample_perimeter_constraint_relation(
        instance_seed=int(instance_seed),
        params=params,
        namespace="polygon_equation.perimeter_constraint.variable_value",
    )
    return PolygonEquationCase(
        side_count=int(relation["side_count"]),
        answer=int(relation["variable_value"]),
        target_name=str(relation["variable_name"]),
        variable_name=str(relation["variable_name"]),
        formula_schema="perimeter_constraint_variable_value",
        relation="visible_perimeter_constraint_side_expression_sum",
        output_role="variable_value",
        side_labels=dict(relation["side_labels"]),
        side_mark_counts=dict(relation["side_mark_counts"]),
        center_label=str(relation["center_label"]),
        witness=dict(relation["witness"]),
    )


@register_task
class GeometryPolygonEquationDiagramPerimeterConstraintVariableValueTask:
    """Task-owned variable objective from a perimeter constraint."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_polygon_equation_task(
            task_id=TASK_ID,
            build_case=_build_case,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


__all__ = ["GeometryPolygonEquationDiagramPerimeterConstraintVariableValueTask", "TASK_ID", "SUPPORTED_QUERY_IDS"]
