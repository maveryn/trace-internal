"""Public registration facade for synthetic 3D chart panel tasks."""

from __future__ import annotations

from ...registry import register_task
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin
from .panel_common import SUPPORTED_QUERY_IDS, SUPPORTED_SCENE_VARIANTS
from .panel_task import ChartsThreeDPanelQueryTask as _ChartsThreeDPanelQueryTask


class ChartsThreeDPanelQueryTask(_ChartsThreeDPanelQueryTask):
    """Shared generator for synthetic 3D chart panel questions."""


@register_task
class ChartsThreeDReferenceNearestLabelTask(FixedChartQueryVariantTaskMixin, ChartsThreeDPanelQueryTask):
    """Return the 3D point label nearest to a target axis value."""

    task_id = "task_charts__surface_3d__reference_nearest_label"
    fixed_query_id = "reference_nearest_label"


@register_task
class ChartsThreeDSurfaceExtremumLabelTask(FixedChartQueryVariantTaskMixin, ChartsThreeDPanelQueryTask):
    """Return the surface-grid category with an extremal value under a slice."""

    task_id = "task_charts__surface_3d__surface_extremum_label"
    fixed_query_id = "surface_extremum_label"


@register_task
class ChartsThreeDSeriesTrendLabelTask(FixedChartQueryVariantTaskMixin, ChartsThreeDPanelQueryTask):
    """Return the 3D series label with the requested trend extremum."""

    task_id = "task_charts__surface_3d__series_trend_label"
    fixed_query_id = "series_trend_label"


@register_task
class ChartsThreeDPanelVariationLabelTask(FixedChartQueryVariantTaskMixin, ChartsThreeDPanelQueryTask):
    """Return the small-multiple 3D panel with the largest vertical range."""

    task_id = "task_charts__surface_3d__panel_variation_label"
    fixed_query_id = "panel_variation_label"


__all__ = [
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
    "ChartsThreeDPanelQueryTask",
    "ChartsThreeDPanelVariationLabelTask",
    "ChartsThreeDReferenceNearestLabelTask",
    "ChartsThreeDSeriesTrendLabelTask",
    "ChartsThreeDSurfaceExtremumLabelTask",
]
