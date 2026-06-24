"""Public task wrapper for wall-plane side-relation selection."""

from __future__ import annotations

from typing import Any, Dict

from trace.tasks.registry import register_task
from trace.tasks.three_d.room._lifecycle import generate_room_side_relation_task
from trace.tasks.three_d.room.shared.spatial_primitives import REFERENCE_OBJECT_TYPE
from trace.tasks.three_d.room.shared.state import SCENE_ID


TASK_ID = "task_three_d__room__wall_object_side_relation_label"
SUPPORTED_QUERY_IDS = ("left_of_reference_on_wall", "right_of_reference_on_wall")
SIDE_RELATION_BY_QUERY_ID = {
    "left_of_reference_on_wall": "left",
    "right_of_reference_on_wall": "right",
}


@register_task
class ThreeDRoomWallObjectSideRelationLabelTask:
    """Choose the option-panel wall object on the requested side of a TV."""

    task_id = TASK_ID
    domain = "three_d"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int):
        return generate_room_side_relation_task(
            int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            task_identifier=TASK_ID,
            supported_branches=SUPPORTED_QUERY_IDS,
            branch_to_relation=SIDE_RELATION_BY_QUERY_ID,
        )


__all__ = [
    "REFERENCE_OBJECT_TYPE",
    "SCENE_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDRoomWallObjectSideRelationLabelTask",
]
