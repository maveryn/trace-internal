"""Find the perimeter of a regular polygon."""

from __future__ import annotations

from trace.core.types import TypedValue
from trace.tasks.registry import register_task

from ._lifecycle import RegularPolygonObjectivePlan, run_regular_polygon_public_entry
from .shared.defaults import DOMAIN
from .shared.sampling import perimeter_from_area_apothem, perimeter_from_side

TASK_ID = "task_geometry__regular_polygon_decomposition__perimeter_value"
QUERY_ID_SIDE = "perimeter_from_side_length"
QUERY_ID_AREA_APOTHEM = "perimeter_from_total_area_and_apothem"
SUPPORTED_QUERY_IDS = (QUERY_ID_SIDE, QUERY_ID_AREA_APOTHEM)
DEFAULT_QUERY_ID = QUERY_ID_SIDE
PROMPT_TASK_KEY = "perimeter_value_query"


def _prepare_perimeter(instance_seed, task_params, selected_branch, branch_probabilities):
    if selected_branch == QUERY_ID_SIDE:
        problem = perimeter_from_side(int(instance_seed), task_params, seed_namespace=f"{TASK_ID}.{selected_branch}")
        annotation_roles = ("O", "A", "B")
    elif selected_branch == QUERY_ID_AREA_APOTHEM:
        problem = perimeter_from_area_apothem(int(instance_seed), task_params, seed_namespace=f"{TASK_ID}.{selected_branch}")
        annotation_roles = ("O", "A", "B", "M")
    else:
        raise ValueError(f"unsupported query branch for {TASK_ID}: {selected_branch}")
    return RegularPolygonObjectivePlan(
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_branch_key=str(selected_branch),
        problem=problem,
        answer_gt=TypedValue(type="integer", value=int(round(float(problem.answer)))),
        annotation_roles=tuple(annotation_roles),
        query_params={
            "query_id_probabilities": dict(branch_probabilities),
            "case_index": int(problem.case_index),
            "n_sides": int(problem.n_sides),
            "wedge_count": int(problem.wedge_count),
        },
        trace_values={"answer_family": "perimeter", "target_role": "perimeter"},
    )


@register_task
class GeometryRegularPolygonDecompositionPerimeterTask:
    """Find the perimeter of a regular polygon."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    prepare_objective = staticmethod(_prepare_perimeter)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_regular_polygon_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))
