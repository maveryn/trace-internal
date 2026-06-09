"""Public exports for multiseries chart comparison tasks."""

from __future__ import annotations

from typing import Any, Dict

from ...base import TaskOutput
from ...registry import register_task
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from .comparison_common import TASK_ID, _SUPPORTED_RATIO_MEASURES
from .comparison_task import _ChartsMultiseriesComparisonQueryTaskBase


class ChartsMultiseriesComparisonQueryTask(_ChartsMultiseriesComparisonQueryTaskBase):
    """Answer label, count, and aggregate comparison queries over multiseries charts."""

    task_id = TASK_ID


class _ForcedRatioMeasureTaskMixin:
    """Force one ratio-measure branch within ranked ratio extremum tasks."""

    fixed_ratio_measure: str

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        requested_ratio_measure = params.get("ratio_measure")
        if requested_ratio_measure is not None and str(requested_ratio_measure) != str(self.fixed_ratio_measure):
            raise ValueError(
                "public multiseries ratio task ratio_measure must match "
                f"'{self.fixed_ratio_measure}' (got: {requested_ratio_measure})"
            )
        forced_params = dict(params)
        forced_params["ratio_measure"] = str(self.fixed_ratio_measure)
        forced_params["ratio_measure_weights"] = {
            str(value): (1.0 if str(value) == str(self.fixed_ratio_measure) else 0.0)
            for value in _SUPPORTED_RATIO_MEASURES
        }
        return super().generate(  # type: ignore[misc]
            int(instance_seed),
            params=forced_params,
            max_attempts=int(max_attempts),
        )


@register_task
class ChartsMultiseriesRankedChangeExtremumTask(
    MergedChartQueryVariantTaskMixin,
    ChartsMultiseriesComparisonQueryTask,
):
    """Return the category label at a ranked change or absolute-gap extremum."""

    task_id = "task_charts__multiseries__ranked_change_extremum_label"
    allowed_query_ids = ("ranked_change_extremum",)


@register_task
class ChartsMultiseriesRankedPairRatioExtremumTask(
    _ForcedRatioMeasureTaskMixin,
    MergedChartQueryVariantTaskMixin,
    ChartsMultiseriesComparisonQueryTask,
):
    """Return the category label at a ranked pair-ratio extremum."""

    task_id = "task_charts__multiseries__ranked_pair_ratio_extremum_label"
    allowed_query_ids = ("ranked_ratio_extremum",)
    fixed_ratio_measure = "pair_ratio"


@register_task
class ChartsMultiseriesRankedSeriesShareExtremumTask(
    _ForcedRatioMeasureTaskMixin,
    MergedChartQueryVariantTaskMixin,
    ChartsMultiseriesComparisonQueryTask,
):
    """Return the category label at a ranked series-share extremum."""

    task_id = "task_charts__multiseries__ranked_series_share_extremum_label"
    allowed_query_ids = ("ranked_ratio_extremum",)
    fixed_ratio_measure = "series_share"


@register_task
class ChartsMultiseriesSeriesComparisonCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMultiseriesComparisonQueryTask,
):
    """Count categories satisfying a pairwise series comparison."""

    task_id = "task_charts__multiseries__series_comparison_count"
    fixed_query_id = "series_comparison_count"


@register_task
class ChartsMultiseriesPairEqualityLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMultiseriesComparisonQueryTask,
):
    """Return the category label where two series have exactly equal values."""

    task_id = "task_charts__multiseries__pair_equality_label"
    fixed_query_id = "pair_equality_label"


@register_task
class ChartsMultiseriesSeriesRankAtCategoryLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMultiseriesComparisonQueryTask,
):
    """Return the ranked series label within one queried category."""

    task_id = "task_charts__multiseries__series_rank_at_category_label"
    fixed_query_id = "series_rank_at_category_label"


@register_task
class ChartsMultiseriesCategoryTotalExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMultiseriesComparisonQueryTask,
):
    """Return a category label ranked by total across all series."""

    task_id = "task_charts__multiseries__category_total_extremum_label"
    fixed_query_id = "category_total_extremum_label"



__all__ = [
    "ChartsMultiseriesComparisonQueryTask",
    "ChartsMultiseriesCategoryTotalExtremumLabelTask",
    "ChartsMultiseriesPairEqualityLabelTask",
    "ChartsMultiseriesRankedChangeExtremumTask",
    "ChartsMultiseriesRankedPairRatioExtremumTask",
    "ChartsMultiseriesRankedSeriesShareExtremumTask",
    "ChartsMultiseriesSeriesComparisonCountTask",
    "ChartsMultiseriesSeriesRankAtCategoryLabelTask",
]
