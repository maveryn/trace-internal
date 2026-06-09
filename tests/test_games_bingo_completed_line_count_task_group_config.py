"""Config regression tests for games bingo defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_bingo_completed_line_count_defaults_expose_scene_query_and_target_axes() -> None:
    cfg = get_task_group_defaults("games", "bingo")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__bingo__completed_line_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"single_card"}
    assert set(generation["query_id_weights"].keys()) == {
        "completed_axis_line_count",
        "line_sum_extremum_value",
        "near_complete_row_count",
        "near_complete_column_count",
        "called_marked_number_count",
    }
    assert float(generation["query_id_weights"]["completed_axis_line_count"]) == 1.0
    assert float(generation["query_id_weights"]["line_sum_extremum_value"]) == 1.0
    assert float(generation["query_id_weights"]["near_complete_row_count"]) == 1.0
    assert float(generation["query_id_weights"]["near_complete_column_count"]) == 1.0
    assert float(generation["query_id_weights"]["called_marked_number_count"]) == 1.0
    assert set(generation["line_axis_weights"].keys()) == {"row", "column"}
    assert set(generation["extremum_weights"].keys()) == {"max", "min"}
    assert set(generation["style_variant_weights"].keys()) == {
        "classic",
        "soft",
        "outlined",
        "mint",
        "lavender",
        "amber",
        "slate",
    }
    assert set(generation["mark_shape_weights"].keys()) == {"ellipse", "cell", "ring", "slash"}
    assert set(generation["cell_fill_pattern_weights"].keys()) == {"solid", "column_tint", "checker_tint"}
    assert list(generation["completed_axis_line_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["line_sum_completed_line_count_support"]) == [2, 3, 4]
    assert list(generation["near_complete_line_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["called_marked_number_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["called_number_count_support"]) == [5, 6, 7, 8]
    assert float(generation["line_sum_distractor_mark_prob"]) == 0.2
    assert int(rendering["card_width_px"]) > 0
    assert int(rendering["card_height_px"]) > 0
    assert float(rendering["unit_size_scale_min"]) == 0.5
    assert float(rendering["unit_size_scale_max"]) == 1.0
    assert bool(rendering["dynamic_canvas_size_enabled"]) is True
    assert int(rendering["number_font_size_px"]) > 0
    assert int(rendering["called_panel_width_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_bingo_v0"
    assert "5 x 5 bingo card" in str(prompt["object_description_single_card"])
    assert "{line_axis}" in str(prompt["answer_hint_completed_axis_line_count"])
    assert "{extremum}" in str(prompt["answer_hint_line_sum_extremum_value"])
    assert "near-complete" in str(prompt["near_complete_line_rule_text"])
    assert "near-complete" in str(prompt["answer_hint_near_complete_row_count"])
    assert "gap cell" in str(prompt["annotation_hint_near_complete_column_count"])
    assert "called" in str(prompt["answer_hint_called_marked_number_count"]).lower()
