"""Public task for `task_icons__named_field__multi_attribute_exclusion_count`."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import (
    MULTI_ATTRIBUTE_EXCLUSION_TASK_ID as TASK_ID,
    QUERY_IDS_BY_TASK_ID,
    _IconsCountingNamedShapeColorBooleanCountTaskBase,
)


SUPPORTED_QUERY_IDS: Tuple[str, ...] = QUERY_IDS_BY_TASK_ID[TASK_ID]


@register_task
class IconsNamedFieldMultiAttributeExclusionCountTask(_IconsCountingNamedShapeColorBooleanCountTaskBase):
    """Count icons satisfying one shape/attribute condition while excluding the other."""

    task_id = TASK_ID
    domain = "icons"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def _build_boolean_query_ids(self) -> Tuple[str, ...]:
        """Bind this public objective to its two exclusion predicate queries."""

        return SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one exclusion-predicate named-field counting task."""

        query_ids = self._build_boolean_query_ids()
        if tuple(query_ids) != SUPPORTED_QUERY_IDS:
            raise RuntimeError("multi-attribute exclusion query support changed unexpectedly")
        merged_params = dict(params)
        return super().generate(int(instance_seed), params=merged_params, max_attempts=int(max_attempts))


__all__ = ["IconsNamedFieldMultiAttributeExclusionCountTask", "SUPPORTED_QUERY_IDS"]
