"""Config regression tests for games bingo defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_bingo_completed_line_count_defaults_expose_scene_query_and_target_axes() -> None:
    cfg = get_task_group_defaults("games", "bingo")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games_bingo_completed_line_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"single_card"}
    assert set(generation["query_variant_weights"].keys()) == {
        "completed_row_count",
        "completed_column_count",
        "completed_straight_line_count",
    }
    assert set(generation["style_variant_weights"].keys()) == {"classic", "soft", "outlined"}
    assert list(generation["completed_row_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["completed_column_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["completed_straight_line_count_support"]) == [0, 1, 2, 3, 4, 5, 6, 7, 8]
    assert int(rendering["card_width_px"]) > 0
    assert int(rendering["card_height_px"]) > 0
    assert int(rendering["number_font_size_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_bingo_v1"
    assert "5 x 5 bingo card" in str(prompt["object_description_single_card"])
    assert "completed rows" in str(prompt["answer_hint_completed_row_count"])
    assert "completed columns" in str(prompt["answer_hint_completed_column_count"])
