"""Compute a circular-sector central angle from visible measurements."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import SectorObjectivePlan, run_sector_public_entry
from .shared.defaults import DOMAIN
from .shared.sampling import sample_sector_angle_from_arc_length, sample_sector_angle_from_area


TASK_ID = "task_geometry__sector__sector_angle_value"
SUPPORTED_QUERY_IDS = (
    "angle_from_arc_length_and_radius",
    "angle_from_area_and_radius",
)
DEFAULT_QUERY_ID = "angle_from_arc_length_and_radius"
PROMPT_TASK_KEY = "sector_angle_value_query"
ANNOTATION_ROLES_BY_QUERY = {
    "angle_from_arc_length_and_radius": ("target_angle_cue", "radius_label", "arc_length_label"),
    "angle_from_area_and_radius": ("target_angle_cue", "radius_label", "sector_area_label"),
}


def _prepare_sector_angle_objective(
    instance_seed: int,
    selected_branch: str,
    branch_probabilities: Dict[str, float],
    task_params: Mapping[str, Any],
) -> SectorObjectivePlan:
    if selected_branch == "angle_from_arc_length_and_radius":
        problem = sample_sector_angle_from_arc_length(
            int(instance_seed),
            seed_namespace=f"{TASK_ID}.{selected_branch}",
            params=task_params,
        )
    elif selected_branch == "angle_from_area_and_radius":
        problem = sample_sector_angle_from_area(
            int(instance_seed),
            seed_namespace=f"{TASK_ID}.{selected_branch}",
            params=task_params,
        )
    else:
        raise ValueError(f"unsupported query branch for {TASK_ID}: {selected_branch}")
    return SectorObjectivePlan(
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_branch_key=str(selected_branch),
        problem=problem,
        answer_type="number",
        annotation_roles=ANNOTATION_ROLES_BY_QUERY[str(selected_branch)],
        replay_params={
            "query_id_probabilities": dict(branch_probabilities),
            "case_index": int(problem.case_index),
            "formula_family": str(problem.formula_family),
        },
        trace_values={"program_scope": "sector_angle_value"},
    )


@register_task
class GeometrySectorAngleValueTask:
    """Compute a circular-sector central angle from visible measurements."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    prepare_objective = staticmethod(_prepare_sector_angle_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_sector_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometrySectorAngleValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
