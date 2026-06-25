"""Infer a triangle side after deriving a shared rectangle height."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task

from ._lifecycle import TriangleRelationsObjectivePlan, bind_triangle_relations_plan, run_triangle_relations_public_entry
from .shared.construction import case_trace_values, rectangle_triangle_shared_height_cases
from .shared.sampling import choose_case_by_answer
from .shared.state import DOMAIN, SCENE_ID

TASK_ID = "task_geometry__triangle_relations__pythagorean_length_value_rectangle_triangle_shared_height_length"
TASK_PROMPT_KEY = "pythagorean_length_value_rectangle_triangle_shared_height_length_query"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
_CASE_POOL = rectangle_triangle_shared_height_cases()


def _prepare_shared_height(*, instance_seed: int, params: Mapping[str, Any], selected_branch: str, branch_probabilities: Mapping[str, float]) -> TriangleRelationsObjectivePlan:
    """Bind one rectangle-triangle shared-height case."""

    if str(selected_branch) != SINGLE_QUERY_ID:
        raise ValueError(f"unsupported query branch for {TASK_ID}: {selected_branch}")
    case, answer_probs = choose_case_by_answer(cases=_CASE_POOL, answer_fn=lambda item: item.answer, params=params, instance_seed=int(instance_seed), namespace=TASK_ID)
    return bind_triangle_relations_plan(prompt_key=TASK_PROMPT_KEY, case=case, answer_support_probabilities=answer_probs, branch_probabilities=branch_probabilities, trace_values=case_trace_values(case))


@register_task
class GeometryPythagoreanLengthRectangleTriangleSharedHeightTask:
    """Infer a triangle side after deriving a shared rectangle height."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SINGLE_QUERY_ID
    prepare_objective = staticmethod(_prepare_shared_height)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_triangle_relations_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometryPythagoreanLengthRectangleTriangleSharedHeightTask", "SCENE_ID", "SUPPORTED_QUERY_IDS", "TASK_ID"]
