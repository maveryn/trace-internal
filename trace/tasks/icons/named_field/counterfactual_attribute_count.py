"""Public task for `task_icons__named_field__counterfactual_attribute_count`."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import (
    COUNTERFACTUAL_ATTRIBUTE_TASK_ID as TASK_ID,
    COUNTERFACTUAL_QUERY_IDS,
    COUNTERFACTUAL_QUERY_IDS_BY_TASK_ID,
    _IconsNamedFieldCounterfactualCountTaskBase,
)


SUPPORTED_QUERY_IDS: Tuple[str, ...] = COUNTERFACTUAL_QUERY_IDS_BY_TASK_ID[TASK_ID]


@register_task
class IconsNamedFieldCounterfactualAttributeCountTask(_IconsNamedFieldCounterfactualCountTaskBase):
    """Count target-shape icons after a hypothetical shape replacement/removal."""

    task_id = TASK_ID
    domain = "icons"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def _build_counterfactual_query_ids(self) -> Tuple[str, ...]:
        """Bind this public objective to target-count edit queries."""

        return SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one counterfactual target-attribute count task."""

        query_ids = self._build_counterfactual_query_ids()
        if tuple(query_ids) != SUPPORTED_QUERY_IDS:
            raise RuntimeError("counterfactual attribute query support changed unexpectedly")
        merged_params = dict(params)
        return super().generate(int(instance_seed), params=merged_params, max_attempts=int(max_attempts))


__all__ = [
    "COUNTERFACTUAL_QUERY_IDS",
    "COUNTERFACTUAL_QUERY_IDS_BY_TASK_ID",
    "IconsNamedFieldCounterfactualAttributeCountTask",
    "SUPPORTED_QUERY_IDS",
]
