"""Regression tests for task-group default config loading."""

from __future__ import annotations

import json
import math

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


def _polygon_area(points: list[list[int]]) -> int:
    double_area = 0
    for index, (x_value, y_value) in enumerate(points):
        next_x, next_y = points[(index + 1) % len(points)]
        double_area += (int(x_value) * int(next_y)) - (int(y_value) * int(next_x))
    assert abs(int(double_area)) % 2 == 0
    return int(abs(int(double_area)) // 2)


def _polygon_perimeter(points: list[list[int]]) -> int:
    total = 0.0
    for index, (x_value, y_value) in enumerate(points):
        next_x, next_y = points[(index + 1) % len(points)]
        total += math.hypot(float(next_x) - float(x_value), float(next_y) - float(y_value))
    rounded = int(round(total))
    assert abs(float(total) - float(rounded)) <= 1e-9
    return int(rounded)


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
    assert "task_geometry_measurement_angle" in generation_overrides
    assert int(cfg["generation"]["shared"]["answer_min"]) >= 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip()
    assert str(prompt_shared["task_family_key"]).strip()
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
        task_id="task_geometry_measurement_angle",
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
        task_id="task_geometry_measurement_area",
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
        task_id="task_geometry_measurement_perimeter",
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
        task_id="task_geometry_measurement_length",
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
        task_id="task_geometry_measurement_slope",
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
    assert sorted(generation_shared["task_variant_weights"].keys()) == [
        "max",
        "mean",
        "median",
        "min",
        "mode",
        "range",
        "sum",
    ]
    assert sorted(generation_shared["scene_variant_weights"].keys()) == [
        "area",
        "bar",
        "donut",
        "dot_plot",
        "horizontal_bar",
        "line",
        "lollipop",
        "pie",
        "radar",
        "scatter",
    ]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["plot_margin_left_px"]) > 0
    assert int(render_shared["plot_margin_bottom_px"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_statistics_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "labeled_chart_statistics"
    assert str(prompt_shared["task_key"]).strip() == "summary_value_query"
    assert str(prompt_shared["object_description_bar"]).strip()
    assert str(prompt_shared["evidence_hint_mode"]).strip()
    assert str(prompt_shared["json_example_mean"]).strip()
    assert str(prompt_shared["json_example_answer_only_sum"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_charts_statistics_summary_value",
    )
    assert int(generation_defaults["mark_count_min"]) >= 5
    assert int(generation_defaults["mark_count_max"]) == 10
    assert int(generation_defaults["value_max"]) == 20
    assert int(rendering_defaults["canvas_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_statistics_v1"

    label_generation, _, label_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_charts_statistics_summary_label",
    )
    assert {
        "argmax",
        "argmin",
        "median_label",
    }.issubset(set(label_generation["task_variant_weights"].keys()))
    assert str(label_prompt["task_key"]).strip() == "summary_label_query"
    assert str(label_prompt["answer_hint"]).strip()
    assert str(label_prompt["evidence_hint_argmax"]).strip()
    assert str(label_prompt["json_example_median_label"]).strip()

    value_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_charts_statistics_summary_value",
    )
    label_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_charts_statistics_summary_label",
    )
    assert sorted(value_complexity["criteria_weights"].keys()) == [
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    ]
    assert sorted(label_complexity["criteria_weights"].keys()) == [
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    ]


def test_charts_distribution_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "distribution")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["bin_count_min"]) >= 4
    assert int(generation_shared["bin_count_max"]) >= int(generation_shared["bin_count_min"])
    assert int(generation_shared["bin_width_min"]) >= 1
    assert int(generation_shared["bin_width_max"]) >= int(generation_shared["bin_width_min"])
    assert int(generation_shared["bin_frequency_min"]) >= 1
    assert int(generation_shared["bin_frequency_max"]) >= int(generation_shared["bin_frequency_min"])
    assert int(generation_shared["category_count_min"]) >= 4
    assert int(generation_shared["category_count_max"]) >= int(generation_shared["category_count_min"])
    assert sorted(cfg["generation"]["task_overrides"]["task_charts_distribution_histogram_count"]["task_variant_weights"].keys()) == [
        "cumulative_count_to_bin",
        "interval_mass",
        "modal_bin_count",
    ]
    assert sorted(cfg["generation"]["task_overrides"]["task_charts_distribution_boxplot_label"]["task_variant_weights"].keys()) == [
        "highest_median",
        "largest_iqr",
        "smallest_iqr",
    ]
    assert sorted(cfg["generation"]["task_overrides"]["task_charts_distribution_density_label"]["task_variant_weights"].keys()) == [
        "bimodal_label",
        "highest_mode",
        "lowest_mode",
    ]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["plot_margin_bottom_px"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_distribution_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "distribution_chart"
    assert str(prompt_shared["task_key"]).strip() == "histogram_count_query"
    assert str(prompt_shared["object_description_histogram"]).strip()
    assert str(prompt_shared["object_description_violin"]).strip()
    assert str(prompt_shared["json_example_interval_mass"]).strip()

    histogram_generation, histogram_rendering, histogram_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_charts_distribution_histogram_count",
    )
    assert {
        "modal_bin_count",
        "interval_mass",
        "cumulative_count_to_bin",
    }.issubset(set(histogram_generation["task_variant_weights"].keys()))
    assert int(histogram_rendering["canvas_width"]) > 0
    assert str(histogram_prompt["bundle_id"]).strip() == "charts_distribution_v1"
    assert str(histogram_prompt["object_description_histogram"]).strip()

    boxplot_generation, _, boxplot_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_charts_distribution_boxplot_label",
    )
    assert {
        "highest_median",
        "largest_iqr",
        "smallest_iqr",
    }.issubset(set(boxplot_generation["task_variant_weights"].keys()))
    assert str(boxplot_prompt["task_key"]).strip() == "boxplot_label_query"
    assert str(boxplot_prompt["answer_hint"]).strip()
    assert str(boxplot_prompt["evidence_hint_largest_iqr"]).strip()

    density_generation, _, density_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_charts_distribution_density_label",
    )
    assert {
        "highest_mode",
        "lowest_mode",
        "bimodal_label",
    }.issubset(set(density_generation["task_variant_weights"].keys()))
    assert str(density_prompt["task_key"]).strip() == "density_label_query"
    assert str(density_prompt["evidence_hint_bimodal_label"]).strip()

    histogram_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_charts_distribution_histogram_count",
    )
    boxplot_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_charts_distribution_boxplot_label",
    )
    density_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_charts_distribution_density_label",
    )
    for complexity_defaults in (histogram_complexity, boxplot_complexity, density_complexity):
        assert sorted(complexity_defaults["criteria_weights"].keys()) == [
            "reasoning_load",
            "scene_variant_load",
            "visual_scan",
        ]


