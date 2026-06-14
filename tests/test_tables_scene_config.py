"""Regression tests for scene default config loading."""

from __future__ import annotations

import json

import pytest

from trace.core.scene_config import (
    get_domain_defaults,
    get_scene_defaults,
    resolve_scene_section_defaults,
)
from trace.tasks.shared.config_defaults import (
    required_group_default,
    required_group_defaults,
    resolve_optional_int_bounds,
    resolve_required_float_bounds,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from trace.tasks.graph.shared.graph_sample_types import SUPPORTED_LAYOUT_VARIANTS


FULL_NODE_LINK_LAYOUT_VARIANTS = set(SUPPORTED_LAYOUT_VARIANTS)


def test_tables_statistics_defaults_loaded() -> None:
    cfg = get_scene_defaults("charts", "table_statistics")
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
    assert sorted(generation_defaults["query_id_weights"].keys()) == [
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
    assert str(prompt_defaults["annotation_hint_column_sum"]).strip()
    assert str(prompt_defaults["json_example_column_median"]).strip()

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_table_filtered_column_summary_base",
    )
    assert sorted(generation_defaults["query_id_weights"].keys()) == [
        "filtered_column_mean",
    ]
    assert int(generation_defaults["row_count_min"]) == 10
    assert int(generation_defaults["row_count_max"]) == 20
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["canvas_height"]) == 900
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_table_statistics_v0"
    assert str(prompt_defaults["task_key"]).strip() == "filtered_subset_value_query"
    assert str(prompt_defaults["annotation_hint_filtered_column_sum"]).strip()
    assert str(prompt_defaults["json_example_filtered_column_mean"]).strip()

def test_tables_counting_defaults_loaded() -> None:
    cfg = get_scene_defaults("charts", "table_counting")
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
        task_id="charts_table_value_predicate_count_base",
    )
    assert sorted(generation_defaults["query_id_weights"].keys()) == [
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
    assert str(prompt_defaults["annotation_hint_categorical_value_count"]).strip()
    assert str(prompt_defaults["annotation_hint_threshold_count"]).strip()
    assert str(prompt_defaults["json_example_in_interval"]).strip()

def test_tables_ranking_defaults_loaded() -> None:
    cfg = get_scene_defaults("charts", "table_ranking")
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
    assert sorted(generation_defaults["query_id_weights"].keys()) == ["kth_rank_in_column"]
    assert sorted(generation_defaults["rank_direction_weights"].keys()) == ["highest", "lowest"]
    assert int(generation_defaults["row_count_min"]) == 10
    assert int(generation_defaults["row_count_max"]) == 20
    assert int(rendering_defaults["canvas_height"]) == 900
    assert str(prompt_defaults["bundle_id"]).strip() == "charts_table_ranking_v0"
    assert str(prompt_defaults["annotation_hint_kth_rank_in_column"]).strip()
    assert str(prompt_defaults["json_example_kth_rank_in_column"]).strip()

def test_tables_temporal_defaults_loaded() -> None:
    cfg = get_scene_defaults("charts", "table_temporal")
    for section in ("generation", "rendering", "prompt"):
        assert isinstance(cfg.get(section), dict)

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "charts_table_temporal_v0"
    assert str(prompt_shared["scene_key"]).strip() == "styled_table_temporal"
    assert str(prompt_shared["task_key"]).strip() == "temporal_value_query"

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_table_temporal_value_base",
    )
    assert sorted(generation_defaults["query_id_weights"].keys()) == [
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
    assert str(prompt_defaults["annotation_hint_absolute_difference_between_rows_over_year_interval"]).strip()
    assert str(prompt_defaults["annotation_hint_sum_absolute_differences_between_rows_over_year_interval"]).strip()
    assert str(prompt_defaults["json_example_sum_absolute_differences_between_rows_over_year_interval"]).strip()
