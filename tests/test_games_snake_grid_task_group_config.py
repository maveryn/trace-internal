"""Config regression tests for games Snake-grid defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.snake_common import (
    SUPPORTED_SNAKE_QUERY_IDS,
    SUPPORTED_SNAKE_SCENE_VARIANTS,
    SUPPORTED_SNAKE_STYLE_VARIANTS,
)
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_snake_grid_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "snake")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__snake__safe_direction_count",
    )

    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_shortest_food_path_length_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == set(SUPPORTED_SNAKE_SCENE_VARIANTS)
    assert set(generation["query_id_weights"].keys()) == set(SUPPORTED_SNAKE_QUERY_IDS)
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_SNAKE_STYLE_VARIANTS)
    assert list(generation["board_size_support"]) == [7, 8, 9, 10]
    assert list(generation["safe_direction_count_support"]) == [0, 1, 2, 3]
    assert list(generation["shortest_food_path_length_support"]) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert list(generation["planned_move_outcome_support"]) == ["point", "game_over"]
    assert list(generation["obstacle_count_support"]) == [2, 3, 4, 5, 6]
    assert int(rendering["canvas_width"]) == 900
    assert int(rendering["max_board_size_px"]) == 720
    assert str(prompt["bundle_id"]) == "games_snake_v0"
    assert "connected body cells" in str(prompt["object_description_square_grid"]).lower()
    assert "blocked" in str(prompt["shortest_food_path_rule_text"]).lower()
