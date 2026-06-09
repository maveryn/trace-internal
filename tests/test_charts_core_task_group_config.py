"""Regression tests for task-group default config loading."""

from __future__ import annotations

import json

import pytest

from trace.core.task_group_config import (
    get_domain_defaults,
    get_task_group_defaults,
    resolve_task_group_section_defaults,
)
from trace.tasks.shared.config_defaults import (
    required_group_default,
    required_group_defaults,
    resolve_optional_int_bounds,
    resolve_required_float_bounds,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from trace.tasks.graph.shared.graph_sampling import SUPPORTED_LAYOUT_VARIANTS


FULL_NODE_LINK_LAYOUT_VARIANTS = set(SUPPORTED_LAYOUT_VARIANTS)


def test_charts_statistics_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "statistics")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["mark_count_min"]) >= 5
    assert int(generation_shared["mark_count_max"]) == 10
    assert int(generation_shared["value_min"]) >= 0
    assert int(generation_shared["value_max"]) == 20
    assert sorted(generation_shared["query_id_weights"].keys()) == [
        "order_statistic_label",
        "order_statistic_value",
    ]
    assert sorted(generation_shared["statistic_kind_weights"].keys()) == [
        "median",
        "nth_highest",
        "nth_lowest",
    ]
    assert sorted(generation_shared["scene_variant_weights"].keys()) == [
        "area",
        "bar",
        "dot_plot",
        "horizontal_bar",
        "line",
        "lollipop",
        "scatter",
    ]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["plot_margin_left_px"]) > 0
    assert int(render_shared["plot_margin_bottom_px"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_statistics_v0"
    assert str(prompt_shared["scene_key"]).strip() == "labeled_chart_statistics"
    assert str(prompt_shared["task_key"]).strip() == "summary_value_query"
    assert str(prompt_shared["object_description_bar"]).strip()
    assert str(prompt_shared["annotation_hint_median"]).strip()
    assert str(prompt_shared["json_example_nth_highest"]).strip()
    assert str(prompt_shared["json_example_answer_only_nth_lowest"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_statistics_summary_query_base",
    )
    positive_task_weights = {
        str(key): float(value)
        for key, value in generation_defaults["query_id_weights"].items()
        if float(value) > 0.0
    }
    assert {
        "order_statistic_value",
        "order_statistic_label",
    } == set(positive_task_weights.keys())
    assert sorted(generation_defaults["statistic_kind_weights"].keys()) == [
        "median",
        "nth_highest",
        "nth_lowest",
    ]
    assert int(generation_defaults["mark_count_min"]) == 15
    assert int(generation_defaults["mark_count_max"]) == 25
    assert int(generation_defaults["rank_n_min"]) == 3
    assert int(generation_defaults["rank_n_max"]) == 8
    assert int(generation_defaults["value_max"]) == 99
    positive_value_scene_weights = {
        str(key): float(value)
        for key, value in generation_defaults["scene_variant_weights"].items()
        if float(value) > 0.0
    }
    assert sorted(positive_value_scene_weights.keys()) == [
        "area",
        "bar",
        "dot_plot",
        "horizontal_bar",
        "line",
        "lollipop",
        "scatter",
    ]
    assert "pie" not in generation_defaults["scene_variant_weights"]
    assert "donut" not in generation_defaults["scene_variant_weights"]
    assert "radar" not in generation_defaults["scene_variant_weights"]
    assert int(rendering_defaults["canvas_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_statistics_v0"
    assert str(prompt_defaults["task_key_value"]).strip() == "summary_value_query"
    assert str(prompt_defaults["task_key_label"]).strip() == "summary_label_query"
    assert str(prompt_defaults["answer_hint_value"]).strip()
    assert str(prompt_defaults["answer_hint_label"]).strip()
    assert str(prompt_defaults["annotation_hint_nth_highest"]).strip()
    assert str(prompt_defaults["annotation_hint_nth_lowest"]).strip()
    assert str(prompt_defaults["annotation_hint_label_nth_highest"]).strip()
    assert str(prompt_defaults["annotation_hint_label_nth_lowest"]).strip()
    assert str(prompt_defaults["json_example_label_median"]).strip()

def test_charts_distribution_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "distribution")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["bin_count_min"]) == 12
    assert int(generation_shared["bin_count_max"]) == 20
    assert int(generation_shared["bin_width_min"]) == 1
    assert int(generation_shared["bin_width_max"]) == 2
    assert int(generation_shared["bin_start_min"]) == 1
    assert int(generation_shared["bin_start_max"]) == 99
    assert int(generation_shared["bin_frequency_min"]) >= 1
    assert int(generation_shared["bin_frequency_max"]) == 24
    assert int(generation_shared["interval_bin_span_min"]) == 8
    assert int(generation_shared["interval_bin_span_max"]) == 16
    assert int(generation_shared["outside_interval_bin_count_min"]) == 6
    assert int(generation_shared["outside_interval_bin_count_max"]) == 12
    assert int(generation_shared["category_count_min"]) == 6
    assert int(generation_shared["category_count_max"]) == 15
    assert sorted(cfg["generation"]["task_overrides"]["charts_distribution_histogram_count_base"]["query_id_weights"].keys()) == [
        "bin_count_between_values",
        "interval_mass",
        "rank_item_bin_label",
    ]
    assert sorted(cfg["generation"]["task_overrides"]["charts_distribution_histogram_count_base"]["interval_relation_weights"].keys()) == [
        "inside",
        "outside",
    ]
    assert sorted(cfg["generation"]["task_overrides"]["charts_distribution_boxplot_label_base"]["query_id_weights"].keys()) == [
        "iqr_extremum_label",
        "median_reference_label",
    ]
    assert sorted(cfg["generation"]["task_overrides"]["charts_distribution_boxplot_label_base"]["median_reference_direction_weights"].keys()) == [
        "above_reference_q3",
        "below_reference_q1",
    ]
    assert sorted(cfg["generation"]["task_overrides"]["charts_distribution_boxplot_label_base"]["extremum_direction_weights"].keys()) == [
        "largest",
        "smallest",
    ]
    assert sorted(cfg["generation"]["task_overrides"]["charts_distribution_violin_label_base"]["query_id_weights"].keys()) == [
        "bimodal_label",
        "highest_mode",
        "lowest_mode",
        "narrowest_support",
        "widest_support",
    ]
    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["plot_margin_bottom_px"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_distribution_v0"
    assert str(prompt_shared["scene_key"]).strip() == "distribution_chart"
    assert str(prompt_shared["task_key"]).strip() == "histogram_count_query"
    assert str(prompt_shared["object_description_histogram"]).strip()
    assert str(prompt_shared["json_example_interval_mass"]).strip()
    assert str(prompt_shared["annotation_hint_interval_mass"]).strip()
    assert str(prompt_shared["json_example_bin_count_between_values"]).strip()

    histogram_generation, histogram_rendering, histogram_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_distribution_histogram_count_base",
    )
    assert {
        "bin_count_between_values",
        "interval_mass",
        "rank_item_bin_label",
    } == set(histogram_generation["query_id_weights"].keys())
    assert {"inside", "outside"} == set(histogram_generation["interval_relation_weights"].keys())
    assert int(histogram_rendering["canvas_width"]) > 0
    assert str(histogram_prompt["bundle_id"]).strip() == "charts_distribution_v0"
    assert str(histogram_prompt["object_description_histogram"]).strip()

    boxplot_generation, _, boxplot_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_distribution_boxplot_label_base",
    )
    assert int(boxplot_generation["category_count_min"]) == 6
    assert int(boxplot_generation["category_count_max"]) == 15
    assert {
        "median_reference_label",
        "iqr_extremum_label",
    }.issubset(set(boxplot_generation["query_id_weights"].keys()))
    assert int(boxplot_generation["query_id_overrides"]["iqr_extremum_label"]["iqr_winner_gap_min"]) == 1
    assert int(boxplot_generation["query_id_overrides"]["iqr_extremum_label"]["iqr_winner_gap_max"]) == 1
    assert str(boxplot_prompt["task_key"]).strip() == "boxplot_label_query"
    assert str(boxplot_prompt["answer_hint"]).strip()
    assert str(boxplot_prompt["annotation_hint_iqr_extremum_label"]).strip()

    violin_generation, violin_rendering, violin_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_distribution_violin_label_base",
    )
    assert int(violin_generation["violin_category_count_min"]) == 5
    assert int(violin_generation["violin_category_count_max"]) == 8
    assert {
        "highest_mode",
        "lowest_mode",
        "bimodal_label",
        "widest_support",
        "narrowest_support",
    } == set(violin_generation["query_id_weights"].keys())
    assert int(violin_rendering["canvas_width"]) > 0
    assert str(violin_prompt["task_key"]).strip() == "violin_label_query"
    assert str(violin_prompt["object_description_violin"]).strip()

    histogram_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="charts_distribution_histogram_count_base",
    )
    boxplot_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="charts_distribution_boxplot_label_base",
    )
    violin_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="charts_distribution_violin_label_base",
    )
    for complexity_defaults in (histogram_complexity, boxplot_complexity, violin_complexity):
        assert sorted(complexity_defaults["criteria_weights"].keys()) == [
            "reasoning_load",
            "scene_variant_load",
            "visual_scan",
        ]

