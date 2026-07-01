"""Compute a Cartesian component from a displayed polar point."""

from __future__ import annotations

from typing import Any

from trace.tasks.registry import register_task

from ._lifecycle import run_cartesian_component_value

TASK_ID = "task_geometry__coordinate_conversion__cartesian_component_value"
SCENE_ID = "coordinate_conversion"
QUERY_IDS = ("x_from_polar_point", "y_from_polar_point")
QUERY_COMPONENTS = {
    "x_from_polar_point": "x",
    "y_from_polar_point": "y",
}


def _prepare_cartesian_component_objective(selected_branch: str) -> dict[str, str]:
    """Bind the public branch to the requested Cartesian component."""

    return {
        "component": str(QUERY_COMPONENTS[str(selected_branch)]),
        "object_description_key": "object_description_polar_point",
        "annotation_hint_key": "annotation_hint_segment_op",
    }


@register_task
class GeometryCoordinateConversionCartesianComponentValueTask:
    """Answer a Cartesian component for a displayed polar point."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = QUERY_IDS
    prepare_objective = staticmethod(_prepare_cartesian_component_objective)

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int):
        """Generate one polar-to-Cartesian coordinate conversion instance."""

        return run_cartesian_component_value(self, instance_seed, params=params, max_attempts=max_attempts)


__all__ = [
    "GeometryCoordinateConversionCartesianComponentValueTask",
    "QUERY_IDS",
    "SCENE_ID",
    "TASK_ID",
]
