"""Config regression tests for games Mancala defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_mancala_move_count_defaults_expose_scene_query_and_answer_axes() -> None:
    cfg = get_task_group_defaults("games", "mancala")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games_mancala_move_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"midgame_board", "crowded_board"}
    assert set(generation["query_variant_weights"].keys()) == {
        "extra_turn_move_count",
        "capture_move_count",
    }
    assert set(generation["style_variant_weights"].keys()) == {"classic", "soft", "outlined"}
    assert list(generation["extra_turn_move_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["capture_move_count_support"]) == [0, 1, 2, 3, 4]
    assert int(rendering["board_width_px"]) > 0
    assert int(rendering["board_height_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_mancala_v1"
    assert "mancala" in str(prompt["object_description_midgame_board"]).lower()
    assert "capture" in str(prompt["answer_hint_capture_move_count"]).lower()
