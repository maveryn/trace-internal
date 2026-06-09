"""Public exports for scatter cluster chart tasks."""

from __future__ import annotations

from ...registry import register_task
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from .cluster_common import TASK_ID, SUPPORTED_QUERY_IDS, SUPPORTED_SCENE_VARIANTS, _SUPPORTED_AREA_RANK_QUERY_IDS
from .cluster_task import ChartsScatterClusterQueryTask as _ChartsScatterClusterQueryTaskBase


class ChartsScatterClusterQueryTask(_ChartsScatterClusterQueryTaskBase):
    """Answer cluster and trend questions over a scatter plot."""

    task_id = TASK_ID


@register_task
class ChartsScatterClusterTrendDirectionLabelTask(FixedChartQueryVariantTaskMixin, ChartsScatterClusterQueryTask):
    """Return the cluster label with a requested trend direction."""

    task_id = "task_charts__scatter_cluster__cluster_trend_direction_label"
    fixed_query_id = "cluster_trend_direction_label"


@register_task
class ChartsScatterClusterSeparationExtremumLabelTask(
    MergedChartQueryVariantTaskMixin,
    ChartsScatterClusterQueryTask,
):
    """Return the cluster label with extremal separation from other clusters."""

    task_id = "task_charts__scatter_cluster__cluster_separation_extremum_label"
    allowed_query_ids = ("cluster_separation_extremum_label",)


@register_task
class ChartsScatterClusterSpreadExtremumLabelTask(
    MergedChartQueryVariantTaskMixin,
    ChartsScatterClusterQueryTask,
):
    """Return the cluster label with extremal within-cluster spread."""

    task_id = "task_charts__scatter_cluster__cluster_spread_extremum_label"
    allowed_query_ids = ("cluster_spread_extremum_label",)


@register_task
class ChartsScatterClusterAreaRankLabelTask(
    MergedChartQueryVariantTaskMixin,
    ChartsScatterClusterQueryTask,
):
    """Return the cluster label at a requested displayed footprint-area rank."""

    task_id = "task_charts__scatter_cluster__cluster_area_rank_label"
    allowed_query_ids = _SUPPORTED_AREA_RANK_QUERY_IDS


@register_task
class ChartsScatterClusterCentroidOptionSelectionLabelTask(FixedChartQueryVariantTaskMixin, ChartsScatterClusterQueryTask):
    """Choose the option marker closest to the centroid of a named cluster."""

    task_id = "task_charts__scatter_cluster__centroid_option_selection_label"
    fixed_query_id = "centroid_option_selection_label"


__all__ = [
    "ChartsScatterClusterAreaRankLabelTask",
    "ChartsScatterClusterCentroidOptionSelectionLabelTask",
    "ChartsScatterClusterQueryTask",
    "ChartsScatterClusterSeparationExtremumLabelTask",
    "ChartsScatterClusterSpreadExtremumLabelTask",
    "ChartsScatterClusterTrendDirectionLabelTask",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
