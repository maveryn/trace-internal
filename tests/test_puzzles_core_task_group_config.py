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
    assert sorted(generation_defaults["query_id_weights"].keys()) == [
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
    assert str(prompt_defaults["annotation_hint_axis_uniqueness"]).strip()
    assert str(prompt_defaults["annotation_hint_king_non_touch"]).strip()
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
    assert sorted(raven_generation_defaults["query_id_weights"].keys()) == [
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
    assert sorted(generation_defaults["query_id_weights"].keys()) == [
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
    assert str(prompt_defaults["annotation_hint_paper_fold_result"]).strip()
    assert str(prompt_defaults["annotation_hint_paper_fold_cut_result"]).strip()
    assert str(prompt_defaults["annotation_hint_overlay_result"]).strip()
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
    assert generation_defaults["query_id_weights"] == {
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
    assert str(prompt_defaults["annotation_hint_total_cube_count"]).strip()
    assert str(prompt_defaults["annotation_hint_missing_to_complete_cuboid_count"]).strip()
    assert str(prompt_defaults["annotation_hint_removed_cube_count"]).strip()
    assert str(prompt_defaults["annotation_hint_painted_exterior_face_count"]).strip()
    assert str(prompt_defaults["annotation_hint_exact_k_painted_faces_cube_count"]).strip()
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
    assert sorted(generation_defaults["query_id_weights"].keys()) == [
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
    label_overrides = generation_defaults["query_id_overrides"]["cyclic_order_equivalent_label"]
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
    assert sorted(generation_defaults["query_id_weights"].keys()) == [
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
    assert str(prompt_defaults["annotation_hint_exit_reachability_label"]).strip()
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
    assert str(prompt["annotation_hint"]).strip()
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
    assert str(reachable_prompt["annotation_hint"]).strip()
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
    assert json.loads(str(reachable_prompt["json_example"])) == {"annotation": [[216, 120], [168, 216]], "answer": 2}
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
    assert str(prompt["annotation_hint"]).strip()
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
    assert str(prompt["annotation_hint"]).strip()
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
    assert str(prompt_components["annotation_hint"]).strip()
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
    assert component_example == {"annotation": [[120, 120], [168, 120], [216, 216]], "answer": 2}
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
    assert str(prompt_largest["annotation_hint"]).strip()
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
        "annotation": [[120, 120], [168, 120], [168, 168], [216, 168]],
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
    assert str(prompt["annotation_hint"]).strip()
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
    assert example == {"annotation": [[120, 120], [168, 120], [168, 168], [168, 216]], "answer": 4}
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
    assert str(prompt["annotation_hint"]).strip()
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
        "annotation": [[168, 168], [216, 168], [264, 168], [312, 168]],
        "answer": 3,
    }
    answer_only_example = json.loads(str(prompt["json_example_answer_only"]))
    assert answer_only_example == {"answer": 3}
