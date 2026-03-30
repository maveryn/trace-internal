"""Config regression tests for games Connect Four defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_connect_four_move_count_defaults_expose_scene_query_and_answer_axes() -> None:
    cfg = get_task_group_defaults("games", "connect_four")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games_connect_four_move_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"midgame_board", "crowded_board"}
    assert set(generation["query_variant_weights"].keys()) == {
        "winning_move_count",
        "safe_move_count",
    }
    assert set(generation["style_variant_weights"].keys()) == {"classic", "soft", "outlined"}
    assert list(generation["winning_move_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["safe_move_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert int(rendering["max_board_width_px"]) > 0
    assert int(rendering["player_badge_height_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_connect_four_v1"
    assert "connect four" in str(prompt["object_description_midgame_board"]).lower()
    assert "safe" in str(prompt["answer_hint_safe_move_count"]).lower()