def test_charts_composition_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "composition")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["category_count_min"]) == 4
    assert int(generation_shared["category_count_max"]) == 7
    assert int(generation_shared["series_count_min"]) == 3
    assert int(generation_shared["series_count_max"]) == 5
    assert int(generation_shared["value_min"]) == 4
    assert int(generation_shared["value_max"]) == 18
    assert sorted(generation_shared["task_variant_weights"].keys()) == [
        "combined_share_subset",
        "stack_segment_value",
        "stack_total_at_label",
    ]
    assert sorted(generation_shared["scene_variant_weights"].keys()) == [
        "donut",
        "pie",
        "stacked_bar",
        "stacked_horizontal_bar",
    ]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["plot_margin_left_px"]) > 0
    assert int(render_shared["plot_margin_bottom_px"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_composition_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "composition_chart_value"
    assert str(prompt_shared["task_key"]).strip() == "subset_value_query"
    assert str(prompt_shared["object_description_stacked_bar"]).strip()
    assert str(prompt_shared["object_description_pie"]).strip()
    assert str(prompt_shared["evidence_hint_stack_segment_value"]).strip()
    assert str(prompt_shared["json_example_combined_share_subset"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_charts_composition_subset_value",
    )
    assert int(generation_defaults["category_count_min"]) == 4
    assert int(generation_defaults["series_count_max"]) == 5
    assert int(rendering_defaults["canvas_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_composition_v1"

    complexity_defaults = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_charts_composition_subset_value",
    )
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
    assert sorted(generation_shared["task_variant_weights"].keys()) == [
        "longest_decreasing_streak",
        "longest_increasing_streak",
        "peak_count",
        "trough_count",
    ]
    assert sorted(generation_shared["scene_variant_weights"].keys()) == [
        "area",
        "bar",
        "dot_plot",
        "horizontal_bar",
        "line",
        "lollipop",
    ]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["plot_margin_left_px"]) > 0
    assert int(render_shared["plot_margin_bottom_px"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_trend_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "ordered_chart_trend"
    assert str(prompt_shared["task_key"]).strip() == "structure_value_query"
    assert str(prompt_shared["object_description_horizontal_bar"]).strip()
    assert str(prompt_shared["evidence_hint_peak_count"]).strip()
    assert str(prompt_shared["json_example_longest_increasing_streak"]).strip()
    assert str(prompt_shared["json_example_answer_only_trough_count"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_charts_trend_structure_value",
    )
    assert int(generation_defaults["mark_count_min"]) == 6
    assert int(generation_defaults["mark_count_max"]) == 10
    assert int(rendering_defaults["canvas_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_trend_v1"

    complexity_defaults = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_charts_trend_structure_value",
    )
    assert sorted(complexity_defaults["criteria_weights"].keys()) == [
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    ]


def test_tables_statistics_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tables", "statistics")
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
    assert str(prompt_shared["bundle_id"]).strip() == "tables_statistics_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "styled_table_statistics"
    assert str(prompt_shared["task_key"]).strip() == "summary_label_query"
    assert str(prompt_shared["object_description_spreadsheet"]).strip()
    assert str(prompt_shared["evidence_hint_argmax"]).strip()
    assert str(prompt_shared["json_example_argmin"]).strip()
    assert str(prompt_shared["json_example_answer_only_argmax"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tables_statistics_summary_label",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == [
        "argmax",
        "argmin",
        "row_sum_argmax",
        "row_sum_argmin",
    ]
    assert int(generation_defaults["row_count_min"]) >= 5
    assert int(generation_defaults["numeric_column_count_max"]) == 5
    assert int(rendering_defaults["canvas_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "tables_statistics_v1"
    assert str(prompt_defaults["evidence_hint_row_sum_argmax"]).strip()
    assert str(prompt_defaults["json_example_row_sum_argmin"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tables_statistics_summary_value",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == [
        "column_mean",
        "column_median",
        "column_sum",
        "row_mean",
        "row_sum",
        "table_mean",
        "table_sum",
    ]
    assert int(generation_defaults["row_count_min"]) >= 5
    assert int(rendering_defaults["canvas_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "tables_statistics_v1"
    assert str(prompt_defaults["task_key"]).strip() == "summary_value_query"
    assert str(prompt_defaults["evidence_hint_column_sum"]).strip()
    assert str(prompt_defaults["json_example_column_median"]).strip()
    assert str(prompt_defaults["evidence_hint_row_sum"]).strip()
    assert str(prompt_defaults["json_example_row_mean"]).strip()
    assert str(prompt_defaults["evidence_hint_table_sum"]).strip()
    assert str(prompt_defaults["json_example_table_mean"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tables_statistics_filtered_subset_value",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == [
        "filtered_column_mean",
        "filtered_column_sum",
    ]
    assert int(rendering_defaults["canvas_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "tables_statistics_v1"
    assert str(prompt_defaults["task_key"]).strip() == "filtered_subset_value_query"
    assert str(prompt_defaults["evidence_hint_filtered_column_sum"]).strip()
    assert str(prompt_defaults["json_example_filtered_column_mean"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tables_statistics_filtered_subset_label",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == [
        "filtered_argmax",
        "filtered_argmin",
    ]
    assert int(rendering_defaults["canvas_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "tables_statistics_v1"
    assert str(prompt_defaults["task_key"]).strip() == "filtered_subset_label_query"
    assert str(prompt_defaults["evidence_hint_filtered_argmax"]).strip()
    assert str(prompt_defaults["json_example_filtered_argmin"]).strip()


def test_tables_counting_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tables", "counting")
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
    assert str(prompt_shared["bundle_id"]).strip() == "tables_counting_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "styled_table_counting"
    assert str(prompt_shared["task_key"]).strip() == "value_count_query"

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tables_counting_value_count",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == [
        "above_threshold",
        "below_threshold",
        "col_a_gt_col_b",
        "col_a_lt_col_b",
        "in_interval",
    ]
    assert int(rendering_defaults["canvas_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "tables_counting_v1"
    assert str(prompt_defaults["evidence_hint_above_threshold"]).strip()
    assert str(prompt_defaults["json_example_in_interval"]).strip()
    assert str(prompt_defaults["evidence_hint_col_a_gt_col_b"]).strip()
    assert str(prompt_defaults["json_example_col_a_lt_col_b"]).strip()


def test_tables_readout_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tables", "readout")
    for section in ("generation", "rendering", "prompt"):
        assert isinstance(cfg.get(section), dict)

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "tables_readout_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "styled_table_readout"
    assert str(prompt_shared["task_key"]).strip() == "subset_value_query"

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tables_readout_subset_value",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == [
        "cell_difference_two_abs",
        "cell_lookup",
        "cell_sum_two",
    ]
    assert int(rendering_defaults["canvas_height"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "tables_readout_v1"
    assert str(prompt_defaults["evidence_hint_cell_lookup"]).strip()
    assert str(prompt_defaults["evidence_hint_cell_sum_two"]).strip()
    assert str(prompt_defaults["evidence_hint_cell_difference_two_abs"]).strip()
    assert str(prompt_defaults["json_example_cell_lookup"]).strip()
    assert str(prompt_defaults["json_example_cell_sum_two"]).strip()


def test_tables_relation_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tables", "relation")
    for section in ("generation", "rendering", "prompt"):
        assert isinstance(cfg.get(section), dict)

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "tables_relation_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "styled_table_relation"
    assert str(prompt_shared["task_key"]).strip() == "row_compare_label_query"

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tables_relation_row_compare_label",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == [
        "higher_of_two_rows",
        "lower_of_two_rows",
    ]
    assert int(rendering_defaults["canvas_height"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "tables_relation_v1"
    assert str(prompt_defaults["evidence_hint_higher_of_two_rows"]).strip()
    assert str(prompt_defaults["evidence_hint_lower_of_two_rows"]).strip()
    assert str(prompt_defaults["json_example_higher_of_two_rows"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tables_relation_extremum_transfer_value",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == [
        "argmax_transfer",
        "argmin_transfer",
    ]
    assert int(rendering_defaults["canvas_height"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "tables_relation_v1"
    assert str(prompt_defaults["task_key"]).strip() == "extremum_transfer_value_query"
    assert str(prompt_defaults["evidence_hint_argmax_transfer"]).strip()
    assert str(prompt_defaults["json_example_argmin_transfer"]).strip()


def test_tables_ranking_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tables", "ranking")
    for section in ("generation", "rendering", "prompt"):
        assert isinstance(cfg.get(section), dict)

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "tables_ranking_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "styled_table_ranking"
    assert str(prompt_shared["task_key"]).strip() == "kth_label_query"

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tables_ranking_label",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == [
        "kth_highest_in_column",
        "kth_lowest_in_column",
    ]
    assert int(rendering_defaults["canvas_height"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "tables_ranking_v1"
    assert str(prompt_defaults["evidence_hint_kth_highest_in_column"]).strip()
    assert str(prompt_defaults["json_example_kth_lowest_in_column"]).strip()


def test_tables_temporal_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tables", "temporal")
    for section in ("generation", "rendering", "prompt"):
        assert isinstance(cfg.get(section), dict)

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "tables_temporal_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "styled_table_temporal"
    assert str(prompt_shared["task_key"]).strip() == "temporal_value_query"

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tables_temporal_value",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == [
        "absolute_difference_between_years",
        "delta_between_years",
        "mean_over_year_interval",
        "sum_over_year_interval",
        "value_at_year",
    ]
    assert int(rendering_defaults["canvas_height"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "tables_temporal_v1"
    assert str(prompt_defaults["evidence_hint_value_at_year"]).strip()
    assert str(prompt_defaults["evidence_hint_delta_between_years"]).strip()
    assert str(prompt_defaults["evidence_hint_sum_over_year_interval"]).strip()
    assert str(prompt_defaults["json_example_mean_over_year_interval"]).strip()


def test_puzzles_arithmetic_defaults_loaded() -> None:
    cfg = get_task_group_defaults("puzzles", "arithmetic")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "puzzles_arithmetic_v1"
    assert str(prompt_shared["answer_hint"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_puzzles_arithmetic_equation_value",
    )
    assert str(prompt_defaults["task_family_key"]).strip() == "arithmetic_unknown_slot_puzzle"
    assert str(prompt_defaults["task_key"]).strip() == "equation_value_query"
    assert str(prompt_defaults["object_description_equation_strip"]).strip()
    assert sorted(generation_defaults["task_variant_weights"].keys()) == [
        "operand_unknown",
        "result_unknown",
    ]
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == [
        "equation_card",
        "equation_outline",
        "equation_strip",
    ]
    assert int(generation_defaults["answer_min"]) >= 1
    assert int(generation_defaults["answer_max"]) == 24
    assert int(generation_defaults["operand_count_min"]) == 2
    assert int(generation_defaults["operand_count_max"]) == 5
    assert int(generation_defaults["operand_value_min"]) == 1
    assert int(generation_defaults["operand_value_max"]) == 12
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["slot_width_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "puzzles_arithmetic_v1"
    assert str(prompt_defaults["evidence_hint_result_unknown"]).strip()
    assert str(prompt_defaults["evidence_hint_operand_unknown"]).strip()
    assert str(prompt_defaults["json_example_result_unknown"]).strip()
    assert str(prompt_defaults["json_example_answer_only_operand_unknown"]).strip()

    arithmetic_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_puzzles_arithmetic_equation_value",
    )
    assert arithmetic_complexity["criteria_weights"] == {
        "visual_scan": pytest.approx(0.34),
        "reasoning_load": pytest.approx(0.33),
        "scene_variant_load": pytest.approx(0.33),
    }

    balance_generation, balance_rendering, balance_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_puzzles_arithmetic_balance_value",
    )
    assert str(balance_prompt["task_family_key"]).strip() == "arithmetic_balance_query_puzzle"
    assert str(balance_prompt["task_key"]).strip() == "balance_value_query"
    assert str(balance_prompt["object_description_balance_strip"]).strip()
    assert sorted(balance_generation["task_variant_weights"].keys()) == [
        "sum_pair_unknown",
        "three_panel_chain_unknown",
        "two_panel_chain_unknown",
    ]
    assert sorted(balance_generation["scene_variant_weights"].keys()) == [
        "balance_card",
        "balance_outline",
        "balance_strip",
    ]
    assert int(balance_generation["answer_min"]) >= 1
    assert int(balance_generation["answer_max"]) == 24
    assert int(balance_generation["object_value_min"]) == 1
    assert int(balance_generation["object_value_max"]) == 12
    assert int(balance_rendering["canvas_width"]) > 0
    assert int(balance_rendering["query_box_width_px"]) > 0
    assert str(balance_prompt["evidence_hint_sum_pair_unknown"]).strip()
    assert str(balance_prompt["evidence_hint_three_panel_chain_unknown"]).strip()
    assert str(balance_prompt["json_example_two_panel_chain_unknown"]).strip()
    assert str(balance_prompt["json_example_answer_only_sum_pair_unknown"]).strip()


def test_charts_multiseries_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "multiseries")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["category_count_min"]) == 5
    assert int(generation_shared["category_count_max"]) == 10
    assert int(generation_shared["series_count_min"]) == 2
    assert int(generation_shared["series_count_max"]) == 3
    assert int(generation_shared["target_answer_min"]) == 0
    assert int(generation_shared["target_answer_max"]) == 8
    assert sorted(generation_shared["task_variant_weights"].keys()) == [
        "series_a_gt_b_count",
        "series_a_lt_b_count",
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
    assert str(prompt_shared["bundle_id"]).strip() == "charts_multiseries_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "multiseries_chart_comparison"
    assert str(prompt_shared["task_key"]).strip() == "pairwise_comparison_count_query"
    assert str(prompt_shared["object_description_grouped_bar"]).strip()
    assert str(prompt_shared["object_description_grouped_horizontal_bar"]).strip()
    assert str(prompt_shared["object_description_multi_line"]).strip()
    assert str(prompt_shared["object_description_grouped_lollipop"]).strip()
    assert str(prompt_shared["json_example_series_a_gt_b_count"]).strip()
    assert str(prompt_shared["json_example_series_a_lt_b_count"]).strip()

    complexity_defaults = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_charts_multiseries_pairwise_comparison_count",
    )
    assert sorted(complexity_defaults["criteria_weights"].keys()) == [
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    ]


def test_charts_counting_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "counting")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["mark_count_min"]) >= 5
    assert int(generation_shared["mark_count_max"]) == 10
    assert int(generation_shared["value_max"]) == 20
    assert int(generation_shared["target_answer_min"]) == 0
    assert int(generation_shared["target_answer_max"]) == 10
    assert sorted(generation_shared["task_variant_weights"].keys()) == [
        "above_threshold",
        "below_threshold",
        "in_interval",
    ]
    assert sorted(generation_shared["scene_variant_weights"].keys()) == [
        "area",
        "bar",
        "donut",
        "dot_plot",
        "horizontal_bar",
        "line",
        "lollipop",
        "pie",
        "radar",
        "scatter",
    ]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_counting_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "labeled_chart_counting"
    assert str(prompt_shared["task_key"]).strip() == "value_count_query"
    assert str(prompt_shared["object_description_bar"]).strip()
    assert str(prompt_shared["evidence_hint_in_interval"]).strip()
    assert str(prompt_shared["json_example_below_threshold"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_charts_counting_value_count",
    )
    assert int(generation_defaults["mark_count_min"]) >= 5
    assert int(generation_defaults["mark_count_max"]) == 10
    assert int(generation_defaults["target_answer_max"]) == 10
    assert int(rendering_defaults["canvas_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_counting_v1"

    complexity_defaults = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_charts_counting_value_count",
    )
    assert sorted(complexity_defaults["criteria_weights"].keys()) == [
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    ]


def test_charts_readout_defaults_loaded() -> None:
    cfg = get_task_group_defaults("charts", "readout")
    for section in ("generation", "rendering", "prompt", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["mark_count_min"]) >= 5
    assert int(generation_shared["mark_count_max"]) == 10
    assert int(generation_shared["value_max"]) == 20
    assert sorted(generation_shared["task_variant_weights"].keys()) == [
        "difference_two_abs",
        "max_two",
        "mean_two",
        "min_two",
        "sum_two",
    ]
    assert sorted(generation_shared["scene_variant_weights"].keys()) == [
        "area",
        "bar",
        "donut",
        "dot_plot",
        "horizontal_bar",
        "line",
        "lollipop",
        "pie",
        "radar",
        "scatter",
    ]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_readout_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "labeled_chart_readout"
    assert str(prompt_shared["task_key"]).strip() == "subset_value_query"
    assert str(prompt_shared["evidence_hint"]).strip()
    assert str(prompt_shared["json_example_sum_two"]).strip()
    assert str(prompt_shared["json_example_answer_only_mean_two"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_charts_readout_subset_value",
    )
    assert int(generation_defaults["mark_count_min"]) >= 5
    assert int(generation_defaults["mark_count_max"]) == 10
    assert int(generation_defaults["value_max"]) == 20
    assert int(rendering_defaults["canvas_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_readout_v1"

    complexity_defaults = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_charts_readout_subset_value",
    )
    assert sorted(complexity_defaults["criteria_weights"].keys()) == [
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    ]


def test_geometry_analytical_defaults_loaded() -> None:
    cfg = get_task_group_defaults("geometry", "analytical_2d")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["answer_min"]) >= 0
    assert int(generation_shared["answer_max"]) >= int(generation_shared["answer_min"])
    assert sorted(generation_shared["shape_weights"].keys()) == [
        "circle",
        "ellipse",
        "parallelogram",
        "rectangle",
        "rhombus",
        "trapezoid",
        "triangle",
    ]
    assert sorted(generation_shared["mode_weights"].keys()) == ["derived", "explicit"]
    assert bool(generation_shared["balanced_shape_sampling"]) is True
    assert bool(generation_shared["balanced_mode_sampling"]) is True

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_size_min"]) > 0
    assert int(render_shared["canvas_size_max"]) >= int(render_shared["canvas_size_min"])
    assert int(render_shared["graph_cells_min"]) > 0
    assert int(render_shared["graph_cells_max"]) >= int(render_shared["graph_cells_min"])
    assert int(render_shared["line_width_min"]) >= 1
    assert int(render_shared["line_width_max"]) >= int(render_shared["line_width_min"])
    assert int(render_shared["helper_line_width_min"]) >= 1
    assert int(render_shared["helper_line_width_max"]) >= int(render_shared["helper_line_width_min"])
    assert int(render_shared["label_stroke_width_min"]) >= 1
    assert int(render_shared["label_stroke_width_max"]) >= int(render_shared["label_stroke_width_min"])
    assert int(render_shared["analytical_unit_spacing_px"]) >= 2
    assert int(render_shared["analytical_unit_padding_px"]) >= 0
    assert 0.0 < float(render_shared["analytical_scene_fill_ratio"]) < 1.0
    visual_background = cfg["visual"]["background"]
    assert bool(visual_background["enabled"]) is True
    assert {"solid_cool", "solid_offwhite", "solid_warm"}.issubset(set(visual_background["styles"].keys()))
    assert float(visual_background["weights"]["graph_paper"]) == 0.0
    assert float(visual_background["weights"]["solid_offwhite"]) > 0.0

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "visual_scan": 0.20,
        "analytical_reasoning": 0.55,
        "ambiguity": 0.20,
        "output_burden": 0.05,
    }

    prompt_generation, prompt_rendering, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_analytical_2d_area",
    )
    assert int(prompt_generation["side_min"]) > 0
    assert int(prompt_generation["side_max"]) >= int(prompt_generation["side_min"])
    assert int(prompt_generation["circle_radius_min"]) > 0
    assert int(prompt_generation["circle_radius_max"]) >= int(prompt_generation["circle_radius_min"])
    assert int(prompt_generation["ellipse_axis_min"]) > 0
    assert int(prompt_generation["ellipse_axis_max"]) >= int(prompt_generation["ellipse_axis_min"])
    assert int(prompt_rendering["line_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip()
    assert str(prompt_defaults["task_family_key"]).strip()
    assert str(prompt_defaults["task_key"]).strip()
    assert str(prompt_defaults["object_description"]).strip()
    assert str(prompt_defaults["evidence_hint_measurement_map"]).strip()
    assert str(prompt_defaults["answer_hint_integer"]).strip()
    assert str(prompt_defaults["answer_hint_pi"]).strip()
    assert str(prompt_defaults["json_example_answer_only_integer"]).strip()
    assert str(prompt_defaults["json_example_answer_only_pi"]).strip()
    for key in (
        "rectangle_explicit",
        "rectangle_derived",
        "triangle_explicit",
        "triangle_derived",
        "parallelogram_explicit",
        "parallelogram_derived",
        "trapezoid_explicit",
        "trapezoid_derived",
        "rhombus_explicit",
        "rhombus_derived",
        "circle_explicit",
        "circle_derived",
        "ellipse_explicit",
        "ellipse_derived",
    ):
        assert str(prompt_defaults[f"question_text_{key}"]).strip()
        assert str(prompt_defaults[f"json_example_{key}"]).strip()

    length_generation, length_rendering, length_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_analytical_2d_length",
    )
    assert sorted(length_generation["variant_weights"].keys()) == [
        "circle_chord_length",
        "inscribed_square_side",
        "isosceles_trapezoid_leg",
        "rectangle_diagonal_side",
        "rhombus_diagonal_side",
        "triangle_altitude_side",
    ]
    assert bool(length_generation["balanced_variant_sampling"]) is True
    assert int(length_generation["dimension_min"]) >= 1
    assert int(length_generation["dimension_max"]) >= int(length_generation["dimension_min"])
    assert int(length_generation["circle_radius_min"]) >= 1
    assert int(length_generation["circle_radius_max"]) >= int(length_generation["circle_radius_min"])
    assert int(length_rendering["line_width"]) > 0
    assert str(length_prompt["bundle_id"]).strip() == "geometry_analytical_length_v1"
    assert str(length_prompt["task_key"]).strip() == "analytical_length_query"
    assert str(length_prompt["task_family_key"]).strip() == "analytical_length_scene"
    assert str(length_prompt["object_description"]).strip()
    assert str(length_prompt["evidence_hint_measurement_map"]).strip()
    assert str(length_prompt["answer_hint_number"]).strip()
    for key in (
        "triangle_altitude_side",
        "rectangle_diagonal_side",
        "rhombus_diagonal_side",
        "isosceles_trapezoid_leg",
        "inscribed_square_side",
        "circle_chord_length",
    ):
        assert str(length_prompt[f"question_text_{key}"]).strip()

    composite_generation, composite_rendering, composite_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_analytical_2d_composite_area",
    )
    assert sorted(composite_generation["variant_weights"].keys()) == [
        "l_shape_cutout",
        "rectangle_inner_cutout",
        "rectangle_triangle_cutout",
        "rectangle_triangle_union",
        "step_rectangles_union",
    ]
    assert bool(composite_generation["balanced_variant_sampling"]) is True
    assert int(composite_generation["dimension_min"]) >= 1
    assert int(composite_generation["dimension_max"]) >= int(composite_generation["dimension_min"])
    assert int(composite_rendering["line_width"]) > 0
    assert float(composite_rendering["analytical_scene_fill_ratio"]) < float(render_shared["analytical_scene_fill_ratio"])
    assert str(composite_prompt["bundle_id"]).strip() == "geometry_analytical_composite_area_v1"
    assert str(composite_prompt["task_key"]).strip() == "analytical_composite_area_query"
    assert str(composite_prompt["task_family_key"]).strip() == "analytical_composite_area_scene"
    assert str(composite_prompt["object_description"]).strip()
    assert str(composite_prompt["evidence_hint_measurement_map"]).strip()
    assert str(composite_prompt["answer_hint_integer"]).strip()
    for key in (
        "rectangle_inner_cutout",
        "rectangle_triangle_cutout",
        "rectangle_triangle_union",
        "l_shape_cutout",
        "step_rectangles_union",
    ):
        assert str(composite_prompt[f"question_text_{key}"]).strip()

    perimeter_generation, perimeter_rendering, perimeter_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_analytical_2d_perimeter",
    )
    assert sorted(perimeter_generation["variant_weights"].keys()) == [
        "inscribed_square_diameter",
        "isosceles_trapezoid_bases_height",
        "rectangle_side_diagonal",
        "rhombus_diagonals",
        "right_triangle_leg_hypotenuse",
    ]
    assert bool(perimeter_generation["balanced_variant_sampling"]) is True
    assert int(perimeter_generation["dimension_min"]) >= 1
    assert int(perimeter_generation["dimension_max"]) >= int(perimeter_generation["dimension_min"])
    assert int(perimeter_generation["circle_radius_min"]) >= 1
    assert int(perimeter_generation["circle_radius_max"]) >= int(perimeter_generation["circle_radius_min"])
    assert int(perimeter_rendering["line_width"]) > 0
    assert str(perimeter_prompt["bundle_id"]).strip() == "geometry_analytical_perimeter_v1"
    assert str(perimeter_prompt["task_key"]).strip() == "analytical_perimeter_query"
    assert str(perimeter_prompt["task_family_key"]).strip() == "analytical_perimeter_scene"
    assert str(perimeter_prompt["object_description"]).strip()
    assert str(perimeter_prompt["evidence_hint_measurement_map"]).strip()
    assert str(perimeter_prompt["answer_hint_number"]).strip()
    for key in (
        "right_triangle_leg_hypotenuse",
        "rectangle_side_diagonal",
        "rhombus_diagonals",
        "isosceles_trapezoid_bases_height",
        "inscribed_square_diameter",
    ):
        assert str(perimeter_prompt[f"question_text_{key}"]).strip()


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
    assert "task_geometry_comparison_angle" in generation_overrides
    assert "task_geometry_comparison_area" in generation_overrides
    assert "task_geometry_comparison_length" in generation_overrides
    assert "task_geometry_comparison_perimeter" in generation_overrides

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
    assert str(prompt_shared["task_family_key"]).strip()
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
        task_id="task_geometry_comparison_angle",
    )
    assert int(angle_generation["min_angle"]) < int(angle_generation["max_angle"])
    assert int(angle_generation["angle_step"]) > 0
    assert sorted(angle_generation["query_type_weights"].keys()) == ["largest", "smallest"]
    assert sorted(angle_generation["object_count_weights"].keys()) == ["4", "5", "6"]
    assert float(angle_generation["min_absolute_gap_degrees"]) > 0.0
    assert int(angle_rendering["line_width"]) > 0
    assert str(angle_prompt["object_description"]).strip()
    assert str(angle_prompt["question_text_largest"]).strip()
    assert str(angle_prompt["question_text_smallest"]).strip()
    assert str(angle_prompt["evidence_hint"]).strip()
    assert str(angle_prompt["answer_hint"]).strip()

    area_generation, area_rendering, area_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_comparison_area",
    )
    assert int(area_generation["min_rectangle_width"]) < int(area_generation["max_rectangle_width"])
    assert int(area_generation["min_rectangle_height"]) < int(area_generation["max_rectangle_height"])
    assert sorted(area_generation["query_type_weights"].keys()) == ["largest", "smallest"]
    assert sorted(area_generation["object_count_weights"].keys()) == ["4", "5", "6"]
    assert float(area_generation["min_absolute_gap_square_units"]) > 0.0
    assert int(area_rendering["line_width"]) > 0
    assert str(area_prompt["object_description"]).strip()
    assert str(area_prompt["question_text_largest"]).strip()
    assert str(area_prompt["question_text_smallest"]).strip()
    assert str(area_prompt["evidence_hint"]).strip()
    assert str(area_prompt["answer_hint"]).strip()

    perimeter_generation, perimeter_rendering, perimeter_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_comparison_perimeter",
    )
    assert int(perimeter_generation["min_rectangle_width"]) < int(perimeter_generation["max_rectangle_width"])
    assert int(perimeter_generation["min_rectangle_height"]) < int(perimeter_generation["max_rectangle_height"])
    assert sorted(perimeter_generation["query_type_weights"].keys()) == ["largest", "smallest"]
    assert sorted(perimeter_generation["object_count_weights"].keys()) == ["4", "5", "6"]
    assert float(perimeter_generation["min_absolute_gap_units"]) > 0.0
    assert int(perimeter_rendering["line_width"]) > 0
    assert str(perimeter_prompt["object_description"]).strip()
    assert str(perimeter_prompt["question_text_largest"]).strip()
    assert str(perimeter_prompt["question_text_smallest"]).strip()
    assert str(perimeter_prompt["evidence_hint"]).strip()
    assert str(perimeter_prompt["answer_hint"]).strip()

    length_generation, length_rendering, length_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_comparison_length",
    )
    assert int(length_generation["min_segment_length"]) < int(length_generation["max_segment_length"])
    assert int(length_generation["max_abs_vector_component"]) > 0
    assert sorted(length_generation["query_type_weights"].keys()) == ["largest", "smallest"]
    assert sorted(length_generation["object_count_weights"].keys()) == ["4", "5", "6"]
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
    assert "task_geometry_counting_angle" in generation_overrides
    assert "task_geometry_counting_triangle" in generation_overrides
    assert "task_geometry_counting_quadrilateral" in generation_overrides
    assert "task_geometry_counting_shape_type" in generation_overrides
    assert "task_geometry_counting_convexity" in generation_overrides

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
    assert str(prompt_shared["task_family_key"]).strip()
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
        task_id="task_geometry_counting_angle",
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
        task_id="task_geometry_counting_triangle",
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
        task_id="task_geometry_counting_quadrilateral",
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
        task_id="task_geometry_counting_shape_type",
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
        task_id="task_geometry_counting_convexity",
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


def test_geometry_analytical_3d_defaults_loaded() -> None:
    cfg = get_task_group_defaults("geometry", "analytical_3d")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["answer_min"]) >= 0
    assert int(generation_shared["answer_max"]) >= int(generation_shared["answer_min"])
    assert int(generation_shared["dimension_min"]) > 0
    assert int(generation_shared["dimension_max"]) >= int(generation_shared["dimension_min"])
    assert int(generation_shared["radius_min"]) > 0
    assert int(generation_shared["radius_max"]) >= int(generation_shared["radius_min"])
    assert int(generation_shared["sphere_radius_min"]) > 0
    assert int(generation_shared["sphere_radius_max"]) >= int(generation_shared["sphere_radius_min"])
    assert "task_geometry_analytical_3d_volume" in cfg["generation"]["task_overrides"]
    assert "task_geometry_analytical_3d_surface_area" in cfg["generation"]["task_overrides"]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_size_min"]) > 0
    assert int(render_shared["canvas_size_max"]) >= int(render_shared["canvas_size_min"])
    assert int(render_shared["line_width_min"]) >= 1
    assert int(render_shared["line_width_max"]) >= int(render_shared["line_width_min"])
    assert int(render_shared["helper_line_width_min"]) >= 1
    assert int(render_shared["helper_line_width_max"]) >= int(render_shared["helper_line_width_min"])
    assert int(render_shared["label_stroke_width_min"]) >= 1
    assert int(render_shared["label_stroke_width_max"]) >= int(render_shared["label_stroke_width_min"])

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "visual_scan": 0.20,
        "analytical_reasoning": 0.55,
        "ambiguity": 0.20,
        "output_burden": 0.05,
    }

    gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_analytical_3d_volume",
    )
    assert sorted(gen_defaults["variant_weights"].keys()) == [
        "cone_given_r_h",
        "cylinder_given_r_h",
        "rectangular_prism_given_lwh",
        "sphere_given_r",
        "square_pyramid_given_base_height",
        "triangular_prism_given_b_h_l",
    ]
    assert bool(gen_defaults["balanced_variant_sampling"]) is True
    assert int(render_defaults["line_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip()
    assert str(prompt_defaults["task_family_key"]).strip()
    assert str(prompt_defaults["task_key"]).strip()
    assert str(prompt_defaults["object_description"]).strip()
    assert str(prompt_defaults["evidence_hint_measurement_map"]).strip()
    assert str(prompt_defaults["answer_hint_integer"]).strip()
    assert str(prompt_defaults["answer_hint_pi"]).strip()
    assert str(prompt_defaults["json_example_answer_only_integer"]).strip()
    assert str(prompt_defaults["json_example_answer_only_pi"]).strip()
    for key in (
        "rectangular_prism_given_lwh",
        "triangular_prism_given_b_h_l",
        "square_pyramid_given_base_height",
        "cylinder_given_r_h",
        "cone_given_r_h",
        "sphere_given_r",
    ):
        assert str(prompt_defaults[f"question_text_{key}"]).strip()

    surface_generation, _surface_rendering, surface_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_analytical_3d_surface_area",
    )
    assert sorted(surface_generation["variant_weights"].keys()) == [
        "cone_given_r_slant_height",
        "cylinder_given_r_h",
        "rectangular_prism_given_lwh",
        "sphere_given_r",
        "square_pyramid_given_base_side_slant_height",
        "triangular_prism_given_a_b_c_l",
    ]
    assert bool(surface_generation["balanced_variant_sampling"]) is True
    assert str(surface_prompt["bundle_id"]).strip() == "geometry_analytical_surface_area_v1"
    assert str(surface_prompt["task_key"]).strip() == "analytical_surface_area_query"
    for key in (
        "rectangular_prism_given_lwh",
        "triangular_prism_given_a_b_c_l",
        "square_pyramid_given_base_side_slant_height",
        "cylinder_given_r_h",
        "cone_given_r_slant_height",
        "sphere_given_r",
    ):
        assert str(surface_prompt[f"question_text_{key}"]).strip()


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
    assert "task_icons_counting_color" in cfg["generation"]["task_overrides"]
    assert "task_icons_counting_attribute_binding" in cfg["generation"]["task_overrides"]
    assert "task_icons_counting_size_relation" in cfg["generation"]["task_overrides"]
    assert "task_icons_counting_singleton_type" in cfg["generation"]["task_overrides"]
    assert "task_icons_counting_type" in cfg["generation"]["task_overrides"]
    assert "task_icons_counting_orientation" in cfg["generation"]["task_overrides"]

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
    assert str(prompt_shared["task_family_key"]).strip()
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

    color_generation, color_rendering, color_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_counting_color",
    )
    assert str(color_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert float(color_rendering["min_color_distance"]) == 60.0
    assert int(color_rendering["palette_size_min"]) == 3
    assert int(color_rendering["palette_size_max"]) == 4
    assert str(color_prompt["object_description"]).strip()
    assert str(color_prompt["question_text"]).strip()
    assert str(color_prompt["evidence_hint"]).strip()
    assert str(color_prompt["answer_hint"]).strip()
    assert str(color_prompt["json_example"]).strip()
    assert str(color_prompt["json_example_answer_only"]).strip()

    attribute_binding_generation, attribute_binding_rendering, attribute_binding_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_counting_attribute_binding",
    )
    assert str(attribute_binding_generation["pool_manifest"]).strip() == "non_symmetry.txt"
    assert list(attribute_binding_generation["rotation_candidates_degrees"]) == [0, 90, 180, 270]
    assert float(attribute_binding_rendering["min_color_distance"]) == 40.0
    assert int(attribute_binding_rendering["palette_size_min"]) == 3
    assert int(attribute_binding_rendering["palette_size_max"]) == 4
    assert str(attribute_binding_prompt["object_description"]).strip()
    assert str(attribute_binding_prompt["question_text"]).strip()
    assert str(attribute_binding_prompt["evidence_hint"]).strip()
    assert str(attribute_binding_prompt["answer_hint"]).strip()
    assert str(attribute_binding_prompt["json_example"]).strip()
    assert str(attribute_binding_prompt["json_example_answer_only"]).strip()

    size_generation, size_rendering, size_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_counting_size_relation",
    )
    assert str(size_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert list(size_generation["rotation_candidates_degrees"]) == [0, 90, 180, 270]
    assert list(size_generation["size_relation_candidates"]) == ["smaller", "larger"]
    assert int(size_generation["size_relation_min_delta_px"]) == 12
    assert int(size_generation["object_count_max"]) == 16
    assert int(size_generation["target_count_max"]) == 8
    assert int(size_generation["distractor_count_max"]) == 8
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

    type_generation, type_rendering, type_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_counting_type",
    )
    assert str(type_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert int(type_rendering["canvas_width"]) > 0
    assert int(type_rendering["reference_panel_width_px"]) > 0
    assert str(type_prompt["object_description"]).strip()
    assert str(type_prompt["question_text"]).strip()
    assert str(type_prompt["evidence_hint"]).strip()
    assert str(type_prompt["answer_hint"]).strip()
    assert str(type_prompt["json_example"]).strip()
    assert str(type_prompt["json_example_answer_only"]).strip()

    singleton_generation, singleton_rendering, singleton_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_counting_singleton_type",
    )
    assert str(singleton_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert int(singleton_generation["object_count_min"]) == 6
    assert int(singleton_generation["object_count_max"]) == 15
    assert int(singleton_generation["target_count_min"]) == 0
    assert int(singleton_generation["target_count_max"]) == 5
    assert int(singleton_generation["repeated_type_count_min"]) == 1
    assert int(singleton_generation["repeated_type_count_max"]) == 4
    assert int(singleton_generation["repeated_type_multiplicity_min"]) == 2
    assert int(singleton_generation["repeated_type_multiplicity_max"]) == 4
    assert int(singleton_rendering["canvas_width"]) > 0
    assert int(singleton_rendering["canvas_height"]) > 0
    assert str(singleton_prompt["task_family_key"]).strip() == "single_scene_counting"
    assert str(singleton_prompt["object_description"]).strip()
    assert str(singleton_prompt["question_text"]).strip()
    assert str(singleton_prompt["evidence_hint"]).strip()
    assert str(singleton_prompt["answer_hint"]).strip()
    assert str(singleton_prompt["json_example"]).strip()
    assert str(singleton_prompt["json_example_answer_only"]).strip()

    orientation_generation, orientation_rendering, orientation_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_counting_orientation",
    )
    assert str(orientation_generation["pool_manifest"]).strip() == "non_symmetry.txt"
    assert list(orientation_generation["rotation_candidates_degrees"]) == [0, 90, 180, 270]
    assert int(orientation_rendering["canvas_width"]) > 0
    assert str(orientation_prompt["object_description"]).strip()
    assert str(orientation_prompt["question_text"]).strip()
    assert str(orientation_prompt["evidence_hint"]).strip()
    assert str(orientation_prompt["answer_hint"]).strip()
    assert str(orientation_prompt["json_example"]).strip()
    assert str(orientation_prompt["json_example_answer_only"]).strip()


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
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers"}
    assert set(generation_shared["layout_variant_weights"].keys()) == {"circular", "shell", "spring"}
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
    assert str(prompt_shared["task_family_key"]).strip()
    assert str(prompt_shared["task_key"]).strip()
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()
    assert str(prompt_shared["object_description_undirected"]).strip()
    assert str(prompt_shared["object_description_directed"]).strip()
    assert str(prompt_shared["question_text_degree_count"]).strip()
    assert str(prompt_shared["question_text_in_degree_count"]).strip()
    assert str(prompt_shared["question_text_out_degree_count"]).strip()
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
        task_id="task_graph_counting_degree_count",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == [
        "degree_count",
        "in_degree_count",
        "out_degree_count",
    ]
    assert int(generation_defaults["node_count_min"]) == 5
    assert int(generation_defaults["node_count_max"]) == 10
    assert int(generation_defaults["directed_node_count_max"]) == 9
    assert int(generation_defaults["query_degree_min"]) == 0
    assert int(generation_defaults["query_degree_max"]) == 4
    assert int(generation_defaults["directed_degree_sequence_max_degree"]) == 4
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert int(rendering_defaults["arrow_length_px"]) > 0
    assert int(rendering_defaults["arrow_width_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_counting_v1"
    assert str(prompt_defaults["task_family_key"]).strip() == "single_graph_counting"
    assert str(prompt_defaults["task_key"]).strip() == "degree_count_query"
    assert str(prompt_defaults["object_description_undirected"]).strip()
    assert str(prompt_defaults["object_description_directed"]).strip()
    assert str(prompt_defaults["question_text_degree_count"]).strip()
    assert str(prompt_defaults["question_text_in_degree_count"]).strip()
    assert str(prompt_defaults["question_text_out_degree_count"]).strip()

    articulation_generation_defaults, articulation_rendering_defaults, articulation_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph_counting_articulation_point_count",
        )
    )
    assert "articulation_point_count" in articulation_generation_defaults["task_variant_weights"]
    assert int(articulation_generation_defaults["node_count_min"]) == 5
    assert int(articulation_generation_defaults["node_count_max"]) == 10
    assert int(articulation_generation_defaults["target_count_min"]) == 0
    assert int(articulation_generation_defaults["target_count_max"]) == 8
    assert int(articulation_rendering_defaults["canvas_width"]) > 0
    assert int(articulation_rendering_defaults["node_radius_min_px"]) > 0
    assert str(articulation_prompt_defaults["bundle_id"]).strip() == "graph_counting_v1"
    assert str(articulation_prompt_defaults["task_family_key"]).strip() == "single_graph_counting"
    assert str(articulation_prompt_defaults["task_key"]).strip() == "articulation_point_count_query"
    assert str(articulation_prompt_defaults["question_text_articulation_point_count"]).strip()


def test_graph_relation_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "relation")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 5
    assert int(generation_shared["node_count_max"]) == 10
    assert int(generation_shared["component_count_min"]) == 2
    assert int(generation_shared["component_count_max"]) == 4
    assert int(generation_shared["target_component_size_min"]) == 1
    assert int(generation_shared["target_component_size_max"]) == 6
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers"}
    assert set(generation_shared["layout_variant_weights"].keys()) == {"circular", "shell", "spring"}
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
    assert str(prompt_shared["bundle_id"]).strip() == "graph_relation_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "single_graph_relation"
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
        task_id="task_graph_relation_same_component_count",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == ["same_component_count"]
    assert int(generation_defaults["node_count_min"]) == 5
    assert int(generation_defaults["node_count_max"]) == 10
    assert int(generation_defaults["component_count_min"]) == 2
    assert int(generation_defaults["component_count_max"]) == 4
    assert int(generation_defaults["target_component_size_min"]) == 1
    assert int(generation_defaults["target_component_size_max"]) == 6
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_relation_v1"
    assert str(prompt_defaults["task_family_key"]).strip() == "single_graph_relation"
    assert str(prompt_defaults["task_key"]).strip() == "same_component_count_query"
    assert str(prompt_defaults["question_text_same_component_count"]).strip()

    reachable_generation_defaults, reachable_rendering_defaults, reachable_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph_relation_reachable_count",
    )
    assert "reachable_count" in reachable_generation_defaults["task_variant_weights"]
    assert int(reachable_generation_defaults["node_count_min"]) == 5
    assert int(reachable_generation_defaults["directed_node_count_max"]) == 9
    assert int(reachable_generation_defaults["target_reachable_count_min"]) == 1
    assert int(reachable_generation_defaults["target_reachable_count_max"]) == 7
    assert int(reachable_rendering_defaults["canvas_width"]) > 0
    assert int(reachable_rendering_defaults["node_radius_min_px"]) > 0
    assert str(reachable_prompt_defaults["bundle_id"]).strip() == "graph_relation_v1"
    assert str(reachable_prompt_defaults["task_family_key"]).strip() == "single_graph_relation"
    assert str(reachable_prompt_defaults["task_key"]).strip() == "reachable_count_query"
    assert str(reachable_prompt_defaults["object_description_directed"]).strip()
    assert str(reachable_prompt_defaults["question_text_reachable_count"]).strip()
    assert str(reachable_prompt_defaults["evidence_hint_reachable_count"]).strip()

    cycle_generation_defaults, cycle_rendering_defaults, cycle_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph_relation_unique_cycle_size",
    )
    assert "unique_cycle_size" in cycle_generation_defaults["task_variant_weights"]
    assert int(cycle_generation_defaults["node_count_min"]) == 5
    assert int(cycle_generation_defaults["node_count_max"]) == 10
    assert int(cycle_generation_defaults["target_cycle_size_min"]) == 3
    assert int(cycle_generation_defaults["target_cycle_size_max"]) == 7
    assert int(cycle_rendering_defaults["canvas_width"]) > 0
    assert int(cycle_rendering_defaults["node_radius_min_px"]) > 0
    assert str(cycle_prompt_defaults["bundle_id"]).strip() == "graph_relation_v1"
    assert str(cycle_prompt_defaults["task_family_key"]).strip() == "single_graph_relation"
    assert str(cycle_prompt_defaults["task_key"]).strip() == "unique_cycle_size_query"
    assert str(cycle_prompt_defaults["question_text_unique_cycle_size"]).strip()


def test_graph_comparison_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "comparison")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 5
    assert int(generation_shared["node_count_max"]) == 10
    assert int(generation_shared["component_count_min"]) == 2
    assert int(generation_shared["component_count_max"]) == 4
    assert int(generation_shared["target_largest_component_size_min"]) == 2
    assert int(generation_shared["target_largest_component_size_max"]) == 6
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers"}
    assert set(generation_shared["layout_variant_weights"].keys()) == {"circular", "shell", "spring"}
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
    assert str(prompt_shared["bundle_id"]).strip() == "graph_comparison_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "single_graph_comparison"
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
        task_id="task_graph_comparison_largest_component_size",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == ["largest_component_size"]
    assert int(generation_defaults["node_count_min"]) == 5
    assert int(generation_defaults["node_count_max"]) == 10
    assert int(generation_defaults["component_count_min"]) == 2
    assert int(generation_defaults["component_count_max"]) == 4
    assert int(generation_defaults["target_largest_component_size_min"]) == 2
    assert int(generation_defaults["target_largest_component_size_max"]) == 6
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_comparison_v1"
    assert str(prompt_defaults["task_family_key"]).strip() == "single_graph_comparison"
    assert str(prompt_defaults["task_key"]).strip() == "largest_component_size_query"
    assert str(prompt_defaults["question_text_largest_component_size"]).strip()


def test_graph_path_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "path")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 5
    assert int(generation_shared["node_count_max"]) == 10
    assert int(generation_shared["directed_node_count_max"]) == 9
    assert int(generation_shared["target_shortest_path_length_min"]) == 1
    assert int(generation_shared["target_shortest_path_length_max"]) == 5
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers"}
    assert set(generation_shared["layout_variant_weights"].keys()) == {"circular", "shell", "spring"}
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
    assert str(prompt_shared["bundle_id"]).strip() == "graph_path_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "single_graph_path"
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
        task_id="task_graph_path_shortest_path_length",
    )
    assert sorted(generation_defaults["task_variant_weights"].keys()) == [
        "directed_shortest_path_length",
        "shortest_path_length",
    ]
    assert int(generation_defaults["node_count_min"]) == 5
    assert int(generation_defaults["node_count_max"]) == 10
    assert int(generation_defaults["directed_node_count_max"]) == 9
    assert int(generation_defaults["target_shortest_path_length_min"]) == 1
    assert int(generation_defaults["target_shortest_path_length_max"]) == 5
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_path_v1"
    assert str(prompt_defaults["task_family_key"]).strip() == "single_graph_path"
    assert str(prompt_defaults["task_key"]).strip() == "shortest_path_length_query"
    assert str(prompt_defaults["question_text_shortest_path_length"]).strip()
    assert str(prompt_defaults["question_text_directed_shortest_path_length"]).strip()


def test_icons_transformation_defaults_loaded() -> None:
    cfg = get_task_group_defaults("icons", "transformation")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["object_count_min"]) >= 2
    assert int(generation_shared["object_count_max"]) >= int(generation_shared["object_count_min"])
    assert int(generation_shared["target_count_min"]) == 0
    assert int(generation_shared["target_count_max"]) == 6
    assert int(generation_shared["distractor_count_min"]) == 1
    assert int(generation_shared["distractor_count_max"]) == 6
    assert bool(generation_shared["balanced_sampling"]) is True
    assert "task_icons_transformation_pair_count" in cfg["generation"]["task_overrides"]

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
    assert str(prompt_shared["task_family_key"]).strip()
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
        task_id="task_icons_transformation_pair_count",
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
    assert "task_icons_relation_between_two_anchors_count" in cfg["generation"]["task_overrides"]
    assert "task_icons_relation_mirror_symmetry" in cfg["generation"]["task_overrides"]
    assert "task_icons_relation_occlusion_order" in cfg["generation"]["task_overrides"]
    assert "task_icons_relation_relative_position_type" in cfg["generation"]["task_overrides"]

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
    assert str(prompt_shared["task_family_key"]).strip()
    assert str(prompt_shared["task_key"]).strip()
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "visual_scan": 0.20,
        "ambiguity": 0.25,
        "clutter": 0.15,
        "spatial_reasoning": 0.40,
    }

    mirror_generation, mirror_rendering, mirror_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_relation_mirror_symmetry",
    )
    assert str(mirror_generation["pool_manifest"]).strip() == "non_symmetry.txt"
    assert int(mirror_generation["object_count_min"]) == 6
    assert int(mirror_generation["object_count_max"]) == 6
    assert int(mirror_generation["target_count_max"]) == 4
    assert int(mirror_generation["distractor_count_min"]) == 2
    assert int(mirror_generation["distractor_count_max"]) == 6
    mirror_variant_weights = {
        str(key): float(value)
        for key, value in dict(mirror_generation["variant_weights"]).items()
        if str(key)
        in {
            "mirror_vertical",
            "mirror_horizontal",
            "mirror_diagonal_main",
            "mirror_diagonal_anti",
            "mirror_both_axes",
        }
    }
    assert mirror_variant_weights == {
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
    assert str(mirror_prompt["task_family_key"]).strip() == "reference_grid_mirror_symmetry_relation"
    assert str(mirror_prompt["object_description"]).strip()
    assert str(mirror_prompt["question_text"]).strip()
    assert str(mirror_prompt["evidence_hint"]).strip()
    assert str(mirror_prompt["answer_hint"]).strip()
    assert str(mirror_prompt["json_example"]).strip()
    assert str(mirror_prompt["json_example_answer_only"]).strip()

    strip_generation, strip_rendering, strip_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_relation_between_two_anchors_count",
    )
    assert str(strip_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert int(strip_generation["target_count_max"]) == 5
    assert int(strip_generation["distractor_count_max"]) == 10
    strip_variant_weights = {
        str(key): float(value)
        for key, value in dict(strip_generation["variant_weights"]).items()
        if str(key) in {"inside_vertical_strip", "inside_horizontal_strip"}
    }
    assert strip_variant_weights == {
        "inside_vertical_strip": 1.0,
        "inside_horizontal_strip": 1.0,
    }
    assert float(strip_rendering["scene_max_overlap_fraction"]) == 0.08
    assert int(strip_rendering["strip_boundary_margin_px"]) == 14
    assert float(strip_rendering["strip_span_ratio_min"]) == 0.32
    assert float(strip_rendering["strip_span_ratio_max"]) == 0.60
    assert str(strip_prompt["task_family_key"]).strip() == "scene_two_anchor_relation"
    assert str(strip_prompt["object_description"]).strip()
    assert str(strip_prompt["question_text_inside_vertical_strip"]).strip()
    assert str(strip_prompt["question_text_inside_horizontal_strip"]).strip()
    assert str(strip_prompt["evidence_hint"]).strip()
    assert str(strip_prompt["answer_hint"]).strip()
    assert str(strip_prompt["json_example"]).strip()
    assert str(strip_prompt["json_example_answer_only"]).strip()

    occlusion_generation, occlusion_rendering, occlusion_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_relation_occlusion_order",
    )
    assert str(occlusion_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert int(occlusion_generation["object_count_min"]) == 2
    assert int(occlusion_generation["object_count_max"]) == 12
    assert int(occlusion_generation["target_count_max"]) == 6
    assert int(occlusion_generation["distractor_count_max"]) == 6
    assert int(occlusion_generation["distractor_margin_over_target"]) == 0
    assert int(occlusion_rendering["canvas_width"]) == 1104
    assert int(occlusion_rendering["reference_panel_width_px"]) == 296
    assert float(occlusion_rendering["min_color_distance"]) == 40.0
    assert float(occlusion_rendering["pair_min_color_distance"]) == 80.0
    assert list(occlusion_rendering["overlap_ratio_range"]) == [0.40, 0.60]
    assert str(occlusion_prompt["task_family_key"]).strip() == "reference_grid_occlusion_relation"
    assert str(occlusion_prompt["object_description"]).strip()
    assert str(occlusion_prompt["question_text"]).strip()
    assert str(occlusion_prompt["evidence_hint"]).strip()
    assert str(occlusion_prompt["answer_hint"]).strip()
    assert str(occlusion_prompt["json_example"]).strip()
    assert str(occlusion_prompt["json_example_answer_only"]).strip()

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_relation_relative_position_type",
    )
    assert str(generation["pool_manifest"]).strip() == "all_icons.txt"
    assert int(rendering["canvas_width"]) > 0
    assert float(rendering["scene_max_overlap_fraction"]) == 0.05
    assert int(rendering["anchor_gap_px_directional"]) == 8
    assert str(prompt["object_description"]).strip()
    assert str(prompt["question_text_left_of_anchor"]).strip()
    assert str(prompt["question_text_right_of_anchor"]).strip()
    assert str(prompt["question_text_above_anchor"]).strip()
    assert str(prompt["question_text_below_anchor"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["json_example"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()


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
    assert "task_icons_sequence_missing_count" in cfg["generation"]["task_overrides"]
    assert "task_icons_sequence_rotation_violation" in cfg["generation"]["task_overrides"]

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
    assert str(prompt_shared["task_family_key"]).strip()
    assert str(prompt_shared["task_key"]).strip()
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_sequence_missing_count",
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

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_sequence_rotation_violation",
    )
    assert str(generation["pool_manifest"]).strip() == "non_symmetry.txt"
    assert list(generation["rotation_candidates_degrees"]) == [0, 90, 180, 270]
    assert list(generation["step_candidates_degrees"]) == [90, 270]
    assert int(generation["sequence_length_min"]) == 5
    assert int(generation["sequence_length_max"]) == 7
    assert int(rendering["scene_icon_size_min_px"]) == 48
    assert int(rendering["scene_icon_size_max_px"]) == 72
    assert int(rendering["cell_box_width_min_px"]) == 96
    assert int(rendering["cell_box_width_max_px"]) == 136
    assert str(prompt["task_family_key"]).strip() == "sequence_rotation_violation"
    assert str(prompt["task_key"]).strip() == "rotation_violation_query"
    assert str(prompt["question_text"]).strip()


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
    assert "task_icons_pattern_grid_rotation_violation" in cfg["generation"]["task_overrides"]
    assert "task_icons_pattern_grid_size_violation" in cfg["generation"]["task_overrides"]

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
    assert str(prompt_shared["bundle_id"]).strip() == "icons_pattern_v1"
    assert str(prompt_shared["task_family_key"]).strip() == "numbered_grid_rotation_pattern"
    assert str(prompt_shared["task_key"]).strip() == "grid_rotation_violation_query"
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_pattern_grid_rotation_violation",
    )
    assert str(generation["pool_manifest"]).strip() == "non_symmetry.txt"
    assert list(generation["rotation_candidates_degrees"]) == [0, 90, 180, 270]
    assert list(generation["row_step_candidates_degrees"]) == [90, 180, 270]
    assert list(generation["col_step_candidates_degrees"]) == [90, 180, 270]
    assert int(rendering["scene_icon_size_min_px"]) == 48
    assert int(rendering["scene_icon_size_max_px"]) == 72
    assert str(prompt["object_description"]).strip()
    assert str(prompt["question_text"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["json_example"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons_pattern_grid_size_violation",
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
    assert int(rendering["size_level_gap_px"]) == 8
    assert list(rendering["icon_noise_edit_count_range"]) == [0, 1]
    assert str(prompt["task_key"]).strip() == "grid_size_violation_query"
    assert str(prompt["question_text"]).strip()


def test_tile_path_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tile", "path")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)
    assert "task_tile_path_shortest_path" in cfg["generation"]["task_overrides"]
    assert "task_tile_path_reachable_target_count" in cfg["generation"]["task_overrides"]
    assert isinstance(cfg["visual"]["background"]["styles"], dict)
    assert cfg["visual"]["background"]["styles"]

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tile_path_shortest_path",
    )
    assert int(generation["rows"]) > 0
    assert int(generation["rows"]) == 7
    assert int(generation["cols"]) == 7
    assert int(generation["target_shortest_len_min"]) == 4
    assert int(generation["target_shortest_len_max"]) == 13
    assert float(rendering["aspect_ratio_min"]) == pytest.approx(1.0, rel=1e-9)
    assert float(rendering["aspect_ratio_max"]) == pytest.approx(1.0, rel=1e-9)
    assert str(prompt["bundle_id"]).strip()
    assert str(prompt["task_family_key"]).strip() == "rectangular_tile_board"
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
        task_id="task_tile_path_shortest_path",
    )
    assert dict(shortest_path_complexity["criteria_weights"]) == {
        "visual_scan": 0.30,
        "reasoning_load": 0.70,
    }

    reachable_generation, reachable_rendering, reachable_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tile_path_reachable_target_count",
    )
    assert int(reachable_generation["rows"]) == 7
    assert int(reachable_generation["cols"]) == 7
    assert int(reachable_generation["target_reachable_target_count_min"]) == 0
    assert int(reachable_generation["target_reachable_target_count_max"]) == 6
    assert float(reachable_rendering["aspect_ratio_min"]) == pytest.approx(1.0, rel=1e-9)
    assert float(reachable_rendering["aspect_ratio_max"]) == pytest.approx(1.0, rel=1e-9)
    assert str(reachable_prompt["bundle_id"]).strip() == "tile_path_v1"
    assert str(reachable_prompt["task_family_key"]).strip() == "rectangular_tile_board"
    assert str(reachable_prompt["task_key"]).strip() == "reachable_target_count_query"
    assert str(reachable_prompt["answer_hint"]).strip()
    assert str(reachable_prompt["evidence_hint"]).strip()
    reachable_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_tile_path_reachable_target_count",
    )
    assert dict(reachable_complexity["criteria_weights"]) == {
        "visual_scan": 0.45,
        "reasoning_load": 0.55,
    }
    assert json.loads(str(reachable_prompt["json_example"])) == {"evidence": [[0, 2], [2, 1]], "answer": 2}
    assert json.loads(str(reachable_prompt["json_example_answer_only"])) == {"answer": 2}


def test_tile_pattern_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tile", "pattern")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tile_pattern_match3_run_count",
    )
    assert int(generation["palette_size_min"]) == 2
    assert int(generation["palette_size_max"]) == 3
    assert int(generation["run_length"]) == 3
    assert int(generation["target_qualifying_line_count_min"]) == 1
    assert "target_qualifying_line_count_max" not in generation
    assert int(rendering["short_side_px_min"]) >= 32
    assert str(prompt["bundle_id"]).strip() == "tile_pattern_v1"
    assert str(prompt["task_family_key"]).strip() == "rectangular_tile_board"
    assert str(prompt["task_key"]).strip() == "match3_run_count_query"
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    rows_example = json.loads(str(prompt["json_example_rows"]))
    cols_example = json.loads(str(prompt["json_example_cols"]))
    assert rows_example == {"evidence": [[0, 1], [0, 2], [0, 3], [2, 0], [2, 1], [2, 2]], "answer": 2}
    assert cols_example == {"evidence": [[0, 1], [0, 3], [1, 1], [1, 3], [2, 1], [2, 3]], "answer": 2}
    answer_only_example = json.loads(str(prompt["json_example_answer_only"]))
    assert answer_only_example == {"answer": 2}
    pattern_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_tile_pattern_match3_run_count",
    )
    assert dict(pattern_complexity["criteria_weights"]) == {
        "visual_scan": 0.45,
        "reasoning_load": 0.55,
    }


def test_tile_transition_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tile", "transition")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tile_transition_gravity_max_drop",
    )
    assert int(generation["target_max_drop_min"]) == 1
    assert "target_max_drop_max" not in generation
    assert int(rendering["short_side_px_min"]) >= 32
    assert str(prompt["bundle_id"]).strip() == "tile_transition_v1"
    assert str(prompt["task_family_key"]).strip() == "rectangular_tile_board"
    assert str(prompt["task_key"]).strip() == "gravity_max_drop_query"
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    example = json.loads(str(prompt["json_example"]))
    assert example == {"evidence": [[0, 1], [1, 1], [2, 1]], "answer": 2}
    answer_only_example = json.loads(str(prompt["json_example_answer_only"]))
    assert answer_only_example == {"answer": 2}
    transition_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_tile_transition_gravity_max_drop",
    )
    assert dict(transition_complexity["criteria_weights"]) == {
        "visual_scan": 0.35,
        "reasoning_load": 0.65,
    }


def test_tile_symmetry_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tile", "symmetry")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tile_symmetry_violation_count",
    )
    assert int(generation["palette_size_min"]) == 2
    assert int(generation["palette_size_max"]) == 4
    assert int(generation["target_violation_count_min"]) == 1
    assert int(generation["target_violation_count_max"]) == 10
    assert int(rendering["short_side_px_min"]) >= 32
    assert str(prompt["bundle_id"]).strip() == "tile_symmetry_v1"
    assert str(prompt["task_family_key"]).strip() == "rectangular_tile_board"
    assert str(prompt["task_key"]).strip() == "symmetry_violation_count_query"
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    assert str(prompt["json_example"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()
    symmetry_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_tile_symmetry_violation_count",
    )
    assert dict(symmetry_complexity["criteria_weights"]) == {
        "visual_scan": 0.45,
        "reasoning_load": 0.55,
    }


def test_tile_count_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tile", "count")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["rows_min"]) == 3
    assert int(generation_shared["rows_max"]) == 7
    assert int(generation_shared["cols_min"]) == 3
    assert int(generation_shared["cols_max"]) == 7

    rendering_shared = cfg["rendering"]["shared"]
    assert int(rendering_shared["short_side_px_min"]) >= 32
    assert int(rendering_shared["short_side_px_max"]) >= int(rendering_shared["short_side_px_min"])
    assert float(rendering_shared["aspect_ratio_min"]) >= 1.0
    assert float(rendering_shared["aspect_ratio_max"]) >= float(rendering_shared["aspect_ratio_min"])

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "visual_scan": 0.50,
        "reasoning_load": 0.50,
    }

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tile_count_color_count",
    )
    assert int(generation["palette_size_min"]) >= 2
    assert int(generation["palette_size_max"]) >= int(generation["palette_size_min"])
    assert float(rendering["outer_padding_fraction_min"]) > 0.0
    assert float(rendering["outer_padding_fraction_max"]) >= float(rendering["outer_padding_fraction_min"])
    assert str(prompt["bundle_id"]).strip() == "tile_count_v1"
    assert str(prompt["task_family_key"]).strip() == "rectangular_tile_board"
    assert str(prompt["task_key"]).strip() == "color_count_query"
    assert str(prompt["json_output_contract"]).strip()
    assert str(prompt["json_output_contract_answer_only"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    color_count_complexity = resolve_task_group_section_defaults(cfg, "complexity", task_id="task_tile_count_color_count")
    assert dict(color_count_complexity["criteria_weights"]) == {
        "visual_scan": 0.60,
        "reasoning_load": 0.40,
    }

    generation_components, _rendering_components, prompt_components = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tile_count_color_components",
    )
    assert int(generation_components["palette_size_min"]) == 2
    assert int(generation_components["palette_size_max"]) == 3
    assert int(generation_components["target_component_count_min"]) == 1
    assert "target_component_count_max" not in generation_components
    assert str(prompt_components["bundle_id"]).strip() == "tile_count_v1"
    assert str(prompt_components["task_key"]).strip() == "color_component_count_query"
    assert str(prompt_components["answer_hint"]).strip()
    assert str(prompt_components["evidence_hint"]).strip()
    color_components_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_tile_count_color_components",
    )
    assert dict(color_components_complexity["criteria_weights"]) == {
        "visual_scan": 0.45,
        "reasoning_load": 0.55,
    }
    component_example = json.loads(str(prompt_components["json_example"]))
    assert component_example == {"evidence": [[0, 0], [0, 1], [2, 2]], "answer": 2}
    component_answer_only_example = json.loads(str(prompt_components["json_example_answer_only"]))
    assert component_answer_only_example == {"answer": 2}

    generation_largest, _rendering_largest, prompt_largest = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tile_count_largest_component_size",
    )
    assert int(generation_largest["palette_size_min"]) == 2
    assert int(generation_largest["palette_size_max"]) == 3
    assert int(generation_largest["target_largest_component_size_min"]) == 2
    assert int(generation_largest["target_largest_component_size_max"]) == 10
    assert str(prompt_largest["bundle_id"]).strip() == "tile_count_v1"
    assert str(prompt_largest["task_key"]).strip() == "largest_component_size_query"
    assert str(prompt_largest["answer_hint"]).strip()
    assert str(prompt_largest["evidence_hint"]).strip()
    largest_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_tile_count_largest_component_size",
    )
    assert dict(largest_complexity["criteria_weights"]) == {
        "visual_scan": 0.40,
        "reasoning_load": 0.60,
    }
    largest_example = json.loads(str(prompt_largest["json_example"]))
    assert largest_example == {"evidence": [[0, 0], [0, 1], [1, 1], [1, 2]], "answer": 4}
    largest_answer_only_example = json.loads(str(prompt_largest["json_example_answer_only"]))
    assert largest_answer_only_example == {"answer": 4}


