"""Rectangle minus quarter-sector perimeter objective."""

from __future__ import annotations

from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import complete_composite_shape_task
from .shared.construction import resolve_quarter_cut_dimensions
from .shared.measurements import RADIUS_SUPPORT, one_hot_support, quarter_sector_values, round1
from .shared.state import CompositeShapeProblem

TASK_ID = "task_geometry__composite_shape__rectangle_quarter_sector_cutout_perimeter"
QUERY_ID = "rectangle_quarter_sector_cutout_perimeter"
SUPPORTED_QUERY_IDS = (QUERY_ID,)

def _resolve_problem(*, instance_seed, params):
    """Bind highlighted boundary length for a quarter-sector cutout figure."""

    width_units, height_units, radius_units = resolve_quarter_cut_dimensions(instance_seed=int(instance_seed), params=params, namespace=f"{TASK_ID}.{QUERY_ID}.values")
    sector_area, arc_length = quarter_sector_values(radius_units)
    straight_boundary = (2.0 * float(width_units)) + (2.0 * float(height_units)) - (2.0 * float(radius_units))
    answer = round1(float(straight_boundary) + float(arc_length))
    dimensions = {"width_units": width_units, "height_units": height_units, "radius_units": radius_units, "theta_degrees": 90, "sector_area": round1(sector_area), "arc_length": round1(arc_length), "straight_boundary_length": round1(straight_boundary), "answer_value": answer}
    return CompositeShapeProblem(prompt_key=QUERY_ID, shape_family="quarter_cut", metric_kind="perimeter", answer_value=float(answer), answer_type="number", reasoning_kind="perimeter", scene_kind="geometry_curvilinear_composite_shape", witness_type="curvilinear_composite_formula", dimensions=dimensions, formula_family="rectangle_quarter_sector_boundary", reasoning_steps=3, metadata_fields={"target_support_probabilities": one_hot_support(RADIUS_SUPPORT, radius_units)})


@register_task
class GeometryRectangleQuarterSectorCutoutPerimeterTask:
    """Compute the perimeter of a rectangle with a quarter-sector cutout."""

    task_id = TASK_ID
    domain = "geometry"
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Select the sole perimeter branch and bind its formula inputs."""

        selected_query, query_probabilities, task_params = select_task_query_id(instance_seed=int(instance_seed), params=params, supported_query_ids=SUPPORTED_QUERY_IDS, default_query_id=QUERY_ID, task_id=TASK_ID)
        problem = _resolve_problem(instance_seed=int(instance_seed), params=task_params)
        return complete_composite_shape_task(task_id=TASK_ID, branch_name=str(selected_query), branch_probabilities=query_probabilities, problem=problem, instance_seed=int(instance_seed), params=task_params, max_attempts=int(max_attempts), render_namespace=f"{TASK_ID}.{selected_query}")
