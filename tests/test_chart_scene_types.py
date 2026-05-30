from __future__ import annotations

from trace.tasks.charts.shared import chart_scene, chart_scene_types


def test_chart_scene_reexports_public_spec_types() -> None:
    assert chart_scene.ChartMarkSpec is chart_scene_types.ChartMarkSpec
    assert chart_scene.MultiSeriesChartMarkSpec is chart_scene_types.MultiSeriesChartMarkSpec
    assert chart_scene.HistogramBinSpec is chart_scene_types.HistogramBinSpec
    assert chart_scene.BoxPlotSpec is chart_scene_types.BoxPlotSpec
    assert chart_scene.ViolinPlotSpec is chart_scene_types.ViolinPlotSpec
    assert chart_scene.ChartRenderParams is chart_scene_types.ChartRenderParams
    assert chart_scene.RenderedChartScene is chart_scene_types.RenderedChartScene


def test_chart_scene_reexports_public_variant_constants() -> None:
    assert chart_scene.SUPPORTED_CHART_SCENE_VARIANTS == chart_scene_types.SUPPORTED_CHART_SCENE_VARIANTS
    assert (
        chart_scene.SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS
        == chart_scene_types.SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS
    )
    assert (
        chart_scene.SUPPORTED_COMPOSITION_CHART_SCENE_VARIANTS
        == chart_scene_types.SUPPORTED_COMPOSITION_CHART_SCENE_VARIANTS
    )
    assert (
        chart_scene.SUPPORTED_DISTRIBUTION_CHART_SCENE_VARIANTS
        == chart_scene_types.SUPPORTED_DISTRIBUTION_CHART_SCENE_VARIANTS
    )


def test_chart_scene_star_export_includes_type_module_surface() -> None:
    for name in chart_scene_types.__all__:
        assert name in chart_scene.__all__
