"""Public task module for object-scene exclusive-or counting."""

from __future__ import annotations

from typing import Any, Dict

from ...base import TaskOutput
from ...registry import register_task
from ..shared.object_scene_logical_predicate_count import (
    MULTI_ATTRIBUTE_XOR_COUNT_TASK_ID,
    MULTI_ATTRIBUTE_XOR_QUERY_IDS,
    _ThreeDSpatialLogicalPredicateCountBase,
)


TASK_ID = MULTI_ATTRIBUTE_XOR_COUNT_TASK_ID
SUPPORTED_QUERY_IDS = MULTI_ATTRIBUTE_XOR_QUERY_IDS


@register_task
class ThreeDObjectSceneMultiAttributeXorCountTask(_ThreeDSpatialLogicalPredicateCountBase):
    """Count objects matching exactly one of a color and object type."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate this public object-scene count task through its explicit objective wrapper."""
        seed = int(instance_seed)
        bound_params = dict(params)
        attempts = max(1, int(max_attempts))
        return super().generate(seed, params=bound_params, max_attempts=attempts)


__all__ = ["SUPPORTED_QUERY_IDS", "TASK_ID", "ThreeDObjectSceneMultiAttributeXorCountTask"]
