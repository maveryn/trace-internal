"""Config regression tests for games Snakes and Ladders defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.snakes_ladders_common import SUPPORTED_SNAKES_LADDERS_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_snakes_ladders_defaults_expose_query_style_and_answer_axes() -> None:
    cfg = get_task_group_defaults("games", "snakes_ladders")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__snakes_ladders__best_roll_value",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_board_side_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert bool(generation["balanced_die_value_sampling"]) is True
    assert bool(generation["balanced_horizon_roll_count_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"standard_board"}
    assert set(generation["query_id_weights"].keys()) == {
        "move_outcome_value",
        "best_roll_value",
    }
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_SNAKES_LADDERS_STYLE_VARIANTS)
    assert list(generation["board_side_support"]) == [5, 6, 7]
    assert float(generation["move_outcome_jump_probability"]) == 0.30
    assert list(generation["best_roll_value_support"]) == list(range(14, 50))
    assert list(generation["horizon_roll_count_support"]) == [1, 2]
    assert int(rendering["canvas_width"]) == 1120
    assert int(rendering["board_size_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_snakes_ladders_v0"
    assert "Snakes and Ladders board" in str(prompt["object_description_standard_board"])
    assert "one bounding box" in str(prompt["evidence_hint_best_roll_value"])
