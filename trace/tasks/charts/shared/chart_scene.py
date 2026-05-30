"""Compatibility facade for shared chart-scene rendering helpers.

Renderer implementations live in chart-type-specific modules. Keep this module
as the stable import surface for chart tasks and tests.
"""

from __future__ import annotations

from .chart_scene_boxplot import *  # noqa: F403
from .chart_scene_histogram import *  # noqa: F403
from .chart_scene_labeled import *  # noqa: F403
from .chart_scene_multiseries import *  # noqa: F403
from .chart_scene_stacked import render_stacked_chart_scene
from .chart_scene_types import *  # noqa: F403
from .chart_scene_violin import *  # noqa: F403
from .chart_scene_primitives import resolve_chart_render_params, value_axis_render_metadata


__all__ = [
    'BoxPlotSpec',
    'ChartColor',
    'ChartMarkSpec',
    'ChartRenderParams',
    'HistogramBinSpec',
    'MultiSeriesChartMarkSpec',
    'RenderedChartScene',
    'SUPPORTED_CHART_SCENE_VARIANTS',
    'SUPPORTED_COMPOSITION_CHART_SCENE_VARIANTS',
    'SUPPORTED_DISTRIBUTION_CHART_SCENE_VARIANTS',
    'SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS',
    'ViolinPlotSpec',
    'render_boxplot_scene',
    'render_histogram_scene',
    'render_labeled_chart_scene',
    'render_multiseries_chart_scene',
    'render_paired_boxplot_scene',
    'render_violin_scene',
    'resolve_chart_render_params',
    'value_axis_render_metadata',
]
