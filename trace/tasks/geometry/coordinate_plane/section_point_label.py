"""Choose a section point on a coordinate-plane segment."""

from __future__ import annotations

from typing import Any, Mapping

from ...registry import register_task

from ._lifecycle import CoordinateAlgebraObjective, run_coordinate_algebra_entry

SECTION_POINT_TASK_ID = "task_geometry__coordinate_plane__section_point_label"
TASK_ID = "task_geometry__coordinate_plane__section_point_label"
SCENE_ID = "coordinate_plane"
SECTION_POINT_QUERY_IDS = ("one_third_from_p_to_q", "two_thirds_from_p_to_q")
SUPPORTED_QUERY_IDS = SECTION_POINT_QUERY_IDS
SCENE_KEY = "coordinate_algebra_section_scene"
SEMANTIC_OPERATION_BY_ID = {
    "one_third_from_p_to_q": "section_one_third",
    "two_thirds_from_p_to_q": "section_two_thirds",
}


def _prepare_section_point_objective(
    selected_query: str,
    _query_probabilities: Mapping[str, float],
    _task_params: Mapping[str, Any],
) -> CoordinateAlgebraObjective:
    """Bind the selected section-ratio query to coordinate section semantics."""

    return CoordinateAlgebraObjective(
        semantic_operation=str(SEMANTIC_OPERATION_BY_ID[str(selected_query)]),
        prompt_query_key=str(selected_query),
        scene_key=SCENE_KEY,
    )


@register_task
class GeometryCoordinateSectionPointLabelTask:
    """Choose the candidate point at the requested one-third or two-third position."""

    task_id = TASK_ID
    domain = "geometry"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True
    prepare_objective = staticmethod(_prepare_section_point_objective)

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int):
        """Generate a segment-section candidate selection scene."""

        return run_coordinate_algebra_entry(self, instance_seed, params=params, max_attempts=max_attempts)
