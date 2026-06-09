"""Public exports for Sankey flow chart tasks."""

from __future__ import annotations

from ...registry import register_task
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from .sankey_common import NODE_SIDE_TOTAL_QUERY_IDS, PATH_VALUE_QUERY_IDS, SUPPORTED_QUERY_IDS, SUPPORTED_SCENE_VARIANTS, TASK_ID
from .sankey_task import ChartsFlowSankeyPathValueTask as _ChartsFlowSankeyPathValueTaskBase


class ChartsFlowSankeyPathValueTask(_ChartsFlowSankeyPathValueTaskBase):
    """Answer path arithmetic questions over a weighted Sankey-style chart."""

    task_id = TASK_ID


@register_task
class ChartsFlowSankeyPathBottleneckValuePublicTask(
    MergedChartQueryVariantTaskMixin,
    ChartsFlowSankeyPathValueTask,
):
    """Return the bottleneck value along one Sankey source-middle-target path."""

    task_id = "task_charts__sankey__path_bottleneck_value"
    allowed_query_ids = ("path_bottleneck_value",)


@register_task
class ChartsFlowSankeyPathFlowDifferencePublicTask(
    MergedChartQueryVariantTaskMixin,
    ChartsFlowSankeyPathValueTask,
):
    """Return the absolute difference between two Sankey path edge values."""

    task_id = "task_charts__sankey__path_flow_difference"
    allowed_query_ids = ("path_flow_difference",)


@register_task
class ChartsFlowSankeySourceToTargetTotalFlowPublicTask(
    MergedChartQueryVariantTaskMixin,
    ChartsFlowSankeyPathValueTask,
):
    """Return the total flow across all visible paths from a source to a target."""

    task_id = "task_charts__sankey__source_to_target_total_flow"
    allowed_query_ids = ("source_to_target_total_flow",)


@register_task
class ChartsFlowSankeyNodeSideTotalValuePublicTask(
    MergedChartQueryVariantTaskMixin,
    ChartsFlowSankeyPathValueTask,
):
    """Return a one-sided total for a source or target Sankey node."""

    task_id = "task_charts__sankey__node_side_total_value"
    allowed_query_ids = NODE_SIDE_TOTAL_QUERY_IDS


__all__ = [
    "ChartsFlowSankeyNodeSideTotalValuePublicTask",
    "ChartsFlowSankeyPathBottleneckValuePublicTask",
    "ChartsFlowSankeyPathFlowDifferencePublicTask",
    "ChartsFlowSankeyPathValueTask",
    "ChartsFlowSankeySourceToTargetTotalFlowPublicTask",
    "NODE_SIDE_TOTAL_QUERY_IDS",
    "PATH_VALUE_QUERY_IDS",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
