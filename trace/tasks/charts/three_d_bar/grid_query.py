"""Public exports for 3D bar-grid chart tasks."""

from __future__ import annotations

from ...registry import register_task
from .grid_common import TASK_ID
from .grid_task import ChartsThreeDBarGridQueryTask as _ChartsThreeDBarGridQueryTaskBase


class ChartsThreeDBarGridQueryTask(_ChartsThreeDBarGridQueryTaskBase):
    """Generate one 3D bar-grid chart query."""

    task_id = TASK_ID


@register_task
class ChartsThreeDBarCategoryTotalValueTask(ChartsThreeDBarGridQueryTask):
    """Compute the total for one x-axis category across series in a 3D bar chart."""

    task_id = "task_charts__bar_3d__category_total_value"
    allowed_query_ids = ("category_total_value",)
    default_dataset_enabled = True


@register_task
class ChartsThreeDBarSeriesCategoryScopeTotalValueTask(ChartsThreeDBarGridQueryTask):
    """Compute a total for one series over all or a contiguous subset of categories."""

    task_id = "task_charts__bar_3d__series_category_scope_total_value"
    allowed_query_ids = ("series_total_value", "series_interval_total_value")
    default_dataset_enabled = True


@register_task
class ChartsThreeDBarCategoryExtremumGapValueTask(ChartsThreeDBarGridQueryTask):
    """Compute the gap between extremal bars within one x-axis category."""

    task_id = "task_charts__bar_3d__category_extremum_gap_value"
    allowed_query_ids = ("category_extremum_gap_value",)
    default_dataset_enabled = True


@register_task
class ChartsThreeDBarCategoryTotalGapValueTask(ChartsThreeDBarGridQueryTask):
    """Compute the gap between totals for two x-axis categories."""

    task_id = "task_charts__bar_3d__category_total_gap_value"
    allowed_query_ids = ("category_total_gap_value",)
    default_dataset_enabled = True


@register_task
class ChartsThreeDBarSeriesTotalGapValueTask(ChartsThreeDBarGridQueryTask):
    """Compute the gap between totals for two series."""

    task_id = "task_charts__bar_3d__series_total_gap_value"
    allowed_query_ids = ("series_total_gap_value",)
    default_dataset_enabled = True


@register_task
class ChartsThreeDBarCategoryThresholdCountTask(ChartsThreeDBarGridQueryTask):
    """Count series within one category whose bars satisfy a threshold."""

    task_id = "task_charts__bar_3d__category_threshold_count"
    allowed_query_ids = ("category_threshold_count",)
    default_dataset_enabled = True


@register_task
class ChartsThreeDBarSeriesThresholdCountTask(ChartsThreeDBarGridQueryTask):
    """Count categories within one series whose bars satisfy a threshold."""

    task_id = "task_charts__bar_3d__series_threshold_count"
    allowed_query_ids = ("series_threshold_count",)
    default_dataset_enabled = True


@register_task
class ChartsThreeDBarPairwiseComparisonCountTask(ChartsThreeDBarGridQueryTask):
    """Count categories where one series exceeds another in a 3D bar chart."""

    task_id = "task_charts__bar_3d__pairwise_comparison_count"
    allowed_query_ids = ("series_comparison_count",)
    default_dataset_enabled = True


__all__ = [
    "ChartsThreeDBarCategoryExtremumGapValueTask",
    "ChartsThreeDBarCategoryThresholdCountTask",
    "ChartsThreeDBarCategoryTotalGapValueTask",
    "ChartsThreeDBarCategoryTotalValueTask",
    "ChartsThreeDBarPairwiseComparisonCountTask",
    "ChartsThreeDBarGridQueryTask",
    "ChartsThreeDBarSeriesCategoryScopeTotalValueTask",
    "ChartsThreeDBarSeriesThresholdCountTask",
    "ChartsThreeDBarSeriesTotalGapValueTask",
]
