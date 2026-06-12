"""Count semantic color/object conjunctions in a dense 3D object cluster."""

from __future__ import annotations

from ...registry import register_task
from .shared.attribute_count import ObjectClusterMultiAttributeAndCountBase, TASK_ID


@register_task
class ThreeDObjectClusterMultiAttributeAndCountTask(ObjectClusterMultiAttributeAndCountBase):
    """Count clustered objects matching both object type and semantic color."""


__all__ = [
    "TASK_ID",
    "ThreeDObjectClusterMultiAttributeAndCountTask",
]
