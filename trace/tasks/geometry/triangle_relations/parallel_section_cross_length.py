"""Infer an inner section length from a line parallel to a triangle base."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task

from ._lifecycle import run_triangle_relations_public_entry
from .shared.annotations import triangle_relations_annotation_mode
from .shared.construction import case_trace_values, parallel_section_cross_cases
from .shared.sampling import choose_case_by_answer
from .shared.rendering import render_triangle_relations_scene
from .shared.state import DOMAIN, SCENE_ID, TriangleRelationsProblem

TASK_ID = "task_geometry__triangle_relations__parallel_section_cross_length"
TASK_PROMPT_KEY = "parallel_section_cross_length_query"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
_CASE_POOL = parallel_section_cross_cases()


def _prepare_parallel_cross(*, instance_seed: int, params: Mapping[str, Any], selected_branch: str, branch_probabilities: Mapping[str, float]) -> tuple[TriangleRelationsProblem, int | float, dict[str, Any]]:
    """Bind one parallel-section cross-length case."""

    if str(selected_branch) != SINGLE_QUERY_ID:
        raise ValueError(f"unsupported query branch for {TASK_ID}: {selected_branch}")
    case, answer_probs = choose_case_by_answer(cases=_CASE_POOL, answer_fn=lambda item: item.answer, params=params, instance_seed=int(instance_seed), namespace=TASK_ID)
    trace_values = {
        "target_support_probabilities": dict(answer_probs),
        **case_trace_values(case),
    }
    problem = TriangleRelationsProblem(
        case=case,
        answer_support_probabilities=dict(answer_probs),
        prompt_target=str(case.trace_values.get("target_name", "target value")),
        annotation_mode=triangle_relations_annotation_mode(case),
    )
    return problem, case.answer, trace_values


@register_task
class GeometryTriangleRelationsParallelSectionCrossLengthTask:
    """Infer an inner section length from triangle scaling."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SINGLE_QUERY_ID
    task_prompt_key = TASK_PROMPT_KEY
    render_scene = staticmethod(render_triangle_relations_scene)
    prepare_objective = staticmethod(_prepare_parallel_cross)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_triangle_relations_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometryTriangleRelationsParallelSectionCrossLengthTask", "SCENE_ID", "SUPPORTED_QUERY_IDS", "TASK_ID"]
