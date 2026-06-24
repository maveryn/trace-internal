"""Count candidate polygons similar to a reference polygon."""

from __future__ import annotations

from trace.tasks.registry import register_task

from ._lifecycle import ShapeGalleryObjectivePlan, run_shape_gallery_public_entry
from .shared.relations import SCENE_ID


TASK_ID = "task_geometry__shape_gallery__similar_count"
SUPPORTED_QUERY_IDS = ("single",)
DEFAULT_QUERY_ID = "single"
CONFIG_GROUP_KEY = "shape_gallery_similarity_count"
PROMPT_BRANCH_KEY = "similar_count"


def _prepare_similar_count_objective(
    instance_seed: int,
    selected_branch: str,
    branch_probabilities: dict[str, float],
    task_params: dict,
) -> ShapeGalleryObjectivePlan:
    """Bind the public similar-count objective to relation-count scene primitives."""

    _ = instance_seed, selected_branch, branch_probabilities, task_params
    return ShapeGalleryObjectivePlan(
        scene_family="relation_count",
        config_group_key=CONFIG_GROUP_KEY,
        prompt_branch_key=PROMPT_BRANCH_KEY,
        relation_rule="similar",
        program_scope="similar_count",
    )


@register_task
class GeometryShapeGallerySimilarCountTask:
    """Count candidate polygons similar to a reference polygon."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    prepare_objective = staticmethod(_prepare_similar_count_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_shape_gallery_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometryShapeGallerySimilarCountTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