def test_charts_trend_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "trend")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["mark_count_min"]) == 6
    assert int(generation_shared["mark_count_max"]) == 10
    assert int(generation_shared["value_min"]) >= 1
    assert int(generation_shared["value_max"]) == 20
    assert "query_id_weights" not in generation_shared
    assert "scene_variant_weights" not in generation_shared

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["plot_margin_left_px"]) > 0
    assert int(render_shared["plot_margin_bottom_px"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_trend_v0"
    assert str(prompt_shared["scene_key"]).strip() == "ordered_chart_trend"
    assert str(prompt_shared["task_key"]).strip() == "trend_value_query"
    assert str(prompt_shared["object_description_horizontal_bar"]).strip()
    assert str(prompt_shared["annotation_hint_turning_point_count"]).strip()
    assert str(prompt_shared["json_example_longest_monotone_streak"]).strip()
    assert str(prompt_shared["json_example_answer_only_turning_point_count"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_trend_value_base",
    )
    assert int(generation_defaults["structure_mark_count_min"]) == 6
    assert int(generation_defaults["structure_mark_count_max"]) == 10
    assert int(generation_defaults["interval_mark_count_min"]) == 8
    assert int(generation_defaults["interval_mark_count_max"]) == 14
    assert sorted(generation_defaults["query_id_weights"].keys()) == [
        "endpoint_change_value",
        "interval_rate_value",
        "longest_monotone_streak",
        "threshold_crossing",
        "turning_point_count",
    ]
    assert sorted(generation_defaults["turning_point_type_weights"].keys()) == ["peak", "trough"]
    assert sorted(generation_defaults["streak_direction_weights"].keys()) == ["decreasing", "increasing"]
    assert sorted(generation_defaults["endpoint_change_kind_weights"].keys()) == ["absolute", "percent", "signed"]
    assert sorted(generation_defaults["crossing_mode_weights"].keys()) == ["linear_projection", "observed"]
    assert sorted(generation_defaults["crossing_direction_weights"].keys()) == ["above", "below"]
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == [
        "area",
        "bar",
        "dot_plot",
        "horizontal_bar",
        "line",
        "lollipop",
    ]
    assert int(rendering_defaults["canvas_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_trend_v0"
    assert str(prompt_defaults["task_key"]).strip() == "trend_value_query"
    assert str(prompt_defaults["threshold_task_key"]).strip() == "threshold_crossing_label_query"
    assert str(prompt_defaults["annotation_hint_endpoint_change_value"]).strip()
    assert str(prompt_defaults["annotation_hint_first_crosses_above_threshold"]).strip()
    assert str(prompt_defaults["json_example_interval_rate_value"]).strip()

    interval_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="charts_trend_value_base",
    )
    assert sorted(interval_complexity["criteria_weights"].keys()) == [
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    ]

    complexity_defaults = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="charts_trend_value_base",
    )
    assert sorted(complexity_defaults["criteria_weights"].keys()) == [
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    ]

def test_charts_multiseries_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "multiseries")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["category_count_min"]) == 12
    assert int(generation_shared["category_count_max"]) == 18
    assert int(generation_shared["series_count_min"]) == 3
    assert int(generation_shared["series_count_max"]) == 5
    assert int(generation_shared["target_answer_min"]) == 0
    assert int(generation_shared["target_answer_max"]) == 8
    comparison_generation = resolve_task_group_section_defaults(
        cfg,
        "generation",
        task_id="charts_multiseries_comparison_query_base",
    )
    assert int(comparison_generation["delta_category_count_min"]) == 10
    assert int(comparison_generation["delta_category_count_max"]) == 15
    assert int(comparison_generation["delta_series_count_min"]) == 3
    assert int(comparison_generation["delta_series_count_max"]) == 4
    assert int(comparison_generation["delta_value_max"]) == 30
    assert int(comparison_generation["ratio_category_count_min"]) == 5
    assert int(comparison_generation["ratio_category_count_max"]) == 10
    assert int(comparison_generation["ratio_series_count_min"]) == 3
    assert int(comparison_generation["ratio_series_count_max"]) == 4
    assert int(comparison_generation["ratio_value_max"]) == 80
    assert int(comparison_generation["rank_min"]) == 1
    assert int(comparison_generation["rank_max"]) == 3
    assert int(comparison_generation["derived_score_min"]) == 4
    assert int(comparison_generation["derived_score_max"]) == 24
    assert int(comparison_generation["share_percent_min"]) == 10
    assert int(comparison_generation["share_percent_max"]) == 75
    assert int(comparison_generation["pair_ratio_percent_min"]) == 40
    assert int(comparison_generation["pair_ratio_percent_max"]) == 260
    assert int(comparison_generation["category_total_category_count_min"]) == 6
    assert int(comparison_generation["category_total_category_count_max"]) == 10
    assert int(comparison_generation["category_total_series_count_min"]) == 3
    assert int(comparison_generation["category_total_series_count_max"]) == 5
    assert int(comparison_generation["category_total_rank_min"]) == 1
    assert int(comparison_generation["category_total_rank_max"]) == 2
    assert int(comparison_generation["category_count_min"]) == 8
    assert int(comparison_generation["category_count_max"]) == 12
    assert int(comparison_generation["series_count_min"]) == 4
    assert int(comparison_generation["series_count_max"]) == 5
    assert int(comparison_generation["filtered_category_count_min"]) == 3
    assert int(comparison_generation["filtered_category_count_max"]) == 6
    assert int(comparison_generation["target_gap_min"]) == 2
    assert int(comparison_generation["target_gap_max"]) == 18
    assert sorted(
        key for key, weight in comparison_generation["query_id_weights"].items() if float(weight) > 0.0
    ) == [
        "category_total_extremum_label",
        "conditional_gap_aggregate_value",
        "conditional_gap_extremum_value",
        "pair_equality_label",
        "ranked_change_extremum",
        "ranked_ratio_extremum",
        "series_comparison_count",
        "series_rank_at_category_label",
    ]
    assert sorted(comparison_generation["conditional_gap_aggregate_kind_weights"].keys()) == [
        "mean",
        "range",
    ]
    assert sorted(comparison_generation["change_measure_weights"].keys()) == [
        "absolute_gap",
        "directional_change",
    ]
    assert sorted(comparison_generation["ratio_measure_weights"].keys()) == [
        "pair_ratio",
        "series_share",
    ]
    assert sorted(comparison_generation["change_direction_weights"].keys()) == [
        "decrease",
        "increase",
    ]
    assert sorted(comparison_generation["extremum_direction_weights"].keys()) == [
        "largest",
        "smallest",
    ]
    assert sorted(comparison_generation["condition_comparison_weights"].keys()) == [
        "greater_than",
        "less_than",
    ]
    assert sorted(generation_shared["scene_variant_weights"].keys()) == [
        "grouped_bar",
        "grouped_horizontal_bar",
        "grouped_lollipop",
        "multi_line",
    ]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["plot_margin_left_px"]) > 0
    assert int(render_shared["plot_margin_bottom_px"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_multiseries_v0"
    assert str(prompt_shared["scene_key"]).strip() == "multiseries_chart_comparison"
    assert str(prompt_shared["object_description_grouped_bar"]).strip()
    assert str(prompt_shared["object_description_grouped_horizontal_bar"]).strip()
    assert str(prompt_shared["object_description_multi_line"]).strip()
    assert str(prompt_shared["object_description_grouped_lollipop"]).strip()
    assert str(prompt_shared["json_example_series_comparison_count"]).strip()
    comparison_prompt = resolve_task_group_section_defaults(
        cfg,
        "prompt",
        task_id="charts_multiseries_comparison_query_base",
    )
    assert str(comparison_prompt["task_key_pairwise"]).strip() == "pairwise_comparison_count_query"
    assert str(comparison_prompt["task_key_delta"]).strip() == "delta_extremum_label_query"
    assert str(comparison_prompt["task_key_ratio"]).strip() == "ratio_extremum_label_query"
    assert str(comparison_prompt["task_key_category_total"]).strip() == "category_total_extremum_label_query"
    assert str(comparison_prompt["answer_hint_count"]).strip()
    assert str(comparison_prompt["answer_hint_label"]).strip()
    assert str(comparison_prompt["annotation_hint_ranked_directional_change"]).strip()
    assert str(comparison_prompt["json_example_ranked_absolute_gap"]).strip()
    assert str(comparison_prompt["annotation_hint_ranked_series_share"]).strip()
    assert str(comparison_prompt["json_example_ranked_pair_ratio"]).strip()
    assert str(comparison_prompt["task_key_conditional_gap"]).strip() == "conditional_gap_value_query"
    assert str(comparison_prompt["answer_hint_conditional_gap_value"]).strip()
    assert str(comparison_prompt["annotation_hint_conditional_gap_value"]).strip()
    assert str(comparison_prompt["json_example_conditional_gap_value"]).strip()
    assert str(comparison_prompt["annotation_hint_category_total_extremum"]).strip()
    assert str(comparison_prompt["json_example_category_total_extremum"]).strip()

    comparison_complexity_defaults = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="charts_multiseries_comparison_query_base",
    )
    assert sorted(comparison_complexity_defaults["criteria_weights"].keys()) == [
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    ]

def test_charts_counting_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "counting")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["mark_count_min"]) == 8
    assert int(generation_shared["mark_count_max"]) == 20
    assert int(generation_shared["value_max"]) == 99
    assert int(generation_shared["target_answer_min"]) == 0
    assert int(generation_shared["target_answer_max"]) == 20
    assert sorted(generation_shared["query_id_weights"].keys()) == [
        "in_interval",
        "threshold_count",
    ]
    assert sorted(generation_shared["comparison_weights"].keys()) == [
        "greater_than",
        "less_than",
    ]
    assert sorted(generation_shared["scene_variant_weights"].keys()) == [
        "area",
        "bar",
        "dot_plot",
        "horizontal_bar",
        "line",
        "lollipop",
        "scatter",
    ]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_counting_v0"
    assert str(prompt_shared["scene_key"]).strip() == "labeled_chart_counting"
    assert str(prompt_shared["task_key"]).strip() == "value_count_query"
    assert str(prompt_shared["object_description_bar"]).strip()
    assert str(prompt_shared["annotation_hint_in_interval"]).strip()
    assert str(prompt_shared["json_example_threshold_count"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_counting_value_count_base",
    )
    assert int(generation_defaults["mark_count_min"]) == 8
    assert int(generation_defaults["mark_count_max"]) == 20
    assert int(generation_defaults["target_answer_max"]) == 20
    assert int(rendering_defaults["canvas_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_counting_v0"

    complexity_defaults = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="charts_counting_value_count_base",
    )
    assert sorted(complexity_defaults["criteria_weights"].keys()) == [
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    ]
