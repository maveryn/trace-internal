"""Infer each circle radius from a two-circle rectangle gap area."""

from __future__ import annotations

import math

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task

from ._lifecycle import TangentPackingObjectivePlan, run_tangent_packing_public_entry
from .shared.measurements import case_trace_values, fmt_measure, rectangle_equal_circles_gap
from .shared.rendering import render_two_circles_rectangle_scene
from .shared.sampling import choose_radius
from .shared.state import DOMAIN, TangentPackingProblem

TASK_ID = "task_geometry__tangent_packing__two_circles_in_rectangle_radius_from_gap_area"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
TASK_PROMPT_KEY = "two_circles_in_rectangle_radius_from_gap_area_query"


def _prepare_two_circle_radius_from_gap_area(
    *,
    instance_seed,
    params,
    selected_query,
    branch_probabilities,
) -> TangentPackingObjectivePlan:
    """Bind a two-circle rectangle gap area to each circle radius."""

    case, radius_probabilities = choose_radius(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.radius",
    )
    answer = float(case.radius)
    shaded_area = rectangle_equal_circles_gap(case.radius)
    rectangle_area = float(case.packed_rectangle_width * case.packed_rectangle_height)
    total_circle_area = float(2.0 * math.pi * case.radius * case.radius)
    gap_coefficient = float(8.0 - 2.0 * math.pi)
    radius_from_gap_area = math.sqrt(float(shaded_area) / gap_coefficient)
    two_circle_problem = TangentPackingProblem(
        construction_kind="two_circles_in_rectangle",
        target_kind="radius",
        support_kind="shaded_area",
        target_text="r=?",
        support_text=f"shaded area={fmt_measure(shaded_area)}",
        answer=answer,
        case=case,
        formula_family="two_circles_in_rectangle_radius_from_gap_area",
        formula_text="radius = sqrt(shaded area / (8 - 2*pi))",
        reasoning_steps=1,
    )
    trace_values = {
        **case_trace_values(case),
        "formula_family": "two_circles_in_rectangle_radius_from_gap_area",
        "construction_kind": "two_circles_in_rectangle",
        "target_kind": "radius",
        "support_kind": "shaded_area",
        "visible_shaded_area": float(shaded_area),
        "rectangle_area": rectangle_area,
        "total_circle_area": total_circle_area,
        "gap_coefficient": gap_coefficient,
        "radius_from_gap_area": radius_from_gap_area,
    }
    return TangentPackingObjectivePlan(
        prompt_key=TASK_PROMPT_KEY,
        problem=two_circle_problem,
        render_scene=render_two_circles_rectangle_scene,
        answer_value=float(answer),
        query_params=trace_values,
        trace_values=trace_values,
    )


@register_task
class GeometryTwoCirclesInRectangleRadiusFromGapAreaTask:
    """Infer each circle radius from a two-circle rectangle gap area."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SINGLE_QUERY_ID
    prepare_objective = staticmethod(_prepare_two_circle_radius_from_gap_area)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_tangent_packing_public_entry(self, instance_seed, params=params, max_attempts=max_attempts)


__all__ = ["GeometryTwoCirclesInRectangleRadiusFromGapAreaTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