def test_tile_reachability_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tile", "reachability")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tile_reachability_region_size",
    )
    assert int(generation["rows_min"]) >= 3
    assert int(generation["rows_max"]) == 7
    assert int(generation["cols_min"]) >= 3
    assert int(generation["cols_max"]) == 7
    assert float(generation["obstacle_fraction_min"]) > 0.0
    assert float(generation["obstacle_fraction_max"]) >= float(generation["obstacle_fraction_min"])
    assert float(generation["reachable_fraction_min"]) > 0.0
    assert float(generation["reachable_fraction_max"]) <= 1.0
    assert int(generation["answer_max"]) == 12
    assert int(rendering["short_side_px_min"]) >= 32
    assert str(prompt["bundle_id"]).strip() == "tile_reachability_v1"
    assert str(prompt["task_key"]).strip() == "region_size_query"
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    reachability_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_tile_reachability_region_size",
    )
    assert dict(reachability_complexity["criteria_weights"]) == {
        "visual_scan": 0.45,
        "reasoning_load": 0.55,
    }
    example = json.loads(str(prompt["json_example"]))
    assert example == {"evidence": [[0, 0], [0, 1], [1, 1], [2, 1]], "answer": 4}
    answer_only_example = json.loads(str(prompt["json_example_answer_only"]))
    assert answer_only_example == {"answer": 4}


