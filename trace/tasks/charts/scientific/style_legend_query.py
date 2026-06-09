"""Public registration facade for scientific style-legend chart tasks."""

from __future__ import annotations

from ...registry import register_task
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from .style_legend_common import (
    EXTREMUM_QUERY_IDS,
    GAP_QUERY_IDS,
    SUPPORTED_LEGEND_POSITIONS,
    SUPPORTED_QUERY_IDS,
    SUPPORTED_STYLE_PALETTE_MODES,
    THRESHOLD_QUERY_IDS,
)
from .style_legend_task import ChartsStyleLegendBindingTask as _ChartsStyleLegendBindingTask


class ChartsStyleLegendBindingTask(_ChartsStyleLegendBindingTask):
    """Answer style-bound legend/series questions on scientific line charts."""


@register_task
class ChartsStyleLegendXPositionExtremumSeriesLabelTask(MergedChartQueryVariantTaskMixin, ChartsStyleLegendBindingTask):
    """Select the styled legend series with an extremal value at one x position."""

    task_id = "task_charts__style_legend__x_position_extremum_series_label"
    allowed_query_ids = EXTREMUM_QUERY_IDS


@register_task
class ChartsStyleLegendPairwiseGapValueTask(MergedChartQueryVariantTaskMixin, ChartsStyleLegendBindingTask):
    """Compute a value gap between two styled legend series at one x position."""

    task_id = "task_charts__style_legend__pairwise_gap_value"
    allowed_query_ids = GAP_QUERY_IDS


@register_task
class ChartsStyleLegendThresholdSeriesCountTask(MergedChartQueryVariantTaskMixin, ChartsStyleLegendBindingTask):
    """Count styled legend series satisfying a threshold at one x position."""

    task_id = "task_charts__style_legend__threshold_series_count"
    allowed_query_ids = THRESHOLD_QUERY_IDS


__all__ = [
    "EXTREMUM_QUERY_IDS",
    "GAP_QUERY_IDS",
    "SUPPORTED_LEGEND_POSITIONS",
    "SUPPORTED_QUERY_IDS",
    "SUPPORTED_STYLE_PALETTE_MODES",
    "THRESHOLD_QUERY_IDS",
    "ChartsStyleLegendBindingTask",
    "ChartsStyleLegendPairwiseGapValueTask",
    "ChartsStyleLegendThresholdSeriesCountTask",
    "ChartsStyleLegendXPositionExtremumSeriesLabelTask",
]
