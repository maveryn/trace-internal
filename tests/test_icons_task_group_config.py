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
    assert "task_icons__reference_canvas__reference_attribute_match_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__icon_field__type_frequency_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__named_field__count_arithmetic" in cfg["generation"]["task_overrides"]
    assert "task_icons__named_field__closer_to_reference_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__named_grid__scoped_attribute_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__named_grid__row_column_shape_extreme_number" in cfg["generation"]["task_overrides"]
    assert "task_icons__named_grid__group_predicate_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__named_ring__scoped_attribute_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__venn_field__scoped_attribute_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__reference_canvas__reference_metric_relation_count" in cfg["generation"]["task_overrides"]
    assert set(cfg["generation"]["task_overrides"]["task_icons__reference_canvas__reference_attribute_match_count"]["query_id_weights"].keys()) == {
        "match_type",
        "match_color",
        "match_rotation",
        "match_type_color_rotation",
    }
    assert set(cfg["generation"]["task_overrides"]["task_icons__reference_canvas__reference_metric_relation_count"]["query_id_weights"].keys()) == {
        "size_smaller",
        "size_larger",
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
        task_id="task_icons__reference_canvas__reference_attribute_match_count",
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
    assert str(single_prompt["annotation_hint"]).strip()
    assert str(single_prompt["answer_hint"]).strip()
    assert str(single_prompt["json_example"]).strip()
    assert str(single_prompt["json_example_answer_only"]).strip()

    assert str(single_generation["variant_generation_params"]["match_type_color_rotation"]["pool_manifest"]).strip() == "non_symmetry.txt"
    assert list(single_generation["variant_generation_params"]["match_type_color_rotation"]["rotation_candidates_degrees"]) == [0, 90, 180, 270]
    assert float(single_rendering["variant_render_params"]["match_type_color_rotation"]["min_color_distance"]) == 40.0
    assert int(single_rendering["variant_render_params"]["match_type_color_rotation"]["palette_size_min"]) == 3
    assert int(single_rendering["variant_render_params"]["match_type_color_rotation"]["palette_size_max"]) == 4

    size_relation_generation, size_relation_rendering, size_relation_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__reference_canvas__reference_metric_relation_count",
    )
    assert set(size_relation_generation["query_id_weights"].keys()) == {"size_smaller", "size_larger"}
    assert set(size_relation_prompt["question_text_by_variant"].keys()) == {"size_smaller", "size_larger"}

    size_generation = size_relation_generation["variant_generation_params"]["size_smaller"]
    assert str(size_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert list(size_generation["rotation_candidates_degrees"]) == [0, 90, 180, 270]
    assert list(size_generation["size_relation_candidates"]) == ["smaller", "larger"]
    assert int(size_generation["size_relation_min_delta_px"]) == 18
    assert int(size_generation["object_count_max"]) == 14
    assert int(size_generation["target_count_max"]) == 5
    assert int(size_generation["distractor_count_max"]) == 6
    assert int(size_relation_rendering["variant_render_params"]["size_smaller"]["scene_icon_size_max_px"]) == 120
    assert int(size_relation_rendering["variant_render_params"]["size_smaller"]["reference_icon_size_min_px"]) == 64
    assert int(size_relation_rendering["variant_render_params"]["size_smaller"]["reference_icon_size_max_px"]) == 96
    assert str(size_relation_prompt["question_text_by_variant"]["size_smaller"]).strip()
    assert str(size_relation_prompt["question_text_by_variant"]["size_larger"]).strip()

    singleton_generation, singleton_rendering, singleton_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__icon_field__type_frequency_count",
    )
    assert str(singleton_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert sorted(singleton_generation["query_id_weights"].keys()) == ["most_frequent_type_count", "singleton_type_count"]
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
    assert int(singleton_rendering["scene_icon_size_min_px"]) == 64
    assert int(singleton_rendering["scene_icon_size_max_px"]) == 96
    assert str(singleton_prompt["scene_key"]).strip() == "single_scene_counting"
    assert str(singleton_prompt["object_description"]).strip()
    assert str(singleton_prompt["question_text_by_variant"]["singleton_type_count"]).strip()
    assert str(singleton_prompt["annotation_hint_by_variant"]["singleton_type_count"]).strip()
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
    assert int(most_frequent_params["target_count_min"]) == 2
    assert int(most_frequent_params["target_count_max"]) == 6
    assert int(most_frequent_params["other_repeated_type_count_max"]) == 3
    assert int(most_frequent_rendering["canvas_width"]) > 0
    assert int(most_frequent_rendering["canvas_height"]) > 0
    assert str(most_frequent_prompt["scene_key"]).strip() == "single_scene_counting"
    assert str(most_frequent_prompt["object_description"]).strip()
    assert str(most_frequent_prompt["question_text_by_variant"]["most_frequent_type_count"]).strip()
    assert str(most_frequent_prompt["annotation_hint_by_variant"]["most_frequent_type_count"]).strip()
    assert str(most_frequent_prompt["answer_hint"]).strip()
    assert str(most_frequent_prompt["json_example"]).strip()
    assert str(most_frequent_prompt["json_example_answer_only"]).strip()

    pair_generation, pair_rendering, pair_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__named_field__count_arithmetic",
    )
    assert int(pair_generation["operand_count_min"]) == 1
    assert int(pair_generation["operand_count_max"]) == 6
    assert int(pair_generation["total_answer_min"]) == 2
    assert int(pair_generation["total_answer_max"]) == 10
    assert int(pair_generation["difference_answer_min"]) == 0
    assert int(pair_generation["difference_answer_max"]) == 5
    assert sorted(pair_generation["query_weights"].keys()) == [
        "two_bound_color_difference_count",
        "two_bound_color_total_count",
        "two_shape_difference_count",
        "two_shape_total_count",
    ]
    assert int(pair_rendering["canvas_width"]) > 0
    assert int(pair_rendering["canvas_height"]) > 0
    assert str(pair_prompt["scene_key"]).strip() == "single_scene_counting"
    assert str(pair_prompt["question_text_two_shape_total_count"]).strip()
    assert str(pair_prompt["question_text_two_bound_color_total_count"]).strip()
    assert str(pair_prompt["question_text_two_shape_difference_count"]).strip()
    assert str(pair_prompt["question_text_two_bound_color_difference_count"]).strip()
    assert str(pair_prompt["annotation_hint"]).strip()
    assert str(pair_prompt["answer_hint"]).strip()
    assert str(pair_prompt["json_example"]).strip()
    assert str(pair_prompt["json_example_answer_only"]).strip()

    grid_generation, grid_rendering, grid_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__named_grid__scoped_attribute_count",
    )
    assert int(grid_generation["target_count_min"]) == 1
    assert int(grid_generation["target_count_max"]) == 5
    assert sorted(grid_generation["query_id_weights"].keys()) == ["column_shape_count", "row_shape_count"]
    assert [list(value) for value in grid_generation["grid_size_support"]] == [
        [4, 4],
        [4, 5],
        [4, 6],
        [5, 4],
        [5, 5],
        [5, 6],
        [6, 4],
        [6, 5],
        [6, 6],
    ]
    assert int(grid_rendering["canvas_width"]) == 880
    assert int(grid_rendering["canvas_height"]) == 680
    assert int(grid_rendering["grid_cell_max_size_px"]) == 104
    assert int(grid_rendering["axis_label_font_size_px"]) == 24
    assert str(grid_prompt["scene_key"]).strip() == "single_scene_counting"
    assert str(grid_prompt["question_text_row_shape_count"]).strip()
    assert str(grid_prompt["question_text_column_shape_count"]).strip()
    assert str(grid_prompt["annotation_hint"]).strip()
    assert str(grid_prompt["answer_hint"]).strip()
    assert str(grid_prompt["json_example"]).strip()
    assert str(grid_prompt["json_example_answer_only"]).strip()

    grid_extreme_generation, grid_extreme_rendering, grid_extreme_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__named_grid__row_column_shape_extreme_number",
    )
    assert int(grid_extreme_generation["answer_line_number_min"]) == 1
    assert int(grid_extreme_generation["answer_line_number_max"]) == 6
    assert sorted(grid_extreme_generation["query_id_weights"].keys()) == [
        "column_fewest_shape_number",
        "column_most_shape_number",
        "row_fewest_shape_number",
        "row_most_shape_number",
    ]
    assert [list(value) for value in grid_extreme_generation["grid_size_support"]] == [
        [4, 4],
        [4, 5],
        [4, 6],
        [5, 4],
        [5, 5],
        [5, 6],
        [6, 4],
        [6, 5],
        [6, 6],
    ]
    assert int(grid_extreme_rendering["canvas_width"]) == 880
    assert int(grid_extreme_rendering["canvas_height"]) == 680
    assert str(grid_extreme_prompt["scene_key"]).strip() == "single_scene_counting"
    assert str(grid_extreme_prompt["question_text_row_most_shape_number"]).strip()
    assert str(grid_extreme_prompt["question_text_row_fewest_shape_number"]).strip()
    assert str(grid_extreme_prompt["question_text_column_most_shape_number"]).strip()
    assert str(grid_extreme_prompt["question_text_column_fewest_shape_number"]).strip()
    assert str(grid_extreme_prompt["annotation_hint"]).strip()
    assert str(grid_extreme_prompt["answer_hint"]).strip()
    assert str(grid_extreme_prompt["json_example"]).strip()
    assert str(grid_extreme_prompt["json_example_answer_only"]).strip()

    grid_line_generation, grid_line_rendering, grid_line_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__named_grid__group_predicate_count",
    )
    assert int(grid_line_generation["answer_count_min"]) == 0
    assert int(grid_line_generation["answer_count_max"]) == 5
    assert int(grid_line_generation["at_least_threshold_min"]) == 2
    assert int(grid_line_generation["at_least_threshold_max"]) == 3
    assert int(grid_line_generation["exactly_threshold_min"]) == 1
    assert int(grid_line_generation["exactly_threshold_max"]) == 3
    assert sorted(grid_line_generation["query_id_weights"].keys()) == [
        "column_at_least_shape_count",
        "column_exactly_shape_count",
        "column_no_shape_count",
        "row_at_least_shape_count",
        "row_exactly_shape_count",
        "row_no_shape_count",
    ]
    assert [list(value) for value in grid_line_generation["grid_size_support"]] == [
        [4, 4],
        [4, 5],
        [4, 6],
        [5, 4],
        [5, 5],
        [5, 6],
        [6, 4],
        [6, 5],
        [6, 6],
    ]
    assert int(grid_line_rendering["canvas_width"]) == 880
    assert int(grid_line_rendering["canvas_height"]) == 680
    assert str(grid_line_prompt["scene_key"]).strip() == "single_scene_counting"
    assert str(grid_line_prompt["question_text_row_at_least_shape_count"]).strip()
    assert str(grid_line_prompt["question_text_column_at_least_shape_count"]).strip()
    assert str(grid_line_prompt["question_text_row_exactly_shape_count"]).strip()
    assert str(grid_line_prompt["question_text_column_exactly_shape_count"]).strip()
    assert str(grid_line_prompt["question_text_row_no_shape_count"]).strip()
    assert str(grid_line_prompt["question_text_column_no_shape_count"]).strip()
    assert str(grid_line_prompt["annotation_hint"]).strip()
    assert str(grid_line_prompt["answer_hint"]).strip()
    assert str(grid_line_prompt["json_example"]).strip()
    assert str(grid_line_prompt["json_example_answer_only"]).strip()

    ring_generation, ring_rendering, ring_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__named_ring__scoped_attribute_count",
    )
    assert int(ring_generation["ring_icon_count_min"]) == 12
    assert int(ring_generation["ring_icon_count_max"]) == 22
    assert int(ring_generation["answer_count_min"]) == 0
    assert int(ring_generation["answer_count_max"]) == 6
    assert int(ring_generation["arc_span_min"]) == 3
    assert int(ring_generation["arc_span_max"]) == 12
    assert sorted(ring_generation["query_id_weights"].keys()) == [
        "clockwise_arc_shape_count",
        "counterclockwise_arc_shape_count",
    ]
    assert int(ring_rendering["canvas_width"]) == 880
    assert int(ring_rendering["canvas_height"]) == 680
    assert int(ring_rendering["ring_margin_px"]) == 86
    assert int(ring_rendering["marker_label_radius_px"]) == 18
    assert str(ring_prompt["scene_key"]).strip() == "single_scene_counting"
    assert str(ring_prompt["question_text_clockwise_arc_shape_count"]).strip()
    assert str(ring_prompt["question_text_counterclockwise_arc_shape_count"]).strip()
    assert str(ring_prompt["annotation_hint"]).strip()
    assert str(ring_prompt["answer_hint"]).strip()
    assert str(ring_prompt["json_example"]).strip()
    assert str(ring_prompt["json_example_answer_only"]).strip()

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
    assert str(closer_prompt["annotation_hint"]).strip()
    assert str(closer_prompt["answer_hint"]).strip()
    assert str(closer_prompt["json_example"]).strip()
    assert str(closer_prompt["json_example_answer_only"]).strip()

    venn_generation, venn_rendering, venn_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__venn_field__scoped_attribute_count",
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
    assert str(venn_prompt["annotation_hint"]).strip()
    assert str(venn_prompt["answer_hint"]).strip()
    assert str(venn_prompt["json_example"]).strip()
    assert str(venn_prompt["json_example_answer_only"]).strip()

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
    assert "task_icons__pair_grid__attribute_delta_pair_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__pair_grid__reference_transform_match_count" in cfg["generation"]["task_overrides"]

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
        task_id="task_icons__pair_grid__reference_transform_match_count",
    )
    assert str(generation["pool_manifest"]).strip() == "all_icons.txt"
    assert int(generation["object_count_min"]) == 6
    assert int(generation["object_count_max"]) == 6
    transform_params = generation["variant_generation_params"]["same_pair_transform"]
    assert str(transform_params["pool_manifest"]).strip() == "non_symmetry.txt"
    assert list(transform_params["transform_ids"]) == [
        "rot90",
        "rot180",
        "rot270",
        "flip_h",
        "flip_v",
        "flip_diag_main",
        "flip_diag_anti",
    ]
    assert int(transform_params["transform_check_size_px"]) > 0
    assert int(rendering["canvas_width"]) > 0
    assert int(rendering["reference_panel_width_px"]) > 0
    assert str(prompt["object_description"]).strip()
    assert str(prompt["question_text"]).strip()
    assert str(prompt["annotation_hint"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["json_example"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()

    assert sorted(generation["query_id_weights"].keys()) == [
        "same_pair_transform",
    ]

    attribute_generation, attribute_rendering, attribute_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__pair_grid__attribute_delta_pair_count",
    )
    assert sorted(attribute_generation["query_id_weights"].keys()) == [
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
    assert str(attribute_prompt["annotation_hint"]).strip()
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
    assert "task_icons__reference_canvas__anchor_position_count" in cfg["generation"]["task_overrides"]
    assert "task_icons__named_field__reference_distance_rank_label" in cfg["generation"]["task_overrides"]
    assert "task_icons__named_path__path_neighbor_label" in cfg["generation"]["task_overrides"]

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
    assert str(mirror_prompt["annotation_hint"]).strip()
    assert str(mirror_prompt["answer_hint"]).strip()
    assert str(mirror_prompt["json_example"]).strip()
    assert str(mirror_prompt["json_example_answer_only"]).strip()

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
    assert str(strip_prompt["annotation_hint"]).strip()
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
    assert str(occlusion_prompt["annotation_hint"]).strip()
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
    assert str(prompt["annotation_hint"]).strip()
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
    assert str(distance_prompt["annotation_hint"]).strip()
    assert str(distance_prompt["answer_hint"]).strip()
    assert str(distance_prompt["json_example"]).strip()
    assert str(distance_prompt["json_example_answer_only"]).strip()

    path_generation, path_rendering, path_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__named_path__path_neighbor_label",
    )
    assert int(path_generation["candidate_count"]) == 6
    assert int(path_generation["distractor_count_min"]) == 4
    assert int(path_generation["distractor_count_max"]) == 8
    assert int(path_generation["target_occurrence_count_min"]) == 2
    assert int(path_generation["target_occurrence_count_max"]) == 4
    assert dict(path_generation["path_neighbor_query_weights"]) == {
        "after_first_shape_label": 1.0,
        "before_first_shape_label": 1.0,
        "after_last_shape_label": 1.0,
        "before_last_shape_label": 1.0,
        "after_second_shape_label": 1.0,
        "before_second_shape_label": 1.0,
    }
    assert list(path_generation["named_icon_fill_style_support"]) == ["solid", "striped", "dotted", "half_filled"]
    assert int(path_rendering["canvas_width"]) == 1280
    assert int(path_rendering["canvas_height"]) == 720
    assert int(path_rendering["scene_icon_size_min_px"]) == 44
    assert int(path_rendering["scene_icon_size_max_px"]) == 60
    assert int(path_rendering["path_stroke_width_px"]) == 7
    assert int(path_rendering["candidate_label_font_size_px"]) == 24
    assert str(path_prompt["scene_key"]).strip() == "named_path_relation"
    assert str(path_prompt["object_description"]).strip()
    for suffix in (
        "after_first_shape_label",
        "before_first_shape_label",
        "after_last_shape_label",
        "before_last_shape_label",
        "after_second_shape_label",
        "before_second_shape_label",
    ):
        assert str(path_prompt[f"question_text_{suffix}"]).strip()
    assert str(path_prompt["annotation_hint"]).strip()
    assert str(path_prompt["answer_hint"]).strip()
    assert str(path_prompt["json_example"]).strip()
    assert str(path_prompt["json_example_answer_only"]).strip()

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
    assert "task_icons__named_strip__shape_run_length" in cfg["generation"]["task_overrides"]

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
    assert str(prompt["annotation_hint"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["json_example"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_icons__named_strip__shape_run_length",
    )
    assert sorted(generation["query_id_weights"].keys()) == [
        "longest_shape_run_length",
        "shortest_shape_run_length",
    ]
    assert int(generation["strip_length_min"]) == 12
    assert int(generation["strip_length_max"]) == 16
    assert int(generation["longest_run_length_min"]) == 2
    assert int(generation["longest_run_length_max"]) == 6
    assert int(generation["shortest_run_length_min"]) == 1
    assert int(generation["shortest_run_length_max"]) == 5
    assert int(rendering["scene_icon_size_min_px"]) == 42
    assert int(rendering["scene_icon_size_max_px"]) == 58
    assert int(rendering["cell_padding_px"]) == 4
    assert str(prompt["scene_key"]).strip() == "named_strip_run_length"
    assert str(prompt["task_key"]).strip() == "run_length_query"
    assert str(prompt["question_text_longest_shape_run_length"]).strip()
    assert str(prompt["question_text_shortest_shape_run_length"]).strip()
    assert str(prompt["annotation_hint"]).strip()
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
    assert "task_icons__pattern_grid__attribute_pattern_violation_index" in cfg["generation"]["task_overrides"]
    assert "task_icons__sequence_strip__rotation_sequence_violation_index" in cfg["generation"]["task_overrides"]

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
        task_id="task_icons__pattern_grid__attribute_pattern_violation_index",
    )
    assert sorted(generation["query_id_weights"].keys()) == ["grid_color_violation", "grid_size_violation"]
    color_generation = generation["variant_generation_params"]["grid_color_violation"]
    assert str(color_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert list(color_generation["color_levels"]) == [0, 1, 2, 3, 4, 5, 6, 7]
    assert list(color_generation["base_color_level_candidates"]) == [0, 1, 2, 3, 4, 5, 6, 7]
    assert list(color_generation["row_step_color_candidates"]) == [-2, -1, 0, 1, 2]
    assert list(color_generation["col_step_color_candidates"]) == [-2, -1, 0, 1, 2]
    assert list(color_generation["shared_rotation_candidates_degrees"]) == [0, 90, 180, 270]
    color_rendering = rendering["variant_render_params"]["grid_color_violation"]
    assert int(color_rendering["scene_icon_size_min_px"]) == 66
    assert int(color_rendering["scene_icon_size_max_px"]) == 84
    assert int(color_rendering["palette_size_min"]) == 8
    assert int(color_rendering["palette_size_max"]) == 8
    assert list(color_rendering["icon_noise_edit_count_range"]) == [0, 0]

    size_generation = generation["variant_generation_params"]["grid_size_violation"]
    assert str(size_generation["pool_manifest"]).strip() == "all_icons.txt"
    assert list(size_generation["size_levels"]) == [1, 2, 3, 4, 5]
    assert list(size_generation["base_level_candidates"]) == [1, 2, 3, 4, 5]
    assert list(size_generation["row_step_candidates"]) == [-1, 0, 1]
    assert list(size_generation["col_step_candidates"]) == [-1, 0, 1]
    assert list(size_generation["shared_rotation_candidates_degrees"]) == [0, 90, 180, 270]
    size_rendering = rendering["variant_render_params"]["grid_size_violation"]
    assert int(size_rendering["scene_icon_size_min_px"]) == 34
    assert int(size_rendering["scene_icon_size_max_px"]) == 82
    assert int(size_rendering["cell_box_width_min_px"]) == 116
    assert int(size_rendering["cell_box_width_max_px"]) == 152
    assert int(size_rendering["cell_box_height_min_px"]) == 116
    assert int(size_rendering["cell_box_height_max_px"]) == 152
    assert int(size_rendering["size_level_gap_px"]) == 10
    assert list(size_rendering["icon_noise_edit_count_range"]) == [0, 0]
    assert str(prompt["object_description"]).strip()
    assert str(prompt["question_text"]).strip()
    assert str(prompt["annotation_hint"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["json_example"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()
