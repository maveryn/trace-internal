"""Compute circular-sector area from visible sector measurements."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import SectorObjectivePlan, run_sector_public_entry
from .shared.defaults import DOMAIN
from .shared.sampling import sample_sector_area_from_arc_length, sample_sector_area_from_complement_angle


TASK_ID = "task_geometry__sector__sector_area_value"
SUPPORTED_QUERY_IDS = (
    "area_from_arc_length_and_radius",
    "area_from_radius_and_complement_angle",
)
DEFAULT_QUERY_ID = "area_from_arc_length_and_radius"
PROMPT_TASK_KEY = "sector_area_value_query"
ANNOTATION_ROLES_BY_QUERY = {
    "area_from_arc_length_and_radius": ("target_sector_region", "radius_label", "arc_length_label"),
    "area_from_radius_and_complement_angle": ("target_sector_region", "radius_label", "angle_relation_label"),
}


def _prepare_sector_area_objective(
    instance_seed: int,
    selected_branch: str,
    branch_probabilities: Dict[str, float],
    task_params: Mapping[str, Any],
) -> SectorObjectivePlan:
    if selected_branch == "area_from_arc_length_and_radius":
        problem = sample_sector_area_from_arc_length(
            int(instance_seed),
            seed_namespace=f"{TASK_ID}.{selected_branch}",
            params=task_params,
        )
    elif selected_branch == "area_from_radius_and_complement_angle":
        problem = sample_sector_area_from_complement_angle(
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
        trace_values={"program_scope": "sector_area_value"},
    )


@register_task
class GeometrySectorAreaValueTask:
    """Compute circular-sector area from visible sector measurements."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    prepare_objective = staticmethod(_prepare_sector_area_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_sector_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometrySectorAreaValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
