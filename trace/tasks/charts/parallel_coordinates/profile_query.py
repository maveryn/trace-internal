"""Public registration facade for parallel-coordinates chart tasks."""

from __future__ import annotations

from ...registry import register_task
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from .profile_common import (
    CONDITION_QUERY_IDS,
    CROSSING_QUERY_IDS,
    DELTA_QUERY_IDS,
    SUPPORTED_QUERY_IDS,
    SUPPORTED_SCENE_VARIANTS,
)
from .profile_task import ChartsParallelCoordinatesProfileTask as _ChartsParallelCoordinatesProfileTask


class ChartsParallelCoordinatesProfileTask(_ChartsParallelCoordinatesProfileTask):
    """Generate parallel-coordinates profile chart questions."""


@register_task
class ChartsParallelCoordinatesAxisConditionCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsParallelCoordinatesProfileTask,
):
    """Count profiles satisfying two axis predicates."""

    task_id = "task_charts__parallel_coords__axis_condition_count"
    allowed_query_ids = CONDITION_QUERY_IDS


@register_task
class ChartsParallelCoordinatesAxisDeltaExtremumLabelTask(
    MergedChartQueryVariantTaskMixin,
    ChartsParallelCoordinatesProfileTask,
):
    """Return the profile with the largest axis-to-axis change."""

    task_id = "task_charts__parallel_coords__axis_delta_extremum_label"
    allowed_query_ids = DELTA_QUERY_IDS


@register_task
class ChartsParallelCoordinatesAllCrossingsBetweenAdjacentAxesTask(
    MergedChartQueryVariantTaskMixin,
    ChartsParallelCoordinatesProfileTask,
):
    """Count all profile-line crossings between a pair of adjacent axes."""

    task_id = "task_charts__parallel_coords__all_crossings_between_adjacent_axes"
    allowed_query_ids = ("all_crossings_between_adjacent_axes",)


@register_task
class ChartsParallelCoordinatesCrossingsInvolvingProfileBetweenAxesTask(
    MergedChartQueryVariantTaskMixin,
    ChartsParallelCoordinatesProfileTask,
):
    """Count crossings involving one named profile between adjacent axes."""

    task_id = "task_charts__parallel_coords__crossings_involving_profile_between_axes"
    allowed_query_ids = ("crossings_involving_profile_between_axes",)


__all__ = [
    "ChartsParallelCoordinatesAllCrossingsBetweenAdjacentAxesTask",
    "ChartsParallelCoordinatesAxisConditionCountTask",
    "ChartsParallelCoordinatesAxisDeltaExtremumLabelTask",
    "ChartsParallelCoordinatesCrossingsInvolvingProfileBetweenAxesTask",
    "ChartsParallelCoordinatesProfileTask",
    "CONDITION_QUERY_IDS",
    "CROSSING_QUERY_IDS",
    "DELTA_QUERY_IDS",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
