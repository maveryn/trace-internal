"""Public exports for heatmap chart tasks."""

from __future__ import annotations

from ...registry import register_task
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from .grid_common import (
    TASK_ID,
    SUPPORTED_QUERY_IDS,
    SUPPORTED_SCENE_VARIANTS,
    _COLORBAR_THRESHOLD_QUERY_IDS,
)
from .grid_task import _ChartsHeatmapGridQueryTaskBase


class ChartsHeatmapGridQueryTask(_ChartsHeatmapGridQueryTaskBase):
    """Answer label questions over color/intensity heatmap grids."""

    task_id = TASK_ID


@register_task
class ChartsHeatmapAxisConditionExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsHeatmapGridQueryTask,
):
    """Return the row or column label with the most cells satisfying a color condition."""

    task_id = "task_charts__heatmap__axis_condition_extremum_label"
    fixed_query_id = "axis_condition_extremum_label"
    supports_unanswerable = True


@register_task
class ChartsHeatmapAxisCellExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsHeatmapGridQueryTask,
):
    """Return the row or column label containing a requested cell extremum."""

    task_id = "task_charts__heatmap__axis_cell_extremum_label"
    fixed_query_id = "axis_cell_extremum_label"
    supports_unanswerable = True


@register_task
class ChartsHeatmapConditionRunExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsHeatmapGridQueryTask,
):
    """Return the label with the longest consecutive run satisfying a color condition."""

    task_id = "task_charts__heatmap__condition_run_extremum_label"
    fixed_query_id = "condition_run_extremum_label"


@register_task
class ChartsHeatmapColorbarThresholdCellCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsHeatmapGridQueryTask,
):
    """Count cells above or below a numeric threshold on a continuous colorbar scale."""

    task_id = "task_charts__heatmap__colorbar_threshold_cell_count"
    allowed_query_ids = _COLORBAR_THRESHOLD_QUERY_IDS


@register_task
class ChartsHeatmapColorbarIntervalCellCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsHeatmapGridQueryTask,
):
    """Count cells inside an inclusive numeric interval on a continuous colorbar scale."""

    task_id = "task_charts__heatmap__colorbar_interval_cell_count"
    fixed_query_id = "colorbar_interval_cell_count"



__all__ = [
    "SUPPORTED_QUERY_IDS",
    "SUPPORTED_SCENE_VARIANTS",
    "ChartsHeatmapAxisCellExtremumLabelTask",
    "ChartsHeatmapAxisConditionExtremumLabelTask",
    "ChartsHeatmapColorbarIntervalCellCountTask",
    "ChartsHeatmapColorbarThresholdCellCountTask",
    "ChartsHeatmapConditionRunExtremumLabelTask",
    "ChartsHeatmapGridQueryTask",
]