def test_tile_relation_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tile", "relation")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tile_relation_min_distance",
    )
    assert int(generation["target_distance_min"]) == 2
    assert int(generation["target_distance_max"]) == 6
    assert int(generation["component_size_min"]) == 1
    assert int(generation["component_size_max"]) == 6
    assert int(rendering["short_side_px_min"]) >= 32
    assert str(prompt["bundle_id"]).strip() == "tile_relation_v1"
    assert str(prompt["task_family_key"]).strip() == "rectangular_tile_board"
    assert str(prompt["task_key"]).strip() == "min_distance_query"
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["evidence_hint"]).strip()
    relation_complexity = resolve_task_group_section_defaults(
        cfg,
        "complexity",
        task_id="task_tile_relation_min_distance",
    )
    assert dict(relation_complexity["criteria_weights"]) == {
        "visual_scan": 0.35,
        "reasoning_load": 0.65,
    }
    example = json.loads(str(prompt["json_example"]))
    assert example == {"evidence": [[1, 1], [1, 2], [1, 3]], "answer": 2}
    answer_only_example = json.loads(str(prompt["json_example_answer_only"]))
    assert answer_only_example == {"answer": 2}


def test_domain_defaults_and_missing_group_behavior() -> None:
    assert get_task_group_defaults("missing_domain", "missing_group") == {}
    domain_cfg = get_domain_defaults("geometry")
    cfg = get_task_group_defaults("geometry", "missing_group")
    assert cfg["rendering"]["shared"] == domain_cfg["rendering"]["shared"]


