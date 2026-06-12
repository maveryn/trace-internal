"""Public task module for image-plane relation counting."""

from __future__ import annotations

from ...registry import register_task
from .shared.view_relation_count import (
    IMAGE_PLANE_LATERAL_RELATION_COUNT_TASK_ID,
    SCREEN_SIDE_QUERY_IDS,
    _ThreeDSpatialViewRelationCountBase,
)


TASK_ID = IMAGE_PLANE_LATERAL_RELATION_COUNT_TASK_ID
SUPPORTED_QUERY_IDS = SCREEN_SIDE_QUERY_IDS


@register_task
class ThreeDObjectSceneImagePlaneLateralRelationCountTask(_ThreeDSpatialViewRelationCountBase):
    """Count objects left or right of a named reference in the image plane."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS


__all__ = ["SUPPORTED_QUERY_IDS", "TASK_ID", "ThreeDObjectSceneImagePlaneLateralRelationCountTask"]
