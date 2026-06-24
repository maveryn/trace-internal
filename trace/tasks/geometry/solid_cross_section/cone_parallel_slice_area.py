from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import SolidCrossSectionObjectivePlan, run_solid_cross_section_public_entry
from .shared.annotations import CONE_ANNOTATION_KEYS
from .shared.defaults import DOMAIN, SCENE_ID
from .shared.measurements import cone_problem_from_case
from .shared.rendering import render_cone_cross_section
from .shared.sampling import cone_answer_support_size, resolve_cone_slice_case

TASK_ID = "task_geometry__solid_cross_section__cone_parallel_slice_area"
QUERY_ID = "single"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (QUERY_ID,)
DEFAULT_QUERY_ID = QUERY_ID
PROMPT_KEY = QUERY_ID


def _prepare_cone_objective(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    selected_query: str,
    query_probabilities: Mapping[str, float],
) -> SolidCrossSectionObjectivePlan:
    """Bind the cone slice-area objective for one generated instance."""

    case, support_probabilities, construction_case_count = resolve_cone_slice_case(
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{TASK_ID}.{selected_query}",
    )
    problem = cone_problem_from_case(
        case,
        formula_family="cone_parallel_slice_area",
        formula="parallel cone slice: r_slice/R = d/H, area = pi * r_slice^2",
        answer_support_probabilities=support_probabilities,
        construction_case_count_for_answer=int(construction_case_count),
    )
    trace_values = {
        "solid_kind": "cone",
        "base_radius": float(problem.base_radius or 0.0),
        "solid_height": float(problem.solid_height),
        "slice_distance_from_apex": float(problem.slice_distance_from_apex),
        "similarity_scale": float(problem.slice_distance_from_apex) / float(problem.solid_height),
        "slice_radius": float(problem.slice_radius or 0.0),
        "answer_support_size": int(cone_answer_support_size()),
        "construction_case_count_for_answer": int(construction_case_count),
    }
    return SolidCrossSectionObjectivePlan(
        prompt_key=PROMPT_KEY,
        problem=problem,
        render_scene=render_cone_cross_section,
        annotation_keys=CONE_ANNOTATION_KEYS,
        answer_value=float(problem.answer),
        query_params={
            "query_id_probabilities": dict(query_probabilities),
            "answer_support_probabilities": dict(support_probabilities),
            **dict(trace_values),
        },
        trace_values=trace_values,
    )


@register_task
class GeometryConeParallelSliceAreaTask:
    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    prepare_objective = staticmethod(_prepare_cone_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        """Generate one cone parallel-slice area task."""

        return run_solid_cross_section_public_entry(
            self,
            int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )
