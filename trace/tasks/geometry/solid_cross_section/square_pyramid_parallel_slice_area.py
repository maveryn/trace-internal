from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import SolidCrossSectionObjectivePlan, run_solid_cross_section_public_entry
from .shared.annotations import PYRAMID_ANNOTATION_KEYS
from .shared.defaults import DOMAIN, SCENE_ID
from .shared.measurements import pyramid_problem_from_case
from .shared.rendering import render_square_pyramid_cross_section
from .shared.sampling import pyramid_answer_support_size, resolve_pyramid_slice_case

TASK_ID = "task_geometry__solid_cross_section__square_pyramid_parallel_slice_area"
QUERY_ID = "single"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (QUERY_ID,)
DEFAULT_QUERY_ID = QUERY_ID
PROMPT_KEY = QUERY_ID


def _prepare_pyramid_objective(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    selected_query: str,
    query_probabilities: Mapping[str, float],
) -> SolidCrossSectionObjectivePlan:
    """Bind the square-pyramid slice-area objective for one generated instance."""

    case, support_probabilities, construction_case_count = resolve_pyramid_slice_case(
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{selected_query}",
    )
    problem = pyramid_problem_from_case(
        case,
        formula_family="square_pyramid_parallel_slice_area",
        formula="parallel square-pyramid slice: s_slice/s = d/H, area = s_slice^2",
        answer_support_probabilities=support_probabilities,
        construction_case_count_for_answer=int(construction_case_count),
    )
    trace_values = {
        "solid_kind": "square_pyramid",
        "base_side": float(problem.base_side or 0.0),
        "solid_height": float(problem.solid_height),
        "slice_distance_from_apex": float(problem.slice_distance_from_apex),
        "similarity_scale": float(problem.slice_distance_from_apex) / float(problem.solid_height),
        "slice_side": float(problem.slice_side or 0.0),
        "answer_support_size": int(pyramid_answer_support_size()),
        "construction_case_count_for_answer": int(construction_case_count),
    }
    return SolidCrossSectionObjectivePlan(
        prompt_key=PROMPT_KEY,
        problem=problem,
        render_scene=render_square_pyramid_cross_section,
        annotation_keys=PYRAMID_ANNOTATION_KEYS,
        answer_value=float(problem.answer),
        query_params={
            "query_id_probabilities": dict(query_probabilities),
            "answer_support_probabilities": dict(support_probabilities),
            **dict(trace_values),
        },
        trace_values=trace_values,
    )


@register_task
class GeometrySquarePyramidParallelSliceAreaTask:
    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    prepare_objective = staticmethod(_prepare_pyramid_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        """Generate one square-pyramid parallel-slice area task."""

        return run_solid_cross_section_public_entry(
            self,
            int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )
