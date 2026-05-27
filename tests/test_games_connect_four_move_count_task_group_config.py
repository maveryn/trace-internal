"""Config regression tests for games Connect Four defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_connect_four_move_count_defaults_expose_scene_query_and_answer_axes() -> None:
    cfg = get_task_group_defaults("games", "connect_four")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__connect_four__move_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_board_size_variant_sampling"]) is True
    assert bool(generation["balanced_safe_board_size_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"midgame_board", "crowded_board"}
    assert set(generation["board_size_variant_weights"].keys()) == {"standard_7x6", "small_6x5"}
    assert set(generation["safe_board_size_variant_weights"].keys()) == {"square_5x5", "square_6x6"}
    assert set(generation["query_variant_weights"].keys()) == {
        "winning_move_count",
        "safe_move_count",
    }
    assert set(generation["style_variant_weights"].keys()) == {
        "classic",
        "soft",
        "outlined",
        "arcade_blue",
        "teal_frame",
        "charcoal",
    }
    assert list(generation["winning_move_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["safe_move_count_support"]) == [1, 2, 3, 4, 5, 6]
    assert int(generation["midgame_min_occupied_count"]) == 8
    assert int(generation["midgame_max_occupied_count"]) == 16
    assert int(generation["crowded_min_occupied_count"]) == 16
    assert int(generation["crowded_max_occupied_count"]) == 24
    assert int(generation["safe_midgame_min_occupied_count"]) == 8
    assert int(generation["safe_midgame_max_occupied_count"]) == 16
    assert int(generation["safe_crowded_min_occupied_count"]) == 16
    assert int(generation["safe_crowded_max_occupied_count"]) == 24
    assert int(rendering["max_board_width_px"]) > 0
    assert int(rendering["player_badge_height_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_connect_four_v0"
    assert "connect four" in str(prompt["object_description_midgame_board"]).lower()
    assert "safe" in str(prompt["answer_hint_safe_move_count"]).lower()
