"""Rectangle minus semicircle area objective."""

from __future__ import annotations

from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import complete_composite_shape_task
from .shared.construction import resolve_semicircle_dimensions
from .shared.measurements import WIDTH_SUPPORT, one_hot_support, round1, semicircle_arc_length, semicircle_area
from .shared.state import CompositeShapeProblem

TASK_ID = "task_geometry__composite_shape__rectangle_semicircle_cutout_area"
QUERY_ID = "rectangle_semicircle_cutout_area"
SUPPORTED_QUERY_IDS = (QUERY_ID,)

def _resolve_problem(*, instance_seed, params):
    """Bind rectangle-minus-semicircle shaded area from visible dimensions."""

    width_units, height_units, radius_units = resolve_semicircle_dimensions(instance_seed=int(instance_seed), params=params, namespace=f"{TASK_ID}.{QUERY_ID}.values")
    semi_area = semicircle_area(radius_units)
    answer = round1(float(width_units * height_units) - float(semi_area))
    dimensions = {"width_units": width_units, "height_units": height_units, "radius_units": radius_units, "semicircle_area": round1(semi_area), "arc_length": round1(semicircle_arc_length(radius_units)), "answer_value": answer}
    return CompositeShapeProblem(
        prompt_key=QUERY_ID,
        shape_family="semi_cut",
        metric_kind="area",
        answer_value=float(answer),
        answer_type="number",
        reasoning_kind="area",
        scene_kind="geometry_curvilinear_composite_shape",
        witness_type="curvilinear_composite_formula",
        dimensions=dimensions,
        formula_family="rectangle_minus_semicircle",
        reasoning_steps=2,
        metadata_fields={"target_support_probabilities": one_hot_support(WIDTH_SUPPORT, width_units)},
        execution_fields={"area_formula": "width*height - 0.5*pi*r^2", "answer_rounding": "nearest_tenth"},
    )


@register_task
class GeometryRectangleSemicircleCutoutAreaTask:
    """Compute the area of a rectangle with a semicircle cutout."""

    task_id = TASK_ID
    domain = "geometry"
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Select the sole area branch and bind its formula inputs."""

        selected_query, query_probabilities, task_params = select_task_query_id(instance_seed=int(instance_seed), params=params, supported_query_ids=SUPPORTED_QUERY_IDS, default_query_id=QUERY_ID, task_id=TASK_ID)
        problem = _resolve_problem(instance_seed=int(instance_seed), params=task_params)
        return complete_composite_shape_task(task_id=TASK_ID, branch_name=str(selected_query), branch_probabilities=query_probabilities, problem=problem, instance_seed=int(instance_seed), params=task_params, max_attempts=int(max_attempts), render_namespace=f"{TASK_ID}.{selected_query}")
