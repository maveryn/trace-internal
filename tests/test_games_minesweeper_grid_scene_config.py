"""Config regression tests for games Minesweeper-grid defaults."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.games.shared.style import SUPPORTED_MINESWEEPER_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_minesweeper_grid_defaults_expose_scene_query_target_and_board_axes() -> None:
    cfg = get_scene_defaults("games", "minesweeper")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__minesweeper__forced_cell_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_board_size_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"open_grid", "mixed_grid"}
    assert set(generation["query_id_weights"].keys()) == {
        "forced_mine_count",
        "forced_safe_count",
        "remaining_mine_count",
        "reveal_outcome_label",
        "satisfied_clue_count",
    }
    assert float(generation["query_id_weights"]["forced_mine_count"]) == 1.0
    assert float(generation["query_id_weights"]["forced_safe_count"]) == 1.0
    assert float(generation["query_id_weights"]["remaining_mine_count"]) == 1.0
    assert float(generation["query_id_weights"]["reveal_outcome_label"]) == 1.0
    assert float(generation["query_id_weights"]["satisfied_clue_count"]) == 1.0
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_MINESWEEPER_STYLE_VARIANTS)
    assert list(generation["board_size_support"]) == [4, 5, 6, 7, 8]
    assert list(generation["forced_cell_board_size_support"]) == [4, 5]
    assert list(generation["reveal_outcome_board_size_support"]) == [5, 6, 7, 8]
    assert list(generation["forced_mine_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["forced_safe_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["remaining_mine_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["reveal_outcome_support"]) == [0, 1, 2, 3, 4, 5, 6, 7, 8]
    assert list(generation["satisfied_clue_count_support"]) == [1, 2, 3, 4, 5]
    assert int(rendering["canvas_width"]) == 900
    assert int(rendering["canvas_height"]) == 900
    assert int(rendering["max_board_size_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_minesweeper_v0"
    assert "Minesweeper grid" in str(prompt["object_description_open_grid"])
    assert "eight neighboring cells" in str(prompt["minesweeper_rule_text"])
    assert "must be mines" in str(prompt["answer_hint_forced_mine_count"])
    assert "must be safe" in str(prompt["answer_hint_forced_safe_count"])
    assert "additional mines" in str(prompt["answer_hint_remaining_mine_count"])
    assert "marked opened number cell" in str(prompt["annotation_hint_remaining_mine_count"])
    assert "option letter" in str(prompt["answer_hint_reveal_outcome_label"])
    assert "target_cell" in str(prompt["annotation_hint_reveal_outcome_label"])
    assert "adjacent flags" in str(prompt["answer_hint_satisfied_clue_count"])
