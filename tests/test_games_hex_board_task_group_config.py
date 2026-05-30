"""Config regression tests for games Hex-board defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.style import SUPPORTED_HEX_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_hex_board_defaults_expose_scene_query_target_board_and_style_axes() -> None:
    cfg = get_task_group_defaults("games", "hex")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__hex__winning_move_cell_label",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_player_color_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_board_size_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert bool(generation["balanced_target_label_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"open_board", "crowded_board"}
    assert set(generation["query_id_weights"].keys()) == {"winning_move_cell_label", "connection_gap_count"}
    assert set(generation["player_color_weights"].keys()) == {"red", "blue"}
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_HEX_STYLE_VARIANTS)
    assert list(generation["board_size_support"]) == [5, 6, 7, 8]
    assert list(generation["connection_gap_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["candidate_count_support"]) == [4, 5, 6, 7, 8]
    assert list(generation["winning_move_label_support"]) == list("ABCDEFGH")
    assert int(rendering["canvas_width"]) == 980
    assert int(rendering["max_board_width_px"]) > 0
    assert bool(rendering["dynamic_canvas_size_enabled"]) is True
    assert int(rendering["canvas_min_width_px"]) >= 560
    assert str(prompt["bundle_id"]) == "games_hex_v0"
    assert "Hex board" in str(prompt["object_description_open_board"])
    assert "Red connects" in str(prompt["red_goal_text"])
    assert "Blue connects" in str(prompt["blue_goal_text"])
    assert "pixel-space point" in str(prompt["evidence_hint_winning_move_cell_label"])
