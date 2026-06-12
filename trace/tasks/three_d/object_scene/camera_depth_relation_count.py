"""Public task module for camera-depth relation counting."""

from __future__ import annotations

from ...registry import register_task
from .shared.view_relation_count import (
    CAMERA_DEPTH_QUERY_IDS,
    CAMERA_DEPTH_RELATION_COUNT_TASK_ID,
    _ThreeDSpatialViewRelationCountBase,
)


TASK_ID = CAMERA_DEPTH_RELATION_COUNT_TASK_ID
SUPPORTED_QUERY_IDS = CAMERA_DEPTH_QUERY_IDS


@register_task
class ThreeDObjectSceneCameraDepthRelationCountTask(_ThreeDSpatialViewRelationCountBase):
    """Count objects closer or farther than a named reference in camera depth."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS


__all__ = ["SUPPORTED_QUERY_IDS", "TASK_ID", "ThreeDObjectSceneCameraDepthRelationCountTask"]