def test_measurement_prompt_examples_are_task_valid() -> None:
    cfg = get_task_group_defaults("geometry", "measurement")

    _angle_generation, _angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_angle",
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
        task_id="task_geometry_measurement_slope",
    )
    slope_example = json.loads(str(slope_prompt["json_example"]))
    assert list(slope_example.keys()) == ["evidence", "answer"]
    assert isinstance(slope_example["evidence"], list)
    assert len(slope_example["evidence"]) == 2
    assert int(slope_example["evidence"][1]) == 0
    assert isinstance(slope_example["answer"], float)
    slope_answer_only_example = json.loads(str(slope_prompt["json_example_answer_only"]))
    assert list(slope_answer_only_example.keys()) == ["answer"]
    assert isinstance(slope_answer_only_example["answer"], float)

    _area_generation, _area_rendering, area_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_area",
    )
    area_example = json.loads(str(area_prompt["json_example_integer"]))
    assert list(area_example.keys()) == ["evidence", "answer"]
    assert isinstance(area_example["evidence"], list)
    area_points = [[int(point[0]), int(point[1])] for point in area_example["evidence"]]
    assert len(area_points) >= 3
    assert int(area_example["answer"]) == int(_polygon_area(area_points))
    for key, expected_points in (
        ("json_example_triangle", 3),
        ("json_example_quadrilateral", 4),
    ):
        polygon_example = json.loads(str(area_prompt[key]))
        assert list(polygon_example.keys()) == ["evidence", "answer"]
        assert isinstance(polygon_example["evidence"], list)
        polygon_points = [[int(point[0]), int(point[1])] for point in polygon_example["evidence"]]
        assert len(polygon_points) == int(expected_points)
        assert int(polygon_example["answer"]) == int(_polygon_area(polygon_points))
    area_pi_example = json.loads(str(area_prompt["json_example_pi"]))
    assert list(area_pi_example.keys()) == ["evidence", "answer"]
    assert area_pi_example["evidence"] == [[0, 0]]
    assert str(area_pi_example["answer"]).endswith("π")
    area_answer_only_integer = json.loads(str(area_prompt["json_example_answer_only_integer"]))
    assert list(area_answer_only_integer.keys()) == ["answer"]
    assert int(area_answer_only_integer["answer"]) >= 0
    area_answer_only_pi = json.loads(str(area_prompt["json_example_answer_only_pi"]))
    assert list(area_answer_only_pi.keys()) == ["answer"]
    assert str(area_answer_only_pi["answer"]).endswith("π")

    _perim_generation, _perim_rendering, perim_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_perimeter",
    )
    perim_example = json.loads(str(perim_prompt["json_example_integer"]))
    assert list(perim_example.keys()) == ["evidence", "answer"]
    assert isinstance(perim_example["evidence"], list)
    perim_points = [[int(point[0]), int(point[1])] for point in perim_example["evidence"]]
    assert len(perim_points) >= 3
    assert int(perim_example["answer"]) == int(_polygon_perimeter(perim_points))
    for key, expected_points in (
        ("json_example_triangle", 3),
        ("json_example_quadrilateral", 4),
    ):
        polygon_example = json.loads(str(perim_prompt[key]))
        assert list(polygon_example.keys()) == ["evidence", "answer"]
        assert isinstance(polygon_example["evidence"], list)
        polygon_points = [[int(point[0]), int(point[1])] for point in polygon_example["evidence"]]
        assert len(polygon_points) == int(expected_points)
        assert int(polygon_example["answer"]) == int(_polygon_perimeter(polygon_points))
    perim_pi_example = json.loads(str(perim_prompt["json_example_pi"]))
    assert list(perim_pi_example.keys()) == ["evidence", "answer"]
    assert perim_pi_example["evidence"] == [[0, 0]]
    assert str(perim_pi_example["answer"]).endswith("π")
    perim_answer_only_integer = json.loads(str(perim_prompt["json_example_answer_only_integer"]))
    assert list(perim_answer_only_integer.keys()) == ["answer"]
    assert int(perim_answer_only_integer["answer"]) >= 0
    perim_answer_only_pi = json.loads(str(perim_prompt["json_example_answer_only_pi"]))
    assert list(perim_answer_only_pi.keys()) == ["answer"]
    assert str(perim_answer_only_pi["answer"]).endswith("π")

    _length_generation, _length_rendering, length_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_length",
    )
    length_example = json.loads(str(length_prompt["json_example_integer"]))
    assert list(length_example.keys()) == ["evidence", "answer"]
    assert isinstance(length_example["evidence"], list)
    length_points = [[int(point[0]), int(point[1])] for point in length_example["evidence"]]
    assert len(length_points) == 2
    dx = int(length_points[1][0]) - int(length_points[0][0])
    dy = int(length_points[1][1]) - int(length_points[0][1])
    assert int(length_example["answer"]) == int(round(math.hypot(float(dx), float(dy))))
    center_example = json.loads(str(length_prompt["json_example_circle_radius_integer"]))
    assert list(center_example.keys()) == ["evidence", "answer"]
    assert isinstance(center_example["evidence"], list)
    assert len(center_example["evidence"]) == 1
    only_point = center_example["evidence"][0]
    assert isinstance(only_point, list) and len(only_point) == 2
    length_answer_only_example = json.loads(str(length_prompt["json_example_answer_only_integer"]))
    assert list(length_answer_only_example.keys()) == ["answer"]
    assert int(length_answer_only_example["answer"]) >= 0


