"""Public task wrapper for closest-camera wall-object selection."""

from __future__ import annotations

from typing import Any, Dict

from trace.tasks.registry import register_task
from trace.tasks.three_d.room._lifecycle import generate_room_camera_distance_task
from trace.tasks.three_d.room.shared.metrics import (
    CAMERA_DISTANCE_MIN_MARGIN,
    CAMERA_DISTANCE_MIN_ROOM_DEPTH_MARGIN,
    LETTERED_WALL_OBJECT_MIN_VISIBLE_PX,
)
from trace.tasks.three_d.room.shared.state import SCENE_ID


TASK_ID = "task_three_d__room__wall_object_camera_distance_label"
QUERY_ID = "single"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


@register_task
class ThreeDRoomWallObjectCameraDistanceLabelTask:
    """Choose the option-panel wall-mounted object closest to the camera."""

    task_id = TASK_ID
    domain = "three_d"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int):
        return generate_room_camera_distance_task(
            int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            task_identifier=TASK_ID,
            single_branch=QUERY_ID,
        )


__all__ = [
    "CAMERA_DISTANCE_MIN_MARGIN",
    "CAMERA_DISTANCE_MIN_ROOM_DEPTH_MARGIN",
    "LETTERED_WALL_OBJECT_MIN_VISIBLE_PX",
    "SCENE_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "ThreeDRoomWallObjectCameraDistanceLabelTask",
]
