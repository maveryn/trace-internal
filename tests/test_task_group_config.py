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


def test_geometry_measurement_defaults_loaded() -> None:
    cfg = get_task_group_defaults("geometry", "measurement")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_size_min"]) > 0
    assert int(render_shared["canvas_size_max"]) >= int(render_shared["canvas_size_min"])
    assert int(render_shared["graph_cells_min"]) > 0
    assert int(render_shared["graph_cells_max"]) >= int(render_shared["graph_cells_min"])
    assert int(render_shared["line_width_min"]) >= 1
    assert int(render_shared["line_width_max"]) >= int(render_shared["line_width_min"])
    assert int(render_shared["label_stroke_width_min"]) >= 1
    assert int(render_shared["label_stroke_width_max"]) >= int(render_shared["label_stroke_width_min"])

    generation_overrides = cfg["generation"]["task_overrides"]
    assert "source_geometry_measurement_angle" in generation_overrides
    assert int(cfg["generation"]["shared"]["answer_min"]) >= 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip()
    assert str(prompt_shared["scene_key"]).strip()
    assert str(prompt_shared["task_key"]).strip()
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "visual_scan": 0.20,
        "measurement_precision": 0.50,
        "ambiguity": 0.25,
        "output_burden": 0.05,
    }

    angle_generation, angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_measurement_angle",
    )
    for key in ("min_angle", "max_angle", "angle_step"):
        assert key in angle_generation
    assert int(angle_generation["max_angle"]) >= int(angle_generation["min_angle"])
    assert int(angle_generation["angle_step"]) > 0
    assert int(angle_rendering["line_width"]) > 0
    assert str(angle_prompt["evidence_hint"]).strip()
    assert str(angle_prompt["answer_hint"]).strip()
    assert str(angle_prompt["json_example"]).strip()
    assert str(angle_prompt["json_example_answer_only"]).strip()

    area_generation, area_rendering, area_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_measurement_area",
    )
    assert sorted(area_generation["variant_weights"].keys()) == ["ellipse", "quadrilateral", "triangle"]
    assert bool(area_generation["balanced_variant_sampling"]) is True
    assert bool(area_generation["ellipse_allow_circle"]) is True
    assert int(area_rendering["line_width"]) > 0
    assert str(area_prompt["question_text_polygon"]).strip()
    assert str(area_prompt["question_text_ellipse"]).strip()
    assert str(area_prompt["evidence_hint_polygon"]).strip()
    assert str(area_prompt["evidence_hint_ellipse"]).strip()
    assert str(area_prompt["answer_hint_integer"]).strip()
    assert str(area_prompt["answer_hint_pi"]).strip()
    assert str(area_prompt["json_example_triangle"]).strip()
    assert str(area_prompt["json_example_quadrilateral"]).strip()
    assert str(area_prompt["json_example_ellipse"]).strip()
    assert str(area_prompt["json_example_integer"]).strip()
    assert str(area_prompt["json_example_pi"]).strip()
    assert str(area_prompt["json_example_answer_only_integer"]).strip()
    assert str(area_prompt["json_example_answer_only_pi"]).strip()

    perim_generation, perim_rendering, perim_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_measurement_perimeter",
    )
    assert sorted(perim_generation["variant_weights"].keys()) == ["circle", "quadrilateral", "triangle"]
    assert bool(perim_generation["balanced_variant_sampling"]) is True
    assert int(perim_generation["circle_radius_min"]) >= 1
    assert int(perim_generation["circle_radius_max"]) >= int(perim_generation["circle_radius_min"])
    assert int(perim_rendering["line_width"]) > 0
    assert str(perim_prompt["question_text_polygon"]).strip()
    assert str(perim_prompt["question_text_circle"]).strip()
    assert str(perim_prompt["evidence_hint_polygon"]).strip()
    assert str(perim_prompt["evidence_hint_circle"]).strip()
    assert str(perim_prompt["answer_hint_integer"]).strip()
    assert str(perim_prompt["answer_hint_pi"]).strip()
    assert str(perim_prompt["json_example_triangle"]).strip()
    assert str(perim_prompt["json_example_quadrilateral"]).strip()
    assert str(perim_prompt["json_example_circle"]).strip()
    assert str(perim_prompt["json_example_integer"]).strip()
    assert str(perim_prompt["json_example_pi"]).strip()
    assert str(perim_prompt["json_example_answer_only_integer"]).strip()
    assert str(perim_prompt["json_example_answer_only_pi"]).strip()

    length_generation, length_rendering, length_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_measurement_length",
    )
    assert sorted(length_generation["variant_weights"].keys()) == [
        "circle_diameter",
        "circle_radius",
        "ellipse_major_axis",
        "ellipse_minor_axis",
        "pentagon",
        "quadrilateral",
        "segment",
        "triangle",
    ]
    assert bool(length_generation["balanced_variant_sampling"]) is True
    assert int(length_generation["answer_min"]) <= int(length_generation["answer_max"])
    assert int(length_generation["segment_length_min"]) >= 1
    assert int(length_generation["segment_length_max"]) >= int(length_generation["segment_length_min"])
    assert int(length_rendering["line_width"]) > 0
    assert str(length_prompt["question_template_segment"]).strip()
    assert str(length_prompt["question_template_polygon_side"]).strip()
    assert str(length_prompt["question_text_circle_radius"]).strip()
    assert str(length_prompt["question_text_circle_diameter"]).strip()
    assert str(length_prompt["question_text_ellipse_major_axis"]).strip()
    assert str(length_prompt["question_text_ellipse_minor_axis"]).strip()
    assert str(length_prompt["evidence_hint_segment"]).strip()
    assert str(length_prompt["evidence_hint_polygon_side"]).strip()
    assert str(length_prompt["evidence_hint_circle_center"]).strip()
    assert str(length_prompt["evidence_hint_ellipse_axis"]).strip()
    assert str(length_prompt["answer_hint_integer"]).strip()
    assert str(length_prompt["json_example_segment_integer"]).strip()
    assert str(length_prompt["json_example_polygon_side_integer"]).strip()
    assert str(length_prompt["json_example_circle_radius_integer"]).strip()
    assert str(length_prompt["json_example_circle_diameter_integer"]).strip()
    assert str(length_prompt["json_example_ellipse_major_axis_integer"]).strip()
    assert str(length_prompt["json_example_ellipse_minor_axis_integer"]).strip()
    assert str(length_prompt["json_example_integer"]).strip()
    assert str(length_prompt["json_example_answer_only_integer"]).strip()

    slope_generation, slope_rendering, slope_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_measurement_slope",
    )
    assert int(slope_generation["slope_tenths_min"]) < 0
    assert int(slope_generation["slope_tenths_max"]) > 0
    assert bool(slope_generation["balanced_sampling"]) is True
    assert int(slope_rendering["line_width"]) > 0
    assert str(slope_prompt["object_description"]).strip()
    assert str(slope_prompt["question_text"]).strip()
    assert str(slope_prompt["evidence_hint"]).strip()
    assert str(slope_prompt["answer_hint"]).strip()
    assert str(slope_prompt["json_example"]).strip()
    assert str(slope_prompt["json_example_answer_only"]).strip()


def test_charts_statistics_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "statistics")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["mark_count_min"]) >= 5
    assert int(generation_shared["mark_count_max"]) == 10
    assert int(generation_shared["value_min"]) >= 0
    assert int(generation_shared["value_max"]) == 20
    assert sorted(generation_shared["query_variant_weights"].keys()) == [
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
    assert str(prompt_shared["evidence_hint_median"]).strip()
    assert str(prompt_shared["json_example_nth_highest"]).strip()
    assert str(prompt_shared["json_example_answer_only_nth_lowest"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_statistics_summary_query_base",
    )
    positive_task_weights = {
        str(key): float(value)
        for key, value in generation_defaults["query_variant_weights"].items()
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
    assert str(prompt_defaults["evidence_hint_nth_highest"]).strip()
    assert str(prompt_defaults["evidence_hint_nth_lowest"]).strip()
    assert str(prompt_defaults["evidence_hint_label_nth_highest"]).strip()
    assert str(prompt_defaults["evidence_hint_label_nth_lowest"]).strip()
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
    assert sorted(cfg["generation"]["task_overrides"]["charts_distribution_histogram_count_base"]["query_variant_weights"].keys()) == [
        "bin_count_between_values",
        "interval_mass",
        "rank_item_bin_label",
    ]
    assert sorted(cfg["generation"]["task_overrides"]["charts_distribution_histogram_count_base"]["interval_relation_weights"].keys()) == [
        "inside",
        "outside",
    ]
    assert sorted(cfg["generation"]["task_overrides"]["charts_distribution_boxplot_label_base"]["query_variant_weights"].keys()) == [
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
    assert sorted(cfg["generation"]["task_overrides"]["charts_distribution_violin_label_base"]["query_variant_weights"].keys()) == [
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
    assert str(prompt_shared["evidence_hint_interval_mass"]).strip()
    assert str(prompt_shared["json_example_bin_count_between_values"]).strip()

    histogram_generation, histogram_rendering, histogram_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_distribution_histogram_count_base",
    )
    assert {
        "bin_count_between_values",
        "interval_mass",
        "rank_item_bin_label",
    } == set(histogram_generation["query_variant_weights"].keys())
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
    }.issubset(set(boxplot_generation["query_variant_weights"].keys()))
    assert int(boxplot_generation["query_variant_overrides"]["iqr_extremum_label"]["iqr_winner_gap_min"]) == 1
    assert int(boxplot_generation["query_variant_overrides"]["iqr_extremum_label"]["iqr_winner_gap_max"]) == 1
    assert str(boxplot_prompt["task_key"]).strip() == "boxplot_label_query"
    assert str(boxplot_prompt["answer_hint"]).strip()
    assert str(boxplot_prompt["evidence_hint_iqr_extremum_label"]).strip()

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
    } == set(violin_generation["query_variant_weights"].keys())
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
    assert "query_variant_weights" not in generation_shared
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
    assert str(prompt_shared["evidence_hint_turning_point_count"]).strip()
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
    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
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
    assert str(prompt_defaults["evidence_hint_endpoint_change_value"]).strip()
    assert str(prompt_defaults["evidence_hint_first_crosses_above_threshold"]).strip()
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


def test_tables_statistics_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "table_statistics")
    for section in ("generation", "rendering", "prompt"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["row_count_min"]) >= 5
    assert int(generation_shared["row_count_max"]) == 10
    assert int(generation_shared["numeric_column_count_min"]) >= 3
    assert int(generation_shared["numeric_column_count_max"]) == 5
    assert int(generation_shared["value_min"]) >= 0
    assert int(generation_shared["value_max"]) == 32
    assert sorted(generation_shared["scene_variant_weights"].keys()) == [
        "card_table",
        "ledger",
        "spreadsheet",
        "zebra",
    ]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["table_margin_left_px"]) > 0
    assert int(render_shared["table_margin_bottom_px"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_table_statistics_v0"
    assert str(prompt_shared["scene_key"]).strip() == "styled_table_statistics"
    assert str(prompt_shared["object_description_spreadsheet"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_table_column_summary_base",
    )
    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "column_mean",
        "column_median",
        "column_sum",
    ]
    assert int(generation_defaults["row_count_min"]) == 10
    assert int(generation_defaults["row_count_max"]) == 20
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["canvas_height"]) == 900
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_table_statistics_v0"
    assert str(prompt_defaults["task_key"]).strip() == "summary_value_query"
    assert str(prompt_defaults["evidence_hint_column_sum"]).strip()
    assert str(prompt_defaults["json_example_column_median"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_table_filtered_column_summary_base",
    )
    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "filtered_column_mean",
    ]
    assert int(generation_defaults["row_count_min"]) == 10
    assert int(generation_defaults["row_count_max"]) == 20
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["canvas_height"]) == 900
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_table_statistics_v0"
    assert str(prompt_defaults["task_key"]).strip() == "filtered_subset_value_query"
    assert str(prompt_defaults["evidence_hint_filtered_column_sum"]).strip()
    assert str(prompt_defaults["json_example_filtered_column_mean"]).strip()


def test_tables_counting_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "table_counting")
    for section in ("generation", "rendering", "prompt"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["row_count_min"]) >= 5
    assert int(generation_shared["row_count_max"]) == 10
    assert sorted(generation_shared["scene_variant_weights"].keys()) == [
        "card_table",
        "ledger",
        "spreadsheet",
        "zebra",
    ]

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_table_counting_v0"
    assert str(prompt_shared["scene_key"]).strip() == "styled_table_counting"
    assert str(prompt_shared["task_key"]).strip() == "value_count_query"

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_charts__table__value_predicate_count",
    )
    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "categorical_value_count",
        "in_interval",
        "threshold_count",
    ]
    assert sorted(generation_defaults["comparison_weights"].keys()) == [
        "greater_than",
        "less_than",
    ]
    assert int(generation_defaults["row_count_min"]) == 10
    assert int(generation_defaults["row_count_max"]) == 20
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["canvas_height"]) == 900
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_table_counting_v0"
    assert str(prompt_defaults["evidence_hint_categorical_value_count"]).strip()
    assert str(prompt_defaults["evidence_hint_threshold_count"]).strip()
    assert str(prompt_defaults["json_example_in_interval"]).strip()


def test_tables_ranking_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "table_ranking")
    for section in ("generation", "rendering", "prompt"):
        assert isinstance(cfg.get(section), dict)

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_table_ranking_v0"
    assert str(prompt_shared["scene_key"]).strip() == "styled_table_ranking"
    assert str(prompt_shared["task_key"]).strip() == "kth_label_query"

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_charts__table__column_rank_label",
    )
    assert sorted(generation_defaults["query_variant_weights"].keys()) == ["kth_rank_in_column"]
    assert sorted(generation_defaults["rank_direction_weights"].keys()) == ["highest", "lowest"]
    assert int(generation_defaults["row_count_min"]) == 10
    assert int(generation_defaults["row_count_max"]) == 20
    assert int(rendering_defaults["canvas_height"]) == 900
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_table_ranking_v0"
    assert str(prompt_defaults["evidence_hint_kth_rank_in_column"]).strip()
    assert str(prompt_defaults["json_example_kth_rank_in_column"]).strip()


def test_tables_temporal_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "table_temporal")
    for section in ("generation", "rendering", "prompt"):
        assert isinstance(cfg.get(section), dict)

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_table_temporal_v0"
    assert str(prompt_shared["scene_key"]).strip() == "styled_table_temporal"
    assert str(prompt_shared["task_key"]).strip() == "temporal_value_query"

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_charts__table__temporal_row_interval_difference_value",
    )
    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "absolute_difference_between_rows_over_year_interval",
        "sum_absolute_differences_between_rows_over_year_interval",
    ]
    assert int(generation_defaults["row_count_min"]) == 10
    assert int(generation_defaults["row_count_max"]) == 20
    assert int(generation_defaults["numeric_column_count_min"]) == 8
    assert int(generation_defaults["numeric_column_count_max"]) == 16
    assert int(generation_defaults["interval_length_min"]) == 4
    assert int(generation_defaults["interval_length_max"]) == 5
    assert int(generation_defaults["value_min"]) == 1
    assert int(generation_defaults["value_max"]) == 99
    assert int(rendering_defaults["canvas_width"]) == 1360
    assert int(rendering_defaults["canvas_height"]) == 872
    assert float(rendering_defaults["row_label_width_fraction"]) == 0.08
    assert int(rendering_defaults["row_label_min_width_px"]) == 76
    assert int(rendering_defaults["label_font_size_px"]) == 18
    assert int(rendering_defaults["value_font_size_px"]) == 18
    assert int(rendering_defaults["cell_padding_px"]) == 8
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_table_temporal_v0"
    assert str(prompt_defaults["evidence_hint_absolute_difference_between_rows_over_year_interval"]).strip()
    assert str(prompt_defaults["evidence_hint_sum_absolute_differences_between_rows_over_year_interval"]).strip()
    assert str(prompt_defaults["json_example_sum_absolute_differences_between_rows_over_year_interval"]).strip()


def test_puzzles_logic_defaults_loaded() -> None:
    cfg = get_task_group_defaults("puzzles", "logic")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "puzzles_logic_v0"
    assert str(prompt_shared["answer_hint"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="puzzles_logic_grid_completion_internal",
    )
    assert str(prompt_defaults["scene_key"]).strip() == "logic_option_completion_puzzle"
    assert str(prompt_defaults["task_key"]).strip() == "grid_completion_query"
    assert str(prompt_defaults["object_description_logic_strip"]).strip()
    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "axis_uniqueness",
        "king_non_touch",
        "row_and_column_uniqueness",
    ]
    assert sorted(generation_defaults["uniqueness_axis_weights"].keys()) == ["column", "row"]
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == [
        "logic_card",
        "logic_outline",
        "logic_strip",
    ]
    assert int(generation_defaults["board_size_min"]) == 5
    assert int(generation_defaults["board_size_max"]) == 7
    assert int(generation_defaults["king_non_touch_board_size_min"]) == 3
    assert int(generation_defaults["king_non_touch_board_size_max"]) == 5
    assert int(generation_defaults["option_count"]) == 6
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["option_panel_width_px"]) > 0
    assert str(prompt_defaults["evidence_hint_axis_uniqueness"]).strip()
    assert str(prompt_defaults["evidence_hint_king_non_touch"]).strip()
    assert str(prompt_defaults["json_example_row_and_column_uniqueness"]).strip()
    assert str(prompt_defaults["json_example_king_non_touch"]).strip()
    assert str(prompt_defaults["json_example_answer_only_axis_uniqueness"]).strip()

    logic_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="puzzles_logic_grid_completion_internal",
    )
    assert logic_complexity["criteria_weights"] == {
        "visual_scan": pytest.approx(0.20),
        "reasoning_load": pytest.approx(0.75),
        "scene_variant_load": pytest.approx(0.05),
    }

    raven_generation_defaults, raven_rendering_defaults, raven_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="puzzles_logic_raven_matrix_internal",
    )
    assert str(raven_prompt_defaults["scene_key"]).strip() == "raven_matrix_puzzle"
    assert str(raven_prompt_defaults["task_key"]).strip() == "raven_matrix_query"
    assert str(raven_prompt_defaults["object_description_raven_strip"]).strip()
    assert sorted(raven_generation_defaults["query_variant_weights"].keys()) == [
        "analogical_transform_matrix",
        "count_progression_matrix",
        "position_progression_matrix",
        "set_operation_matrix",
        "spatial_transform_matrix",
    ]
    assert sorted(raven_generation_defaults["scene_variant_weights"].keys()) == [
        "raven_card",
        "raven_outline",
        "raven_strip",
    ]
    assert int(raven_generation_defaults["option_count"]) == 6
    assert int(raven_generation_defaults["count_min"]) == 1
    assert int(raven_generation_defaults["count_max"]) == 8
    assert int(raven_rendering_defaults["canvas_width"]) > 0
    assert int(raven_rendering_defaults["cell_size_px"]) > 0
    assert str(raven_prompt_defaults["json_example_spatial_transform_matrix"]).strip()
    assert str(raven_prompt_defaults["json_example_position_progression_matrix"]).strip()

    raven_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="puzzles_logic_raven_matrix_internal",
    )
    assert raven_complexity["criteria_weights"] == {
        "visual_scan": pytest.approx(0.25),
        "reasoning_load": pytest.approx(0.65),
        "scene_variant_load": pytest.approx(0.10),
    }


