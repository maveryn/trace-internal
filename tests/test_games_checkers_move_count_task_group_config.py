"""Config regression tests for games Checkers defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_checkers_move_count_defaults_expose_scene_query_and_answer_axes() -> None:
    cfg = get_task_group_defaults("games", "checkers")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__checkers__move_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"midgame_board", "crowded_board"}
    assert set(generation["query_id_weights"].keys()) == {
        "legal_move_count",
        "capture_move_count",
        "max_capture_chain_length",
        "piece_with_legal_move_count",
        "piece_with_capture_move_count",
        "red_piece_count",
        "black_piece_count",
        "red_edge_piece_count",
        "black_edge_piece_count",
    }
    assert set(generation["style_variant_weights"].keys()) == {
        "classic",
        "soft",
        "outlined",
        "wood_token",
        "blue_table",
        "charcoal",
    }
    assert list(generation["legal_move_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["capture_move_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["max_capture_chain_length_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["piece_with_legal_move_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["piece_with_capture_move_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["piece_state_count_support"]) == [0, 1, 2, 3, 4, 5, 6]
    assert int(rendering["max_board_size_px"]) > 0
    assert int(rendering["player_badge_height_px"]) > 0
    assert bool(rendering["dynamic_canvas_size_enabled"]) is True
    assert int(rendering["canvas_min_width_px"]) > 0
    assert int(rendering["canvas_min_height_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_checkers_v0"
    assert "checkers board" in str(prompt["object_description_midgame_board"]).lower()
    assert "blue" not in str(prompt["king_chain_rule_text"]).lower()
    assert "outlined checker" in str(prompt["king_chain_rule_text"]).lower()
    assert "capture" in str(prompt["answer_hint_capture_move_count"]).lower()
    assert "chain" in str(prompt["answer_hint_max_capture_chain_length"]).lower()
    assert "pieces" in str(prompt["answer_hint_piece_with_legal_move_count"]).lower()
    assert "pixel-space points" in str(prompt["annotation_hint_piece_with_capture_move_count"]).lower()
    assert "red pieces" in str(prompt["answer_hint_red_piece_count"]).lower()
    assert "board edge" in str(prompt["answer_hint_black_edge_piece_count"]).lower()
    assert "pixel-space points" in str(prompt["annotation_hint_red_edge_piece_count"]).lower()
