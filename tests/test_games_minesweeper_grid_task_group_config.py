"""Config regression tests for games Minesweeper-grid defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.style import SUPPORTED_MINESWEEPER_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_minesweeper_grid_defaults_expose_scene_query_target_and_board_axes() -> None:
    cfg = get_task_group_defaults("games", "minesweeper")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__minesweeper__forced_cell_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_board_size_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"open_grid", "mixed_grid"}
    assert set(generation["query_variant_weights"].keys()) == {
        "forced_mine_count",
        "forced_safe_count",
        "satisfied_clue_count",
    }
    assert float(generation["query_variant_weights"]["forced_mine_count"]) == 1.0
    assert float(generation["query_variant_weights"]["forced_safe_count"]) == 1.0
    assert float(generation["query_variant_weights"]["satisfied_clue_count"]) == 1.0
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_MINESWEEPER_STYLE_VARIANTS)
    assert list(generation["board_size_support"]) == [4, 5, 6, 7, 8]
    assert list(generation["forced_cell_board_size_support"]) == [4, 5]
    assert list(generation["forced_mine_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["forced_safe_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["satisfied_clue_count_support"]) == [1, 2, 3, 4, 5]
    assert int(rendering["canvas_width"]) == 900
    assert int(rendering["canvas_height"]) == 900
    assert int(rendering["max_board_size_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_minesweeper_v0"
    assert "Minesweeper grid" in str(prompt["object_description_open_grid"])
    assert "eight neighboring cells" in str(prompt["minesweeper_rule_text"])
    assert "must be mines" in str(prompt["answer_hint_forced_mine_count"])
    assert "must be safe" in str(prompt["answer_hint_forced_safe_count"])
    assert "adjacent flags" in str(prompt["answer_hint_satisfied_clue_count"])
