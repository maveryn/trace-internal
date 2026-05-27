"""Config regression tests for games Chess-board defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_chess_board_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "chess")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__chess__marked_piece_destination_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"sparse_board", "crowded_board"}
    assert set(generation["query_id_weights"].keys()) == {
        "marked_piece_move_count",
        "marked_piece_capture_count",
        "player_capture_piece_count",
        "check_attacker_count",
        "king_escape_square_count",
    }
    assert list(generation["marked_piece_move_count_support"]) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert list(generation["marked_piece_capture_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["player_capture_piece_count_support"]) == [1, 2, 3, 4, 5, 6]
    assert list(generation["check_attacker_count_support"]) == [1, 2, 3, 4]
    assert list(generation["king_escape_square_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert int(rendering["max_board_size_px"]) > 0
    assert int(rendering["marked_square_outline_width_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_chess_v0"
    assert "chess" in str(prompt["object_description_sparse_board"]).lower()
    assert "bounding boxes" in str(prompt["evidence_hint_marked_piece_move_count"])
    assert "destination square" in str(prompt["evidence_hint_marked_piece_capture_count"])
    assert "safe" in str(prompt["answer_hint_king_escape_square_count"]).lower()
