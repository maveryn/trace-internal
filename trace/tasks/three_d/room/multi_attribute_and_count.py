"""Public task wrapper for room wall-mounted object counting."""

from __future__ import annotations

from typing import Any, Dict

from trace.tasks.registry import register_task
from trace.tasks.three_d.room._lifecycle import generate_room_count_task
from trace.tasks.three_d.room.shared.state import SCENE_ID


TASK_ID = "task_three_d__room__multi_attribute_and_count"
QUERY_ID = "single"
SUPPORTED_QUERY_IDS = (QUERY_ID,)


@register_task
class ThreeDRoomMultiAttributeAndCountTask:
    """Count target objects mounted on walls in a perspective 3D room."""

    task_id = TASK_ID
    domain = "three_d"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int):
        return generate_room_count_task(
            int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            task_identifier=TASK_ID,
            single_branch=QUERY_ID,
        )


__all__ = ["SCENE_ID", "SUPPORTED_QUERY_IDS", "TASK_ID", "ThreeDRoomMultiAttributeAndCountTask"]
