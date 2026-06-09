"""Public registration facade for combo chart panel tasks."""

from __future__ import annotations

from ...registry import register_task
from .panel_common import _THRESHOLD_CROSSING_QUERY_IDS
from .panel_task import ChartsComboPanelQueryTask as _ChartsComboPanelQueryTask


class ChartsComboPanelQueryTask(_ChartsComboPanelQueryTask):
    """Shared generator for public combo-chart tasks."""


@register_task
class ChartsComboCrossMarkDifferenceValueTask(ChartsComboPanelQueryTask):
    """Compute differences between the primary mark value and overlaid line value."""

    task_id = "task_charts__combo_mark__cross_mark_difference_value"
    query_ids = (
        "primary_minus_line_at_label",
        "line_minus_primary_at_label",
    )


@register_task
class ChartsComboConditionedLineExtremumLabelTask(ChartsComboPanelQueryTask):
    """Filter by the primary mark series and find an extremum in the line series."""

    task_id = "task_charts__combo_mark__conditioned_line_extremum_label"
    query_ids = (
        "max_line_where_primary_above_threshold",
        "min_line_where_primary_above_threshold",
    )


@register_task
class ChartsComboConditionedPrimaryExtremumLabelTask(ChartsComboPanelQueryTask):
    """Filter by the line series and find an extremum in the primary mark series."""

    task_id = "task_charts__combo_mark__conditioned_primary_extremum_label"
    query_ids = (
        "max_primary_where_line_below_threshold",
        "min_primary_where_line_below_threshold",
    )


@register_task
class ChartsComboDualThresholdConditionCountTask(ChartsComboPanelQueryTask):
    """Count categories satisfying two one-bound threshold conditions."""

    task_id = "task_charts__combo_mark__dual_threshold_condition_count"
    query_ids = (
        "primary_above_and_line_above",
        "primary_above_and_line_below",
        "primary_below_and_line_above",
    )


@register_task
class ChartsComboIntervalThresholdConditionCountTask(ChartsComboPanelQueryTask):
    """Count categories satisfying one interval condition and one threshold condition."""

    task_id = "task_charts__combo_mark__interval_threshold_condition_count"
    query_ids = (
        "primary_between_and_line_above",
        "line_between_and_primary_above",
    )


@register_task
class ChartsComboAbsoluteGapExtremumLabelTask(ChartsComboPanelQueryTask):
    """Find the category with an extremal absolute gap between encodings."""

    task_id = "task_charts__combo_mark__absolute_gap_extremum_label"
    query_ids = (
        "largest_absolute_gap_label",
        "smallest_nonzero_absolute_gap_label",
    )


@register_task
class ChartsComboDirectionalGapExtremumLabelTask(ChartsComboPanelQueryTask):
    """Find the category with the largest directional gap between encodings."""

    task_id = "task_charts__combo_mark__directional_gap_extremum_label"
    query_ids = (
        "largest_primary_over_line_gap_label",
        "largest_line_over_primary_gap_label",
    )


@register_task
class ChartsComboSeriesThresholdCrossingLabelTask(ChartsComboPanelQueryTask):
    """Return the first category where one combo series crosses a threshold."""

    task_id = "task_charts__combo_mark__series_threshold_crossing_label"
    query_ids = _THRESHOLD_CROSSING_QUERY_IDS


__all__ = [
    "ChartsComboAbsoluteGapExtremumLabelTask",
    "ChartsComboConditionedLineExtremumLabelTask",
    "ChartsComboConditionedPrimaryExtremumLabelTask",
    "ChartsComboCrossMarkDifferenceValueTask",
    "ChartsComboDirectionalGapExtremumLabelTask",
    "ChartsComboDualThresholdConditionCountTask",
    "ChartsComboIntervalThresholdConditionCountTask",
    "ChartsComboPanelQueryTask",
    "ChartsComboSeriesThresholdCrossingLabelTask",
]
