"""Solve altitude or projection lengths from the altitude-to-hypotenuse theorem."""

from __future__ import annotations

from typing import Dict

from trace.core.types import TypedValue
from trace.tasks.registry import register_task

from ._lifecycle import RightTriangleAltitudeObjectivePlan, run_right_triangle_altitude_public_entry
from .shared.defaults import DOMAIN
from .shared.sampling import sample_altitude_from_split_hypotenuse, sample_projection_from_altitude


TASK_ID = "task_geometry__right_triangle_altitude_theorem__altitude_to_hypotenuse_value"
SUPPORTED_QUERY_IDS = (
    "altitude_from_split_hypotenuse",
    "missing_projection_from_altitude",
)
DEFAULT_QUERY_ID = "altitude_from_split_hypotenuse"
PROMPT_TASK_KEY = "altitude_to_hypotenuse_value_query"
ANNOTATION_ROLES = ("A", "B", "C", "D")


def _prepare_altitude_objective(
    instance_seed: int,
    selected_branch: str,
    branch_probabilities: Dict[str, float],
) -> RightTriangleAltitudeObjectivePlan:
    if selected_branch == "altitude_from_split_hypotenuse":
        problem = sample_altitude_from_split_hypotenuse(
            int(instance_seed),
            seed_namespace=f"{TASK_ID}.{selected_branch}",
        )
    elif selected_branch == "missing_projection_from_altitude":
        problem = sample_projection_from_altitude(
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
        trace_values={"answer_family": "length", "program_scope": "altitude_to_hypotenuse_value"},
    )


@register_task
class GeometryRightTriangleAltitudeTheoremAltitudeValueTask:
    """Solve altitude or projection lengths from the altitude-to-hypotenuse theorem."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    prepare_objective = staticmethod(_prepare_altitude_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_right_triangle_altitude_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometryRightTriangleAltitudeTheoremAltitudeValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
