"""Config regression tests for games 2048-board defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.twenty_forty_eight_common import SUPPORTED_2048_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_2048_board_defaults_expose_query_style_move_and_answer_axes() -> None:
    cfg = get_task_group_defaults("games", "2048")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__2048__merge_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_move_direction_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert bool(generation["balanced_target_label_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"standard_board"}
    assert set(generation["query_id_weights"].keys()) == {
        "merge_count",
        "score_value",
        "max_tile_value",
        "move_result_board_label",
    }
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_2048_STYLE_VARIANTS)
    assert set(generation["move_direction_weights"].keys()) == {"up", "down", "left", "right"}
    assert list(generation["merge_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["score_value_support"]) == [0, 4, 8, 12, 16, 24, 32, 40]
    assert list(generation["max_tile_value_support"]) == [16, 32, 64, 128, 256]
    assert list(generation["result_board_label_support"]) == list("ABCDEF")
    assert list(generation["result_board_option_count_support"]) == [4, 6]
    assert int(rendering["canvas_width"]) == 900
    assert int(rendering["board_size_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_2048_v0"
    assert "2048 board" in str(prompt["object_description_standard_board"])
    assert "slides all tiles" in str(prompt["move_rule_text"])
    assert "candidate result board" in str(prompt["annotation_hint_move_result_board_label"])
