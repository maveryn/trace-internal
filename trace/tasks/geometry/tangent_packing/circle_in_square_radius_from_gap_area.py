"""Infer the circle radius from the shaded square-container gap area."""

from __future__ import annotations

import math

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task

from ._lifecycle import TangentPackingObjectivePlan, run_tangent_packing_public_entry
from .shared.measurements import case_trace_values, fmt_measure, square_container_circle_gap
from .shared.rendering import render_circle_in_square_scene
from .shared.sampling import choose_radius
from .shared.state import DOMAIN, TangentPackingProblem

TASK_ID = "task_geometry__tangent_packing__circle_in_square_radius_from_gap_area"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
TASK_PROMPT_KEY = "circle_in_square_radius_from_gap_area_query"


def _prepare_circle_in_square_radius(
    *,
    instance_seed,
    params,
    selected_query,
    branch_probabilities,
) -> TangentPackingObjectivePlan:
    """Bind square gap area to circle radius via shaded_area = (4 - pi) r^2."""

    case, radius_probabilities = choose_radius(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.radius",
    )
    answer = float(case.radius)
    shaded_area = square_container_circle_gap(case.radius)
    square_area = float(case.square_side * case.square_side)
    circle_area = float(math.pi * case.radius * case.radius)
    gap_coefficient = float(4.0 - math.pi)
    derived_radius_check = math.sqrt(float(shaded_area) / gap_coefficient)
    problem_fields = {
        "construction_kind": "circle_in_square",
        "target_kind": "radius",
        "support_kind": "shaded_area",
        "target_text": "r=?",
        "support_text": f"shaded area={fmt_measure(shaded_area)}",
        "answer": answer,
        "case": case,
        "formula_family": "circle_in_square_radius_from_gap_area",
        "formula_text": "radius = sqrt(shaded area / (4 - pi))",
        "reasoning_steps": 1,
    }
    square_case_values = case_trace_values(case)
    trace_values = {
        "formula_family": "circle_in_square_radius_from_gap_area",
        "construction_kind": "circle_in_square",
        "target_kind": "radius",
        "support_kind": "shaded_area",
        "visible_shaded_area": float(shaded_area),
        "square_area": square_area,
        "circle_area": circle_area,
        "gap_coefficient": gap_coefficient,
        "derived_radius_check": derived_radius_check,
        **square_case_values,
    }
    return TangentPackingObjectivePlan(
        prompt_key=TASK_PROMPT_KEY,
        problem=TangentPackingProblem(**problem_fields),
        render_scene=render_circle_in_square_scene,
        answer_value=float(answer),
        query_params=trace_values,
        trace_values=trace_values,
    )


@register_task
class GeometryCircleInSquareRadiusFromGapAreaTask:
    """Infer the circle radius from the shaded square-container gap area."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SINGLE_QUERY_ID
    prepare_objective = staticmethod(_prepare_circle_in_square_radius)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_tangent_packing_public_entry(self, instance_seed, params=params, max_attempts=max_attempts)


__all__ = ["GeometryCircleInSquareRadiusFromGapAreaTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
