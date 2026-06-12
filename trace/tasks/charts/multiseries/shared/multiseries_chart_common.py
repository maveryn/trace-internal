"""Import facade for multiseries chart dataset and rendering helpers."""

from __future__ import annotations

from .multiseries_category_total import build_category_total_extremum_label_dataset
from .multiseries_chart_config import (
    MultiseriesChartDefaults,
    SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS,
    build_multiseries_mark_specs,
    projected_category_annotation,
    projected_multiseries_mark_annotation,
    resolve_category_count_bounds,
    resolve_multiseries_chart_colors,
    resolve_series_count_bounds,
    sample_series_labels,
)
from .multiseries_derived_datasets import (
    build_delta_extremum_label_dataset,
    build_ratio_extremum_label_dataset,
)
from .multiseries_pair_datasets import (
    build_pair_equality_label_dataset,
    build_pairwise_comparison_count_dataset,
    build_series_rank_at_category_label_dataset,
)


__all__ = [
    "MultiseriesChartDefaults",
    "SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS",
    "build_category_total_extremum_label_dataset",
    "build_delta_extremum_label_dataset",
    "build_multiseries_mark_specs",
    "build_pair_equality_label_dataset",
    "build_pairwise_comparison_count_dataset",
    "build_ratio_extremum_label_dataset",
    "build_series_rank_at_category_label_dataset",
    "projected_category_annotation",
    "projected_multiseries_mark_annotation",
    "resolve_category_count_bounds",
    "resolve_multiseries_chart_colors",
    "resolve_series_count_bounds",
    "sample_series_labels",
]
