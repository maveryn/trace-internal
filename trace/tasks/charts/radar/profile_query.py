"""Public registration facade for radar chart profile tasks."""

from __future__ import annotations

from ...registry import register_task
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from .profile_task import ChartsRadarMultiplotQueryTask as _ChartsRadarMultiplotQueryTask


class ChartsRadarMultiplotQueryTask(_ChartsRadarMultiplotQueryTask):
    """Answer comparison and filtering queries on radar chart displays."""


@register_task
class ChartsRadarHighlightedMetricThresholdPanelCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsRadarMultiplotQueryTask,
):
    """Count radar panels where the highlighted metric satisfies a threshold."""

    task_id = "task_charts__radar__highlighted_metric_threshold_panel_count"
    allowed_query_ids = (
        "highlighted_metric_threshold_panel_count",
    )


@register_task
class ChartsRadarMatchingConditionPanelCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsRadarMultiplotQueryTask,
):
    """Count radar panels matching a multi-metric condition."""

    task_id = "task_charts__radar__matching_condition_panel_count"
    allowed_query_ids = (
        "matching_condition_panel_count",
    )


@register_task
class ChartsRadarThresholdMetricCountForPanelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsRadarMultiplotQueryTask,
):
    """Count metrics in one radar panel satisfying a threshold."""

    task_id = "task_charts__radar__threshold_metric_count_for_panel"
    fixed_query_id = "threshold_metric_count_for_panel"


@register_task
class ChartsRadarProfileAdvantageCountTask(FixedChartQueryVariantTaskMixin, ChartsRadarMultiplotQueryTask):
    """Count metrics where one radar profile exceeds another."""

    task_id = "task_charts__radar__profile_advantage_count"
    fixed_query_id = "profile_advantage_count"


__all__ = [
    "ChartsRadarHighlightedMetricThresholdPanelCountTask",
    "ChartsRadarMatchingConditionPanelCountTask",
    "ChartsRadarMultiplotQueryTask",
    "ChartsRadarProfileAdvantageCountTask",
    "ChartsRadarThresholdMetricCountForPanelTask",
]
