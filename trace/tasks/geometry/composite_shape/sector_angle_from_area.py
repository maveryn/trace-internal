"""Sector angle from area objective."""

from __future__ import annotations

from trace.tasks.registry import register_task

from ._lifecycle import run_composite_shape_public_entry
from .shared.construction import resolve_answer_balanced_sector_dimensions
from .shared.measurements import SECTOR_DIMENSION_CANDIDATES, round1, sector_arc_length, sector_area
from .shared.sampling import group_cases_by_answer
from .shared.state import CompositeShapeProblem

TASK_ID = "task_geometry__composite_shape__sector_angle_from_area"
QUERY_ID = "sector_angle_from_area"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


def _answer_for_case(case: tuple[int, int]) -> float:
    theta_degrees, radius_units = case
    sector_area_value = round1(sector_area(theta_degrees, radius_units))
    return round1(
        (360.0 * float(sector_area_value))
        / (3.141592653589793 * float(radius_units) ** 2)
    )


_CASES_BY_ANSWER = group_cases_by_answer(
    SECTOR_DIMENSION_CANDIDATES,
    answer_fn=_answer_for_case,
)

def _resolve_problem(*, selected_query: str, instance_seed, params):
    """Bind a missing central angle from radius and visible sector area."""

    theta_degrees, radius_units, answer_probabilities = (
        resolve_answer_balanced_sector_dimensions(
            instance_seed=int(instance_seed),
            params=params,
            namespace=f"{TASK_ID}.{QUERY_ID}.values",
            answer_cases=_CASES_BY_ANSWER,
            answer_fn=_answer_for_case,
        )
    )
    arc_length = round1(sector_arc_length(theta_degrees, radius_units))
    sector_area_value = round1(sector_area(theta_degrees, radius_units))
    answer = _answer_for_case((theta_degrees, radius_units))
    dimensions = {"theta_degrees": theta_degrees, "radius_units": radius_units, "arc_length": float(arc_length), "sector_area": float(sector_area_value), "answer_value": answer}
    return CompositeShapeProblem(prompt_key=QUERY_ID, shape_family="sector", metric_kind="sector_from_area", answer_value=float(answer), answer_type="number", reasoning_kind="sector_angle", scene_kind="geometry_curvilinear_composite_shape", witness_type="curvilinear_composite_formula", dimensions=dimensions, formula_family="sector_angle_from_area", reasoning_steps=2, prompt_slots={"sector_area": sector_area_value}, metadata_fields={"target_answer_support_probabilities": dict(answer_probabilities)})


@register_task
class GeometrySectorAngleFromAreaTask:
    """Compute a sector angle from the sector area."""

    task_id = TASK_ID
    domain = "geometry"
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Select the sole sector branch and bind its area formula."""

        return run_composite_shape_public_entry(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            resolve_problem=_resolve_problem,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )
