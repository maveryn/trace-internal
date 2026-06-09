"""Mixed-dashboard cross-panel chart task public registrations."""

from __future__ import annotations

from ...registry import register_task
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from .cross_panel_common import SUPPORTED_PANEL_KINDS, SUPPORTED_QUERY_IDS, SUPPORTED_SCENE_VARIANTS
from .cross_panel_task import ChartsDashboardCrossPanelQueryTask


@register_task
class ChartsDashboardSourceRankTargetValueTask(
    MergedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Use source-panel rank to select a target-panel value."""

    task_id = "task_charts__dashboard__source_rank_target_value"
    allowed_query_ids = (
        "source_rank_target_value",
    )


@register_task
class ChartsDashboardSourceRankDifferenceValueTask(
    MergedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Use source-panel rank to select a cross-panel difference."""

    task_id = "task_charts__dashboard__source_rank_difference_value"
    allowed_query_ids = (
        "source_rank_difference_value",
    )


@register_task
class ChartsDashboardDualSourceTargetSumValueTask(
    FixedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Sum target values selected from two source-panel rankings."""

    task_id = "task_charts__dashboard__dual_source_target_sum_value"
    fixed_query_id = "dual_source_target_sum_value"


@register_task
class ChartsDashboardDualConditionCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Count categories satisfying two dashboard panel conditions."""

    task_id = "task_charts__dashboard__dual_condition_count"
    fixed_query_id = "dual_condition_count"


@register_task
class ChartsDashboardPanelGapExtremumCategoryLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Return the category with an extremal gap between two panels."""

    task_id = "task_charts__dashboard__panel_gap_extremum_category_label"
    fixed_query_id = "panel_gap_extremum_category_label"
    supports_unanswerable = True


@register_task
class ChartsDashboardSharedLabelRankGapExtremumTask(
    FixedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Return the shared category with an extremal rank-position gap."""

    task_id = "task_charts__dashboard__shared_label_rank_gap_extremum"
    fixed_query_id = "shared_label_rank_gap_extremum"


@register_task
class ChartsDashboardStatementOptionSelectionLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Select the rendered statement option with the requested truth value."""

    task_id = "task_charts__dashboard__statement_option_selection_label"
    fixed_query_id = "statement_option_selection_label"


@register_task
class ChartsDashboardTopKOverlapCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Count shared category labels between two top-k dashboard panels."""

    task_id = "task_charts__dashboard__top_k_overlap_count"
    fixed_query_id = "top_k_overlap_count"


@register_task
class ChartsDashboardCategoryPanelConditionCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Count dashboard panels where one category satisfies a value condition."""

    task_id = "task_charts__dashboard__category_panel_condition_count"
    fixed_query_id = "category_panel_condition_count"


__all__ = [
    "ChartsDashboardCategoryPanelConditionCountTask",
    "ChartsDashboardCrossPanelQueryTask",
    "ChartsDashboardDualConditionCountTask",
    "ChartsDashboardDualSourceTargetSumValueTask",
    "ChartsDashboardPanelGapExtremumCategoryLabelTask",
    "ChartsDashboardSharedLabelRankGapExtremumTask",
    "ChartsDashboardSourceRankDifferenceValueTask",
    "ChartsDashboardSourceRankTargetValueTask",
    "ChartsDashboardStatementOptionSelectionLabelTask",
    "ChartsDashboardTopKOverlapCountTask",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_PANEL_KINDS",
    "SUPPORTED_QUERY_IDS",
]
