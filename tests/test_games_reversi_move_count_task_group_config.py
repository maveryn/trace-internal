"""Config regression tests for games Reversi defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.style import SUPPORTED_REVERSI_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_reversi_move_count_defaults_expose_scene_query_and_answer_axes() -> None:
    cfg = get_task_group_defaults("games", "reversi")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__reversi__legal_destination_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"compact_board", "classic_board"}
    assert set(generation["query_id_weights"].keys()) == {
        "legal_move_count",
        "corner_move_count",
        "flip_count_for_marked_move",
        "black_frontier_disc_count",
        "white_frontier_disc_count",
    }
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_REVERSI_STYLE_VARIANTS)
    assert list(generation["legal_move_count_support"]) == [0, 1, 2, 3, 4, 5, 6]
    assert list(generation["corner_move_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["flip_count_support"]) == [2, 3, 4, 5, 6]
    assert list(generation["frontier_disc_count_support"]) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert int(rendering["max_board_size_px"]) > 0
    assert int(rendering["player_badge_height_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_reversi_v0"
    assert "6 by 6" in str(prompt["object_description_compact_board"])
    assert "corner" in str(prompt["annotation_hint_corner_move_count"]).lower()
    assert "pixel point" in str(prompt["annotation_hint_flip_count_for_marked_move"]).lower()
    assert "flip" in str(prompt["answer_hint_flip_count_for_marked_move"]).lower()
    assert "frontier" in str(prompt["frontier_rule_text"]).lower()
    assert "black frontier" in str(prompt["answer_hint_black_frontier_disc_count"]).lower()
