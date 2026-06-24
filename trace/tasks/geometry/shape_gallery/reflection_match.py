"""Choose the candidate polygon matching a shown reflection."""

from __future__ import annotations

from trace.tasks.registry import register_task

from ._lifecycle import ShapeGalleryObjectivePlan, run_shape_gallery_public_entry
from .shared.relations import SCENE_ID


TASK_ID = "task_geometry__shape_gallery__reflection_match"
SUPPORTED_QUERY_IDS = ("single",)
DEFAULT_QUERY_ID = "single"
CONFIG_GROUP_KEY = "shape_gallery_transformation_match"
PROMPT_BRANCH_KEY = "reflection_match"


def _prepare_reflection_match_objective(
    instance_seed: int,
    selected_branch: str,
    branch_probabilities: dict[str, float],
    task_params: dict,
) -> ShapeGalleryObjectivePlan:
    """Bind the public reflection-match objective to transform-selection primitives."""

    _ = instance_seed, selected_branch, branch_probabilities, task_params
    return ShapeGalleryObjectivePlan(
        scene_family="transform_selection",
        config_group_key=CONFIG_GROUP_KEY,
        prompt_branch_key=PROMPT_BRANCH_KEY,
        transform_rule="reflection",
        program_scope="reflection_match",
    )


@register_task
class GeometryShapeGalleryReflectionMatchTask:
    """Choose the candidate polygon matching a shown reflection."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    prepare_objective = staticmethod(_prepare_reflection_match_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_shape_gallery_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometryShapeGalleryReflectionMatchTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
