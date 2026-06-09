"""Import facade for distribution-style chart dataset builders."""

from __future__ import annotations

from .distribution_boxplot import (
    build_boxplot_dataset_for_variant,
    build_boxplot_median_rank_difference_dataset,
    build_boxplot_paired_median_shift_dataset,
)
from .distribution_chart_config import (
    BoxPlotQueryVariant,
    DensityQueryVariant,
    DistributionChartDefaults,
    HistogramQueryVariant,
)
from .distribution_density import build_density_dataset_for_variant
from .distribution_histogram import build_histogram_dataset_for_variant
from .labeled_chart_common import (
    LabeledChartDefaults,
    projected_mark_annotation,
    resolve_chart_axis_variant,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
)


__all__ = [
    "BoxPlotQueryVariant",
    "DensityQueryVariant",
    "DistributionChartDefaults",
    "HistogramQueryVariant",
    "LabeledChartDefaults",
    "build_boxplot_dataset_for_variant",
    "build_boxplot_median_rank_difference_dataset",
    "build_boxplot_paired_median_shift_dataset",
    "build_density_dataset_for_variant",
    "build_histogram_dataset_for_variant",
    "projected_mark_annotation",
    "resolve_chart_axis_variant",
    "resolve_chart_mark_colors",
    "resolve_chart_render_params_for_task",
]
