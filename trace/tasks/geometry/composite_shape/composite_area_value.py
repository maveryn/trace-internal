"""Composite-shape area objective."""

from __future__ import annotations

from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import complete_composite_shape_task
from .shared.sampling import select_case_value
from .shared.state import CompositeShapeProblem

TASK_ID = "task_geometry__composite_shape__composite_area_value"
QUERY_RECTANGLE_CUT = "rectangle_minus_triangle_area"
QUERY_L_PROFILE = "l_shape_area"
SUPPORTED_QUERY_IDS = (QUERY_RECTANGLE_CUT, QUERY_L_PROFILE)

_RECT_CUT_CASES = ((12, 8, 6, 4), (14, 9, 8, 5), (13, 10, 4, 5), (16, 10, 6, 8), (15, 12, 10, 6))
_L_PROFILE_CASES = ((13, 9, 4, 3), (12, 10, 4, 3), (15, 10, 6, 4), (14, 11, 5, 4), (16, 12, 6, 5))


def _resolve_problem(selected_query: str, *, instance_seed, params):
    """Bind the selected area formula and its shape-specific dimensions."""

    if selected_query == QUERY_RECTANGLE_CUT:
        width, height, cut_base, cut_height = select_case_value(
            _RECT_CUT_CASES,
            instance_seed=int(instance_seed),
            params=params,
            namespace=f"{TASK_ID}.{QUERY_RECTANGLE_CUT}.case",
        )
        answer = (int(width) * int(height)) - ((int(cut_base) * int(cut_height)) // 2)
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
            metadata_fields={"area_case_family": "rect_cut"},
        )
    if selected_query != QUERY_L_PROFILE:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_query}")
    width, height, cut_width, cut_height = select_case_value(
        _L_PROFILE_CASES,
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{QUERY_L_PROFILE}.case",
    )
    answer = (int(width) * int(height)) - (int(cut_width) * int(cut_height))
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
        metadata_fields={"area_case_family": "l_profile"},
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

        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_RECTANGLE_CUT,
            task_id=TASK_ID,
        )
        problem = _resolve_problem(selected_query, instance_seed=int(instance_seed), params=task_params)
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
