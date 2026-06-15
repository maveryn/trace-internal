"""Tabbed rectilinear perimeter objective."""

from __future__ import annotations

from trace.tasks.registry import register_task

from ._lifecycle import run_composite_shape_public_entry
from .shared.sampling import group_cases_by_answer, select_answer_balanced_case
from .shared.state import CompositeShapeProblem

TASK_ID = "task_geometry__composite_shape__tabbed_rectilinear_perimeter"
QUERY_ID = "tabbed_rectilinear_perimeter"
SUPPORTED_QUERY_IDS = (QUERY_ID,)

_CASES = tuple(
    (width, height, tab_height)
    for width in range(9, 26)
    for height in range(6, 17)
    for tab_height in range(2, 10)
)


def _answer(case: tuple[int, int, int]) -> int:
    width, height, tab_height = case
    return (2 * int(width)) + (2 * int(height)) + (2 * int(tab_height))


_CASES_BY_ANSWER = group_cases_by_answer(_CASES, answer_fn=_answer)


def _resolve_problem(*, selected_query: str, instance_seed, params):
    """Bind a rectilinear tab perimeter from total width, height, and tab height."""

    (
        width,
        height,
        tab_height,
    ), answer_probabilities = select_answer_balanced_case(
        _CASES_BY_ANSWER,
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{QUERY_ID}.case",
    )
    answer = _answer((width, height, tab_height))
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
        metadata_fields={
            "target_answer_support_probabilities": dict(answer_probabilities),
        },
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

        return run_composite_shape_public_entry(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            resolve_problem=_resolve_problem,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )
