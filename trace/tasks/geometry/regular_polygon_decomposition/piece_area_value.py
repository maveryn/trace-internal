"""Find regular-polygon wedge or wedge-group area."""

from __future__ import annotations

from trace.core.types import TypedValue
from trace.tasks.registry import register_task

from ._lifecycle import RegularPolygonObjectivePlan, run_regular_polygon_public_entry
from .shared.defaults import DOMAIN
from .shared.sampling import area_from_adjacent_equal_pieces, area_from_one_equal_piece, area_from_side_and_apothem

TASK_ID = "task_geometry__regular_polygon_decomposition__piece_area_value"
QUERY_ID_SINGLE_WEDGE = "single_wedge_area_from_total"
QUERY_ID_SHADED_WEDGES = "shaded_wedges_area_from_total"
QUERY_ID_SIDE_APOTHEM = "wedge_area_from_side_and_apothem"
SUPPORTED_QUERY_IDS = (QUERY_ID_SINGLE_WEDGE, QUERY_ID_SHADED_WEDGES, QUERY_ID_SIDE_APOTHEM)
DEFAULT_QUERY_ID = QUERY_ID_SINGLE_WEDGE
PROMPT_TASK_KEY = "piece_area_value_query"
ANNOTATION_ROLES = ("O", "A", "B", "W")


def _prepare_piece_area(instance_seed, task_params, selected_branch, branch_probabilities):
    if selected_branch == QUERY_ID_SINGLE_WEDGE:
        problem = area_from_one_equal_piece(int(instance_seed), task_params, seed_namespace=f"{TASK_ID}.{selected_branch}")
    elif selected_branch == QUERY_ID_SHADED_WEDGES:
        problem = area_from_adjacent_equal_pieces(int(instance_seed), task_params, seed_namespace=f"{TASK_ID}.{selected_branch}")
    elif selected_branch == QUERY_ID_SIDE_APOTHEM:
        problem = area_from_side_and_apothem(int(instance_seed), task_params, seed_namespace=f"{TASK_ID}.{selected_branch}")
    else:
        raise ValueError(f"unsupported query branch for {TASK_ID}: {selected_branch}")
    answer_value = round(float(problem.answer), 1)
    return RegularPolygonObjectivePlan(
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_branch_key=str(selected_branch),
        problem=problem,
        answer_gt=TypedValue(type="number", value=float(answer_value)),
        annotation_roles=ANNOTATION_ROLES,
        query_params={
            "query_id_probabilities": dict(branch_probabilities),
            "case_index": int(problem.case_index),
            "n_sides": int(problem.n_sides),
            "wedge_count": int(problem.wedge_count),
        },
        trace_values={"answer_family": "area", "target_role": "wedge_area"},
    )


@register_task
class GeometryRegularPolygonDecompositionPieceAreaTask:
    """Find regular-polygon wedge or wedge-group area."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    prepare_objective = staticmethod(_prepare_piece_area)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_regular_polygon_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))
