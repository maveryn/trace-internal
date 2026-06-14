"""Tabbed rectilinear perimeter objective."""

from __future__ import annotations

from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import complete_composite_shape_task
from .shared.sampling import select_case_value
from .shared.state import CompositeShapeProblem

TASK_ID = "task_geometry__composite_shape__tabbed_rectilinear_perimeter"
QUERY_ID = "tabbed_rectilinear_perimeter"
SUPPORTED_QUERY_IDS = (QUERY_ID,)

_CASES = ((10, 6, 2), (12, 7, 3), (14, 8, 4), (16, 9, 5), (18, 10, 6), (20, 11, 7))


def _resolve_problem(*, instance_seed, params):
    """Bind a rectilinear tab perimeter from total width, height, and tab height."""

    width, height, tab_height = select_case_value(
        _CASES,
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{QUERY_ID}.case",
    )
    answer = (2 * int(width)) + (2 * int(height)) + (2 * int(tab_height))
    return CompositeShapeProblem(
        prompt_key=QUERY_ID,
        shape_family="tabbed",
        metric_kind="perimeter",
        answer_value=int(answer),
        answer_type="integer",
        reasoning_kind="composite_perimeter",
        scene_kind="geometry_rectilinear_composite_shape",
        witness_type="rectilinear_composite_perimeter_formula",
        dimensions={"width": width, "height": height, "tab_height": tab_height},
        formula_family="tabbed_rectilinear_outline",
        reasoning_steps=2,
        execution_fields={"perimeter_formula": "2*width + 2*height + 2*tab_height"},
    )


@register_task
class GeometryCompositeShapeTabbedRectilinearPerimeterTask:
    """Compute the perimeter of a tabbed rectilinear composite shape."""

    task_id = TASK_ID
    domain = "geometry"
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Bind a tabbed-outline case and construct the perimeter output."""

        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
        )
        problem = _resolve_problem(instance_seed=int(instance_seed), params=task_params)
        return complete_composite_shape_task(
            task_id=TASK_ID,
            branch_name=str(selected_query),
            branch_probabilities=query_probabilities,
            problem=problem,
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
            render_namespace=f"{TASK_ID}.{selected_query}",
        )
