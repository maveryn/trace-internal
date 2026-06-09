"""Config regression tests for puzzle Sudoku-grid defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.style import SUPPORTED_SUDOKU_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_puzzles_sudoku_grid_defaults_present() -> None:
    cfg = get_task_group_defaults("puzzles", "sudoku")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_puzzles__sudoku__marked_cell_value",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_unit_type_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"sparse_grid", "filled_grid"}
    assert set(generation["query_id_weights"].keys()) == {
        "marked_cell_value",
        "marked_cell_candidate_count",
        "unit_missing_digits_count",
        "repeated_digit_count",
    }
    assert set(generation["unit_type_weights"].keys()) == {"row", "column", "box"}
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_SUDOKU_STYLE_VARIANTS)
    assert list(generation["marked_cell_value_support"]) == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert list(generation["marked_cell_candidate_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["unit_missing_digits_count_support"]) == [2, 3, 4, 5, 6]
    assert list(generation["repeated_digit_count_support"]) == [0, 1, 2, 3, 4]
    assert int(rendering["max_board_size_px"]) > 0
    assert int(rendering["marked_cell_outline_width_px"]) > 0
    assert str(prompt["bundle_id"]) == "puzzles_sudoku_v0"
    assert "Sudoku" in str(prompt["object_description_sparse_grid"])
    assert "bounding boxes" in str(prompt["annotation_hint_marked_cell_value"])
