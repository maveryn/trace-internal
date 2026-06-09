"""Public exports for annotated matrix-cell chart tasks."""

from __future__ import annotations

from ...registry import register_task
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from .cell_common import SUPPORTED_QUERY_IDS, SUPPORTED_SCENE_VARIANTS, TASK_ID
from .cell_task import ChartsMatrixCellQueryTask as _ChartsMatrixCellQueryTaskBase


class ChartsMatrixCellQueryTask(_ChartsMatrixCellQueryTaskBase):
    """Answer questions over printed values in annotated matrix charts."""

    task_id = TASK_ID


@register_task
class ChartsMatrixAxisExtremumLabelTask(MergedChartQueryVariantTaskMixin, ChartsMatrixCellQueryTask):
    """Return a matrix row/column label from extremum-style cell queries."""

    task_id = "task_charts__matrix__axis_extremum_label"
    allowed_query_ids = ("axis_extremum_label",)
    supports_unanswerable = True


@register_task
class ChartsMatrixOffDiagonalConfusionLabelTask(MergedChartQueryVariantTaskMixin, ChartsMatrixCellQueryTask):
    """Return the label selected by an off-diagonal confusion cell query."""

    task_id = "task_charts__matrix__off_diagonal_confusion_label"
    allowed_query_ids = ("off_diagonal_confusion_label",)
    supports_unanswerable = True


@register_task
class ChartsMatrixThresholdCellCountTask(FixedChartQueryVariantTaskMixin, ChartsMatrixCellQueryTask):
    """Count matrix cells satisfying a threshold condition."""

    task_id = "task_charts__matrix__threshold_cell_count"
    fixed_query_id = "threshold_cell_count"


__all__ = [
    "ChartsMatrixAxisExtremumLabelTask",
    "ChartsMatrixCellQueryTask",
    "ChartsMatrixOffDiagonalConfusionLabelTask",
    "ChartsMatrixThresholdCellCountTask",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