def test_puzzles_spatial_defaults_loaded() -> None:
    cfg = get_task_group_defaults("puzzles", "spatial")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "puzzles_spatial_v0"
    assert str(prompt_shared["answer_hint"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="puzzles_spatial_transform_result_internal",
    )
    assert str(prompt_defaults["scene_key"]).strip() == "spatial_transform_result_puzzle"
    assert str(prompt_defaults["task_key"]).strip() == "transform_result_query"
    assert str(prompt_defaults["object_description_fold_strip"]).strip()
    assert str(prompt_defaults["object_description_overlay_strip"]).strip()
    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "overlay_result",
        "paper_fold_cut_result",
        "paper_fold_result",
    ]
    assert sorted(generation_defaults["fold_axis_weights"].keys()) == [
        "horizontal",
        "vertical",
    ]
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == [
        "fold_card",
        "fold_outline",
        "fold_strip",
        "overlay_card",
        "overlay_outline",
        "overlay_strip",
    ]
    assert int(generation_defaults["option_count_min"]) == 5
    assert int(generation_defaults["option_count_max"]) == 6
    assert int(generation_defaults["mark_count_min"]) == 3
    assert int(generation_defaults["mark_count_max"]) == 5
    assert int(generation_defaults["cut_count_min"]) == 1
    assert int(generation_defaults["cut_count_max"]) == 2
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["canvas_height"]) >= 900
    assert int(rendering_defaults["reference_panel_height_px"]) > 0
    assert int(rendering_defaults["option_gap_px"]) >= 0
    assert int(rendering_defaults["option_row_gap_px"]) >= 0
    assert sorted(str(item) for item in rendering_defaults["mark_shape_options"]) == [
        "circle",
        "diamond",
        "rounded_square",
        "square",
    ]
    assert sorted(str(item) for item in rendering_defaults["cut_hole_shape_options"]) == [
        "circle",
        "diamond",
        "rounded_square",
        "square",
    ]
    assert str(prompt_defaults["evidence_hint_paper_fold_result"]).strip()
    assert str(prompt_defaults["evidence_hint_paper_fold_cut_result"]).strip()
    assert str(prompt_defaults["evidence_hint_overlay_result"]).strip()
    assert str(prompt_defaults["json_example_paper_fold_result"]).strip()
    assert str(prompt_defaults["json_example_paper_fold_cut_result"]).strip()
    assert str(prompt_defaults["json_example_answer_only_overlay_result"]).strip()
    assert str(prompt_defaults["json_example_answer_only_paper_fold_result"]).strip()

    spatial_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="puzzles_spatial_transform_result_internal",
    )
    assert spatial_complexity["criteria_weights"] == {
        "reasoning_load": pytest.approx(0.42),
        "scene_variant_load": pytest.approx(0.20),
        "visual_scan": pytest.approx(0.38),
    }

def test_puzzles_spatial_cube_structure_defaults_loaded() -> None:
    cfg = get_task_group_defaults("puzzles", "spatial")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="puzzles_spatial_cube_structure_internal",
    )
    assert str(prompt_defaults["scene_key"]).strip() == "spatial_cube_structure_puzzle"
    assert str(prompt_defaults["task_key"]).strip() == "cube_structure_count_query"
    assert str(prompt_defaults["answer_hint_integer"]).strip()
    assert str(prompt_defaults["object_description_stack_strip"]).strip()
    assert str(prompt_defaults["object_description_single_stack_stack_strip"]).strip()
    assert str(prompt_defaults["object_description_change_pair_stack_strip"]).strip()
    assert generation_defaults["query_variant_weights"] == {
        "visible_cube_count": 1.0,
    }
    assert generation_defaults["change_type_weights"] == {
        "missing_to_complete": 1.0,
        "removed": 1.0,
    }
    assert generation_defaults["painted_query_weights"] == {
        "exterior_face_total": 1.0,
        "exact_k_faces_cube_count": 1.0,
    }
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == [
        "stack_card",
        "stack_outline",
        "stack_strip",
    ]
    assert int(generation_defaults["width_min"]) == 2
    assert int(generation_defaults["width_max"]) == 6
    assert int(generation_defaults["depth_max"]) == 6
    assert int(generation_defaults["height_max"]) == 3
    assert int(generation_defaults["total_cube_count_min"]) == 7
    assert int(generation_defaults["total_cube_count_max"]) == 12
    assert int(generation_defaults["painted_exterior_total_cube_count_min"]) == 3
    assert int(generation_defaults["painted_exterior_total_cube_count_max"]) == 5
    assert int(generation_defaults["painted_exterior_height_min"]) == 2
    assert int(generation_defaults["painted_exterior_height_max"]) == 2
    assert int(generation_defaults["cuboid_width_max"]) == 6
    assert int(generation_defaults["cuboid_depth_max"]) == 6
    assert int(generation_defaults["cuboid_height_max"]) == 3
    assert int(generation_defaults["original_max_height_min"]) == 2
    assert int(generation_defaults["original_max_height_max"]) == 5
    assert int(generation_defaults["removed_cube_count_min"]) == 1
    assert int(generation_defaults["removed_cube_count_max"]) == 6
    assert int(generation_defaults["missing_cube_count_min"]) == 1
    assert int(generation_defaults["missing_cube_count_max"]) == 6
    assert list(generation_defaults["painted_face_target_k_support"]) == [2, 3, 4, 5]
    assert int(generation_defaults["exact_k_painted_cube_count_min"]) == 0
    assert int(generation_defaults["exact_k_painted_cube_count_max"]) == 8
    assert list(generation_defaults["cube_color_name_support"]) == [
        "orange",
        "blue",
        "green",
        "purple",
        "cyan",
        "magenta",
        "brown",
    ]
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["structure_padding_px"]) > 0
    assert int(rendering_defaults["structure_pair_gap_px"]) > 0
    assert int(rendering_defaults["caption_font_size_px"]) > 0
    assert str(prompt_defaults["evidence_hint_total_cube_count"]).strip()
    assert str(prompt_defaults["evidence_hint_missing_to_complete_cuboid_count"]).strip()
    assert str(prompt_defaults["evidence_hint_removed_cube_count"]).strip()
    assert str(prompt_defaults["evidence_hint_painted_exterior_face_count"]).strip()
    assert str(prompt_defaults["evidence_hint_exact_k_painted_faces_cube_count"]).strip()
    assert str(prompt_defaults["json_example_total_cube_count"]).strip()
    assert str(prompt_defaults["json_example_missing_to_complete_cuboid_count"]).strip()
    assert str(prompt_defaults["json_example_removed_cube_count"]).strip()
    assert str(prompt_defaults["json_example_painted_exterior_face_count"]).strip()
    assert str(prompt_defaults["json_example_exact_k_painted_faces_cube_count"]).strip()

    spatial_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="puzzles_spatial_cube_structure_internal",
    )
    assert spatial_complexity["criteria_weights"] == {
        "reasoning_load": pytest.approx(0.4),
        "scene_variant_load": pytest.approx(0.15),
        "visual_scan": pytest.approx(0.45),
    }


def test_puzzles_topology_cyclic_order_match_internal_defaults_loaded() -> None:
    cfg = get_task_group_defaults("puzzles", "topology")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="puzzles_topology_cyclic_order_match_internal",
    )
    assert str(prompt_defaults["scene_key"]).strip() == "topology_cyclic_order_puzzle"
    assert str(prompt_defaults["task_key"]).strip() == "cyclic_order_match_query"
    assert str(prompt_defaults["object_description_necklace_board"]).strip()
    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "cyclic_order_equivalent_label",
    ]
    assert sorted(generation_defaults["token_render_style_weights"].keys()) == [
        "colored_beads",
        "colored_shape_tokens",
        "outline_shape_tokens",
        "shape_tokens",
        "symbol_badges",
    ]
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == [
        "charm_card_grid",
        "necklace_board",
        "route_loop_diagram",
        "token_ring_outline",
    ]
    assert sorted(generation_defaults["loop_path_style_weights"].keys()) == [
        "beaded_string",
        "ellipse",
        "polygon_loop",
        "rounded_rect",
        "wavy_loop",
    ]
    assert int(generation_defaults["option_count_min"]) == 6
    assert int(generation_defaults["option_count_max"]) == 6
    assert int(generation_defaults["valid_option_count_min"]) == 1
    assert int(generation_defaults["valid_option_count_max"]) == 5
    assert int(generation_defaults["bead_count_min"]) == 4
    assert int(generation_defaults["bead_count_max"]) == 6
    label_overrides = generation_defaults["query_variant_overrides"]["cyclic_order_equivalent_label"]
    assert int(label_overrides["option_count_min"]) == 6
    assert int(label_overrides["option_count_max"]) == 6
    assert int(label_overrides["bead_count_min"]) == 4
    assert int(label_overrides["bead_count_max"]) == 5
    assert float(generation_defaults["min_color_distance"]) == 50.0
    assert str(generation_defaults["color_distance_space"]) == "lab"
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["reference_panel_height_px"]) > 0
    assert int(rendering_defaults["option_image_width_px"]) > 0
    assert int(rendering_defaults["shape_bead_inset_px"]) == 2
    assert str(prompt_defaults["json_example_cyclic_order_equivalent_label"]).strip()

    topology_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="puzzles_topology_cyclic_order_match_internal",
    )
    assert topology_complexity["criteria_weights"] == {
        "reasoning_load": pytest.approx(0.4),
        "scene_variant_load": pytest.approx(0.24),
        "visual_scan": pytest.approx(0.36),
    }


def test_puzzles_topology_maze_exit_internal_defaults_loaded() -> None:
    cfg = get_task_group_defaults("puzzles", "topology")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="puzzles_topology_maze_exit_internal",
    )
    assert str(prompt_defaults["scene_key"]).strip() == "topology_maze_exit_puzzle"
    assert str(prompt_defaults["task_key"]).strip() == "maze_exit_label_query"
    assert str(prompt_defaults["object_description_classic_wall_maze"]).strip()
    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "exit_reachability_label",
        "reachable_exit_count",
    ]
    assert sorted(generation_defaults["target_reachability_weights"].keys()) == [
        "reachable",
        "unreachable",
    ]
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == [
        "block_wall_maze",
        "classic_wall_maze",
        "paper_labyrinth_maze",
    ]
    assert int(generation_defaults["maze_rows_min"]) == 6
    assert int(generation_defaults["maze_rows_max"]) == 8
    assert int(generation_defaults["maze_cols_min"]) == 7
    assert int(generation_defaults["maze_cols_max"]) == 10
    assert int(generation_defaults["exit_count_min"]) == 4
    assert int(generation_defaults["exit_count_max"]) == 6
    assert int(generation_defaults["reachable_exit_count_min"]) == 1
    assert int(generation_defaults["reachable_exit_count_max"]) == 5
    assert int(rendering_defaults["canvas_width"]) == 1200
    assert int(rendering_defaults["canvas_height"]) == 900
    assert int(rendering_defaults["exit_marker_radius_px"]) == 27
    assert str(prompt_defaults["evidence_hint_exit_reachability_label"]).strip()
    assert str(prompt_defaults["json_example_exit_reachability_label"]).strip()

    topology_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="puzzles_topology_maze_exit_internal",
    )
    assert topology_complexity["criteria_weights"] == {
        "reasoning_load": pytest.approx(0.44),
        "scene_variant_load": pytest.approx(0.20),
        "visual_scan": pytest.approx(0.36),
    }


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
        key for key, weight in comparison_generation["query_variant_weights"].items() if float(weight) > 0.0
    ) == [
        "category_total_extremum_label",
        "conditional_gap_aggregate_value",
        "conditional_gap_extremum_value",
        "ranked_change_extremum",
        "ranked_ratio_extremum",
        "series_comparison_count",
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
    assert str(comparison_prompt["evidence_hint_ranked_directional_change"]).strip()
    assert str(comparison_prompt["json_example_ranked_absolute_gap"]).strip()
    assert str(comparison_prompt["evidence_hint_ranked_series_share"]).strip()
    assert str(comparison_prompt["json_example_ranked_pair_ratio"]).strip()
    assert str(comparison_prompt["task_key_conditional_gap"]).strip() == "conditional_gap_value_query"
    assert str(comparison_prompt["answer_hint_conditional_gap_value"]).strip()
    assert str(comparison_prompt["evidence_hint_conditional_gap_value"]).strip()
    assert str(comparison_prompt["json_example_conditional_gap_value"]).strip()
    assert str(comparison_prompt["evidence_hint_category_total_extremum"]).strip()
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
    assert sorted(generation_shared["query_variant_weights"].keys()) == [
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
    assert str(prompt_shared["evidence_hint_in_interval"]).strip()
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



def test_geometry_comparison_defaults_loaded() -> None:
    cfg = get_task_group_defaults("geometry", "comparison")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["object_count_min"]) >= 2
    assert int(generation_shared["object_count_max"]) >= int(generation_shared["object_count_min"])
    assert bool(generation_shared["balanced_sampling"]) is True
    assert float(generation_shared["min_normalized_gap"]) > 0.0

    generation_overrides = cfg["generation"]["task_overrides"]
    assert "source_geometry_comparison_angle" in generation_overrides
    assert "source_geometry_comparison_area" in generation_overrides
    assert "source_geometry_comparison_length" in generation_overrides
    assert "source_geometry_comparison_perimeter" in generation_overrides

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_size_min"]) > 0
    assert int(render_shared["canvas_size_max"]) >= int(render_shared["canvas_size_min"])
    assert int(render_shared["graph_cells_min"]) > 0
    assert int(render_shared["graph_cells_max"]) >= int(render_shared["graph_cells_min"])
    assert int(render_shared["line_width_min"]) >= 1
    assert int(render_shared["line_width_max"]) >= int(render_shared["line_width_min"])
    assert int(render_shared["label_stroke_width_min"]) >= 1
    assert int(render_shared["label_stroke_width_max"]) >= int(render_shared["label_stroke_width_min"])

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip()
    assert str(prompt_shared["scene_key"]).strip()
    assert str(prompt_shared["task_key"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "visual_scan": 0.25,
        "comparison_reasoning": 0.35,
        "ambiguity": 0.35,
        "output_burden": 0.05,
    }

    angle_generation, angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_comparison_angle",
    )
    assert int(angle_generation["min_angle"]) < int(angle_generation["max_angle"])
    assert int(angle_generation["angle_step"]) > 0
    assert sorted(angle_generation["query_type_weights"].keys()) == ["largest", "smallest"]
    assert sorted(angle_generation["object_count_weights"].keys()) == ["4", "5", "6", "7", "8"]
    assert float(angle_generation["min_absolute_gap_degrees"]) > 0.0
    assert int(angle_rendering["line_width"]) > 0
    assert str(angle_prompt["object_description"]).strip()
    assert str(angle_prompt["question_text_largest"]).strip()
    assert str(angle_prompt["question_text_smallest"]).strip()
    assert str(angle_prompt["evidence_hint"]).strip()
    assert str(angle_prompt["answer_hint"]).strip()

    area_generation, area_rendering, area_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_comparison_area",
    )
    assert int(area_generation["min_rectangle_width"]) < int(area_generation["max_rectangle_width"])
    assert int(area_generation["min_rectangle_height"]) < int(area_generation["max_rectangle_height"])
    assert int(area_generation["min_triangle_base"]) < int(area_generation["max_triangle_base"])
    assert int(area_generation["min_triangle_height"]) < int(area_generation["max_triangle_height"])
    assert sorted(area_generation["query_type_weights"].keys()) == ["largest", "smallest"]
    assert sorted(area_generation["object_count_weights"].keys()) == ["4", "5", "6", "7", "8"]
    assert float(area_generation["min_absolute_gap_square_units"]) > 0.0
    assert float(area_generation["min_absolute_triangle_area_gap_square_units"]) > 0.0
    assert int(area_rendering["line_width"]) > 0
    assert str(area_prompt["object_description"]).strip()
    assert str(area_prompt["object_description_triangle"]).strip()
    assert str(area_prompt["question_text_largest"]).strip()
    assert str(area_prompt["question_text_smallest"]).strip()
    assert str(area_prompt["question_text_largest_triangle"]).strip()
    assert str(area_prompt["question_text_smallest_triangle"]).strip()
    assert str(area_prompt["evidence_hint"]).strip()
    assert str(area_prompt["evidence_hint_triangle"]).strip()
    assert str(area_prompt["answer_hint"]).strip()
    assert str(area_prompt["answer_hint_triangle"]).strip()

    perimeter_generation, perimeter_rendering, perimeter_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_comparison_perimeter",
    )
    assert int(perimeter_generation["min_rectangle_width"]) < int(perimeter_generation["max_rectangle_width"])
    assert int(perimeter_generation["min_rectangle_height"]) < int(perimeter_generation["max_rectangle_height"])
    assert int(perimeter_generation["min_triangle_base"]) < int(perimeter_generation["max_triangle_base"])
    assert int(perimeter_generation["min_triangle_height"]) < int(perimeter_generation["max_triangle_height"])
    assert sorted(perimeter_generation["query_type_weights"].keys()) == ["largest", "smallest"]
    assert sorted(perimeter_generation["object_count_weights"].keys()) == ["4", "5", "6", "7", "8"]
    assert float(perimeter_generation["min_absolute_gap_units"]) > 0.0
    assert float(perimeter_generation["min_absolute_triangle_perimeter_gap_units"]) > 0.0
    assert int(perimeter_rendering["line_width"]) > 0
    assert str(perimeter_prompt["object_description"]).strip()
    assert str(perimeter_prompt["object_description_triangle"]).strip()
    assert str(perimeter_prompt["question_text_largest"]).strip()
    assert str(perimeter_prompt["question_text_smallest"]).strip()
    assert str(perimeter_prompt["question_text_largest_triangle"]).strip()
    assert str(perimeter_prompt["question_text_smallest_triangle"]).strip()
    assert str(perimeter_prompt["evidence_hint"]).strip()
    assert str(perimeter_prompt["evidence_hint_triangle"]).strip()
    assert str(perimeter_prompt["answer_hint"]).strip()
    assert str(perimeter_prompt["answer_hint_triangle"]).strip()

    length_generation, length_rendering, length_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_comparison_length",
    )
    assert int(length_generation["min_segment_length"]) < int(length_generation["max_segment_length"])
    assert int(length_generation["max_abs_vector_component"]) > 0
    assert sorted(length_generation["query_type_weights"].keys()) == ["largest", "smallest"]
    assert sorted(length_generation["object_count_weights"].keys()) == ["4", "5", "6", "7", "8"]
    assert float(length_generation["min_absolute_gap_units"]) > 0.0
    assert int(length_rendering["line_width"]) > 0
    assert str(length_prompt["object_description"]).strip()
    assert str(length_prompt["question_text_largest"]).strip()
    assert str(length_prompt["question_text_smallest"]).strip()
    assert str(length_prompt["evidence_hint"]).strip()
    assert str(length_prompt["answer_hint"]).strip()


