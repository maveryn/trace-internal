"""Rectangle plus semicircle perimeter objective."""

from __future__ import annotations

from trace.tasks.registry import register_task

from ._lifecycle import run_composite_shape_public_entry
from .shared.construction import resolve_semicircle_side_remainder_perimeter_case
from .shared.measurements import (
    SEMICIRCLE_DIMENSION_CANDIDATES,
    semicircle_side_remainder_perimeter,
)
from .shared.sampling import group_cases_by_answer
from .shared.state import CompositeShapeProblem

TASK_ID = "task_geometry__composite_shape__rectangle_semicircle_cap_perimeter"
QUERY_ID = "rectangle_semicircle_cap_perimeter"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


def _answer_for_case(case: tuple[int, int, int]) -> float:
    width_units, height_units, radius_units = case
    return semicircle_side_remainder_perimeter(
        width_units,
        height_units,
        radius_units,
    )


_CASES_BY_ANSWER = group_cases_by_answer(
    SEMICIRCLE_DIMENSION_CANDIDATES,
    answer_fn=_answer_for_case,
)

def _resolve_problem(*, selected_query: str, instance_seed, params):
    """Bind highlighted perimeter for a rectangle with a semicircle cap."""

    resolved = resolve_semicircle_side_remainder_perimeter_case(
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{QUERY_ID}.values",
        answer_cases=_CASES_BY_ANSWER,
        answer_fn=_answer_for_case,
    )
    return CompositeShapeProblem(
        prompt_key=QUERY_ID,
        shape_family="semi_cap",
        metric_kind="perimeter",
        answer_value=float(resolved.answer),
        answer_type="number",
        reasoning_kind="perimeter",
        scene_kind="geometry_curvilinear_composite_shape",
        witness_type="curvilinear_composite_formula",
        dimensions=resolved.dimensions,
        formula_family="rectangle_semicircle_cap_boundary_with_side_remainders",
        reasoning_steps=2,
        metadata_fields={
            "target_answer_support_probabilities": dict(resolved.answer_probabilities),
        },
        execution_fields=resolved.execution_fields,
    )


@register_task
class GeometryRectangleSemicircleCapPerimeterTask:
    """Compute the perimeter of a rectangle with a semicircle cap."""

    task_id = TASK_ID
    domain = "geometry"
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Select the sole perimeter branch and bind its formula inputs."""

        return run_composite_shape_public_entry(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            resolve_problem=_resolve_problem,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )
