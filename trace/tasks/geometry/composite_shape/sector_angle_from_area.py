"""Sector angle from area objective."""

from __future__ import annotations

from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import complete_composite_shape_task
from .shared.construction import resolve_sector_dimensions
from .shared.measurements import THETA_SUPPORT, one_hot_support, round1, sector_arc_length, sector_area
from .shared.state import CompositeShapeProblem

TASK_ID = "task_geometry__composite_shape__sector_angle_from_area"
QUERY_ID = "sector_angle_from_area"
SUPPORTED_QUERY_IDS = (QUERY_ID,)

def _resolve_problem(*, instance_seed, params):
    """Bind a missing central angle from radius and visible sector area."""

    theta_degrees, radius_units = resolve_sector_dimensions(instance_seed=int(instance_seed), params=params, namespace=f"{TASK_ID}.{QUERY_ID}.values")
    arc_length = round1(sector_arc_length(theta_degrees, radius_units))
    sector_area_value = round1(sector_area(theta_degrees, radius_units))
    answer = round1((360.0 * float(sector_area_value)) / (3.141592653589793 * float(radius_units) ** 2))
    dimensions = {"theta_degrees": theta_degrees, "radius_units": radius_units, "arc_length": float(arc_length), "sector_area": float(sector_area_value), "answer_value": answer}
    return CompositeShapeProblem(prompt_key=QUERY_ID, shape_family="sector", metric_kind="sector_from_area", answer_value=float(answer), answer_type="number", reasoning_kind="sector_angle", scene_kind="geometry_curvilinear_composite_shape", witness_type="curvilinear_composite_formula", dimensions=dimensions, formula_family="sector_angle_from_area", reasoning_steps=2, prompt_slots={"sector_area": sector_area_value}, metadata_fields={"target_support_probabilities": one_hot_support(THETA_SUPPORT, theta_degrees)})


@register_task
class GeometrySectorAngleFromAreaTask:
    """Compute a sector angle from the sector area."""

    task_id = TASK_ID
    domain = "geometry"
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Select the sole sector branch and bind its area formula."""

        selected_query, query_probabilities, task_params = select_task_query_id(instance_seed=int(instance_seed), params=params, supported_query_ids=SUPPORTED_QUERY_IDS, default_query_id=QUERY_ID, task_id=TASK_ID)
        problem = _resolve_problem(instance_seed=int(instance_seed), params=task_params)
        return complete_composite_shape_task(task_id=TASK_ID, branch_name=str(selected_query), branch_probabilities=query_probabilities, problem=problem, instance_seed=int(instance_seed), params=task_params, max_attempts=int(max_attempts), render_namespace=f"{TASK_ID}.{selected_query}")
