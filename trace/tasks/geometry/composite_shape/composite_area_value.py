"""Composite-shape area objective."""

from __future__ import annotations

from trace.tasks.registry import register_task

from ._lifecycle import run_composite_shape_public_entry
from .shared.sampling import group_cases_by_answer, select_answer_balanced_case
from .shared.state import CompositeShapeProblem

TASK_ID = "task_geometry__composite_shape__composite_area_value"
QUERY_RECTANGLE_CUT = "rectangle_minus_triangle_area"
QUERY_L_PROFILE = "l_shape_area"
SUPPORTED_QUERY_IDS = (QUERY_RECTANGLE_CUT, QUERY_L_PROFILE)

_RECT_CUT_CASES = tuple(
    (width, height, cut_base, cut_height)
    for width in range(10, 33)
    for height in range(8, 25)
    for cut_base in range(3, width - 2)
    for cut_height in range(3, height - 2)
    if (cut_base * cut_height) % 2 == 0
)
_L_PROFILE_CASES = tuple(
    (width, height, cut_width, cut_height)
    for width in range(10, 35)
    for height in range(8, 27)
    for cut_width in range(3, width - 2)
    for cut_height in range(3, height - 2)
)


def _rect_cut_answer(case: tuple[int, int, int, int]) -> int:
    width, height, cut_base, cut_height = case
    return (int(width) * int(height)) - ((int(cut_base) * int(cut_height)) // 2)


def _l_profile_answer(case: tuple[int, int, int, int]) -> int:
    width, height, cut_width, cut_height = case
    return (int(width) * int(height)) - (int(cut_width) * int(cut_height))


_RECT_CUT_CASES_BY_ANSWER = group_cases_by_answer(
    _RECT_CUT_CASES,
    answer_fn=_rect_cut_answer,
)
_L_PROFILE_CASES_BY_ANSWER = group_cases_by_answer(
    _L_PROFILE_CASES,
    answer_fn=_l_profile_answer,
)


def _resolve_problem(selected_query: str, *, instance_seed, params):
    """Bind the selected area formula and its shape-specific dimensions."""

    if selected_query == QUERY_RECTANGLE_CUT:
        (
            width,
            height,
            cut_base,
            cut_height,
        ), answer_probabilities = select_answer_balanced_case(
            _RECT_CUT_CASES_BY_ANSWER,
            instance_seed=int(instance_seed),
            params=params,
            namespace=f"{TASK_ID}.{QUERY_RECTANGLE_CUT}.case",
        )
        answer = _rect_cut_answer((width, height, cut_base, cut_height))
        return CompositeShapeProblem(
            prompt_key=QUERY_RECTANGLE_CUT,
            shape_family="rect_cut",
            metric_kind="area",
            answer_value=int(answer),
            answer_type="integer",
            reasoning_kind="composite_area",
            scene_kind="geometry_rectilinear_composite_shape",
            witness_type="rectilinear_composite_area_formula",
            dimensions={"width": width, "height": height, "cut_base": cut_base, "cut_height": cut_height},
            formula_family="outer_rectangle_minus_triangle",
            reasoning_steps=3,
            metadata_fields={
                "area_case_family": "rect_cut",
                "target_answer_support_probabilities": dict(answer_probabilities),
            },
        )
    if selected_query != QUERY_L_PROFILE:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_query}")
    (
        width,
        height,
        cut_width,
        cut_height,
    ), answer_probabilities = select_answer_balanced_case(
        _L_PROFILE_CASES_BY_ANSWER,
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{QUERY_L_PROFILE}.case",
    )
    answer = _l_profile_answer((width, height, cut_width, cut_height))
    return CompositeShapeProblem(
        prompt_key=QUERY_L_PROFILE,
        shape_family="l_profile",
        metric_kind="area",
        answer_value=int(answer),
        answer_type="integer",
        reasoning_kind="composite_area",
        scene_kind="geometry_rectilinear_composite_shape",
        witness_type="rectilinear_composite_area_formula",
        dimensions={"width": width, "height": height, "cut_width": cut_width, "cut_height": cut_height},
        formula_family="outer_rectangle_minus_corner_rectangle",
        reasoning_steps=3,
        metadata_fields={
            "area_case_family": "l_profile",
            "target_answer_support_probabilities": dict(answer_probabilities),
        },
        execution_fields={"area_formula": "width*height - cut_width*cut_height"},
    )


@register_task
class GeometryMeasurementCompositeAreaValueTask:
    """Compute a composite shaded area by subtraction/decomposition."""

    task_id = TASK_ID
    domain = "geometry"
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Select an area program and bind its answer before rendering."""

        return run_composite_shape_public_entry(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_RECTANGLE_CUT,
            resolve_problem=_resolve_problem,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )
