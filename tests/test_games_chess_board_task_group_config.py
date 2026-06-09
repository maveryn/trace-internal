"""Config regression tests for games Chess-board defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.style import SUPPORTED_CHESS_STYLE_VARIANTS, build_games_chess_theme
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults
from trace.tasks.shared.text_legibility import contrast_ratio


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
        "king_square_attacker_count",
        "white_piece_attacks_target_square_count",
        "black_piece_attacks_target_square_count",
        "rook_line_blocker_count",
        "bishop_diagonal_blocker_count",
        "queen_line_blocker_count",
        "king_escape_square_count",
        "piece_kind_count",
        "colored_piece_kind_count",
    }
    assert list(generation["marked_piece_move_count_support"]) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert list(generation["marked_piece_capture_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["player_capture_piece_count_support"]) == [1, 2, 3, 4, 5, 6]
    assert list(generation["target_square_attacker_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["marked_piece_blocker_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["king_escape_square_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["piece_type_count_support"]) == [0, 1, 2, 3, 4, 5, 6]
    assert list(generation["piece_count_distractor_count_support"]) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert set(generation["target_piece_kind_weights"].keys()) == {"king", "queen", "rook", "bishop", "knight", "pawn"}
    assert set(generation["target_piece_color_weights"].keys()) == {"white", "black"}
    assert int(rendering["max_board_size_px"]) > 0
    assert int(rendering["marked_square_outline_width_px"]) > 0
    assert bool(rendering["dynamic_canvas_size_enabled"]) is True
    assert int(rendering["canvas_min_width_px"]) > 0
    assert int(rendering["canvas_min_height_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_chess_v0"
    assert "chess" in str(prompt["object_description_sparse_board"]).lower()
    assert "blue" not in str(prompt["marked_piece_rule_text"]).lower()
    assert "blue" not in str(prompt["target_square_rule_text"]).lower()
    assert "blue" not in str(prompt["king_square_attacker_rule_text"]).lower()
    assert "blue" not in str(prompt["king_escape_rule_text"]).lower()
    assert "red outlined square" in str(prompt["marked_piece_rule_text"]).lower()
    assert "red outlined square" in str(prompt["target_square_rule_text"]).lower()
    assert "red outlined square" in str(prompt["king_square_attacker_rule_text"]).lower()
    assert "red outlined square" in str(prompt["blocker_rule_text"]).lower()
    assert "blue outlined square" in str(prompt["blocker_rule_text"]).lower()
    assert "red outlined square" in str(prompt["king_escape_rule_text"]).lower()
    assert "bounding boxes" in str(prompt["annotation_hint_marked_piece_move_count"])
    assert "destination square" in str(prompt["annotation_hint_marked_piece_capture_count"])
    assert "safe" in str(prompt["answer_hint_king_escape_square_count"]).lower()
    assert "{target_piece_kind" in str(prompt["answer_hint_piece_kind_count"])


def test_games_chess_board_themes_keep_fixed_pieces_readable() -> None:
    for style_variant in SUPPORTED_CHESS_STYLE_VARIANTS:
        theme = build_games_chess_theme(style_variant=style_variant)
        assert theme.piece_rendering == "glyph"
        assert theme.white_piece_fill_rgb == (255, 255, 255)
        assert theme.white_piece_outline_rgb == (0, 0, 0)
        assert theme.black_piece_fill_rgb == (0, 0, 0)
        assert theme.black_piece_outline_rgb == (255, 255, 255)
        assert theme.marked_square_outline_rgb == (220, 38, 38)
        assert theme.marked_square_fill_rgba == (220, 38, 38, 0)
        for square_rgb in (theme.light_square_rgb, theme.dark_square_rgb):
            assert contrast_ratio(theme.white_piece_fill_rgb, square_rgb) >= 1.9
            assert contrast_ratio(theme.black_piece_fill_rgb, square_rgb) >= 2.8
