"""Solve leg or projection lengths from the right-triangle altitude theorem."""

from __future__ import annotations

from typing import Dict

from trace.core.types import TypedValue
from trace.tasks.registry import register_task

from ._lifecycle import RightTriangleAltitudeObjectivePlan, run_right_triangle_altitude_public_entry
from .shared.defaults import DOMAIN
from .shared.sampling import sample_leg_from_hypotenuse_projection, sample_projection_from_leg_and_hypotenuse


TASK_ID = "task_geometry__right_triangle_altitude_theorem__leg_projection_length_value"
SUPPORTED_QUERY_IDS = (
    "leg_from_hypotenuse_projection",
    "projection_from_leg_and_hypotenuse",
)
DEFAULT_QUERY_ID = "leg_from_hypotenuse_projection"
PROMPT_TASK_KEY = "leg_projection_length_value_query"
ANNOTATION_ROLES = ("A", "B", "C", "D")


def _prepare_leg_projection_objective(
    instance_seed: int,
    selected_branch: str,
    branch_probabilities: Dict[str, float],
) -> RightTriangleAltitudeObjectivePlan:
    if selected_branch == "leg_from_hypotenuse_projection":
        problem = sample_leg_from_hypotenuse_projection(
            int(instance_seed),
            seed_namespace=f"{TASK_ID}.{selected_branch}",
        )
    elif selected_branch == "projection_from_leg_and_hypotenuse":
        problem = sample_projection_from_leg_and_hypotenuse(
            int(instance_seed),
            seed_namespace=f"{TASK_ID}.{selected_branch}",
        )
    else:
        raise ValueError(f"unsupported query branch for {TASK_ID}: {selected_branch}")
    return RightTriangleAltitudeObjectivePlan(
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_branch_key=str(selected_branch),
        problem=problem,
        answer_gt=TypedValue(type="integer", value=int(problem.answer)),
        annotation_roles=ANNOTATION_ROLES,
        query_params={
            "query_id_probabilities": dict(branch_probabilities),
            "case_index": int(problem.case_index),
            "target_role": str(problem.target_role),
        },
        trace_values={"answer_family": "length", "program_scope": "leg_projection_length_value"},
    )


@register_task
class GeometryRightTriangleAltitudeTheoremLegProjectionValueTask:
    """Solve leg or projection lengths from the right-triangle altitude theorem."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    prepare_objective = staticmethod(_prepare_leg_projection_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_right_triangle_altitude_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometryRightTriangleAltitudeTheoremLegProjectionValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
