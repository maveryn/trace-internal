"""Scientific multi-panel subplot query task public registrations."""

from __future__ import annotations

from ...registry import register_task
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin
from .multipanel_common import SUPPORTED_QUERY_IDS, SUPPORTED_SCENE_VARIANTS
from .multipanel_task import ChartsScientificMultipanelSubplotQueryTask


@register_task
class ChartsScientificCurveAtXExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsScientificMultipanelSubplotQueryTask,
):
    """Return the panel or curve label with an extremal value at a shared x-position."""

    task_id = "task_charts__curve_panels__curve_at_x_extremum_label"
    fixed_query_id = "curve_at_x_extremum_label"


@register_task
class ChartsScientificThresholdSeriesCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsScientificMultipanelSubplotQueryTask,
):
    """Count series satisfying a threshold condition in a scientific panel."""

    task_id = "task_charts__curve_panels__threshold_series_count"
    fixed_query_id = "threshold_series_count"


@register_task
class ChartsScientificPanelPointThresholdCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsScientificMultipanelSubplotQueryTask,
):
    """Count plotted markers satisfying a threshold condition in one scientific panel."""

    task_id = "task_charts__curve_panels__panel_point_threshold_count"
    fixed_query_id = "panel_point_threshold_count"


@register_task
class ChartsScientificPanelCurveThresholdCrossingCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsScientificMultipanelSubplotQueryTask,
):
    """Count method curves crossing a threshold in one scientific panel."""

    task_id = "task_charts__curve_panels__panel_curve_threshold_crossing_count"
    fixed_query_id = "panel_curve_threshold_crossing_count"


@register_task
class ChartsScientificCrossPanelDeltaExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsScientificMultipanelSubplotQueryTask,
):
    """Return the label with an extremal cross-panel delta."""

    task_id = "task_charts__curve_panels__cross_panel_delta_extremum_label"
    fixed_query_id = "cross_panel_delta_extremum_label"


@register_task
class ChartsScientificCrossPanelThresholdEarliestLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsScientificMultipanelSubplotQueryTask,
):
    """Return the panel whose selected curve crosses a threshold earliest."""

    task_id = "task_charts__curve_panels__cross_panel_threshold_earliest_label"
    fixed_query_id = "cross_panel_threshold_earliest_label"


@register_task
class ChartsScientificCurveIntersectionCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsScientificMultipanelSubplotQueryTask,
):
    """Count curve intersections in a scientific subplot."""

    task_id = "task_charts__curve_panels__curve_intersection_count"
    fixed_query_id = "curve_intersection_count"


@register_task
class ChartsScientificEarliestMaximumPanelLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsScientificMultipanelSubplotQueryTask,
):
    """Return the panel label whose selected curve reaches its maximum earliest."""

    task_id = "task_charts__curve_panels__earliest_maximum_panel_label"
    fixed_query_id = "earliest_maximum_panel_label"


__all__ = [
    "ChartsScientificCrossPanelDeltaExtremumLabelTask",
    "ChartsScientificCrossPanelThresholdEarliestLabelTask",
    "ChartsScientificCurveAtXExtremumLabelTask",
    "ChartsScientificCurveIntersectionCountTask",
    "ChartsScientificEarliestMaximumPanelLabelTask",
    "ChartsScientificMultipanelSubplotQueryTask",
    "ChartsScientificPanelCurveThresholdCrossingCountTask",
    "ChartsScientificPanelPointThresholdCountTask",
    "ChartsScientificThresholdSeriesCountTask",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
