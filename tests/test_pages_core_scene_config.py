"""Regression tests for scene default config loading."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from trace.core.types import TypedValue
from trace.core.scene_config import (
    get_domain_defaults,
    get_scene_defaults,
    get_scene_defaults,
    resolve_scene_section_defaults,
)
from trace.tasks.base import TaskOutput
from trace.tasks.shared.config_defaults import (
    required_group_default,
    required_group_defaults,
    resolve_optional_int_bounds,
    resolve_required_float_bounds,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.graph.shared.graph_sample_types import SUPPORTED_LAYOUT_VARIANTS
from trace.tasks.pages.shared.render_audit_defaults import (
    wrap_pages_generation,
    wrap_pages_scene_generation,
)


FULL_NODE_LINK_LAYOUT_VARIANTS = set(SUPPORTED_LAYOUT_VARIANTS)


def _dummy_pages_output() -> TaskOutput:
    return TaskOutput(
        prompt="demo",
        answer_gt=TypedValue(type="integer", value=1),
        annotation_gt=TypedValue(type="bbox_set", value=[]),
        image=Image.new("RGB", (120, 80), "white"),
        image_id="img0",
        trace_payload={"render_spec": {}, "render_map": {}, "scene_ir": {"entities": []}},
        task_versions={},
        scene_id="demo_scene",
        query_id="default",
    )


def test_pages_scene_render_wrapper_uses_scene_metadata_without_scene_id() -> None:
    def _generate(_self, instance_seed: int, *, params: dict, max_attempts: int) -> TaskOutput:
        assert instance_seed == 17
        assert max_attempts == 1
        assert params["pages_context_text_enabled"] is False
        return _dummy_pages_output()

    wrapped = wrap_pages_scene_generation(
        _generate,
        task_id="task_pages__demo_scene__lookup_value",
        scene_id="demo_scene",
    )
    output = wrapped(
        object(),
        17,
        params={"pages_context_text_enabled": False, "pages_font_family": "georama"},
        max_attempts=1,
    )

    font_assets = output.trace_payload["render_spec"]["font_assets"]
    assert font_assets["task_id"] == "task_pages__demo_scene__lookup_value"
    assert font_assets["scene_id"] == "demo_scene"
    assert "scene_id" not in font_assets
    assert output.trace_payload["render_spec"]["context_text_layer"]["enabled"] is False


def test_pages_legacy_render_wrapper_keeps_scene_id_metadata() -> None:
    def _generate(_self, instance_seed: int, *, params: dict, max_attempts: int) -> TaskOutput:
        return _dummy_pages_output()

    wrapped = wrap_pages_generation(
        _generate,
        task_id="task_pages__demo_scene__lookup_value",
        scene_id="demo_group",
    )
    output = wrapped(
        object(),
        19,
        params={"pages_context_text_enabled": False, "pages_font_family": "georama"},
        max_attempts=1,
    )

    font_assets = output.trace_payload["render_spec"]["font_assets"]
    assert font_assets["scene_id"] == "demo_group"
    assert "scene_id" not in font_assets


def test_pages_calendar_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "calendar")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="pages_calendar_month_view_base",
    )

    assert sorted(generation_defaults["query_id_weights"].keys()) == [
        "count_marked_day_class",
        "date_of_weekday_occurrence",
        "workday_after_offset_date",
        "workday_before_offset_date",
    ]
    assert sorted(generation_defaults["marked_day_class_weights"].keys()) == ["weekday", "weekend"]
    assert sorted(generation_defaults["surface_mode_weights"].keys()) == ["dark", "light"]
    assert sorted(generation_defaults["text_color_mode_weights"].keys()) == ["accent", "cool", "neutral", "warm"]
    assert bool(generation_defaults["balanced_query_id_sampling"]) is True
    assert bool(generation_defaults["balanced_surface_mode_sampling"]) is True
    assert bool(generation_defaults["balanced_text_color_mode_sampling"]) is True
    assert list(generation_defaults["weekend_weekday_indices"]) == [5, 6]
    assert list(generation_defaults["date_occurrence_support"]) == [1, 2, 3, 4, 5]
    assert list(generation_defaults["marked_weekend_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation_defaults["marked_weekday_count_support"]) == [0, 1, 2, 3, 4, 5, 6]
    assert list(generation_defaults["marked_weekday_distractor_support"]) == [1, 2, 3, 4]
    assert list(generation_defaults["marked_weekend_distractor_support"]) == [1, 2, 3, 4]
    assert list(generation_defaults["workday_offset_support"]) == [2, 3, 4, 5, 6, 7]

    assert int(rendering_defaults["canvas_width"]) == 860
    assert int(rendering_defaults["canvas_height"]) == 760
    assert int(rendering_defaults["title_font_size_px"]) == 30
    assert int(rendering_defaults["date_font_size_px"]) == 22

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_calendar_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "month_calendar"
    assert str(prompt_defaults["task_key"]).strip() == "calendar_month_query"
    assert str(prompt_defaults["annotation_hint_workday_after_offset_date"]).strip()
    assert str(prompt_defaults["annotation_hint_workday_before_offset_date"]).strip()

def test_pages_calendar_event_grid_scene_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "calendar_event_grid")
    date_slot_generation, date_slot_rendering, date_slot_prompt = split_scene_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__calendar_event_grid__date_slot_category_label",
    )
    category_count_generation, _category_count_rendering, category_count_prompt = split_scene_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__calendar_event_grid__category_slot_day_count",
    )
    date_for_category_generation, _date_for_category_rendering, date_for_category_prompt = split_scene_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__calendar_event_grid__date_for_category_slot_label",
    )

    assert sorted(date_slot_generation["query_id_weights"].keys()) == ["date_slot_category_label"]
    assert sorted(category_count_generation["query_id_weights"].keys()) == ["category_slot_day_count"]
    assert sorted(date_for_category_generation["query_id_weights"].keys()) == ["date_for_category_slot_label"]
    assert sorted(date_slot_generation["slot_id_weights"].keys()) == ["end", "mid", "top"]
    assert list(date_slot_generation["target_count_support"]) == [2, 3, 4, 5, 6]
    assert len(date_slot_generation["event_category_labels"]) == 10
    assert int(date_slot_rendering["canvas_width"]) == 980
    assert int(date_slot_rendering["canvas_height"]) == 780
    assert str(date_slot_prompt["bundle_id"]).strip() == "pages_calendar_event_grid_v0"
    assert str(date_slot_prompt["scene_key"]).strip() == "calendar_event_grid"
    assert str(date_slot_prompt["task_key"]).strip() == "calendar_event_grid_query"
    assert str(date_slot_prompt["annotation_hint_date_slot_category_label"]).strip()
    assert str(category_count_prompt["annotation_hint_category_slot_day_count"]).strip()
    assert str(date_for_category_prompt["annotation_hint_date_for_category_slot_label"]).strip()


def test_pages_schedule_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "schedule")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="pages_schedule_day_planner_base",
    )

    assert sorted(generation_defaults["query_id_weights"].keys()) == [
        "longer_than_reference_count",
        "maximum_non_overlapping_count",
        "overlap_count",
    ]
    assert bool(generation_defaults["balanced_query_id_sampling"]) is True
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
    cfg = get_scene_defaults("pages", "timeline")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="pages_timeline_milestones_base",
    )

    assert sorted(generation_defaults["query_id_weights"].keys()) == [
        "event_date_gap_value",
        "interval_membership_count",
    ]
    assert sorted(generation_defaults["interval_relation_weights"].keys()) == ["between", "outside"]
    assert bool(generation_defaults["balanced_query_id_sampling"]) is True
    assert list(generation_defaults["event_count_support"]) == [6, 7, 8, 9, 10, 11, 12]
    assert list(generation_defaults["between_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation_defaults["outside_count_support"]) == [2, 3, 4, 5, 6, 7, 8]
    assert list(generation_defaults["date_gap_support"]) == [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24]

    assert int(rendering_defaults["canvas_width"]) == 1120
    assert int(rendering_defaults["canvas_height"]) == 700
    assert int(rendering_defaults["card_width_px"]) == 106
    assert int(rendering_defaults["marker_radius_px"]) == 10

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_timeline_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "milestone_timeline"
    assert str(prompt_defaults["task_key"]).strip() == "timeline_milestone_query"
    assert str(prompt_defaults["annotation_hint_event_date_gap_value"]).strip()


def test_pages_infographic_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "infographic")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="pages_infographic_metric_arithmetic_value_base",
    )
    sectioned_generation, sectioned_rendering, sectioned_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__sectioned_infographic__section_item_count",
    )
    filtered_sectioned_generation, _filtered_sectioned_rendering, filtered_sectioned_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__sectioned_infographic__section_filtered_item_label",
    )

    assert list(generation_defaults["rank_position_support"]) == [2, 3]
    assert int(generation_defaults["card_count_min"]) == 20
    assert int(generation_defaults["card_count_max"]) == 30
    assert int(generation_defaults["section_count_min"]) == 4
    assert int(generation_defaults["section_count_max"]) == 6
    assert bool(generation_defaults["balanced_query_id_sampling"]) is True

    assert int(rendering_defaults["canvas_width"]) == 912
    assert int(rendering_defaults["canvas_height"]) == 1416
    assert int(rendering_defaults["section_header_height_px"]) == 34

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_infographic_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "infographic_metric_arithmetic"
    assert str(prompt_defaults["task_key"]).strip() == "metric_arithmetic_query"
    assert str(prompt_defaults["annotation_hint_metric_ranked_item"]).strip()
    assert str(prompt_defaults["annotation_hint_metric_ranked_item_scoped"]).strip()

    assert sorted(sectioned_generation["sectioned_query_id_weights"].keys()) == ["section_item_count"]
    assert sorted(filtered_sectioned_generation["sectioned_query_id_weights"].keys()) == [
        "section_filtered_item_label"
    ]
    assert sorted(sectioned_generation["scene_variant_weights"].keys()) == [
        "bullet_columns",
        "checklist_bands",
        "topic_cards",
    ]
    assert sorted(filtered_sectioned_generation["scene_variant_weights"].keys()) == [
        "bullet_columns",
        "checklist_bands",
        "topic_cards",
    ]
    assert list(sectioned_generation["section_count_support"]) == [3, 4, 5]
    assert list(sectioned_generation["item_count_support"]) == [3, 4, 5, 6, 7]
    assert list(filtered_sectioned_generation["section_count_support"]) == [3, 4, 5]
    assert list(filtered_sectioned_generation["item_count_support"]) == [3, 4, 5, 6, 7]
    assert int(sectioned_rendering["canvas_width"]) == 1040
    assert int(sectioned_rendering["canvas_height"]) == 980
    assert str(sectioned_prompt["bundle_id"]).strip() == "pages_infographic_v0"
    assert str(sectioned_prompt["scene_key_sectioned"]).strip() == "sectioned_infographic"
    assert str(sectioned_prompt["task_key_sectioned"]).strip() == "sectioned_infographic_query"
    assert str(sectioned_prompt["annotation_hint_section_item_count"]).strip()
    assert str(filtered_sectioned_prompt["bundle_id"]).strip() == "pages_infographic_v0"
    assert str(filtered_sectioned_prompt["scene_key_sectioned"]).strip() == "sectioned_infographic"
    assert str(filtered_sectioned_prompt["task_key_sectioned"]).strip() == "sectioned_infographic_query"
    assert str(filtered_sectioned_prompt["answer_hint_section_filtered_item"]).strip()
    assert str(filtered_sectioned_prompt["annotation_hint_section_filtered_item"]).strip()


def test_pages_mixed_infographic_page_scene_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "mixed_infographic_page")
    generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__mixed_infographic_page__module_field_value_label",
    )

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_mixed_infographic_page_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "mixed_infographic_page"
    assert str(prompt_defaults["task_key"]).strip() == "mixed_infographic_lookup_query"
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == [
        "collage_board",
        "compact_newsletter",
        "dashboard_blocks",
        "masonry_report",
        "poster_sections",
        "radial_mosaic",
    ]
    assert int(rendering_defaults["canvas_width"]) == 1040
    assert int(rendering_defaults["canvas_height"]) == 1320
    assert str(prompt_defaults["annotation_hint"]).strip()


def test_pages_schema_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "schema")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__schema__relationship_cardinality_label",
    )

    assert sorted(generation_defaults["query_weights"].keys()) == [
        "all_field_count",
        "attribute_field_count",
        "relationship_cardinality_between_tables",
        "target_table_for_relationship_label",
        "total_relationship_count",
    ]
    assert int(generation_defaults["table_count_min"]) == 8
    assert int(generation_defaults["table_count_max"]) == 8
    assert int(generation_defaults["relationship_count_min"]) == 6
    assert int(generation_defaults["relationship_count_max"]) == 9
    assert bool(generation_defaults["balanced_query_sampling"]) is True

    assert int(rendering_defaults["canvas_width"]) == 1300
    assert int(rendering_defaults["canvas_height"]) == 950
    assert int(rendering_defaults["marker_font_size_px"]) == 12

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_schema_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "database_schema_diagram"
    assert str(prompt_defaults["cardinality_answer_hint"]).strip()
    assert str(prompt_defaults["annotation_hint_relationship_cardinality"]).strip()


def test_pages_step_list_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "step_list")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="pages_step_list_ordinal_step_detail_source",
    )
    shared_control_generation, shared_control_rendering, shared_control_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__instruction_panel__shared_control_for_step_set_label",
    )
    pair_generation, pair_rendering, pair_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__instruction_panel__step_for_control_pair_label",
    )

    assert sorted(generation_defaults["query_id_weights"].keys()) == [
        "nth_step_detail",
        "nth_step_title",
        "step_after_named_step",
        "step_number_for_detail",
        "step_title_for_detail",
    ]
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == [
        "horizontal_cards",
        "two_column_cards",
        "vertical_cards",
    ]
    assert sorted(generation_defaults["ordinal_reference_weights"].keys()) == ["final", "first", "interior"]
    assert bool(generation_defaults["balanced_query_id_sampling"]) is True
    assert list(generation_defaults["step_count_support"]) == [5, 6, 7, 8]

    assert int(rendering_defaults["canvas_width"]) == 1000
    assert int(rendering_defaults["canvas_height"]) == 820
    assert int(rendering_defaults["number_badge_size_px"]) == 38

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_step_list_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "step_list"
    assert str(prompt_defaults["task_key"]).strip() == "step_lookup_query"
    assert str(prompt_defaults["annotation_hint"]).strip()
    assert str(prompt_defaults["annotation_hint_step_title_for_detail"]).strip()
    assert str(prompt_defaults["annotation_hint_step_number_for_detail"]).strip()

    assert [
        key
        for key, value in sorted(shared_control_generation["query_id_weights"].items())
        if float(value) > 0.0
    ] == ["shared_control_for_step_set_label"]
    assert [
        key
        for key, value in sorted(pair_generation["query_id_weights"].items())
        if float(value) > 0.0
    ] == ["step_for_control_pair_label"]
    assert [
        key
        for key, value in sorted(shared_control_generation["scene_variant_weights"].items())
        if float(value) > 0.0
    ] == ["checklist_table", "manual_cards", "side_legend_sheet"]
    assert [
        key
        for key, value in sorted(pair_generation["scene_variant_weights"].items())
        if float(value) > 0.0
    ] == ["checklist_table", "manual_cards", "side_legend_sheet"]
    assert list(shared_control_generation["controls_per_step_support"]) == [2, 3]
    assert list(shared_control_generation["control_count_support"]) == [9, 10, 11, 12]
    assert list(shared_control_generation["step_set_size_support"]) == [2, 3]
    assert list(pair_generation["controls_per_step_support"]) == [2, 3]
    assert list(pair_generation["control_count_support"]) == [9, 10, 11, 12]
    assert int(shared_control_rendering["canvas_width"]) == 1100
    assert int(shared_control_rendering["canvas_height"]) == 880
    assert int(shared_control_rendering["control_chip_height_px"]) == 30
    assert int(pair_rendering["canvas_width"]) == 1100
    assert int(pair_rendering["canvas_height"]) == 880
    assert str(shared_control_prompt["scene_key"]).strip() == "instruction_panel"
    assert str(shared_control_prompt["task_key"]).strip() == "instruction_panel_query"
    assert str(shared_control_prompt["annotation_hint"]).strip()
    assert str(pair_prompt["scene_key"]).strip() == "instruction_panel"
    assert str(pair_prompt["task_key"]).strip() == "instruction_panel_query"
    assert "integer step number" in str(pair_prompt["answer_hint"])

def test_pages_document_lookup_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "document_lookup")
    profile_generation, profile_rendering, profile_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__profile_card_grid__profile_for_field_value",
    )
    value_profile_generation, _value_profile_rendering, value_profile_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__profile_card_grid__value_for_named_profile_field",
    )
    extremum_generation, _extremum_rendering, extremum_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__profile_card_grid__field_extremum_profile_label",
    )
    profile_ranked_generation, _profile_ranked_rendering, profile_ranked_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__profile_card_grid__field_ranked_profile_label",
    )
    ranked_generation, ranked_rendering, ranked_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__ranked_list__ordinal_entry_label",
    )

    assert sorted(profile_generation["query_id_weights"].keys()) == ["profile_for_field_value"]
    assert sorted(value_profile_generation["query_id_weights"].keys()) == ["value_for_named_profile_field"]
    assert sorted(extremum_generation["query_id_weights"].keys()) == [
        "highest_field_profile_label",
        "lowest_field_profile_label",
    ]
    assert sorted(profile_ranked_generation["query_id_weights"].keys()) == [
        "nth_highest_field_profile_label",
        "nth_lowest_field_profile_label",
    ]
    assert sorted(profile_generation["scene_variant_weights"].keys()) == ["compact_cards", "directory_grid"]
    assert sorted(extremum_generation["scene_variant_weights"].keys()) == ["compact_cards", "directory_grid"]
    assert sorted(profile_ranked_generation["scene_variant_weights"].keys()) == ["compact_cards", "directory_grid"]
    assert list(profile_generation["card_count_support"]) == [6, 9]
    assert list(extremum_generation["card_count_support"]) == [6, 9]
    assert list(profile_ranked_generation["card_count_support"]) == [6, 9]
    assert list(profile_ranked_generation["rank_position_support"]) == [2, 3]
    assert bool(profile_generation["balanced_query_id_sampling"]) is True
    assert int(profile_rendering["canvas_width"]) == 1120
    assert int(profile_rendering["canvas_height"]) == 860
    assert str(profile_prompt["bundle_id"]).strip() == "pages_document_lookup_v0"
    assert str(profile_prompt["scene_key"]).strip() == "profile_card_grid"
    assert str(profile_prompt["task_key"]).strip() == "profile_attribute_lookup_query"
    assert str(profile_prompt["annotation_hint"]).strip()
    assert str(value_profile_prompt["scene_key"]).strip() == "profile_card_grid"
    assert str(extremum_prompt["scene_key"]).strip() == "profile_card_grid"
    assert str(extremum_prompt["task_key"]).strip() == "profile_attribute_lookup_query"
    assert str(extremum_prompt["annotation_hint"]).strip()
    assert str(profile_ranked_prompt["scene_key"]).strip() == "profile_card_grid"
    assert str(profile_ranked_prompt["task_key"]).strip() == "profile_attribute_lookup_query"
    assert str(profile_ranked_prompt["annotation_hint"]).strip()

    assert sorted(ranked_generation["query_id_weights"].keys()) == [
        "entry_after_named_entry",
        "from_end_entry_label",
        "nth_entry_label",
    ]
    assert sorted(ranked_generation["scene_variant_weights"].keys()) == ["stacked_lists", "two_column_lists"]
    assert list(ranked_generation["section_count_support"]) == [2, 3]
    assert list(ranked_generation["item_count_support"]) == [5, 6, 7]
    assert sorted(ranked_generation["from_end_reference_weights"].keys()) == ["last", "second_last", "third_last"]
    assert int(ranked_rendering["canvas_width"]) == 1000
    assert int(ranked_rendering["canvas_height"]) == 850
    assert str(ranked_prompt["bundle_id"]).strip() == "pages_document_lookup_v0"
    assert str(ranked_prompt["scene_key"]).strip() == "ranked_list"
    assert str(ranked_prompt["task_key"]).strip() == "ranked_list_entry_query"
    assert str(ranked_prompt["annotation_hint"]).strip()


def test_pages_category_grid_scene_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "category_grid")
    category_slot_generation, category_slot_rendering, category_slot_prompt = split_scene_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__category_grid__category_slot_item_label",
    )
    category_count_generation, _category_count_rendering, category_count_prompt = split_scene_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__category_grid__category_item_count",
    )

    assert sorted(category_slot_generation["query_id_weights"].keys()) == ["category_slot_item_label"]
    assert sorted(category_count_generation["query_id_weights"].keys()) == ["category_item_count"]
    assert sorted(category_slot_generation["scene_variant_weights"].keys()) == [
        "card_grid",
        "column_groups",
        "compact_index",
    ]
    assert sorted(category_count_generation["scene_variant_weights"].keys()) == [
        "card_grid",
        "column_groups",
        "compact_index",
    ]
    assert list(category_slot_generation["category_count_support"]) == [3, 4]
    assert list(category_slot_generation["subcategory_count_support"]) == [2, 3]
    assert list(category_slot_generation["item_count_support"]) == [2, 3, 4, 5, 6]
    assert int(category_slot_rendering["canvas_height"]) == 900
    assert str(category_slot_prompt["bundle_id"]).strip() == "pages_category_grid_v0"
    assert str(category_slot_prompt["scene_key"]).strip() == "category_grid"
    assert str(category_slot_prompt["task_key"]).strip() == "category_grid_lookup_query"
    assert str(category_slot_prompt["annotation_hint"]).strip()
    assert str(category_count_prompt["scene_key"]).strip() == "category_grid"
    assert str(category_count_prompt["task_key"]).strip() == "category_grid_lookup_query"
    assert str(category_count_prompt["annotation_hint"]).strip()
    assert "integer" in str(category_count_prompt["answer_hint"])


def test_pages_comparison_panel_scene_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "comparison_panel")
    generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__comparison_panel__side_attribute_value_label",
    )

    assert sorted(generation_defaults["query_id_weights"].keys()) == ["side_attribute_value_label"]
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == ["feature_bands", "matrix_sheet"]
    assert list(generation_defaults["side_count_support"]) == [2, 3]
    assert list(generation_defaults["attribute_count_support"]) == [4, 5, 6]
    assert int(rendering_defaults["canvas_width"]) == 1120
    assert int(rendering_defaults["canvas_height"]) == 860
    assert str(prompt_defaults["bundle_id"]).strip() == "pages_comparison_panel_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "comparison_panel"
    assert str(prompt_defaults["task_key"]).strip() == "comparison_panel_lookup_query"
    assert str(prompt_defaults["annotation_hint"]).strip()


def test_pages_cycle_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "cycle")
    generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__cycle__offset_stage_label",
    )

    assert sorted(generation_defaults["query_id_weights"].keys()) == ["offset_stage_label"]
    assert sorted(generation_defaults["query_relationship_weights"].keys()) == ["after", "before"]
    assert bool(generation_defaults["balanced_query_relationship_sampling"]) is True
    assert bool(generation_defaults["balanced_scene_variant_sampling"]) is True
    assert sorted(generation_defaults["scene_variant_weights"].keys()) == ["cycle_ring"]
    assert sorted(generation_defaults["cycle_direction_weights"].keys()) == ["clockwise", "counterclockwise"]
    assert int(generation_defaults["stage_count_min"]) == 5
    assert int(generation_defaults["stage_count_max"]) == 12

    assert int(rendering_defaults["canvas_width"]) == 1600
    assert int(rendering_defaults["canvas_height"]) == 1250
    assert int(rendering_defaults["outer_margin_px"]) == 220
    assert int(rendering_defaults["node_width_px"]) == 122
    assert int(rendering_defaults["ring_radius_x_px"]) == 360
    cycle_context_text = cfg["visual"]["context_text"]
    assert str(cycle_context_text["pages_context_density"]) == "two_side_notes"
    assert int(cycle_context_text["pages_context_simple_count"]) == 2
    assert int(cycle_context_text["pages_context_side_note_count"]) == 2
    assert int(cycle_context_text["pages_context_text_max_elements"]) == 6

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_cycle_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "cycle_diagram"
    assert str(prompt_defaults["task_key"]).strip() == "offset_stage_query"
    assert str(prompt_defaults["annotation_hint_offset_stage_label"]).strip()

def test_pages_arithmetic_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "arithmetic")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="pages_form_section_section_expression_source",
    )

    assert sorted(generation_defaults["query_id_weights"].keys()) == [
        "difference_two_amounts_in_section",
        "sum_minus_amount_in_section",
        "sum_two_amounts_in_section",
    ]
    assert bool(generation_defaults["balanced_query_id_sampling"]) is True
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
    assert str(prompt_defaults["annotation_hint"]).strip()

def test_pages_cross_form_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "cross_form")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="pages_paired_forms_reconciliation_source",
    )

    assert sorted(generation_defaults["query_id_weights"].keys()) == [
        "shortfall_minus_overage_value",
        "sum_absolute_quantity_differences",
        "total_amount_delta",
    ]
    assert bool(generation_defaults["balanced_query_id_sampling"]) is True
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
    assert str(prompt_defaults["annotation_hint_total_amount_delta"]).strip()
    assert str(prompt_defaults["annotation_hint_shortfall_minus_overage_value"]).strip()
    assert str(prompt_defaults["annotation_hint_sum_absolute_quantity_differences"]).strip()

def test_pages_hierarchy_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "hierarchy")
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="pages_hierarchy_tree_count_base",
    )

    assert sorted(generation_defaults["query_id_weights"].keys()) == [
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
    assert str(prompt_defaults["annotation_hint_subtree_descendant_count"]).strip()

def test_pages_map_defaults_loaded() -> None:
    cfg = get_scene_defaults("pages", "map")
    destination_generation, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__map__destination_after_directions_label",
    )
    landmark_generation, _landmark_rendering, _landmark_prompt = split_scene_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_pages__map__landmark_after_route_step_label",
    )

    assert sorted(destination_generation["query_id_weights"].keys()) == ["destination_after_directions"]
    assert sorted(landmark_generation["query_id_weights"].keys()) == ["landmark_after_route_step"]
    assert bool(destination_generation["balanced_query_id_sampling"]) is True
    assert bool(destination_generation["balanced_scene_variant_sampling"]) is True
    assert sorted(destination_generation["scene_variant_weights"].keys()) == ["campus_map"]
    assert int(destination_generation["landmark_count_min"]) == 10
    assert int(destination_generation["landmark_count_max"]) == 14

    assert int(rendering_defaults["canvas_width"]) == 1280
    assert int(rendering_defaults["canvas_height"]) == 900
    assert int(rendering_defaults["landmark_width_px"]) == 126
    assert int(rendering_defaults["highlighted_path_width_px"]) == 18

    assert str(prompt_defaults["bundle_id"]).strip() == "pages_map_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "printed_map"
    assert str(prompt_defaults["task_key"]).strip() == "map_navigation_query"
    assert str(prompt_defaults["annotation_hint_destination_after_directions"]).strip()