def test_geometry_counting_defaults_loaded() -> None:
    cfg = get_task_group_defaults("geometry", "counting")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["object_count_min"]) >= 2
    assert int(generation_shared["object_count_max"]) >= int(generation_shared["object_count_min"])
    assert bool(generation_shared["balanced_sampling"]) is True

    generation_overrides = cfg["generation"]["task_overrides"]
    assert "source_geometry_counting_angle" in generation_overrides
    assert "source_geometry_counting_triangle" in generation_overrides
    assert "source_geometry_counting_quadrilateral" in generation_overrides
    assert "source_geometry_counting_shape_type" in generation_overrides
    assert "source_geometry_counting_convexity" in generation_overrides

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_size_min"]) > 0
    assert int(render_shared["canvas_size_max"]) >= int(render_shared["canvas_size_min"])
    assert int(render_shared["graph_cells_min"]) > 0
    assert int(render_shared["graph_cells_max"]) >= int(render_shared["graph_cells_min"])
    assert int(render_shared["line_width_min"]) >= 1
    assert int(render_shared["line_width_max"]) >= int(render_shared["line_width_min"])
    assert int(render_shared["label_stroke_width_min"]) >= 1
    assert int(render_shared["label_stroke_width_max"]) >= int(render_shared["label_stroke_width_min"])

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip()
    assert str(prompt_shared["scene_key"]).strip()
    assert str(prompt_shared["task_key"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "visual_scan": 0.35,
        "classification_reasoning": 0.35,
        "ambiguity": 0.25,
        "output_burden": 0.05,
    }

    angle_generation, angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_counting_angle",
    )
    assert int(angle_generation["min_angle"]) < int(angle_generation["max_angle"])
    assert int(angle_generation["angle_step"]) > 0
    assert sorted(angle_generation["variant_weights"].keys()) == ["acute_angle", "obtuse_angle", "right_angle"]
    assert bool(angle_generation["balanced_variant_sampling"]) is True
    assert sorted(angle_generation["object_count_weights"].keys()) == ["10", "6", "7", "8", "9"]
    assert float(angle_generation["boundary_margin_degrees"]) >= 0.0
    assert int(angle_rendering["line_width"]) > 0
    assert str(angle_prompt["object_description"]).strip()
    assert str(angle_prompt["question_text_acute_angle"]).strip()
    assert str(angle_prompt["question_text_right_angle"]).strip()
    assert str(angle_prompt["question_text_obtuse_angle"]).strip()
    assert str(angle_prompt["evidence_hint"]).strip()
    assert str(angle_prompt["answer_hint"]).strip()
    assert str(angle_prompt["json_example"]).strip()
    assert str(angle_prompt["json_example_answer_only"]).strip()

    triangle_generation, triangle_rendering, triangle_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_counting_triangle",
    )
    assert float(triangle_generation["min_side_units"]) < float(triangle_generation["max_side_units"])
    assert float(triangle_generation["right_angle_margin_degrees"]) > 0.0
    assert float(triangle_generation["min_side_gap_units"]) > 0.0
    assert sorted(triangle_generation["variant_weights"].keys()) == [
        "acute_triangle",
        "equilateral_triangle",
        "isosceles_triangle",
        "obtuse_triangle",
        "right_triangle",
        "scalene_triangle",
    ]
    assert bool(triangle_generation["balanced_variant_sampling"]) is True
    assert sorted(triangle_generation["object_count_weights"].keys()) == ["5", "6", "7", "8"]
    assert int(triangle_rendering["graph_cells_min"]) < int(triangle_rendering["graph_cells_max"])
    assert int(triangle_rendering["object_label_offset_px"]) > 0
    assert str(triangle_prompt["object_description"]).strip()
    assert str(triangle_prompt["question_text_equilateral_triangle"]).strip()
    assert str(triangle_prompt["question_text_isosceles_triangle"]).strip()
    assert str(triangle_prompt["question_text_scalene_triangle"]).strip()
    assert str(triangle_prompt["question_text_right_triangle"]).strip()
    assert str(triangle_prompt["question_text_acute_triangle"]).strip()
    assert str(triangle_prompt["question_text_obtuse_triangle"]).strip()
    assert str(triangle_prompt["evidence_hint"]).strip()
    assert str(triangle_prompt["answer_hint"]).strip()
    assert str(triangle_prompt["json_example"]).strip()
    assert str(triangle_prompt["json_example_answer_only"]).strip()

    quadrilateral_generation, quadrilateral_rendering, quadrilateral_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_counting_quadrilateral",
    )
    assert float(quadrilateral_generation["min_extent_units"]) < float(quadrilateral_generation["max_extent_units"])
    assert float(quadrilateral_generation["min_side_gap_units"]) > 0.0
    assert float(quadrilateral_generation["min_slant_units"]) > 0.0
    assert sorted(quadrilateral_generation["variant_weights"].keys()) == [
        "parallelogram_only",
        "rectangle_non_square",
        "rhombus_non_square",
        "square",
    ]
    assert bool(quadrilateral_generation["balanced_variant_sampling"]) is True
    assert sorted(quadrilateral_generation["object_count_weights"].keys()) == ["5", "6", "7"]
    assert int(quadrilateral_rendering["graph_cells_min"]) < int(quadrilateral_rendering["graph_cells_max"])
    assert int(quadrilateral_rendering["object_label_offset_px"]) > 0
    assert str(quadrilateral_prompt["object_description"]).strip()
    assert str(quadrilateral_prompt["question_text_square"]).strip()
    assert str(quadrilateral_prompt["question_text_rectangle_non_square"]).strip()
    assert str(quadrilateral_prompt["question_text_rhombus_non_square"]).strip()
    assert str(quadrilateral_prompt["question_text_parallelogram_only"]).strip()
    assert str(quadrilateral_prompt["evidence_hint"]).strip()
    assert str(quadrilateral_prompt["answer_hint"]).strip()
    assert str(quadrilateral_prompt["json_example"]).strip()
    assert str(quadrilateral_prompt["json_example_answer_only"]).strip()

    shape_type_generation, shape_type_rendering, shape_type_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_counting_shape_type",
    )
    assert float(shape_type_generation["min_extent_units"]) < float(shape_type_generation["max_extent_units"])
    assert float(shape_type_generation["ellipse_axis_ratio_min"]) > 1.0
    assert float(shape_type_generation["min_side_gap_units"]) > 0.0
    assert float(shape_type_generation["min_slant_units"]) > 0.0
    assert sorted(shape_type_generation["variant_weights"].keys()) == [
        "circle",
        "ellipse",
        "hexagon",
        "pentagon",
        "quadrilateral",
        "triangle",
    ]
    assert bool(shape_type_generation["balanced_variant_sampling"]) is True
    assert sorted(shape_type_generation["object_count_weights"].keys()) == ["6", "7", "8", "9"]
    assert int(shape_type_rendering["graph_cells_min"]) < int(shape_type_rendering["graph_cells_max"])
    assert int(shape_type_rendering["object_label_offset_px"]) > 0
    assert str(shape_type_prompt["object_description"]).strip()
    assert str(shape_type_prompt["question_text_triangle"]).strip()
    assert str(shape_type_prompt["question_text_quadrilateral"]).strip()
    assert str(shape_type_prompt["question_text_pentagon"]).strip()
    assert str(shape_type_prompt["question_text_hexagon"]).strip()
    assert str(shape_type_prompt["question_text_circle"]).strip()
    assert str(shape_type_prompt["question_text_ellipse"]).strip()
    assert str(shape_type_prompt["evidence_hint"]).strip()
    assert str(shape_type_prompt["answer_hint"]).strip()
    assert str(shape_type_prompt["json_example"]).strip()
    assert str(shape_type_prompt["json_example_answer_only"]).strip()

    convexity_generation, convexity_rendering, convexity_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_counting_convexity",
    )
    assert sorted(convexity_generation["variant_weights"].keys()) == ["concave_polygon", "convex_polygon"]
    assert sorted(convexity_generation["object_count_weights"].keys()) == ["6", "7", "8", "9"]
    assert sorted(convexity_generation["side_count_weights"].keys()) == ["4", "5", "6"]
    assert bool(convexity_generation["balanced_variant_sampling"]) is True
    assert int(convexity_rendering["graph_cells_min"]) < int(convexity_rendering["graph_cells_max"])
    assert int(convexity_rendering["object_label_offset_px"]) > 0
    assert str(convexity_prompt["object_description"]).strip()
    assert str(convexity_prompt["question_text_convex_polygon"]).strip()
    assert str(convexity_prompt["question_text_concave_polygon"]).strip()
    assert str(convexity_prompt["evidence_hint"]).strip()
    assert str(convexity_prompt["answer_hint"]).strip()
    assert str(convexity_prompt["json_example"]).strip()
    assert str(convexity_prompt["json_example_answer_only"]).strip()



def test_icons_counting_defaults_loaded() -> None:
    cfg = get_task_group_defaults("icons", "counting")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["object_count_min"]) >= 1
    assert int(generation_shared["object_count_max"]) >= int(generation_shared["object_count_min"])
    assert int(generation_shared["target_count_min"]) == 0
    assert int(generation_shared["target_count_max"]) == 10
    assert int(generation_shared["distractor_count_min"]) == 1
    assert int(generation_shared["distractor_count_max"]) == 10
    assert bool(generation_shared["balanced_sampling"]) is True
    assert "task_icons__reference_canvas__attribute_match_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__icon_field__type_frequency_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__reference_canvas__size_relation_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__named_field__shape_pair_total_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__named_field__shape_pair_difference_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__named_field__closer_to_reference_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__venn_field__venn_region_shape_count" in cfg["generation"]["task_overrides"]
    assert set(cfg["generation"]["task_overrides"]["task_icons__reference_canvas__attribute_match_count"]["query_variant_weights"].keys()) == {
        "match_type",
        "match_color",
        "match_rotation",
        "match_type_color_rotation",
    }

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["reference_panel_width_px"]) > 0
    assert int(render_shared["scene_icon_size_min_px"]) > 0
    assert int(render_shared["scene_icon_size_max_px"]) >= int(render_shared["scene_icon_size_min_px"])
    assert 0.0 <= float(render_shared["scene_max_overlap_fraction"]) <= 1.0
    assert int(render_shared["scene_placement_max_attempts"]) > 0
    assert 1 <= int(render_shared["palette_size_min"]) <= int(render_shared["palette_size_max"])
    assert float(render_shared["min_color_distance"]) > 0.0
    assert str(render_shared["color_distance_space"]).strip() in {"lab", "rgb"}
    assert "icon_tint_rgb" not in render_shared
    assert list(render_shared["icon_noise_edit_types"]) == ["blur", "downsample", "jpeg", "noise"]
    assert list(render_shared["icon_noise_edit_count_range"]) == [0, 2]
    assert "noise" in render_shared["icon_noise_value_ranges"]

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip()
    assert str(prompt_shared["scene_key"]).strip()
    assert str(prompt_shared["task_key"]).strip()
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "visual_scan": 0.30,
        "ambiguity": 0.20,
        "clutter": 0.15,
        "semantic_match": 0.35,
    }

    single_generation, single_rendering, single_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__reference_canvas__attribute_match_count",
    )
    assert str(single_generation["variant_generation_params"]["match_type"]["pool_manifest"]).strip() == "all_icons.txt"
    assert str(single_generation["variant_generation_params"]["match_color"]["pool_manifest"]).strip() == "all_icons.txt"
    assert str(single_generation["variant_generation_params"]["match_rotation"]["pool_manifest"]).strip() == "non_symmetry.txt"
    assert list(single_generation["variant_generation_params"]["match_rotation"]["rotation_candidates_degrees"]) == [0, 90, 180, 270]
    assert float(single_rendering["variant_render_params"]["match_color"]["min_color_distance"]) == 60.0
    assert int(single_rendering["variant_render_params"]["match_color"]["palette_size_min"]) == 3
    assert int(single_rendering["variant_render_params"]["match_color"]["palette_size_max"]) == 4
    assert str(single_prompt["object_description"]).strip()
    assert set(single_prompt["question_text_by_variant"].keys()) == {
        "match_type",
        "match_color",
        "match_rotation",
        "match_type_color_rotation",
    }
    assert str(single_prompt["evidence_hint"]).strip()
    assert str(single_prompt["answer_hint"]).strip()
    assert str(single_prompt["json_example"]).strip()
    assert str(single_prompt["json_example_answer_only"]).strip()

    assert str(single_generation["variant_generation_params"]["match_type_color_rotation"]["pool_manifest"]).strip() == "non_symmetry.txt"
    assert list(single_generation["variant_generation_params"]["match_type_color_rotation"]["rotation_candidates_degrees"]) == [0, 90, 180, 270]
    assert float(single_rendering["variant_render_params"]["match_type_color_rotation"]["min_color_distance"]) == 40.0
    assert int(single_rendering["variant_render_params"]["match_type_color_rotation"]["palette_size_min"]) == 3
    assert int(single_rendering["variant_render_params"]["match_type_color_rotation"]["palette_size_max"]) == 4

    size_generation, size_rendering, size_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__reference_canvas__size_relation_count",
    )
    assert str(size_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert list(size_generation["rotation_candidates_degrees"]) == [0, 90, 180, 270]
    assert list(size_generation["size_relation_candidates"]) == ["smaller", "larger"]
    assert int(size_generation["size_relation_min_delta_px"]) == 18
    assert int(size_generation["object_count_max"]) == 14
    assert int(size_generation["target_count_max"]) == 5
    assert int(size_generation["distractor_count_max"]) == 6
    assert int(size_rendering["scene_icon_size_max_px"]) == 120
    assert int(size_rendering["reference_icon_size_min_px"]) == 64
    assert int(size_rendering["reference_icon_size_max_px"]) == 96
    assert str(size_prompt["object_description"]).strip()
    assert str(size_prompt["question_text_smaller"]).strip()
    assert str(size_prompt["question_text_larger"]).strip()
    assert str(size_prompt["evidence_hint"]).strip()
    assert str(size_prompt["answer_hint"]).strip()
    assert str(size_prompt["json_example"]).strip()
    assert str(size_prompt["json_example_answer_only"]).strip()

    singleton_generation, singleton_rendering, singleton_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__icon_field__type_frequency_count",
    )
    assert str(singleton_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert sorted(singleton_generation["query_variant_weights"].keys()) == ["most_frequent_type_count", "singleton_type_count"]
    singleton_params = singleton_generation["variant_generation_params"]["singleton_type_count"]
    assert int(singleton_params["object_count_min"]) == 5
    assert int(singleton_params["object_count_max"]) == 10
    assert int(singleton_params["target_count_min"]) == 0
    assert int(singleton_params["target_count_max"]) == 4
    assert int(singleton_params["repeated_type_count_min"]) == 1
    assert int(singleton_params["repeated_type_count_max"]) == 4
    assert int(singleton_params["repeated_type_multiplicity_min"]) == 2
    assert int(singleton_params["repeated_type_multiplicity_max"]) == 4
    assert int(singleton_rendering["canvas_width"]) > 0
    assert int(singleton_rendering["canvas_height"]) > 0
    assert str(singleton_prompt["scene_key"]).strip() == "single_scene_counting"
    assert str(singleton_prompt["object_description"]).strip()
    assert str(singleton_prompt["question_text_by_variant"]["singleton_type_count"]).strip()
    assert str(singleton_prompt["evidence_hint_by_variant"]["singleton_type_count"]).strip()
    assert str(singleton_prompt["answer_hint"]).strip()
    assert str(singleton_prompt["json_example"]).strip()
    assert str(singleton_prompt["json_example_answer_only"]).strip()

    most_frequent_generation, most_frequent_rendering, most_frequent_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__icon_field__type_frequency_count",
    )
    most_frequent_params = most_frequent_generation["variant_generation_params"]["most_frequent_type_count"]
    assert str(most_frequent_params["pool_manifest"]).strip() == "all_icons.txt"
    assert int(most_frequent_params["object_count_min"]) == 7
    assert int(most_frequent_params["object_count_max"]) == 12
    assert int(most_frequent_params["target_count_min"]) == 3
    assert int(most_frequent_params["target_count_max"]) == 5
    assert int(most_frequent_params["other_repeated_type_count_max"]) == 3
    assert int(most_frequent_rendering["canvas_width"]) > 0
    assert int(most_frequent_rendering["canvas_height"]) > 0
    assert str(most_frequent_prompt["scene_key"]).strip() == "single_scene_counting"
    assert str(most_frequent_prompt["object_description"]).strip()
    assert str(most_frequent_prompt["question_text_by_variant"]["most_frequent_type_count"]).strip()
    assert str(most_frequent_prompt["evidence_hint_by_variant"]["most_frequent_type_count"]).strip()
    assert str(most_frequent_prompt["answer_hint"]).strip()
    assert str(most_frequent_prompt["json_example"]).strip()
    assert str(most_frequent_prompt["json_example_answer_only"]).strip()

    pair_generation, pair_rendering, pair_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__named_field__shape_pair_total_count",
    )
    assert int(pair_generation["operand_count_min"]) == 1
    assert int(pair_generation["operand_count_max"]) == 6
    assert int(pair_generation["total_answer_min"]) == 2
    assert int(pair_generation["total_answer_max"]) == 10
    assert int(pair_generation["difference_answer_min"]) == 0
    assert int(pair_generation["difference_answer_max"]) == 5
    assert sorted(pair_generation["query_weights"].keys()) == [
        "two_bound_color_total_count",
        "two_shape_total_count",
    ]
    assert int(pair_rendering["canvas_width"]) > 0
    assert int(pair_rendering["canvas_height"]) > 0
    assert str(pair_prompt["scene_key"]).strip() == "single_scene_counting"
    assert str(pair_prompt["question_text_two_shape_total_count"]).strip()
    assert str(pair_prompt["question_text_two_bound_color_total_count"]).strip()
    assert str(pair_prompt["evidence_hint"]).strip()
    assert str(pair_prompt["answer_hint"]).strip()
    assert str(pair_prompt["json_example"]).strip()
    assert str(pair_prompt["json_example_answer_only"]).strip()

    pair_diff_generation, pair_diff_rendering, pair_diff_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__named_field__shape_pair_difference_count",
    )
    assert sorted(pair_diff_generation["query_weights"].keys()) == [
        "two_bound_color_difference_count",
        "two_shape_difference_count",
    ]
    assert int(pair_diff_rendering["canvas_width"]) > 0
    assert str(pair_diff_prompt["question_text_two_shape_difference_count"]).strip()
    assert str(pair_diff_prompt["question_text_two_bound_color_difference_count"]).strip()

    closer_generation, closer_rendering, closer_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__named_field__closer_to_reference_count",
    )
    assert int(closer_generation["target_icon_count_min"]) == 4
    assert int(closer_generation["target_icon_count_max"]) == 8
    assert int(closer_generation["target_answer_min"]) == 0
    assert int(closer_generation["target_answer_max"]) == 4
    assert sorted(closer_generation["query_weights"].keys()) == [
        "closer_to_reference_a_count",
        "closer_to_reference_b_count",
    ]
    assert list(closer_generation["reference_axis_degrees"]) == [0, 35, 90, 145]
    assert int(closer_rendering["canvas_width"]) > 0
    assert int(closer_rendering["canvas_height"]) > 0
    assert int(closer_rendering["distance_margin_px"]) == 42
    assert str(closer_prompt["scene_key"]).strip() == "single_scene_counting"
    assert str(closer_prompt["question_text_closer_to_reference_a_count"]).strip()
    assert str(closer_prompt["question_text_closer_to_reference_b_count"]).strip()
    assert str(closer_prompt["evidence_hint"]).strip()
    assert str(closer_prompt["answer_hint"]).strip()
    assert str(closer_prompt["json_example"]).strip()
    assert str(closer_prompt["json_example_answer_only"]).strip()

    venn_generation, venn_rendering, venn_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__venn_field__venn_region_shape_count",
    )
    assert int(venn_generation["object_count_min"]) == 8
    assert int(venn_generation["object_count_max"]) == 16
    assert int(venn_generation["target_count_min"]) == 1
    assert int(venn_generation["target_count_max"]) == 5
    assert sorted(venn_generation["named_venn_query_ids"]) == [
        "inside_both_circles_count",
        "inside_either_circle_count",
        "inside_exactly_one_circle_count",
        "outside_both_circles_count",
    ]
    assert sorted(venn_generation["target_attribute_mode_weights"].keys()) == [
        "color_shape",
        "fill_style_shape",
        "shape_only",
    ]
    assert int(venn_rendering["canvas_width"]) > 0
    assert int(venn_rendering["canvas_height"]) > 0
    assert int(venn_rendering["venn_boundary_margin_px"]) == 12
    assert str(venn_prompt["scene_key"]).strip() == "single_scene_counting"
    assert str(venn_prompt["question_text_inside_both_circles_count"]).strip()
    assert str(venn_prompt["question_text_inside_either_circle_count"]).strip()
    assert str(venn_prompt["question_text_inside_exactly_one_circle_count"]).strip()
    assert str(venn_prompt["question_text_outside_both_circles_count"]).strip()
    assert str(venn_prompt["evidence_hint"]).strip()
    assert str(venn_prompt["answer_hint"]).strip()
    assert str(venn_prompt["json_example"]).strip()
    assert str(venn_prompt["json_example_answer_only"]).strip()


