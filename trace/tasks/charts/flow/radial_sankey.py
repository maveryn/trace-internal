"""Public exports for radial Sankey-style flow chart tasks."""

from __future__ import annotations

from typing import Any, Dict

from ...base import TaskOutput
from ...registry import register_task
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from .radial_sankey_common import (
    DOMINANT_ENDPOINT_QUERY_IDS,
    SUPPORTED_QUERY_IDS,
    SUPPORTED_SCENE_VARIANTS,
    TASK_ID,
    TRANSFER_TOTAL_QUERY_IDS,
)
from .radial_sankey_task import ChartsFlowRadialSankeyTask as _ChartsFlowRadialSankeyTaskBase


class ChartsFlowRadialSankeyTask(_ChartsFlowRadialSankeyTaskBase):
    """Answer endpoint-selection and transfer-total questions over a radial Sankey chart."""

    task_id = TASK_ID


@register_task
class ChartsFlowRadialSankeyTransferTotalValuePublicTask(
    MergedChartQueryVariantTaskMixin,
    ChartsFlowRadialSankeyTask,
):
    """Return a grouped transfer total from a radial Sankey chart."""

    task_id = "task_charts__radial_sankey__transfer_total_value"
    allowed_query_ids = TRANSFER_TOTAL_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        transfer_params = dict(params)
        transfer_params.setdefault("radial_group_size_min", 2)
        transfer_params.setdefault("radial_group_size_max", 2)
        transfer_params.setdefault("radial_source_count_min", 4)
        transfer_params.setdefault("radial_source_count_max", 4)
        transfer_params.setdefault("radial_target_count_min", 4)
        transfer_params.setdefault("radial_target_count_max", 4)
        transfer_params.setdefault("radial_link_count_min", 5)
        transfer_params.setdefault("radial_link_count_max", 7)
        return super().generate(int(instance_seed), params=transfer_params, max_attempts=int(max_attempts))


@register_task
class ChartsFlowRadialSankeyDominantEndpointLabelPublicTask(
    MergedChartQueryVariantTaskMixin,
    ChartsFlowRadialSankeyTask,
):
    """Return a dominant source or target endpoint from a radial Sankey chart."""

    task_id = "task_charts__radial_sankey__dominant_endpoint_label"
    allowed_query_ids = DOMINANT_ENDPOINT_QUERY_IDS


__all__ = [
    "ChartsFlowRadialSankeyDominantEndpointLabelPublicTask",
    "ChartsFlowRadialSankeyTask",
    "ChartsFlowRadialSankeyTransferTotalValuePublicTask",
    "DOMINANT_ENDPOINT_QUERY_IDS",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
    "TRANSFER_TOTAL_QUERY_IDS",
]
