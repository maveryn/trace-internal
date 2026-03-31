"""Config regression tests for games nine-men's-morris defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_nine_mens_morris_pieces_in_mill_count_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "nine_mens_morris")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games_nine_mens_morris_pieces_in_mill_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"single_board"}
    assert set(generation["query_variant_weights"].keys()) == {
        "white_pieces_in_mill_count",
        "black_pieces_in_mill_count",
        "all_pieces_in_mill_count",
    }
    assert list(generation["white_pieces_in_mill_count_support"]) == [0, 3, 5, 6, 7, 8, 9]
    assert list(generation["black_pieces_in_mill_count_support"]) == [0, 3, 5, 6, 7, 8, 9]
    assert list(generation["all_pieces_in_mill_count_support"]) == [0, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
    assert int(rendering["board_width_px"]) > 0
    assert int(rendering["piece_radius_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_nine_mens_morris_v1"
    assert "mill" in str(prompt["mill_rule_text"]).lower()
