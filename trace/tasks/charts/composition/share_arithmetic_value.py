"""Public task registrations for part-whole composition chart tasks."""

from __future__ import annotations

from ...registry import register_task
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from .share_arithmetic_common import SUPPORTED_QUERY_IDS, SUPPORTED_SCENE_VARIANTS, TASK_ID
from .share_arithmetic_task import ChartsCompositionShareArithmeticValueTask

@register_task
class ChartsCompositionChartContiguousOrderSumTask(
    MergedChartQueryVariantTaskMixin,
    ChartsCompositionShareArithmeticValueTask,
):
    """Compute the combined share over a contiguous chart-order segment."""

    task_id = "task_charts__part_whole__contiguous_chart_order_sum"
    allowed_query_ids = (
        "contiguous_chart_order_sum",
    )


@register_task
class ChartsCompositionChartPositionalSegmentShareSumTask(
    MergedChartQueryVariantTaskMixin,
    ChartsCompositionShareArithmeticValueTask,
):
    """Compute the combined share for positional chart segments."""

    task_id = "task_charts__part_whole__positional_segment_share_sum"
    allowed_query_ids = (
        "positional_segment_share_sum",
    )


@register_task
class ChartsCompositionChartOrderShareToCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsCompositionShareArithmeticValueTask,
):
    """Convert chart-order share into an item count."""

    task_id = "task_charts__part_whole__chart_order_share_to_count"
    allowed_query_ids = (
        "chart_order_share_to_count",
    )


@register_task
class ChartsCompositionChartSectorShareToAngleTask(
    MergedChartQueryVariantTaskMixin,
    ChartsCompositionShareArithmeticValueTask,
):
    """Convert a chart sector share into degrees."""

    task_id = "task_charts__part_whole__sector_share_to_angle"
    allowed_query_ids = (
        "sector_share_to_angle",
    )


@register_task
class ChartsCompositionSubsetDenominatorShareValueTask(
    MergedChartQueryVariantTaskMixin,
    ChartsCompositionShareArithmeticValueTask,
):
    """Compute one category share after redefining the denominator to a visible subset."""

    task_id = "task_charts__part_whole__subset_denominator_share_value"
    allowed_query_ids = (
        "subset_denominator_share_value",
    )


@register_task
class ChartsCompositionChartAdjacentTransferGapValueTask(
    MergedChartQueryVariantTaskMixin,
    ChartsCompositionShareArithmeticValueTask,
):
    """Compute a transfer gap after choosing an adjacent chart-order target."""

    task_id = "task_charts__part_whole__adjacent_transfer_gap_value"
    allowed_query_ids = ("chart_order_adjacent_transfer_gap",)


__all__ = [
    "ChartsCompositionChartAdjacentTransferGapValueTask",
    "ChartsCompositionChartContiguousOrderSumTask",
    "ChartsCompositionChartOrderShareToCountTask",
    "ChartsCompositionChartPositionalSegmentShareSumTask",
    "ChartsCompositionChartSectorShareToAngleTask",
    "ChartsCompositionSubsetDenominatorShareValueTask",
    "ChartsCompositionShareArithmeticValueTask",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
