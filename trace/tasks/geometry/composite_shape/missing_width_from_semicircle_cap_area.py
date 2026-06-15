"""Missing width from rectangle plus semicircle area objective."""

from __future__ import annotations

from trace.tasks.registry import register_task

from ._lifecycle import run_composite_shape_public_entry
from .shared.construction import resolve_answer_balanced_semicircle_dimensions
from .shared.measurements import SEMICIRCLE_DIMENSION_CANDIDATES, round1, semicircle_arc_length, semicircle_area
from .shared.sampling import group_cases_by_answer
from .shared.state import CompositeShapeProblem

TASK_ID = "task_geometry__composite_shape__missing_width_from_semicircle_cap_area"
QUERY_ID = "missing_width_from_semicircle_cap_area"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


def _answer_for_case(case: tuple[int, int, int]) -> float:
    width_units, _height_units, _radius_units = case
    return float(width_units)


_CASES_BY_ANSWER = group_cases_by_answer(
    SEMICIRCLE_DIMENSION_CANDIDATES,
    answer_fn=_answer_for_case,
)

def _resolve_problem(*, selected_query: str, instance_seed, params):
    """Bind missing rectangle width from total area of a cap composite."""

    width_units, height_units, radius_units, answer_probabilities = (
        resolve_answer_balanced_semicircle_dimensions(
            instance_seed=int(instance_seed),
            params=params,
            namespace=f"{TASK_ID}.{QUERY_ID}.values",
            answer_cases=_CASES_BY_ANSWER,
            answer_fn=_answer_for_case,
        )
    )
    semi_area = semicircle_area(radius_units)
    total_area = round1(float(width_units * height_units) + float(semi_area))
    dimensions = {"width_units": width_units, "height_units": height_units, "radius_units": radius_units, "total_area": total_area, "semicircle_area": round1(semi_area), "arc_length": round1(semicircle_arc_length(radius_units)), "answer_value": float(width_units)}
    return CompositeShapeProblem(prompt_key=QUERY_ID, shape_family="semi_cap", metric_kind="missing_width", answer_value=float(width_units), answer_type="number", reasoning_kind="missing_width", scene_kind="geometry_curvilinear_composite_shape", witness_type="curvilinear_composite_formula", dimensions=dimensions, formula_family="width_from_area_plus_semicircle", reasoning_steps=3, prompt_slots={"total_area": total_area}, metadata_fields={"target_answer_support_probabilities": dict(answer_probabilities)})


@register_task
class GeometryMissingWidthFromSemicircleCapAreaTask:
    """Infer a missing rectangle width from a semicircle-cap area."""

    task_id = TASK_ID
    domain = "geometry"
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Select the sole missing-width branch and bind its formula inputs."""

        return run_composite_shape_public_entry(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            resolve_problem=_resolve_problem,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )
