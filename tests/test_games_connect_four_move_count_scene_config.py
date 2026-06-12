"""Config regression tests for games Connect Four defaults."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults


def test_games_connect_four_move_count_defaults_expose_scene_query_and_answer_axes() -> None:
    cfg = get_scene_defaults("games", "connect_four")
    shared_generation, rendering, prompt = split_scene_generation_rendering_prompt_defaults(cfg)
    winning_generation, _winning_rendering, _winning_prompt = split_scene_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__connect_four__winning_move_count",
    )
    safe_generation, _safe_rendering, _safe_prompt = split_scene_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__connect_four__safe_move_count",
    )
    label_generation, _label_rendering, _label_prompt = split_scene_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__connect_four__winning_move_column_label",
    )

    assert bool(shared_generation["balanced_scene_variant_sampling"]) is True
    assert bool(shared_generation["balanced_board_size_variant_sampling"]) is True
    assert bool(shared_generation["balanced_style_variant_sampling"]) is True
    assert bool(shared_generation["balanced_target_answer_sampling"]) is True
    assert set(shared_generation["scene_variant_weights"].keys()) == {"midgame_board", "crowded_board"}
    assert set(shared_generation["board_size_variant_weights"].keys()) == {"standard_7x6", "small_6x5"}
    assert "query_id_weights" not in shared_generation
    assert "safe_board_size_variant_weights" not in shared_generation
    assert "winning_move_count_support" not in shared_generation
    assert "safe_move_count_support" not in shared_generation
    assert set(shared_generation["style_variant_weights"].keys()) == {
        "classic",
        "soft",
        "outlined",
        "arcade_blue",
        "teal_frame",
        "charcoal",
    }
    assert list(winning_generation["winning_move_count_support"]) == [0, 1, 2, 3, 4]
    assert "safe_move_count_support" not in winning_generation
    assert bool(safe_generation["balanced_safe_board_size_variant_sampling"]) is True
    assert set(safe_generation["safe_board_size_variant_weights"].keys()) == {"square_5x5", "square_6x6"}
    assert list(safe_generation["safe_move_count_support"]) == [1, 2, 3, 4, 5, 6]
    assert int(safe_generation["safe_midgame_min_occupied_count"]) == 8
    assert int(safe_generation["safe_midgame_max_occupied_count"]) == 16
    assert int(safe_generation["safe_crowded_min_occupied_count"]) == 16
    assert int(safe_generation["safe_crowded_max_occupied_count"]) == 24
    assert bool(label_generation["balanced_winning_move_label_threat_kind_sampling"]) is True
    assert set(label_generation["winning_move_label_threat_kind_weights"].keys()) == {
        "vertical_threat",
        "horizontal_threat",
    }
    assert int(shared_generation["midgame_min_occupied_count"]) == 8
    assert int(shared_generation["midgame_max_occupied_count"]) == 16
    assert int(shared_generation["crowded_min_occupied_count"]) == 16
    assert int(shared_generation["crowded_max_occupied_count"]) == 24
    assert int(rendering["max_board_width_px"]) > 0
    assert int(rendering["player_badge_height_px"]) > 0
    assert bool(rendering["dynamic_canvas_size_enabled"]) is True
    assert int(rendering["canvas_min_width_px"]) > 0
    assert int(rendering["canvas_min_height_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_connect_four_v1"
