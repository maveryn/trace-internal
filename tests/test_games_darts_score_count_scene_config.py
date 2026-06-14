"""Config regression tests for simplified games darts defaults."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_darts_defaults_expose_simplified_scene_style_and_prompt_axes() -> None:
    cfg = get_scene_defaults("games", "darts")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__darts__dart_score_value",
    )

    shared_generation = cfg["generation"]["shared"]
    assert "query_id_weights" not in shared_generation
    assert "balanced_query_id_sampling" not in shared_generation
    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_score_value_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"single_board"}
    assert set(generation["style_variant_weights"].keys()) == {
        "classic",
        "soft",
        "outlined",
        "league_blue",
        "parchment",
        "neon",
    }
    assert list(generation["score_value_support"]) == list(range(1, 21)) + [50]
    assert int(rendering["board_radius_px"]) > 0
    assert int(rendering["marker_radius_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_darts_v1"
    assert str(prompt["task_key"]) == "darts_query"


def test_games_darts_count_task_overrides_are_task_owned() -> None:
    cfg = get_scene_defaults("games", "darts")
    bull_generation, _rendering, _prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__darts__bullseye_membership_count",
    )
    sector_generation, _rendering, _prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__darts__sector_dart_count",
    )

    assert bool(bull_generation["balanced_target_answer_sampling"]) is True
    assert list(bull_generation["count_target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(bull_generation["count_query_dart_count_support"]) == [4, 5, 6, 7]
    assert bool(sector_generation["balanced_target_answer_sampling"]) is True
    assert bool(sector_generation["balanced_distractor_count_sampling"]) is True
    assert bool(sector_generation["balanced_target_sector_sampling"]) is True
    assert list(sector_generation["sector_target_answer_support"]) == [0, 1, 2, 3, 4]
    assert list(sector_generation["sector_distractor_count_support"]) == [1, 2, 3, 4, 5, 6]
    assert list(sector_generation["target_sector_support"]) == [
        20,
        1,
        18,
        4,
        13,
        6,
        10,
        15,
        2,
        17,
        3,
        19,
        7,
        16,
        8,
        11,
        14,
        9,
        12,
        5,
    ]
