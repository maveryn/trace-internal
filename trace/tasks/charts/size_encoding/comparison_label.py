"""Public registration facade for size-encoded chart comparison tasks."""

from __future__ import annotations

from ...registry import register_task
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin
from .comparison_label_common import SUPPORTED_QUERY_IDS, SUPPORTED_SCENE_VARIANTS
from .comparison_label_task import ChartsSizeEncodingComparisonLabelTask as _ChartsSizeEncodingComparisonLabelTask


class ChartsSizeEncodingComparisonLabelTask(_ChartsSizeEncodingComparisonLabelTask):
    """Answer comparative label queries on size-encoded charts."""


@register_task
class ChartsSizeEncodingFilteredItemExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsSizeEncodingComparisonLabelTask,
):
    """Return the size-encoded item label with an extremal value inside a filter."""

    task_id = "task_charts__size_encoding__filtered_item_extremum_label"
    fixed_query_id = "filtered_item_extremum_label"


@register_task
class ChartsSizeEncodingReferenceSizeNeighborLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsSizeEncodingComparisonLabelTask,
):
    """Return the size neighbor of a reference item."""

    task_id = "task_charts__size_encoding__reference_size_neighbor_label"
    fixed_query_id = "reference_size_neighbor_label"


@register_task
class ChartsSizeEncodingCategoryTotalExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsSizeEncodingComparisonLabelTask,
):
    """Return the category label with an extremal total encoded size."""

    task_id = "task_charts__size_encoding__category_total_extremum_label"
    fixed_query_id = "category_total_extremum_label"


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "SUPPORTED_SCENE_VARIANTS",
    "ChartsSizeEncodingCategoryTotalExtremumLabelTask",
    "ChartsSizeEncodingComparisonLabelTask",
    "ChartsSizeEncodingFilteredItemExtremumLabelTask",
    "ChartsSizeEncodingReferenceSizeNeighborLabelTask",
]
