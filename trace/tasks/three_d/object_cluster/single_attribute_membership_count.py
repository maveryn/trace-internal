"""Count objects of one type in a dense synthetic 3D object cluster."""

from __future__ import annotations

from ...registry import register_task
from .shared.instance_count import ObjectClusterSingleAttributeMembershipCountBase, TASK_ID


@register_task
class ThreeDObjectClusterSingleAttributeMembershipCountTask(ObjectClusterSingleAttributeMembershipCountBase):
    """Count visible instances of one object type in a dense object cluster."""


__all__ = [
    "TASK_ID",
    "ThreeDObjectClusterSingleAttributeMembershipCountTask",
]