def test_graph_counting_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "counting")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 5
    assert int(generation_shared["node_count_max"]) == 10
    assert int(generation_shared["query_degree_min"]) == 0
    assert int(generation_shared["query_degree_max"]) == 4
    assert int(generation_shared["target_count_min"]) == 0
    assert int(generation_shared["target_count_max"]) == 5
    assert int(generation_shared["degree_sequence_max_degree"]) == 5
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_shared["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared["node_shape_variant_weights"].keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(generation_shared["layout_transform_variant_weights"].keys()) == {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert set(generation_shared["node_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }
    assert bool(generation_shared["balanced_topology_profile_sampling"]) is True
    assert bool(generation_shared["balanced_label_variant_sampling"]) is True
    assert bool(generation_shared["balanced_layout_variant_sampling"]) is True
    assert bool(generation_shared["balanced_node_shape_variant_sampling"]) is True
    assert bool(generation_shared["balanced_layout_transform_variant_sampling"]) is True
    assert bool(generation_shared["balanced_node_color_name_sampling"]) is True

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["node_radius_min_px"]) > 0
    assert int(render_shared["node_radius_max_px"]) >= int(render_shared["node_radius_min_px"])
    assert int(render_shared["edge_width_px"]) > 0
    assert int(render_shared["label_font_size_px"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip()
    assert str(prompt_shared["scene_key"]).strip()
    assert str(prompt_shared["task_key"]).strip()
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()
    assert str(prompt_shared["object_description_undirected"]).strip()
    assert str(prompt_shared["object_description_directed"]).strip()
    assert str(prompt_shared["question_text_degree_count"]).strip()
    assert str(prompt_shared["question_text_in_degree"]).strip()
    assert str(prompt_shared["question_text_out_degree"]).strip()
    assert str(prompt_shared["evidence_hint"]).strip()
    assert str(prompt_shared["answer_hint"]).strip()
    assert str(prompt_shared["json_example"]).strip()
    assert str(prompt_shared["json_example_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "topology_reasoning": 0.40,
        "visual_scan": 0.30,
        "ambiguity": 0.20,
        "clutter": 0.10,
    }

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__degree_predicate_count",
    )
    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "degree_count",
        "directed_degree_count",
    ]
    assert sorted(generation_defaults["degree_mode_weights"].keys()) == ["in_degree", "out_degree"]
    assert set(generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(generation_defaults["balanced_edge_routing_variant_sampling"]) is True
    assert bool(generation_defaults["balanced_degree_mode_sampling"]) is True
    assert int(generation_defaults["node_count_min"]) == 5
    assert int(generation_defaults["node_count_max"]) == 10
    assert int(generation_defaults["directed_node_count_max"]) == 10
    assert int(generation_defaults["query_degree_min"]) == 0
    assert int(generation_defaults["query_degree_max"]) == 4
    assert int(generation_defaults["directed_degree_sequence_max_degree"]) == 4
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert int(rendering_defaults["arrow_length_px"]) > 0
    assert int(rendering_defaults["arrow_width_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(prompt_defaults["task_key"]).strip() == "degree_count_query"
    assert str(prompt_defaults["object_description_undirected"]).strip()
    assert str(prompt_defaults["object_description_directed"]).strip()
    assert str(prompt_defaults["question_text_degree_count"]).strip()
    assert str(prompt_defaults["question_text_in_degree"]).strip()
    assert str(prompt_defaults["question_text_out_degree"]).strip()

    named_degree_generation_defaults, named_degree_rendering_defaults, named_degree_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__named_node_degree_value",
        )
    )
    assert sorted(named_degree_generation_defaults["graph_directionality_weights"].keys()) == ["directed", "undirected"]
    assert sorted(named_degree_generation_defaults["degree_mode_weights"].keys()) == [
        "in_degree",
        "out_degree",
        "total_degree",
    ]
    assert set(named_degree_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(named_degree_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(named_degree_generation_defaults["balanced_graph_directionality_sampling"]) is True
    assert bool(named_degree_generation_defaults["balanced_degree_mode_sampling"]) is True
    assert int(named_degree_generation_defaults["node_count_min"]) == 5
    assert int(named_degree_generation_defaults["node_count_max"]) == 10
    assert int(named_degree_generation_defaults["directed_node_count_max"]) == 10
    assert int(named_degree_generation_defaults["target_degree_min"]) == 0
    assert int(named_degree_generation_defaults["target_degree_max"]) == 4
    assert int(named_degree_rendering_defaults["canvas_width"]) > 0
    assert int(named_degree_rendering_defaults["node_radius_min_px"]) > 0
    assert str(named_degree_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(named_degree_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(named_degree_prompt_defaults["task_key"]).strip() == "named_node_degree_value_query"
    assert str(named_degree_prompt_defaults["object_description_undirected"]).strip()
    assert str(named_degree_prompt_defaults["object_description_directed"]).strip()

    source_sink_generation_defaults, source_sink_rendering_defaults, source_sink_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="graph_node_link_source_sink_count_internal",
        )
    )
    assert sorted(source_sink_generation_defaults["source_sink_mode_weights"].keys()) == ["sink", "source"]
    assert set(source_sink_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(source_sink_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(source_sink_generation_defaults["balanced_source_sink_mode_sampling"]) is True
    assert bool(source_sink_generation_defaults["balanced_target_count_sampling"]) is True
    assert int(source_sink_generation_defaults["target_count_min"]) == 0
    assert int(source_sink_generation_defaults["target_count_max"]) == 4
    assert int(source_sink_generation_defaults["query_degree_min"]) == 0
    assert int(source_sink_generation_defaults["query_degree_max"]) == 0
    assert int(source_sink_rendering_defaults["canvas_width"]) > 0
    assert str(source_sink_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(source_sink_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(source_sink_prompt_defaults["task_key"]).strip() == "source_sink_count_query"
    assert str(source_sink_prompt_defaults["object_description_directed"]).strip()

    node_color_generation_defaults, node_color_rendering_defaults, node_color_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__node_color_count",
        )
    )
    assert sorted(node_color_generation_defaults["graph_directionality_weights"].keys()) == ["directed", "undirected"]
    assert set(node_color_generation_defaults["target_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }
    assert set(node_color_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(node_color_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(node_color_generation_defaults["balanced_graph_directionality_sampling"]) is True
    assert bool(node_color_generation_defaults["balanced_target_color_name_sampling"]) is True
    assert bool(node_color_generation_defaults["balanced_target_count_sampling"]) is True
    assert int(node_color_generation_defaults["node_count_min"]) == 8
    assert int(node_color_generation_defaults["node_count_max"]) == 12
    assert int(node_color_generation_defaults["directed_node_count_max"]) == 12
    assert int(node_color_generation_defaults["target_count_min"]) == 3
    assert int(node_color_generation_defaults["target_count_max"]) == 7
    assert int(node_color_rendering_defaults["canvas_width"]) > 0
    assert str(node_color_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(node_color_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(node_color_prompt_defaults["task_key"]).strip() == "node_color_count_query"
    assert str(node_color_prompt_defaults["object_description_undirected"]).strip()
    assert str(node_color_prompt_defaults["object_description_directed"]).strip()

    edge_color_generation_defaults, edge_color_rendering_defaults, edge_color_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__edge_color_count",
        )
    )
    assert sorted(edge_color_generation_defaults["graph_directionality_weights"].keys()) == ["directed", "undirected"]
    assert set(edge_color_generation_defaults["target_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }
    assert set(edge_color_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(edge_color_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(edge_color_generation_defaults["balanced_graph_directionality_sampling"]) is True
    assert bool(edge_color_generation_defaults["balanced_target_color_name_sampling"]) is True
    assert bool(edge_color_generation_defaults["balanced_target_count_sampling"]) is True
    assert int(edge_color_generation_defaults["target_count_min"]) == 0
    assert int(edge_color_generation_defaults["target_count_max"]) == 8
    assert int(edge_color_rendering_defaults["edge_width_px"]) == 5
    assert str(edge_color_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(edge_color_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(edge_color_prompt_defaults["task_key"]).strip() == "edge_color_count_query"
    assert str(edge_color_prompt_defaults["object_description_undirected"]).strip()
    assert str(edge_color_prompt_defaults["object_description_directed"]).strip()

    isolated_removal_generation_defaults, isolated_removal_rendering_defaults, isolated_removal_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__isolated_after_removal_count",
        )
    )
    assert sorted(isolated_removal_generation_defaults["graph_directionality_weights"].keys()) == ["directed", "undirected"]
    assert set(isolated_removal_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(isolated_removal_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(isolated_removal_generation_defaults["balanced_graph_directionality_sampling"]) is True
    assert bool(isolated_removal_generation_defaults["balanced_target_count_sampling"]) is True
    assert int(isolated_removal_generation_defaults["target_count_min"]) == 0
    assert int(isolated_removal_generation_defaults["target_count_max"]) == 5
    assert int(isolated_removal_rendering_defaults["canvas_width"]) > 0
    assert str(isolated_removal_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(isolated_removal_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(isolated_removal_prompt_defaults["task_key"]).strip() == "isolated_node_count_after_node_removal_query"
    assert str(isolated_removal_prompt_defaults["object_description_undirected"]).strip()
    assert str(isolated_removal_prompt_defaults["object_description_directed"]).strip()

    articulation_generation_defaults, articulation_rendering_defaults, articulation_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__articulation_point_count",
        )
    )
    assert sorted(articulation_generation_defaults["query_variant_weights"].keys()) == ["articulation_point_count"]
    assert set(articulation_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(articulation_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(articulation_generation_defaults["node_count_min"]) == 5
    assert int(articulation_generation_defaults["node_count_max"]) == 10
    assert int(articulation_generation_defaults["target_count_min"]) == 0
    assert int(articulation_generation_defaults["target_count_max"]) == 5
    assert int(articulation_rendering_defaults["canvas_width"]) > 0
    assert int(articulation_rendering_defaults["node_radius_min_px"]) > 0
    assert str(articulation_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(articulation_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(articulation_prompt_defaults["task_key"]).strip() == "articulation_point_count_query"
    assert str(articulation_prompt_defaults["question_text_articulation_point_count"]).strip()

    bridge_generation_defaults, bridge_rendering_defaults, bridge_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__bridge_count",
        )
    )
    assert sorted(bridge_generation_defaults["query_variant_weights"].keys()) == ["bridge_count"]
    assert set(bridge_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(bridge_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(bridge_generation_defaults["node_count_min"]) == 5
    assert int(bridge_generation_defaults["node_count_max"]) == 10
    assert int(bridge_generation_defaults["target_count_min"]) == 0
    assert int(bridge_generation_defaults["target_count_max"]) == 5
    assert int(bridge_rendering_defaults["canvas_width"]) > 0
    assert int(bridge_rendering_defaults["node_radius_min_px"]) > 0
    assert str(bridge_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(bridge_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(bridge_prompt_defaults["task_key"]).strip() == "bridge_count_query"
    assert str(bridge_prompt_defaults["question_text_bridge_count"]).strip()


def test_graph_relation_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "relation")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 6
    assert int(generation_shared["node_count_max"]) == 15
    assert int(generation_shared["component_count_min"]) == 2
    assert int(generation_shared["component_count_max"]) == 4
    assert int(generation_shared["target_component_size_min"]) == 2
    assert int(generation_shared["target_component_size_max"]) == 7
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_shared["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared["node_shape_variant_weights"].keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(generation_shared["layout_transform_variant_weights"].keys()) == {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert set(generation_shared["node_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }
    assert bool(generation_shared["balanced_topology_profile_sampling"]) is True
    assert bool(generation_shared["balanced_label_variant_sampling"]) is True
    assert bool(generation_shared["balanced_layout_variant_sampling"]) is True
    assert bool(generation_shared["balanced_node_shape_variant_sampling"]) is True
    assert bool(generation_shared["balanced_layout_transform_variant_sampling"]) is True
    assert bool(generation_shared["balanced_node_color_name_sampling"]) is True

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["node_radius_min_px"]) > 0
    assert int(render_shared["node_radius_max_px"]) >= int(render_shared["node_radius_min_px"])

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "graph_relation_v0"
    assert str(prompt_shared["scene_key"]).strip() == "single_graph_relation"
    assert str(prompt_shared["task_key"]).strip() == "same_component_count_query"
    assert str(prompt_shared["object_description"]).strip()
    assert str(prompt_shared["object_description_directed"]).strip()
    assert str(prompt_shared["question_text_same_component_count"]).strip()
    assert str(prompt_shared["evidence_hint"]).strip()
    assert str(prompt_shared["answer_hint"]).strip()
    assert str(prompt_shared["json_example"]).strip()
    assert str(prompt_shared["json_example_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "topology_reasoning": 0.45,
        "visual_scan": 0.25,
        "ambiguity": 0.20,
        "clutter": 0.10,
    }

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="graph_node_link_same_component_count_internal",
    )
    assert sorted(generation_defaults["query_variant_weights"].keys()) == ["same_component_count"]
    assert set(generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(generation_defaults["node_count_min"]) == 6
    assert int(generation_defaults["node_count_max"]) == 15
    assert int(generation_defaults["component_count_min"]) == 2
    assert int(generation_defaults["component_count_max"]) == 4
    assert int(generation_defaults["target_component_size_min"]) == 2
    assert int(generation_defaults["target_component_size_max"]) == 7
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(prompt_defaults["task_key"]).strip() == "same_component_count_query"
    assert str(prompt_defaults["question_text_same_component_count"]).strip()

    reachable_generation_defaults, reachable_rendering_defaults, reachable_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__reachable_node_count",
    )
    assert sorted(reachable_generation_defaults["query_variant_weights"].keys()) == ["reachable_count"]
    assert set(reachable_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(reachable_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(reachable_generation_defaults["node_count_min"]) == 5
    assert int(reachable_generation_defaults["directed_node_count_max"]) == 9
    assert int(reachable_generation_defaults["target_reachable_count_min"]) == 1
    assert int(reachable_generation_defaults["target_reachable_count_max"]) == 7
    assert int(reachable_rendering_defaults["canvas_width"]) > 0
    assert int(reachable_rendering_defaults["node_radius_min_px"]) > 0
    assert str(reachable_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(reachable_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(reachable_prompt_defaults["task_key"]).strip() == "reachable_count_query"
    assert str(reachable_prompt_defaults["object_description_directed"]).strip()
    assert str(reachable_prompt_defaults["question_text_reachable_count"]).strip()
    assert str(reachable_prompt_defaults["evidence_hint_reachable_count"]).strip()

    reachable_edge_edit_generation_defaults, reachable_edge_edit_rendering_defaults, reachable_edge_edit_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__reachable_node_count_after_edge_edit",
    )
    assert sorted(reachable_edge_edit_generation_defaults["edge_edit_operation_weights"].keys()) == [
        "edge_addition",
        "edge_removal",
    ]
    assert set(reachable_edge_edit_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(reachable_edge_edit_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(reachable_edge_edit_generation_defaults["balanced_edge_edit_operation_sampling"]) is True
    assert bool(reachable_edge_edit_generation_defaults["balanced_target_reachable_count_sampling"]) is True
    assert int(reachable_edge_edit_generation_defaults["node_count_min"]) == 5
    assert int(reachable_edge_edit_generation_defaults["directed_node_count_max"]) == 10
    assert int(reachable_edge_edit_generation_defaults["target_reachable_count_min"]) == 1
    assert int(reachable_edge_edit_generation_defaults["target_reachable_count_max"]) == 8
    assert int(reachable_edge_edit_rendering_defaults["canvas_width"]) > 0
    assert int(reachable_edge_edit_rendering_defaults["node_radius_min_px"]) > 0
    assert str(reachable_edge_edit_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(reachable_edge_edit_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(reachable_edge_edit_prompt_defaults["task_key"]).strip() == "reachable_count_after_edge_edit_query"
    assert str(reachable_edge_edit_prompt_defaults["object_description_directed"]).strip()
    assert str(reachable_edge_edit_prompt_defaults["evidence_hint"]).strip()

    common_generation_defaults, common_rendering_defaults, common_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__common_neighbor_count",
    )
    assert sorted(common_generation_defaults["common_neighbor_mode_weights"].keys()) == [
        "directed_common_predecessor",
        "directed_common_successor",
        "undirected_common_neighbor",
    ]
    assert set(common_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(common_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(common_generation_defaults["balanced_common_neighbor_mode_sampling"]) is True
    assert bool(common_generation_defaults["balanced_target_count_sampling"]) is True
    assert int(common_generation_defaults["node_count_min"]) == 6
    assert int(common_generation_defaults["node_count_max"]) == 10
    assert int(common_generation_defaults["directed_node_count_max"]) == 10
    assert int(common_generation_defaults["target_count_min"]) == 0
    assert int(common_generation_defaults["target_count_max"]) == 4
    assert int(common_rendering_defaults["canvas_width"]) > 0
    assert int(common_rendering_defaults["node_radius_min_px"]) > 0
    assert str(common_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(common_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(common_prompt_defaults["task_key"]).strip() == "common_neighbor_count_query"
    assert str(common_prompt_defaults["object_description"]).strip()
    assert str(common_prompt_defaults["object_description_directed"]).strip()
    assert str(common_prompt_defaults["evidence_hint"]).strip()

    edge_attribute_generation_defaults, edge_attribute_rendering_defaults, edge_attribute_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__edge_attribute_label",
    )
    assert sorted(edge_attribute_generation_defaults["graph_directionality_weights"].keys()) == ["directed", "undirected"]
    assert int(edge_attribute_generation_defaults["edge_label_support_size"]) == 6
    assert set(edge_attribute_generation_defaults["query_variant_weights"].keys()) == {
        "edge_between_nodes_label",
        "directed_edge_between_nodes_label",
        "shortest_path_first_edge_label",
    }
    assert set(edge_attribute_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(edge_attribute_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(edge_attribute_generation_defaults["balanced_query_variant_sampling"]) is True
    assert bool(edge_attribute_generation_defaults["balanced_target_edge_label_sampling"]) is True
    assert int(edge_attribute_generation_defaults["node_count_min"]) == 5
    assert int(edge_attribute_generation_defaults["node_count_max"]) == 8
    assert int(edge_attribute_generation_defaults["directed_node_count_max"]) == 8
    assert int(edge_attribute_generation_defaults["target_shortest_path_length_min"]) == 2
    assert int(edge_attribute_generation_defaults["target_shortest_path_length_max"]) == 3
    assert int(edge_attribute_rendering_defaults["canvas_width"]) > 0
    assert int(edge_attribute_rendering_defaults["node_radius_min_px"]) > 0
    assert str(edge_attribute_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(edge_attribute_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(edge_attribute_prompt_defaults["task_key"]).strip() == "edge_attribute_label_query"
    assert str(edge_attribute_prompt_defaults["object_description_undirected"]).strip()
    assert str(edge_attribute_prompt_defaults["object_description_directed"]).strip()
    assert str(edge_attribute_prompt_defaults["evidence_hint"]).strip()

    edge_edit_generation_defaults, edge_edit_rendering_defaults, edge_edit_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="graph_node_link_component_size_after_edge_edit_internal",
    )
    assert sorted(edge_edit_generation_defaults["edge_edit_operation_weights"].keys()) == [
        "edge_addition",
        "edge_removal",
    ]
    assert set(edge_edit_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(edge_edit_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(edge_edit_generation_defaults["balanced_edge_edit_operation_sampling"]) is True
    assert bool(edge_edit_generation_defaults["balanced_target_component_size_sampling"]) is True
    assert int(edge_edit_generation_defaults["node_count_min"]) == 5
    assert int(edge_edit_generation_defaults["node_count_max"]) == 12
    assert int(edge_edit_generation_defaults["target_component_size_min"]) == 1
    assert int(edge_edit_generation_defaults["target_component_size_max"]) == 8
    assert int(edge_edit_rendering_defaults["canvas_width"]) > 0
    assert int(edge_edit_rendering_defaults["node_radius_min_px"]) > 0
    assert str(edge_edit_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(edge_edit_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(edge_edit_prompt_defaults["task_key"]).strip() == "component_size_after_edge_edit_query"
    assert str(edge_edit_prompt_defaults["object_description"]).strip()
    assert str(edge_edit_prompt_defaults["evidence_hint"]).strip()

    cycle_generation_defaults, cycle_rendering_defaults, cycle_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__unique_cycle_size",
    )
    assert sorted(cycle_generation_defaults["query_variant_weights"].keys()) == ["unique_cycle_size"]
    assert set(cycle_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(cycle_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(cycle_generation_defaults["node_count_min"]) == 5
    assert int(cycle_generation_defaults["node_count_max"]) == 10
    assert int(cycle_generation_defaults["target_cycle_size_min"]) == 3
    assert int(cycle_generation_defaults["target_cycle_size_max"]) == 7
    assert int(cycle_rendering_defaults["canvas_width"]) > 0
    assert int(cycle_rendering_defaults["node_radius_min_px"]) > 0
    assert str(cycle_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(cycle_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(cycle_prompt_defaults["task_key"]).strip() == "unique_cycle_size_query"
    assert str(cycle_prompt_defaults["question_text_unique_cycle_size"]).strip()


def test_graph_comparison_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "comparison")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 6
    assert int(generation_shared["node_count_max"]) == 15
    assert int(generation_shared["component_count_min"]) == 2
    assert int(generation_shared["component_count_max"]) == 4
    assert int(generation_shared["target_largest_component_size_min"]) == 3
    assert int(generation_shared["target_largest_component_size_max"]) == 9
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_shared["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared["node_shape_variant_weights"].keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(generation_shared["layout_transform_variant_weights"].keys()) == {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert set(generation_shared["node_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "graph_comparison_v0"
    assert str(prompt_shared["scene_key"]).strip() == "single_graph_comparison"
    assert str(prompt_shared["task_key"]).strip() == "largest_component_size_query"
    assert str(prompt_shared["object_description"]).strip()
    assert str(prompt_shared["question_text_largest_component_size"]).strip()
    assert str(prompt_shared["evidence_hint"]).strip()
    assert str(prompt_shared["answer_hint"]).strip()
    assert str(prompt_shared["json_example"]).strip()
    assert str(prompt_shared["json_example_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "topology_reasoning": 0.45,
        "visual_scan": 0.20,
        "ambiguity": 0.25,
        "clutter": 0.10,
    }

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="graph_node_link_largest_component_size_internal",
    )
    assert sorted(generation_defaults["query_variant_weights"].keys()) == ["largest_component_size"]
    assert set(generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(generation_defaults["node_count_min"]) == 6
    assert int(generation_defaults["node_count_max"]) == 15
    assert int(generation_defaults["component_count_min"]) == 2
    assert int(generation_defaults["component_count_max"]) == 4
    assert int(generation_defaults["target_largest_component_size_min"]) == 3
    assert int(generation_defaults["target_largest_component_size_max"]) == 9
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_comparison_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "single_graph_comparison"
    assert str(prompt_defaults["task_key"]).strip() == "largest_component_size_query"
    assert str(prompt_defaults["question_text_largest_component_size"]).strip()

    extreme_generation_defaults, extreme_rendering_defaults, extreme_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__degree_extremum_value",
        )
    )
    assert sorted(extreme_generation_defaults["graph_directionality_weights"].keys()) == ["directed", "undirected"]
    assert sorted(extreme_generation_defaults["degree_mode_weights"].keys()) == [
        "in_degree",
        "out_degree",
        "total_degree",
    ]
    assert sorted(extreme_generation_defaults["extremum_mode_weights"].keys()) == ["max", "min"]
    assert set(extreme_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(extreme_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(extreme_generation_defaults["balanced_graph_directionality_sampling"]) is True
    assert bool(extreme_generation_defaults["balanced_degree_mode_sampling"]) is True
    assert bool(extreme_generation_defaults["balanced_extremum_mode_sampling"]) is True
    assert int(extreme_generation_defaults["node_count_min"]) == 5
    assert int(extreme_generation_defaults["node_count_max"]) == 10
    assert int(extreme_generation_defaults["directed_node_count_max"]) == 10
    assert int(extreme_generation_defaults["target_degree_min"]) == 0
    assert int(extreme_generation_defaults["target_degree_max"]) == 4
    assert int(extreme_rendering_defaults["canvas_width"]) > 0
    assert int(extreme_rendering_defaults["node_radius_min_px"]) > 0
    assert str(extreme_prompt_defaults["bundle_id"]).strip() == "graph_comparison_v0"
    assert str(extreme_prompt_defaults["scene_key"]).strip() == "single_graph_comparison"
    assert str(extreme_prompt_defaults["task_key"]).strip() == "extreme_degree_value_query"
    assert str(extreme_prompt_defaults["object_description_undirected"]).strip()
    assert str(extreme_prompt_defaults["object_description_directed"]).strip()


def test_graph_path_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "path")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 5
    assert int(generation_shared["node_count_max"]) == 15
    assert int(generation_shared["directed_node_count_max"]) == 15
    assert int(generation_shared["target_shortest_path_length_min"]) == 3
    assert int(generation_shared["target_shortest_path_length_max"]) == 7
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_shared["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared["node_shape_variant_weights"].keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(generation_shared["layout_transform_variant_weights"].keys()) == {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert set(generation_shared["node_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["node_radius_min_px"]) > 0
    assert int(render_shared["node_radius_max_px"]) >= int(render_shared["node_radius_min_px"])

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "graph_path_v0"
    assert str(prompt_shared["scene_key"]).strip() == "single_graph_path"
    assert str(prompt_shared["task_key"]).strip() == "shortest_path_length_query"
    assert str(prompt_shared["object_description"]).strip()
    assert str(prompt_shared["object_description_directed"]).strip()
    assert str(prompt_shared["question_text_shortest_path_length"]).strip()
    assert str(prompt_shared["question_text_directed_shortest_path_length"]).strip()
    assert str(prompt_shared["evidence_hint"]).strip()
    assert str(prompt_shared["answer_hint"]).strip()
    assert str(prompt_shared["json_example"]).strip()
    assert str(prompt_shared["json_example_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "topology_reasoning": 0.50,
        "visual_scan": 0.20,
        "ambiguity": 0.20,
        "clutter": 0.10,
    }

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__shortest_path_length",
    )
    assert generation_defaults["query_variant_weights"] == {
        "shortest_path_length": 1.0,
        "directed_shortest_path_length": 1.0,
    }
    assert set(generation_defaults["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(generation_defaults["node_count_min"]) == 5
    assert int(generation_defaults["node_count_max"]) == 15
    assert int(generation_defaults["directed_node_count_max"]) == 15
    assert int(generation_defaults["target_shortest_path_length_min"]) == 3
    assert int(generation_defaults["target_shortest_path_length_max"]) == 7
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_path_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "single_graph_path"

    longest_generation_defaults, longest_rendering_defaults, longest_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__longest_path_length",
    )
    assert set(longest_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(longest_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(longest_generation_defaults["balanced_target_longest_path_length_sampling"]) is True
    assert int(longest_generation_defaults["node_count_min"]) == 5
    assert int(longest_generation_defaults["directed_node_count_max"]) == 10
    assert int(longest_generation_defaults["target_longest_path_length_min"]) == 2
    assert int(longest_generation_defaults["target_longest_path_length_max"]) == 6
    assert int(longest_rendering_defaults["canvas_width"]) > 0
    assert int(longest_rendering_defaults["node_radius_min_px"]) > 0
    assert str(longest_prompt_defaults["bundle_id"]).strip() == "graph_path_v0"
    assert str(longest_prompt_defaults["scene_key"]).strip() == "single_graph_path"
    assert str(longest_prompt_defaults["task_key"]).strip() == "longest_path_length_query"
    assert str(longest_prompt_defaults["object_description_directed"]).strip()
    assert str(longest_prompt_defaults["evidence_hint"]).strip()


def test_graph_order_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "order")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 3
    assert int(generation_shared["node_count_max"]) == 7
    assert int(generation_shared["target_position_min"]) == 1
    assert int(generation_shared["target_position_max"]) == 7
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_shared["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared["node_shape_variant_weights"].keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(generation_shared["layout_transform_variant_weights"].keys()) == {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert set(generation_shared["node_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["node_radius_min_px"]) > 0
    assert int(render_shared["node_radius_max_px"]) >= int(render_shared["node_radius_min_px"])

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "graph_order_v0"
    assert str(prompt_shared["scene_key"]).strip() == "single_graph_order"
    assert str(prompt_shared["task_key"]).strip() == "topological_position_query"
    assert str(prompt_shared["object_description"]).strip()
    assert str(prompt_shared["question_text_topological_position"]).strip()
    assert str(prompt_shared["evidence_hint"]).strip()
    assert str(prompt_shared["answer_hint"]).strip()
    assert str(prompt_shared["json_example"]).strip()
    assert str(prompt_shared["json_example_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "topology_reasoning": 0.50,
        "visual_scan": 0.20,
        "ambiguity": 0.20,
        "clutter": 0.10,
    }

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__topological_position_value",
    )
    assert sorted(generation_defaults["query_variant_weights"].keys()) == ["topological_position"]
    assert set(generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(generation_defaults["node_count_min"]) == 3
    assert int(generation_defaults["node_count_max"]) == 7
    assert int(generation_defaults["target_position_min"]) == 1
    assert int(generation_defaults["target_position_max"]) == 7
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_order_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "single_graph_order"


def test_graph_optimization_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "optimization")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 4
    assert int(generation_shared["node_count_max"]) == 7
    assert int(generation_shared["extra_edge_count_min"]) == 1
    assert int(generation_shared["extra_edge_count_max"]) == 2
    assert int(generation_shared["edge_weight_min"]) == 1
    assert int(generation_shared["edge_weight_max"]) == 9
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_shared["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared["node_shape_variant_weights"].keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(generation_shared["layout_transform_variant_weights"].keys()) == {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert set(generation_shared["node_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }

    rendering_shared = cfg["rendering"]["shared"]
    assert int(rendering_shared["canvas_width"]) > 0
    assert int(rendering_shared["edge_weight_label_font_size_px"]) == 22
    assert int(rendering_shared["edge_weight_label_offset_px"]) == 24
    assert int(rendering_shared["edge_weight_label_padding_px"]) == 7

    complexity_shared = cfg["complexity"]["shared"]["criteria_weights"]
    assert set(complexity_shared.keys()) == {"topology_reasoning", "visual_scan", "ambiguity", "clutter"}

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "graph_optimization_v0"
    assert str(prompt_shared["scene_key"]).strip() == "single_graph_optimization"

    _, _, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__mst_weight",
    )
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_optimization_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "single_graph_optimization"
    assert str(prompt_defaults["object_description_undirected"]).strip() == "a labeled connected weighted graph"
    assert str(prompt_defaults["question_text_minimum_spanning_tree_weight"]).strip()
    assert str(prompt_defaults["evidence_hint"]).strip()
    assert str(prompt_defaults["answer_hint"]).strip()
    assert str(prompt_defaults["json_example"]).strip()
    assert str(prompt_defaults["json_example_answer_only"]).strip()


def test_icons_transformation_defaults_loaded() -> None:
    cfg = get_task_group_defaults("icons", "transformation")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["object_count_min"]) == 4
    assert int(generation_shared["object_count_max"]) == 9
    assert int(generation_shared["target_count_min"]) == 0
    assert int(generation_shared["target_count_max"]) == 4
    assert int(generation_shared["distractor_count_min"]) == 1
    assert int(generation_shared["distractor_count_max"]) == 9
    assert bool(generation_shared["balanced_sampling"]) is True
    assert "task_icons__pair_grid__pair_attribute_rule_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__pair_grid__pair_geometric_transform_count" in cfg["generation"]["task_overrides"]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["reference_panel_width_px"]) > 0
    assert int(render_shared["scene_icon_size_min_px"]) > 0
    assert int(render_shared["scene_icon_size_max_px"]) >= int(render_shared["scene_icon_size_min_px"])
    assert int(render_shared["cell_padding_px"]) > 0
    assert int(render_shared["cell_label_font_size_px"]) > 0
    assert int(render_shared["pair_arrow_stroke_px"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip()
    assert str(prompt_shared["scene_key"]).strip()
    assert str(prompt_shared["task_key"]).strip()
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "visual_scan": 0.20,
        "ambiguity": 0.20,
        "clutter": 0.15,
        "rule_inference": 0.45,
    }

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__pair_grid__pair_geometric_transform_count",
    )
    assert str(generation["pool_manifest"]).strip() == "non_symmetry.txt"
    assert list(generation["transform_ids"]) == [
        "rot90",
        "rot180",
        "rot270",
        "flip_h",
        "flip_v",
        "flip_diag_main",
        "flip_diag_anti",
    ]
    assert int(generation["transform_check_size_px"]) > 0
    assert int(rendering["canvas_width"]) > 0
    assert int(rendering["reference_panel_width_px"]) > 0
    assert str(prompt["object_description"]).strip()
    assert str(prompt["question_text"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["json_example"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()

    attribute_generation, attribute_rendering, attribute_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__pair_grid__pair_attribute_rule_count",
    )
    assert str(attribute_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert sorted(attribute_generation["attribute_rule_weights"].keys()) == [
        "color_and_size_change",
        "color_only_change",
        "size_only_change",
    ]
    assert bool(attribute_generation["balanced_attribute_rule_sampling"]) is True
    assert float(attribute_generation["size_scale_small"]) < 1.0 < float(attribute_generation["size_scale_large"])
    assert int(attribute_rendering["reference_icon_size_px"]) > 0
    assert int(attribute_rendering["palette_size_min"]) >= 2
    assert int(attribute_rendering["palette_size_max"]) >= int(attribute_rendering["palette_size_min"])
    assert str(attribute_prompt["object_description"]).strip()
    assert str(attribute_prompt["question_text"]).strip()
    assert str(attribute_prompt["evidence_hint"]).strip()
    assert str(attribute_prompt["answer_hint"]).strip()
    assert str(attribute_prompt["json_example"]).strip()
    assert str(attribute_prompt["json_example_answer_only"]).strip()


def test_icons_relation_defaults_loaded() -> None:
    cfg = get_task_group_defaults("icons", "relation")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["object_count_min"]) >= 1
    assert int(generation_shared["object_count_max"]) >= int(generation_shared["object_count_min"])
    assert int(generation_shared["target_count_min"]) == 0
    assert int(generation_shared["target_count_max"]) == 5
    assert int(generation_shared["distractor_count_min"]) == 1
    assert int(generation_shared["distractor_count_max"]) == 10
    assert int(generation_shared["distractor_margin_over_target"]) == 1
    assert bool(generation_shared["balanced_sampling"]) is True
    assert bool(generation_shared["balanced_variant_sampling"]) is True
    assert "task_icons__two_anchor__between_anchors_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__mirror_grid__mirror_symmetry_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__overlap_grid__occlusion_order_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__mirror_grid__reflection_match_label" in cfg["generation"]["task_overrides"]
    assert "task_icons__reference_canvas__anchor_position_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__named_field__reference_distance_rank_label" in cfg["generation"]["task_overrides"]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["reference_panel_width_px"]) > 0
    assert int(render_shared["scene_icon_size_min_px"]) > 0
    assert int(render_shared["scene_icon_size_max_px"]) >= int(render_shared["scene_icon_size_min_px"])
    assert 0.0 <= float(render_shared["scene_max_overlap_fraction"]) <= 1.0
    assert int(render_shared["anchor_gap_px_directional"]) > 0
    assert float(render_shared["anchor_target_area_ratio_min"]) > 0.0
    assert float(render_shared["anchor_target_area_ratio_max"]) >= float(render_shared["anchor_target_area_ratio_min"])
    assert float(render_shared["anchor_opposite_area_ratio_min"]) > 0.0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip()
    assert str(prompt_shared["scene_key"]).strip()
    assert str(prompt_shared["task_key"]).strip()
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "visual_scan": 0.05,
        "ambiguity": 0.35,
        "clutter": 0.05,
        "spatial_reasoning": 0.55,
    }

    mirror_generation, mirror_rendering, mirror_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__mirror_grid__mirror_symmetry_count",
    )
    assert str(mirror_generation["pool_manifest"]).strip() == "non_symmetry.txt"
    assert int(mirror_generation["object_count_min"]) == 6
    assert int(mirror_generation["object_count_max"]) == 6
    assert int(mirror_generation["target_count_max"]) == 4
    assert int(mirror_generation["distractor_count_min"]) == 2
    assert int(mirror_generation["distractor_count_max"]) == 6
    mirror_signature_weights = {
        str(key): float(value)
        for key, value in dict(mirror_generation["mirror_signature_weights"]).items()
        if str(key)
        in {
            "mirror_vertical",
            "mirror_horizontal",
            "mirror_diagonal_main",
            "mirror_diagonal_anti",
            "mirror_both_axes",
        }
    }
    assert mirror_signature_weights == {
        "mirror_vertical": 1.0,
        "mirror_horizontal": 1.0,
        "mirror_diagonal_main": 1.0,
        "mirror_diagonal_anti": 1.0,
        "mirror_both_axes": 1.0,
    }
    assert int(mirror_rendering["canvas_width"]) == 1104
    assert int(mirror_rendering["canvas_height"]) == 640
    assert int(mirror_rendering["reference_panel_width_px"]) == 296
    assert list(mirror_rendering["symmetric_icon_count_choices"]) == [2, 4, 6]
    assert list(mirror_rendering["both_axes_icon_count_choices"]) == [4]
    assert list(mirror_rendering["nonsymmetric_icon_count_choices"]) == [2, 4, 6]
    assert int(mirror_rendering["patch_inner_margin_px"]) == 8
    assert int(mirror_rendering["patch_min_gap_px"]) == 6
    assert str(mirror_prompt["scene_key"]).strip() == "reference_grid_mirror_symmetry_relation"
    assert str(mirror_prompt["object_description"]).strip()
    assert str(mirror_prompt["question_text"]).strip()
    assert str(mirror_prompt["evidence_hint"]).strip()
    assert str(mirror_prompt["answer_hint"]).strip()
    assert str(mirror_prompt["json_example"]).strip()
    assert str(mirror_prompt["json_example_answer_only"]).strip()

    reflection_generation, reflection_rendering, reflection_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__mirror_grid__reflection_match_label",
    )
    assert str(reflection_generation["pool_manifest"]).strip() == "non_symmetry.txt"
    assert int(reflection_generation["object_count_min"]) == 5
    assert int(reflection_generation["object_count_max"]) == 5
    assert bool(reflection_generation["shuffle_scene_labels"]) is True
    assert dict(reflection_generation["reflection_query_weights"]) == {
        "vertical_reflection_match": 1.0,
        "horizontal_reflection_match": 1.0,
        "diagonal_main_reflection_match": 1.0,
        "diagonal_anti_reflection_match": 1.0,
    }
    assert int(reflection_rendering["canvas_width"]) == 1104
    assert int(reflection_rendering["canvas_height"]) == 640
    assert int(reflection_rendering["reference_panel_width_px"]) == 296
    assert list(reflection_rendering["nonsymmetric_icon_count_choices"]) == [2, 3]
    assert int(reflection_rendering["wrong_axis_distractor_count"]) == 1
    assert str(reflection_prompt["scene_key"]).strip() == "reference_grid_mirror_symmetry_relation"
    for suffix in (
        "vertical_reflection_match",
        "horizontal_reflection_match",
        "diagonal_main_reflection_match",
        "diagonal_anti_reflection_match",
    ):
        assert str(reflection_prompt[f"question_text_{suffix}"]).strip()
    assert str(reflection_prompt["evidence_hint"]).strip()
    assert str(reflection_prompt["answer_hint"]).strip()
    assert str(reflection_prompt["json_example"]).strip()
    assert str(reflection_prompt["json_example_answer_only"]).strip()

    strip_generation, strip_rendering, strip_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__two_anchor__between_anchors_count",
    )
    assert str(strip_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert int(strip_generation["target_count_max"]) == 5
    assert int(strip_generation["distractor_count_max"]) == 10
    assert dict(strip_generation["strip_axis_weights"]) == {"vertical": 1.0, "horizontal": 1.0}
    assert float(strip_rendering["scene_max_overlap_fraction"]) == 0.08
    assert int(strip_rendering["strip_boundary_margin_px"]) == 14
    assert float(strip_rendering["strip_span_ratio_min"]) == 0.32
    assert float(strip_rendering["strip_span_ratio_max"]) == 0.60
    assert str(strip_prompt["scene_key"]).strip() == "scene_two_anchor_relation"
    assert str(strip_prompt["object_description"]).strip()
    assert str(strip_prompt["question_text_vertical_strip"]).strip()
    assert str(strip_prompt["question_text_horizontal_strip"]).strip()
    assert str(strip_prompt["evidence_hint"]).strip()
    assert str(strip_prompt["answer_hint"]).strip()
    assert str(strip_prompt["json_example"]).strip()
    assert str(strip_prompt["json_example_answer_only"]).strip()

    occlusion_generation, occlusion_rendering, occlusion_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__overlap_grid__occlusion_order_count",
    )
    assert str(occlusion_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert int(occlusion_generation["object_count_min"]) == 2
    assert int(occlusion_generation["object_count_max"]) == 8
    assert int(occlusion_generation["target_count_max"]) == 4
    assert int(occlusion_generation["distractor_count_max"]) == 5
    assert int(occlusion_generation["distractor_margin_over_target"]) == 0
    assert int(occlusion_rendering["canvas_width"]) == 1104
    assert int(occlusion_rendering["reference_panel_width_px"]) == 296
    assert float(occlusion_rendering["min_color_distance"]) == 40.0
    assert float(occlusion_rendering["pair_min_color_distance"]) == 80.0
    assert list(occlusion_rendering["overlap_ratio_range"]) == [0.40, 0.60]
    assert str(occlusion_prompt["scene_key"]).strip() == "reference_grid_occlusion_relation"
    assert str(occlusion_prompt["object_description"]).strip()
    assert str(occlusion_prompt["question_text"]).strip()
    assert str(occlusion_prompt["evidence_hint"]).strip()
    assert str(occlusion_prompt["answer_hint"]).strip()
    assert str(occlusion_prompt["json_example"]).strip()
    assert str(occlusion_prompt["json_example_answer_only"]).strip()

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__reference_canvas__anchor_position_count",
    )
    assert str(generation["pool_manifest"]).strip() == "all_icons.txt"
    assert dict(generation["direction_weights"]) == {"left": 1.0, "right": 1.0, "above": 1.0, "below": 1.0}
    assert int(rendering["canvas_width"]) > 0
    assert float(rendering["scene_max_overlap_fraction"]) == 0.05
    assert int(rendering["anchor_gap_px_directional"]) == 8
    assert str(prompt["object_description"]).strip()
    assert str(prompt["question_text_left"]).strip()
    assert str(prompt["question_text_right"]).strip()
    assert str(prompt["question_text_above"]).strip()
    assert str(prompt["question_text_below"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["json_example"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()

    distance_generation, distance_rendering, distance_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__named_field__reference_distance_rank_label",
    )
    assert int(distance_generation["candidate_count"]) == 6
    assert int(distance_generation["distractor_count_min"]) == 4
    assert int(distance_generation["distractor_count_max"]) == 8
    assert dict(distance_generation["distance_rank_query_weights"]) == {
        "closest_to_named_reference_label": 1.0,
        "second_closest_to_named_reference_label": 1.0,
        "farthest_from_named_reference_label": 1.0,
    }
    assert list(distance_generation["named_icon_fill_style_support"]) == ["solid", "striped", "dotted", "half_filled"]
    assert int(distance_rendering["canvas_width"]) == 960
    assert int(distance_rendering["canvas_height"]) == 560
    assert int(distance_rendering["scene_icon_size_min_px"]) == 50
    assert int(distance_rendering["scene_icon_size_max_px"]) == 72
    assert int(distance_rendering["distance_rank_margin_px"]) == 24
    assert int(distance_rendering["candidate_label_font_size_px"]) == 24
    assert str(distance_prompt["scene_key"]).strip() == "named_reference_distance_relation"
    assert str(distance_prompt["object_description"]).strip()
    assert str(distance_prompt["question_text_closest_to_named_reference_label"]).strip()
    assert str(distance_prompt["question_text_second_closest_to_named_reference_label"]).strip()
    assert str(distance_prompt["question_text_farthest_from_named_reference_label"]).strip()
    assert str(distance_prompt["evidence_hint"]).strip()
    assert str(distance_prompt["answer_hint"]).strip()
    assert str(distance_prompt["json_example"]).strip()
    assert str(distance_prompt["json_example_answer_only"]).strip()


def test_icons_sequence_defaults_loaded() -> None:
    cfg = get_task_group_defaults("icons", "sequence")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "visual_scan": 0.25,
        "ambiguity": 0.20,
        "clutter": 0.10,
        "rule_inference": 0.45,
    }

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["sequence_length_min"]) == 4
    assert int(generation_shared["sequence_length_max"]) == 6
    assert int(generation_shared["target_count_min"]) == 0
    assert int(generation_shared["target_count_max"]) == 10
    assert int(generation_shared["step_abs_min"]) == 1
    assert int(generation_shared["step_abs_max"]) == 3
    assert bool(generation_shared["balanced_sampling"]) is True
    assert "task_icons__sequence_strip__missing_count_value" in cfg["generation"]["task_overrides"]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["scene_icon_size_min_px"]) == 24
    assert int(render_shared["scene_icon_size_max_px"]) == 40
    assert float(render_shared["scene_max_overlap_fraction"]) == pytest.approx(0.20, rel=1e-9)
    assert int(render_shared["cell_padding_px"]) > 0
    assert int(render_shared["cell_icon_padding_px"]) >= 0
    assert int(render_shared["cell_box_width_min_px"]) == 112
    assert int(render_shared["cell_box_width_max_px"]) == 160
    assert int(render_shared["cell_box_height_min_px"]) == 96
    assert int(render_shared["cell_box_height_max_px"]) == 144
    assert int(render_shared["cell_label_font_size_px"]) > 0
    assert int(render_shared["missing_mark_font_size_px"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip()
    assert str(prompt_shared["scene_key"]).strip()
    assert str(prompt_shared["task_key"]).strip()
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__sequence_strip__missing_count_value",
    )
    assert str(generation["pool_manifest"]).strip() == "all_icons.txt"
    assert list(generation["rotation_candidates_degrees"]) == [0, 90, 180, 270]
    assert int(rendering["scene_icon_size_min_px"]) == 24
    assert int(rendering["scene_icon_size_max_px"]) == 40
    assert str(prompt["object_description"]).strip()
    assert str(prompt["question_text"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["json_example"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()


def test_icons_pattern_defaults_loaded() -> None:
    cfg = get_task_group_defaults("icons", "pattern")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "visual_scan": 0.25,
        "ambiguity": 0.20,
        "clutter": 0.10,
        "rule_inference": 0.45,
    }

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["grid_rows"]) == 3
    assert int(generation_shared["grid_cols"]) == 3
    assert int(generation_shared["answer_index_min"]) == 1
    assert int(generation_shared["answer_index_max"]) == 9
    assert bool(generation_shared["balanced_sampling"]) is True
    assert "task_icons__pattern_grid__color_pattern_violation_index" in cfg["generation"]["task_overrides"]
    assert "task_icons__sequence_strip__rotation_sequence_violation_index" in cfg["generation"]["task_overrides"]
    assert "task_icons__pattern_grid__size_pattern_violation_index" in cfg["generation"]["task_overrides"]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["scene_icon_size_min_px"]) == 48
    assert int(render_shared["scene_icon_size_max_px"]) == 72
    assert int(render_shared["cell_box_width_min_px"]) == 104
    assert int(render_shared["cell_box_width_max_px"]) == 140
    assert int(render_shared["cell_box_height_min_px"]) == 104
    assert int(render_shared["cell_box_height_max_px"]) == 140
    assert int(render_shared["scene_content_side_padding_px"]) == 10
    assert int(render_shared["scene_content_bottom_padding_px"]) == 10
    assert int(render_shared["scene_content_top_offset_px"]) == 40

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "icons_pattern_v0"
    assert str(prompt_shared["scene_key"]).strip() == "structured_violation_scene"
    assert str(prompt_shared["task_key"]).strip() == "structured_violation_query"
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__sequence_strip__rotation_sequence_violation_index",
    )
    assert str(generation["pool_manifest"]).strip() == "non_symmetry.txt"
    assert list(generation["step_candidates_degrees"]) == [90, 180]
    assert int(generation["sequence_length_min"]) == 10
    assert int(generation["sequence_length_max"]) == 10
    assert int(generation["answer_index_max"]) == 6
    assert int(rendering["scene_icon_size_min_px"]) == 72
    assert int(rendering["scene_icon_size_max_px"]) == 92
    assert str(prompt["object_description"]).strip()
    assert str(prompt["question_text"]).strip()

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__pattern_grid__color_pattern_violation_index",
    )
    assert str(generation["pool_manifest"]).strip() == "all_icons.txt"
    assert list(generation["color_levels"]) == [0, 1, 2, 3, 4, 5, 6, 7]
    assert list(generation["base_color_level_candidates"]) == [0, 1, 2, 3, 4, 5, 6, 7]
    assert list(generation["row_step_color_candidates"]) == [-2, -1, 0, 1, 2]
    assert list(generation["col_step_color_candidates"]) == [-2, -1, 0, 1, 2]
    assert list(generation["shared_rotation_candidates_degrees"]) == [0, 90, 180, 270]
    assert int(rendering["scene_icon_size_min_px"]) == 66
    assert int(rendering["scene_icon_size_max_px"]) == 84
    assert int(rendering["palette_size_min"]) == 8
    assert int(rendering["palette_size_max"]) == 8
    assert list(rendering["icon_noise_edit_count_range"]) == [0, 0]
    assert str(prompt["object_description"]).strip()
    assert str(prompt["question_text"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["json_example"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__pattern_grid__size_pattern_violation_index",
    )
    assert str(generation["pool_manifest"]).strip() == "all_icons.txt"
    assert list(generation["size_levels"]) == [1, 2, 3, 4, 5]
    assert list(generation["base_level_candidates"]) == [1, 2, 3, 4, 5]
    assert list(generation["row_step_candidates"]) == [-1, 0, 1]
    assert list(generation["col_step_candidates"]) == [-1, 0, 1]
    assert list(generation["shared_rotation_candidates_degrees"]) == [0, 90, 180, 270]
    assert int(rendering["scene_icon_size_min_px"]) == 34
    assert int(rendering["scene_icon_size_max_px"]) == 82
    assert int(rendering["cell_box_width_min_px"]) == 116
    assert int(rendering["cell_box_width_max_px"]) == 152
    assert int(rendering["cell_box_height_min_px"]) == 116
    assert int(rendering["cell_box_height_max_px"]) == 152
    assert int(rendering["size_level_gap_px"]) == 10
    assert list(rendering["icon_noise_edit_count_range"]) == [0, 0]
    assert str(prompt["object_description"]).strip()
    assert str(prompt["question_text"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["json_example"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()


def test_cell_board_path_defaults_loaded() -> None:
    cfg = get_task_group_defaults("puzzles", "cell_board_path")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)
    assert "cell_board_shortest_path_internal" in cfg["generation"]["task_overrides"]
    assert "cell_board_target_reachability_count_internal" in cfg["generation"]["task_overrides"]
    assert isinstance(cfg["visual"]["background"]["styles"], dict)
    assert cfg["visual"]["background"]["styles"]

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="cell_board_shortest_path_internal",
    )
    assert int(generation["board_size_min"]) == 6
    assert int(generation["board_size_max"]) == 8
    assert int(generation["target_shortest_len_min"]) == 3
    assert int(generation["target_shortest_len_max"]) == 7
    assert float(rendering["aspect_ratio_min"]) == pytest.approx(1.0, rel=1e-9)
    assert float(rendering["aspect_ratio_max"]) == pytest.approx(1.0, rel=1e-9)
    assert str(prompt["bundle_id"]).strip()
    assert str(prompt["scene_key"]).strip() == "rectangular_tile_board"
    assert str(prompt["task_key"]).strip()
    assert str(prompt["json_output_contract"]).strip()
    assert str(prompt["json_output_contract_answer_only"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    assert str(prompt["json_example"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()
    shortest_path_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="cell_board_shortest_path_internal",
    )
    assert dict(shortest_path_complexity["criteria_weights"]) == {
        "visual_scan": 0.30,
        "reasoning_load": 0.70,
        "scene_variant_load": 0.0,
    }

    reachable_generation, reachable_rendering, reachable_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="cell_board_target_reachability_count_internal",
    )
    assert int(reachable_generation["board_size_min"]) == 6
    assert int(reachable_generation["board_size_max"]) == 8
    assert int(reachable_generation["target_reachable_target_count_min"]) == 0
    assert int(reachable_generation["target_reachable_target_count_max"]) == 5
    assert float(reachable_rendering["aspect_ratio_min"]) == pytest.approx(1.0, rel=1e-9)
    assert float(reachable_rendering["aspect_ratio_max"]) == pytest.approx(1.0, rel=1e-9)
    assert str(reachable_prompt["bundle_id"]).strip() == "puzzles_cell_board_path_v0"
    assert str(reachable_prompt["scene_key"]).strip() == "rectangular_tile_board"
    assert str(reachable_prompt["task_key"]).strip() == "reachable_target_count_query"
    assert str(reachable_prompt["answer_hint"]).strip()
    assert str(reachable_prompt["evidence_hint"]).strip()
    reachable_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="cell_board_target_reachability_count_internal",
    )
    assert dict(reachable_complexity["criteria_weights"]) == {
        "visual_scan": 0.45,
        "reasoning_load": 0.55,
        "scene_variant_load": 0.0,
    }
    assert json.loads(str(reachable_prompt["json_example"])) == {"evidence": [[216, 120], [168, 216]], "answer": 2}
    assert json.loads(str(reachable_prompt["json_example_answer_only"])) == {"answer": 2}


def test_cell_board_symmetry_defaults_loaded() -> None:
    cfg = get_task_group_defaults("puzzles", "cell_board_symmetry")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="cell_board_symmetry_violation_count_internal",
    )
    assert int(generation["palette_size_min"]) == 2
    assert int(generation["palette_size_max"]) == 4
    assert int(generation["target_violation_count_min"]) == 1
    assert int(generation["target_violation_count_max"]) == 5
    assert int(rendering["short_side_px_min"]) >= 28
    assert str(prompt["bundle_id"]).strip() == "puzzles_cell_board_symmetry_v0"
    assert str(prompt["scene_key"]).strip() == "rectangular_tile_board"
    assert str(prompt["task_key"]).strip() == "symmetry_violation_count_query"
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    assert str(prompt["json_example"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()
    symmetry_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="cell_board_symmetry_violation_count_internal",
    )
    assert dict(symmetry_complexity["criteria_weights"]) == {
        "visual_scan": 0.45,
        "reasoning_load": 0.55,
        "scene_variant_load": 0.0,
    }


def test_cell_board_count_defaults_loaded() -> None:
    cfg = get_task_group_defaults("puzzles", "cell_board_count")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["rows_min"]) == 3
    assert int(generation_shared["rows_max"]) == 7
    assert int(generation_shared["cols_min"]) == 3
    assert int(generation_shared["cols_max"]) == 7

    rendering_shared = cfg["rendering"]["shared"]
    assert int(rendering_shared["short_side_px_min"]) >= 28
    assert int(rendering_shared["short_side_px_max"]) >= int(rendering_shared["short_side_px_min"])
    assert float(rendering_shared["aspect_ratio_min"]) >= 1.0
    assert float(rendering_shared["aspect_ratio_max"]) >= float(rendering_shared["aspect_ratio_min"])

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "visual_scan": 0.50,
        "reasoning_load": 0.50,
        "scene_variant_load": 0.0,
    }

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="cell_board_color_count_internal",
    )
    assert int(generation["palette_size_min"]) >= 2
    assert int(generation["palette_size_max"]) >= int(generation["palette_size_min"])
    assert int(generation["target_color_count_min"]) == 4
    assert int(generation["target_color_count_max"]) == 15
    assert float(rendering["outer_padding_fraction_min"]) > 0.0
    assert float(rendering["outer_padding_fraction_max"]) >= float(rendering["outer_padding_fraction_min"])
    assert str(prompt["bundle_id"]).strip() == "puzzles_cell_board_count_v0"
    assert str(prompt["scene_key"]).strip() == "rectangular_tile_board"
    assert str(prompt["task_key"]).strip() == "color_count_query"
    assert str(prompt["json_output_contract"]).strip()
    assert str(prompt["json_output_contract_answer_only"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    color_count_complexity = resolve_task_group_section_defaults(cfg, "complexity", task_id="cell_board_color_count_internal")
    assert dict(color_count_complexity["criteria_weights"]) == {
        "visual_scan": 0.60,
        "reasoning_load": 0.40,
        "scene_variant_load": 0.0,
    }

    generation_components, _rendering_components, prompt_components = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="cell_board_color_components_internal",
    )
    assert int(generation_components["palette_size_min"]) == 2
    assert int(generation_components["palette_size_max"]) == 3
    assert int(generation_components["target_component_count_min"]) == 1
    assert "target_component_count_max" not in generation_components
    assert str(prompt_components["bundle_id"]).strip() == "puzzles_cell_board_count_v0"
    assert str(prompt_components["task_key"]).strip() == "color_component_count_query"
    assert str(prompt_components["answer_hint"]).strip()
    assert str(prompt_components["evidence_hint"]).strip()
    color_components_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="cell_board_color_components_internal",
    )
    assert dict(color_components_complexity["criteria_weights"]) == {
        "visual_scan": 0.05,
        "reasoning_load": 0.95,
        "scene_variant_load": 0.0,
    }
    component_example = json.loads(str(prompt_components["json_example"]))
    assert component_example == {"evidence": [[120, 120], [168, 120], [216, 216]], "answer": 2}
    component_answer_only_example = json.loads(str(prompt_components["json_example_answer_only"]))
    assert component_answer_only_example == {"answer": 2}

    generation_largest, _rendering_largest, prompt_largest = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="cell_board_largest_component_size_internal",
    )
    assert int(generation_largest["palette_size_min"]) == 2
    assert int(generation_largest["palette_size_max"]) == 3
    assert int(generation_largest["target_largest_component_size_min"]) == 2
    assert int(generation_largest["target_largest_component_size_max"]) == 7
    assert str(prompt_largest["bundle_id"]).strip() == "puzzles_cell_board_count_v0"
    assert str(prompt_largest["task_key"]).strip() == "largest_component_size_query"
    assert str(prompt_largest["answer_hint"]).strip()
    assert str(prompt_largest["evidence_hint"]).strip()
    largest_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="cell_board_largest_component_size_internal",
    )
    assert dict(largest_complexity["criteria_weights"]) == {
        "visual_scan": 0.40,
        "reasoning_load": 0.60,
        "scene_variant_load": 0.0,
    }
    largest_example = json.loads(str(prompt_largest["json_example"]))
    assert largest_example == {
        "evidence": [[120, 120], [168, 120], [168, 168], [216, 168]],
        "answer": 4,
    }
    largest_answer_only_example = json.loads(str(prompt_largest["json_example_answer_only"]))
    assert largest_answer_only_example == {"answer": 4}


def test_cell_board_reachability_defaults_loaded() -> None:
    cfg = get_task_group_defaults("puzzles", "cell_board_reachability")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="cell_board_region_size_internal",
    )
    assert int(generation["rows_min"]) >= 3
    assert int(generation["rows_max"]) == 7
    assert int(generation["cols_min"]) >= 3
    assert int(generation["cols_max"]) == 7
    assert float(generation["obstacle_fraction_min"]) > 0.0
    assert float(generation["obstacle_fraction_max"]) >= float(generation["obstacle_fraction_min"])
    assert float(generation["reachable_fraction_min"]) > 0.0
    assert float(generation["reachable_fraction_max"]) <= 1.0
    assert int(generation["answer_min"]) == 3
    assert int(generation["answer_max"]) == 8
    assert int(rendering["short_side_px_min"]) >= 28
    assert str(prompt["bundle_id"]).strip() == "puzzles_cell_board_reachability_v0"
    assert str(prompt["task_key"]).strip() == "region_size_query"
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    reachability_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="cell_board_region_size_internal",
    )
    assert dict(reachability_complexity["criteria_weights"]) == {
        "visual_scan": 0.20,
        "reasoning_load": 0.80,
        "scene_variant_load": 0.0,
    }
    example = json.loads(str(prompt["json_example"]))
    assert example == {"evidence": [[120, 120], [168, 120], [168, 168], [168, 216]], "answer": 4}
    answer_only_example = json.loads(str(prompt["json_example_answer_only"]))
    assert answer_only_example == {"answer": 4}


def test_cell_board_relation_defaults_loaded() -> None:
    cfg = get_task_group_defaults("puzzles", "cell_board_relation")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="cell_board_min_distance_internal",
    )
    assert int(generation["rows_min"]) == 4
    assert int(generation["rows_max"]) == 8
    assert int(generation["cols_min"]) == 4
    assert int(generation["cols_max"]) == 8
    assert int(generation["target_distance_min"]) == 3
    assert int(generation["target_distance_max"]) == 7
    assert int(generation["component_size_min"]) == 1
    assert int(generation["component_size_max"]) == 6
    assert int(rendering["short_side_px_min"]) >= 28
    assert str(prompt["bundle_id"]).strip() == "puzzles_cell_board_relation_v0"
    assert str(prompt["scene_key"]).strip() == "rectangular_tile_board"
    assert str(prompt["task_key"]).strip() == "min_distance_query"
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    relation_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="cell_board_min_distance_internal",
    )
    assert dict(relation_complexity["criteria_weights"]) == {
        "visual_scan": 0.35,
        "reasoning_load": 0.65,
        "scene_variant_load": 0.0,
    }
    example = json.loads(str(prompt["json_example"]))
    assert example == {
        "evidence": [[168, 168], [216, 168], [264, 168], [312, 168]],
        "answer": 3,
    }
    answer_only_example = json.loads(str(prompt["json_example_answer_only"]))
    assert answer_only_example == {"answer": 3}


def test_domain_defaults_and_missing_group_behavior() -> None:
    assert get_task_group_defaults("missing_domain", "missing_group") == {}
    domain_cfg = get_domain_defaults("geometry")
    cfg = get_task_group_defaults("geometry", "missing_group")
    assert cfg["rendering"]["shared"] == domain_cfg["rendering"]["shared"]


def test_measurement_prompt_examples_are_task_valid() -> None:
    cfg = get_task_group_defaults("geometry", "measurement")

    _angle_generation, _angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_measurement_angle",
    )
    angle_example = json.loads(str(angle_prompt["json_example"]))
    assert list(angle_example.keys()) == ["evidence", "answer"]
    assert isinstance(angle_example["evidence"], list)
    assert len(angle_example["evidence"]) == 3
    assert isinstance(angle_example["answer"], int)
    angle_answer_only_example = json.loads(str(angle_prompt["json_example_answer_only"]))
    assert list(angle_answer_only_example.keys()) == ["answer"]
    assert isinstance(angle_answer_only_example["answer"], int)

    _slope_generation, _slope_rendering, slope_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_measurement_slope",
    )
    slope_example = json.loads(str(slope_prompt["json_example"]))
    assert list(slope_example.keys()) == ["evidence", "answer"]
    assert isinstance(slope_example["evidence"], list)
    assert len(slope_example["evidence"]) == 1
    assert isinstance(slope_example["evidence"][0], list)
    assert len(slope_example["evidence"][0]) == 2
    assert isinstance(slope_example["answer"], float)
    slope_answer_only_example = json.loads(str(slope_prompt["json_example_answer_only"]))
    assert list(slope_answer_only_example.keys()) == ["answer"]
    assert isinstance(slope_answer_only_example["answer"], float)

    _area_generation, _area_rendering, area_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_measurement_area",
    )
    area_example = json.loads(str(area_prompt["json_example_integer"]))
    assert list(area_example.keys()) == ["evidence", "answer"]
    assert isinstance(area_example["evidence"], list)
    area_points = [[int(point[0]), int(point[1])] for point in area_example["evidence"]]
    assert len(area_points) >= 3
    assert int(area_example["answer"]) >= 0
    for key, expected_points in (
        ("json_example_triangle", 3),
        ("json_example_quadrilateral", 4),
    ):
        polygon_example = json.loads(str(area_prompt[key]))
        assert list(polygon_example.keys()) == ["evidence", "answer"]
        assert isinstance(polygon_example["evidence"], list)
        polygon_points = [[int(point[0]), int(point[1])] for point in polygon_example["evidence"]]
        assert len(polygon_points) == int(expected_points)
        assert int(polygon_example["answer"]) >= 0
    area_pi_example = json.loads(str(area_prompt["json_example_pi"]))
    assert list(area_pi_example.keys()) == ["evidence", "answer"]
    assert isinstance(area_pi_example["evidence"], list) and len(area_pi_example["evidence"]) == 1
    assert str(area_pi_example["answer"]).endswith("π")
    area_answer_only_integer = json.loads(str(area_prompt["json_example_answer_only_integer"]))
    assert list(area_answer_only_integer.keys()) == ["answer"]
    assert int(area_answer_only_integer["answer"]) >= 0
    area_answer_only_pi = json.loads(str(area_prompt["json_example_answer_only_pi"]))
    assert list(area_answer_only_pi.keys()) == ["answer"]
    assert str(area_answer_only_pi["answer"]).endswith("π")

    _perim_generation, _perim_rendering, perim_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_measurement_perimeter",
    )
    perim_example = json.loads(str(perim_prompt["json_example_integer"]))
    assert list(perim_example.keys()) == ["evidence", "answer"]
    assert isinstance(perim_example["evidence"], list)
    perim_points = [[int(point[0]), int(point[1])] for point in perim_example["evidence"]]
    assert len(perim_points) >= 3
    assert int(perim_example["answer"]) >= 0
    for key, expected_points in (
        ("json_example_triangle", 3),
        ("json_example_quadrilateral", 4),
    ):
        polygon_example = json.loads(str(perim_prompt[key]))
        assert list(polygon_example.keys()) == ["evidence", "answer"]
        assert isinstance(polygon_example["evidence"], list)
        polygon_points = [[int(point[0]), int(point[1])] for point in polygon_example["evidence"]]
        assert len(polygon_points) == int(expected_points)
        assert int(polygon_example["answer"]) >= 0
    perim_pi_example = json.loads(str(perim_prompt["json_example_pi"]))
    assert list(perim_pi_example.keys()) == ["evidence", "answer"]
    assert isinstance(perim_pi_example["evidence"], list) and len(perim_pi_example["evidence"]) == 1
    assert str(perim_pi_example["answer"]).endswith("π")
    perim_answer_only_integer = json.loads(str(perim_prompt["json_example_answer_only_integer"]))
    assert list(perim_answer_only_integer.keys()) == ["answer"]
    assert int(perim_answer_only_integer["answer"]) >= 0
    perim_answer_only_pi = json.loads(str(perim_prompt["json_example_answer_only_pi"]))
    assert list(perim_answer_only_pi.keys()) == ["answer"]
    assert str(perim_answer_only_pi["answer"]).endswith("π")

    _length_generation, _length_rendering, length_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="source_geometry_measurement_length",
    )
    length_example = json.loads(str(length_prompt["json_example_integer"]))
    assert list(length_example.keys()) == ["evidence", "answer"]
    assert isinstance(length_example["evidence"], list)
    length_points = [[int(point[0]), int(point[1])] for point in length_example["evidence"]]
    assert len(length_points) == 2
    assert int(length_example["answer"]) >= 0
    center_example = json.loads(str(length_prompt["json_example_circle_radius_integer"]))
    assert list(center_example.keys()) == ["evidence", "answer"]
    assert isinstance(center_example["evidence"], list)
    assert len(center_example["evidence"]) == 1
    only_point = center_example["evidence"][0]
    assert isinstance(only_point, list) and len(only_point) == 2
    length_answer_only_example = json.loads(str(length_prompt["json_example_answer_only_integer"]))
    assert list(length_answer_only_example.keys()) == ["answer"]
    assert int(length_answer_only_example["answer"]) >= 0



def test_section_defaults_require_shared_and_task_overrides_schema() -> None:
    mapping = {
        "rendering": {
            "canvas_size_min": 111,
            "shared": {"canvas_size_min": 512},
            "task_overrides": {"demo_task": {"canvas_size_min": 768}},
        }
    }
    shared_only = resolve_task_group_section_defaults(mapping, "rendering")
    task_specific = resolve_task_group_section_defaults(mapping, "rendering", task_id="demo_task")
    assert int(shared_only["canvas_size_min"]) == 512
    assert int(task_specific["canvas_size_min"]) == 768
    assert resolve_task_group_section_defaults({"rendering": {"canvas_size_min": 111}}, "rendering") == {}


def test_required_group_helpers_enforce_presence_and_nonempty() -> None:
    assert required_group_default({"value": 3}, "value", context="test") == 3
    resolved = required_group_defaults({"a": 1, "b": "ok"}, ("a", "b"), context="test")
    assert resolved == {"a": 1, "b": "ok"}
    with pytest.raises(ValueError):
        required_group_default({}, "value", context="test")
    with pytest.raises(ValueError):
        required_group_default({"value": "   "}, "value", context="test")
    with pytest.raises(ValueError):
        required_group_defaults({"a": 1}, ("a", "b"), context="test")


def test_resolve_numeric_bounds_helpers() -> None:
    assert resolve_optional_int_bounds(
        {"answer_min": 3},
        {"answer_max": 9},
        min_key="answer_min",
        max_key="answer_max",
        context="test",
    ) == (3, 9)
    assert resolve_optional_int_bounds(
        {},
        {},
        min_key="answer_min",
        max_key="answer_max",
        context="test",
    ) == (None, None)
    with pytest.raises(ValueError):
        resolve_optional_int_bounds(
            {"answer_min": 10, "answer_max": 2},
            {},
            min_key="answer_min",
            max_key="answer_max",
            context="test",
        )
    assert resolve_required_int_bounds(
        {"min": 2},
        {"max": 8},
        min_key="min",
        max_key="max",
        fallback_min=1,
        fallback_max=9,
        context="test",
    ) == (2, 8)
    assert resolve_required_float_bounds(
        {"min_f": 0.1},
        {"max_f": 0.6},
        min_key="min_f",
        max_key="max_f",
        fallback_min=0.0,
        fallback_max=1.0,
        context="test",
    ) == (0.1, 0.6)
    with pytest.raises(ValueError):
        resolve_required_int_bounds(
            {"min": 9, "max": 2},
            {},
            min_key="min",
            max_key="max",
            fallback_min=0,
            fallback_max=1,
            context="test",
        )
    with pytest.raises(ValueError):
        resolve_required_float_bounds(
            {"min_f": 0.9, "max_f": 0.2},
            {},
            min_key="min_f",
            max_key="max_f",
            fallback_min=0.0,
            fallback_max=1.0,
            context="test",
        )


def test_puzzles_clock_defaults_loaded() -> None:
    cfg = get_task_group_defaults("puzzles", "clock")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert sorted(generation_shared["scene_variant_weights"].keys()) == ["classic", "minimal", "outline"]
    assert sorted(generation_shared["style_variant_weights"].keys()) == ["accented", "marker", "studio"]
    assert sorted(generation_shared["accent_color_name_weights"].keys()) == [
        "blue",
        "brown",
        "cyan",
        "green",
        "magenta",
        "maroon",
        "orange",
        "purple",
        "red",
        "yellow",
    ]
    assert bool(generation_shared["balanced_scene_variant_sampling"]) is True
    assert bool(generation_shared["balanced_style_variant_sampling"]) is True
    assert bool(generation_shared["balanced_accent_color_name_sampling"]) is True
    assert int(generation_shared["hour_min"]) == 1
    assert int(generation_shared["hour_max"]) == 12
    assert int(generation_shared["minute_step"]) == 5
    assert int(generation_shared["second_step"]) == 5
    assert float(generation_shared["min_hand_angle_gap_deg"]) == 10.0

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) == 640
    assert int(render_shared["canvas_height"]) == 640
    assert int(render_shared["face_radius_px"]) > 0
    assert int(render_shared["hour_hand_width_px"]) > int(render_shared["minute_hand_width_px"])
    assert int(render_shared["minute_hand_width_px"]) > int(render_shared["second_hand_width_px"])
    assert int(render_shared["minor_tick_dot_radius_px"]) >= 2
    assert int(render_shared["inner_ring_inset_px"]) > 0
    assert int(render_shared["inner_ring_width_px"]) > 0

    complexity_shared = cfg["complexity"]["shared"]
    assert {key: value for key, value in complexity_shared["criteria_weights"].items() if float(value) > 0.0} == {
        "time_reading": 0.70,
        "visual_scan": 0.05,
        "ambiguity": 0.20,
        "clutter": 0.05,
    }

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "puzzles_clock_v0"

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="puzzles_clock_readout_base",
    )
    assert int(generation_defaults["hour_min"]) == 1
    assert int(generation_defaults["hour_max"]) == 12
    assert int(generation_defaults["minute_step"]) == 5
    assert int(generation_defaults["second_step"]) == 5
    assert dict(generation_defaults["delta_minutes_support"]) == {"min": 5, "max": 600, "step": 5}
    assert dict(generation_defaults["delta_seconds_support"]) == {"min": 5, "max": 36000, "step": 5}
    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "offset_time",
    ]
    assert sorted(generation_defaults["offset_unit_weights"].keys()) == ["minutes", "seconds"]
    assert sorted(generation_defaults["offset_direction_weights"].keys()) == ["after", "before"]
    assert bool(generation_defaults["balanced_query_variant_sampling"]) is True
    assert int(rendering_defaults["canvas_width"]) == 640
    assert str(prompt_defaults["bundle_id"]).strip() == "puzzles_clock_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "analog_clock"
    assert str(prompt_defaults["task_key"]).strip() == "clock_readout_query"
    assert str(prompt_defaults["object_description_classic"]).strip()
    assert str(prompt_defaults["evidence_hint"]).strip()
    assert str(prompt_defaults["answer_hint"]).strip()


def test_puzzles_clock_compare_defaults_loaded() -> None:
    cfg = get_task_group_defaults("puzzles", "clock")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_puzzles__clock_collection__compare",
    )

    assert sorted(generation_defaults["query_variant_weights"].keys()) == ["time_extremum_label"]
    assert sorted(generation_defaults["extremum_direction_weights"].keys()) == ["earliest", "latest"]
    assert bool(generation_defaults["balanced_query_variant_sampling"]) is True
    assert list(generation_defaults["clock_label_support"]) == ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
    assert list(generation_defaults["clock_count_support"]) == [6, 7, 8, 9, 10, 11, 12]
    assert int(generation_defaults["min_compare_gap_minutes"]) == 15

    assert int(rendering_defaults["canvas_width"]) == 960
    assert int(rendering_defaults["canvas_height"]) == 760
    assert int(rendering_defaults["face_radius_px"]) == 84
    assert int(rendering_defaults["label_font_size_px"]) == 28

    assert str(prompt_defaults["bundle_id"]).strip() == "puzzles_clock_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "multi_analog_clock"
    assert str(prompt_defaults["task_key"]).strip() == "clock_compare_query"
    assert str(prompt_defaults["object_description_classic"]).strip()
    assert str(prompt_defaults["evidence_hint"]).strip()
    assert str(prompt_defaults["answer_hint"]).strip()


def test_pages_calendar_defaults_loaded() -> None:
    cfg = get_task_group_defaults("pages", "calendar")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="pages_calendar_month_view_base",
    )

    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "count_marked_day_class",
        "date_of_weekday_occurrence",
    ]
    assert sorted(generation_defaults["marked_day_class_weights"].keys()) == ["weekday", "weekend"]
    assert bool(generation_defaults["balanced_query_variant_sampling"]) is True
    assert list(generation_defaults["weekend_weekday_indices"]) == [5, 6]
    assert list(generation_defaults["date_occurrence_support"]) == [1, 2, 3, 4, 5]
    assert list(generation_defaults["marked_weekend_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation_defaults["marked_weekday_count_support"]) == [0, 1, 2, 3, 4, 5, 6]
    assert list(generation_defaults["marked_weekday_distractor_support"]) == [1, 2, 3, 4]
    assert list(generation_defaults["marked_weekend_distractor_support"]) == [1, 2, 3, 4]

    assert int(rendering_defaults["canvas_width"]) == 860
    assert int(rendering_defaults["canvas_height"]) == 760
    assert int(rendering_defaults["title_font_size_px"]) == 30
    assert int(rendering_defaults["date_font_size_px"]) == 22

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_calendar_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "month_calendar"
    assert str(prompt_defaults["task_key"]).strip() == "calendar_month_query"


def test_pages_schedule_defaults_loaded() -> None:
    cfg = get_task_group_defaults("pages", "schedule")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="pages_schedule_day_planner_base",
    )

    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "longer_than_reference_count",
        "maximum_non_overlapping_count",
        "overlap_count",
    ]
    assert bool(generation_defaults["balanced_query_variant_sampling"]) is True
    assert list(generation_defaults["event_count_support"]) == [7, 8, 9, 10]
    assert list(generation_defaults["overlap_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation_defaults["maximum_non_overlapping_support"]) == [2, 3, 4, 5, 6, 7]
    assert int(generation_defaults["slot_minutes"]) == 30
    assert int(generation_defaults["max_lane_count"]) == 5

    assert int(rendering_defaults["canvas_width"]) == 920
    assert int(rendering_defaults["canvas_height"]) == 820
    assert int(rendering_defaults["header_height_px"]) == 92
    assert int(rendering_defaults["time_axis_width_px"]) == 94

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_schedule_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "day_schedule"
    assert str(prompt_defaults["task_key"]).strip() == "schedule_day_query"


def test_pages_timeline_defaults_loaded() -> None:
    cfg = get_task_group_defaults("pages", "timeline")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="pages_timeline_milestones_base",
    )

    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "interval_membership_count",
    ]
    assert sorted(generation_defaults["interval_relation_weights"].keys()) == ["between", "outside"]
    assert bool(generation_defaults["balanced_query_variant_sampling"]) is True
    assert list(generation_defaults["event_count_support"]) == [6, 7, 8, 9, 10, 11, 12]
    assert list(generation_defaults["between_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation_defaults["outside_count_support"]) == [2, 3, 4, 5, 6, 7, 8]

    assert int(rendering_defaults["canvas_width"]) == 1120
    assert int(rendering_defaults["canvas_height"]) == 700
    assert int(rendering_defaults["card_width_px"]) == 106
    assert int(rendering_defaults["marker_radius_px"]) == 10

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_timeline_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "milestone_timeline"
    assert str(prompt_defaults["task_key"]).strip() == "timeline_milestone_query"


def test_pages_cycle_defaults_loaded() -> None:
    cfg = get_task_group_defaults("pages", "cycle")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__cycle__offset_stage_label",
    )

    assert sorted(generation_defaults["query_variant_weights"].keys()) == ["offset_stage_label"]
    assert sorted(generation_defaults["query_relationship_weights"].keys()) == ["after", "before"]
    assert bool(generation_defaults["balanced_query_relationship_sampling"]) is True
    assert bool(generation_defaults["balanced_scene_variant_sampling"]) is True
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == ["cycle_ring"]
    assert sorted(generation_defaults["cycle_direction_weights"].keys()) == ["clockwise", "counterclockwise"]
    assert int(generation_defaults["stage_count_min"]) == 5
    assert int(generation_defaults["stage_count_max"]) == 12

    assert int(rendering_defaults["canvas_width"]) == 1200
    assert int(rendering_defaults["canvas_height"]) == 900
    assert int(rendering_defaults["node_width_px"]) == 122
    assert int(rendering_defaults["ring_radius_x_px"]) == 360

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_cycle_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "cycle_diagram"
    assert str(prompt_defaults["task_key"]).strip() == "offset_stage_query"
    assert str(prompt_defaults["evidence_hint_offset_stage_label"]).strip()


def test_pages_arithmetic_defaults_loaded() -> None:
    cfg = get_task_group_defaults("pages", "arithmetic")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__form_section__section_expression_value",
    )

    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "difference_two_amounts_in_section",
        "sum_minus_amount_in_section",
        "sum_two_amounts_in_section",
    ]
    assert bool(generation_defaults["balanced_query_variant_sampling"]) is True
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == [
        "form_sheet",
        "invoice_sheet",
        "receipt_sheet",
    ]
    assert bool(generation_defaults["balanced_scene_variant_sampling"]) is True

    assert int(rendering_defaults["canvas_width"]) == 1256
    assert int(rendering_defaults["canvas_height"]) == 1000
    assert int(rendering_defaults["sheet_page_width_px"]) == 960
    assert int(rendering_defaults["sheet_page_height_px"]) == 860
    assert int(rendering_defaults["receipt_page_width_px"]) == 520
    assert int(rendering_defaults["receipt_page_height_px"]) == 920
    assert int(rendering_defaults["section_font_size_px"]) == 24

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_arithmetic_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "structured_document_sections"
    assert str(prompt_defaults["task_key"]).strip() == "section_expression_query"
    assert str(prompt_defaults["evidence_hint"]).strip()


def test_pages_cross_form_defaults_loaded() -> None:
    cfg = get_task_group_defaults("pages", "cross_form")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__paired_forms__reconciliation_value",
    )

    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "shortfall_minus_overage_value",
        "sum_absolute_quantity_differences",
        "total_amount_delta",
    ]
    assert bool(generation_defaults["balanced_query_variant_sampling"]) is True
    assert bool(generation_defaults["balanced_scene_variant_sampling"]) is True
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == ["purchase_receipt_pair"]
    assert int(generation_defaults["item_count_min"]) == 6
    assert int(generation_defaults["item_count_max"]) == 9
    assert int(generation_defaults["quantity_max"]) == 99
    assert int(generation_defaults["unit_value_min"]) == 5
    assert int(generation_defaults["unit_value_max"]) == 30
    assert int(generation_defaults["discrepancy_min"]) == 2
    assert int(generation_defaults["discrepancy_max"]) == 10
    assert int(generation_defaults["mismatch_count_min"]) == 3
    assert int(generation_defaults["mismatch_count_max"]) == 5
    assert int(generation_defaults["direction_count_min"]) == 1

    assert int(rendering_defaults["canvas_width"]) == 1392
    assert int(rendering_defaults["canvas_height"]) == 848
    assert int(rendering_defaults["panel_gap_px"]) == 28
    assert int(rendering_defaults["cell_font_size_px"]) == 18

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_cross_form_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "cross_form_reconciliation"
    assert str(prompt_defaults["task_key"]).strip() == "reconciliation_value_query"
    assert str(prompt_defaults["evidence_hint_total_amount_delta"]).strip()
    assert str(prompt_defaults["evidence_hint_shortfall_minus_overage_value"]).strip()
    assert str(prompt_defaults["evidence_hint_sum_absolute_quantity_differences"]).strip()


def test_pages_hierarchy_defaults_loaded() -> None:
    cfg = get_task_group_defaults("pages", "hierarchy")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__hierarchy__tree_count",
    )

    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "path_length_between_two_nodes",
        "subtree_descendant_count",
        "subtree_leaf_count",
    ]
    assert bool(generation_defaults["balanced_scene_variant_sampling"]) is True
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == ["rooted_tree"]
    assert int(generation_defaults["tree_node_count_min"]) == 16
    assert int(generation_defaults["tree_node_count_max"]) == 30

    assert int(rendering_defaults["canvas_width"]) == 1464
    assert int(rendering_defaults["canvas_height"]) == 848
    assert int(rendering_defaults["node_width_px"]) == 84
    assert int(rendering_defaults["label_font_size_px"]) == 14

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_hierarchy_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "hierarchy_diagram"
    assert str(prompt_defaults["task_key"]).strip() == "tree_count_query"
    assert str(prompt_defaults["evidence_hint_subtree_descendant_count"]).strip()


def test_pages_map_defaults_loaded() -> None:
    cfg = get_task_group_defaults("pages", "map")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__map__navigation_label",
    )

    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "destination_after_directions",
        "landmark_after_route_step",
    ]
    assert bool(generation_defaults["balanced_query_variant_sampling"]) is True
    assert bool(generation_defaults["balanced_scene_variant_sampling"]) is True
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == ["campus_map"]
    assert int(generation_defaults["landmark_count_min"]) == 10
    assert int(generation_defaults["landmark_count_max"]) == 14

    assert int(rendering_defaults["canvas_width"]) == 1280
    assert int(rendering_defaults["canvas_height"]) == 900
    assert int(rendering_defaults["landmark_width_px"]) == 126
    assert int(rendering_defaults["highlighted_path_width_px"]) == 18

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_map_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "printed_map"
    assert str(prompt_defaults["task_key"]).strip() == "map_navigation_query"
    assert str(prompt_defaults["evidence_hint_destination_after_directions"]).strip()


def test_gui_counting_defaults_loaded() -> None:
    cfg = get_task_group_defaults("pages", "counting")
    for section in ("generation", "rendering", "prompt", "complexity", "visual"):
        assert isinstance(cfg.get(section), dict)

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__control_board__filter_count",
    )

    assert sorted(generation_defaults["query_variant_weights"].keys()) == [
        "disabled_controls_in_group_count",
        "enabled_action_for_type_count",
        "selected_enabled_controls_in_group_count",
        "selected_rows_with_status_count",
        "value_threshold_in_group_count",
    ]
    assert bool(generation_defaults["balanced_query_variant_sampling"]) is True
    assert bool(generation_defaults["balanced_scene_variant_sampling"]) is True
    assert bool(generation_defaults["balanced_style_variant_sampling"]) is True
    assert list(generation_defaults["row_count_support"]) == [9, 10, 11, 12, 13, 14, 15]
    assert list(generation_defaults["section_count_support"]) == [2, 3]
    assert list(generation_defaults["answer_count_support"]) == [2, 3, 4, 5, 6, 7]
    assert list(generation_defaults["enabled_action_for_type_count_row_count_support"]) == [9, 10, 11, 12]
    assert list(generation_defaults["enabled_action_for_type_count_answer_count_support"]) == [2, 3, 4, 5, 6]
    assert list(generation_defaults["size_threshold_support"]) == [25, 35, 45, 55, 65]
    assert len(generation_defaults["candidate_label_pool"]) == 26

    assert int(rendering_defaults["canvas_width"]) == 1280
    assert int(rendering_defaults["canvas_height"]) == 800
    assert int(rendering_defaults["badge_size_px"]) == 28
    assert int(rendering_defaults["row_height_px"]) == 28

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_counting_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "gui_control_board"
    assert str(prompt_defaults["task_key"]).strip() == "control_filter_count_query"
    assert str(prompt_defaults["answer_hint"]).strip()
    assert str(prompt_defaults["evidence_hint"]).strip()


def test_gui_relation_defaults_loaded() -> None:
    cfg = get_task_group_defaults("pages", "relation")
    for section in ("generation", "rendering", "prompt", "complexity", "visual"):
        assert isinstance(cfg.get(section), dict)

    nav_generation_defaults, nav_rendering_defaults, nav_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__navigation_flow__navigation_path_target_label",
    )

    assert sorted(nav_generation_defaults["query_variant_weights"].keys()) == [
        "menu_path_target_label",
        "ribbon_group_command_label",
    ]
    assert int(nav_generation_defaults["menu_command_count_min"]) == 3
    assert int(nav_generation_defaults["menu_command_count_max"]) == 4
    assert int(nav_generation_defaults["ribbon_tab_count_min"]) == 3
    assert int(nav_generation_defaults["ribbon_tab_count_max"]) == 5
    assert int(nav_generation_defaults["ribbon_group_count_min"]) == 2
    assert int(nav_generation_defaults["ribbon_group_count_max"]) == 3
    assert int(nav_generation_defaults["ribbon_command_count_min"]) == 3
    assert int(nav_generation_defaults["ribbon_command_count_max"]) == 4
    assert list(nav_generation_defaults["nav_menu_pool"]) == ["File", "Edit", "View"]
    assert list(nav_generation_defaults["nav_submenu_pool"]) == ["Arrange", "Inspect"]
    assert list(nav_generation_defaults["nav_menu_group_pool"]) == ["Primary", "Advanced"]
    assert list(nav_generation_defaults["nav_command_pool"]) == ["Align", "Duplicate", "Export", "Preview"]
    assert list(nav_generation_defaults["nav_sidebar_section_pool"]) == ["Workspace", "Assets", "Settings", "Reports"]
    assert list(nav_generation_defaults["nav_sidebar_item_pool"]) == ["Overview", "Timeline", "Details"]
    assert list(nav_generation_defaults["nav_ribbon_tab_pool"]) == ["Home", "Insert", "Review", "Analyze", "Share"]

    assert int(nav_rendering_defaults["canvas_width"]) == 1280
    assert int(nav_rendering_defaults["canvas_height"]) == 800
    assert int(nav_rendering_defaults["badge_size_px"]) == 30

    assert str(nav_prompt_defaults["bundle_id"]).strip() == "pages_relation_v0"
    assert str(nav_prompt_defaults["scene_key"]).strip() == "gui_navigation_paths"
    assert str(nav_prompt_defaults["task_key"]).strip() == "navigation_path_query"
    assert str(nav_prompt_defaults["answer_hint"]).strip()
    assert str(nav_prompt_defaults["evidence_hint"]).strip()

    intent_generation_defaults, intent_rendering_defaults, intent_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_pages__command_matrix__command_intent_target_label",
        )
    )

    assert sorted(intent_generation_defaults["query_variant_weights"].keys()) == [
        "command_intent_target_label",
        "dual_guide_command_label",
    ]
    assert sorted(intent_generation_defaults["intent_category_weights"].keys()) == [
        "create_insert",
        "edit_transform",
        "format_style",
        "select_choose",
        "view_toggle",
    ]
    assert list(intent_generation_defaults["intent_object_pool"]) == ["Document", "Chart", "Layer", "File", "Project"]
    assert list(intent_generation_defaults["intent_create_insert_action_pool"]) == ["Create", "Insert", "Import", "Add", "Upload"]
    assert list(intent_generation_defaults["intent_select_choose_action_pool"]) == ["Select", "Choose", "Check", "Pick", "Highlight"]
    assert list(intent_generation_defaults["intent_view_toggle_action_pool"]) == ["Show", "Hide", "Zoom", "Preview", "Expand"]
    assert list(intent_generation_defaults["intent_edit_transform_action_pool"]) == ["Copy", "Delete", "Move", "Rotate", "Resize"]
    assert list(intent_generation_defaults["intent_format_style_action_pool"]) == ["Format", "Align", "Color", "Size", "Style"]

    assert int(intent_rendering_defaults["canvas_width"]) == 1280
    assert int(intent_rendering_defaults["canvas_height"]) == 800

    assert str(intent_prompt_defaults["bundle_id"]).strip() == "pages_relation_v0"
    assert str(intent_prompt_defaults["scene_key"]).strip() == "gui_command_intents"
    assert str(intent_prompt_defaults["task_key"]).strip() == "command_intent_query"
    assert str(intent_prompt_defaults["answer_hint"]).strip()
    assert str(intent_prompt_defaults["evidence_hint"]).strip()

    professional_generation_defaults, professional_rendering_defaults, professional_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_pages__workspace__professional_target_label",
        )
    )

    assert sorted(professional_generation_defaults["query_variant_weights"].keys()) == [
        "canvas_workspace_control_label",
        "code_workspace_control_label",
        "file_dialog_control_label",
        "property_panel_control_label",
        "toolbar_palette_control_label",
    ]
    assert int(professional_generation_defaults["context_count_min"]) == 3
    assert int(professional_generation_defaults["context_count_max"]) == 5
    assert int(professional_rendering_defaults["canvas_width"]) == 1280
    assert int(professional_rendering_defaults["canvas_height"]) == 800
    assert int(professional_rendering_defaults["badge_size_px"]) == 30
    assert str(professional_prompt_defaults["bundle_id"]).strip() == "pages_relation_v0"
    assert str(professional_prompt_defaults["scene_key"]).strip() == "gui_professional_target_controls"
    assert str(professional_prompt_defaults["task_key"]).strip() == "professional_target_query"
    assert str(professional_prompt_defaults["answer_hint"]).strip()
    assert str(professional_prompt_defaults["evidence_hint"]).strip()

    web_generation_defaults, web_rendering_defaults, web_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_pages__web_action__web_action_target_label",
        )
    )

    assert sorted(web_generation_defaults["query_variant_weights"].keys()) == [
        "click_target_label",
        "select_option_label",
        "type_field_label",
    ]
    assert {
        "content_cms",
        "finance_portal",
        "learning_portal",
        "shop_catalog",
        "support_center",
        "travel_booking",
    }.issubset(set(web_generation_defaults["scene_variant_weights"].keys()))
    assert int(web_generation_defaults["web_click_item_count_min"]) == 4
    assert int(web_generation_defaults["web_click_item_count_max"]) == 6
    assert int(web_generation_defaults["web_type_section_count_min"]) == 3
    assert int(web_generation_defaults["web_select_option_count_max"]) == 4
    assert list(web_generation_defaults["web_click_action_pool"]) == ["Details", "Compare", "Save", "Open"]
    assert int(web_rendering_defaults["canvas_width"]) == 1280
    assert int(web_rendering_defaults["canvas_height"]) == 800
    assert int(web_rendering_defaults["browser_margin_px"]) == 34
    assert int(web_rendering_defaults["instruction_height_px"]) == 60
    assert str(web_prompt_defaults["bundle_id"]).strip() == "pages_relation_v0"
    assert str(web_prompt_defaults["scene_key"]).strip() == "gui_web_action_targets"
    assert str(web_prompt_defaults["task_key"]).strip() == "web_action_query"
    assert str(web_prompt_defaults["answer_hint"]).strip()
    assert str(web_prompt_defaults["evidence_hint"]).strip()