def test_analytical_prompt_examples_are_task_valid() -> None:
    cfg = get_task_group_defaults("geometry", "analytical_2d")
    _generation, _rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_analytical_2d_area",
    )
    integer_answer_only = json.loads(str(prompt["json_example_answer_only_integer"]))
    assert list(integer_answer_only.keys()) == ["answer"]
    assert int(integer_answer_only["answer"]) >= 0

    pi_answer_only = json.loads(str(prompt["json_example_answer_only_pi"]))
    assert list(pi_answer_only.keys()) == ["answer"]
    assert str(pi_answer_only["answer"]).endswith("π")

    for key in (
        "json_example_rectangle_explicit",
        "json_example_rectangle_derived",
        "json_example_triangle_explicit",
        "json_example_triangle_derived",
        "json_example_parallelogram_explicit",
        "json_example_parallelogram_derived",
        "json_example_trapezoid_explicit",
        "json_example_trapezoid_derived",
        "json_example_rhombus_explicit",
        "json_example_rhombus_derived",
        "json_example_circle_explicit",
        "json_example_circle_derived",
        "json_example_ellipse_explicit",
        "json_example_ellipse_derived",
    ):
        parsed = json.loads(str(prompt[key]))
        assert list(parsed.keys()) == ["evidence", "answer"]
        assert isinstance(parsed["evidence"], dict)
        assert parsed["evidence"]
        for annotation, payload in parsed["evidence"].items():
            assert str(annotation).strip()
            assert isinstance(payload, (int, float, str))
        if str(key).startswith(("json_example_circle", "json_example_ellipse")):
            assert isinstance(parsed["answer"], str)
            assert str(parsed["answer"]).endswith("π")
        else:
            assert int(parsed["answer"]) >= 0

    _length_generation, _length_rendering, length_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_analytical_2d_length",
    )
    for key in (
        "triangle_altitude_side",
        "rectangle_diagonal_side",
        "rhombus_diagonal_side",
        "isosceles_trapezoid_leg",
        "inscribed_square_side",
        "circle_chord_length",
    ):
        assert str(length_prompt[f"question_text_{key}"]).strip()

    _perimeter_generation, _perimeter_rendering, perimeter_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_analytical_2d_perimeter",
    )
    for key in (
        "right_triangle_leg_hypotenuse",
        "rectangle_side_diagonal",
        "rhombus_diagonals",
        "isosceles_trapezoid_bases_height",
        "inscribed_square_diameter",
    ):
        assert str(perimeter_prompt[f"question_text_{key}"]).strip()


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
