"""Config regression tests for games darts defaults."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_darts_defaults_expose_scene_style_and_prompt_axes() -> None:
    cfg = get_scene_defaults("games", "darts")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__darts__total_score_option_label",
    )

    shared_generation = cfg["generation"]["shared"]
    assert "query_id_weights" not in shared_generation
    assert "balanced_query_id_sampling" not in shared_generation
    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_dart_count_sampling"]) is True
    assert bool(generation["balanced_score_option_count_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"single_board"}
    assert set(generation["style_variant_weights"].keys()) == {
        "classic",
        "soft",
        "outlined",
        "league_blue",
        "parchment",
        "neon",
    }
    assert list(generation["total_score_dart_count_support"]) == [1]
    assert list(generation["score_option_count_support"]) == [4, 6]
    assert int(rendering["board_radius_px"]) > 0
    assert int(rendering["marker_radius_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_darts_v1"


def test_games_darts_count_task_overrides_are_task_owned() -> None:
    cfg = get_scene_defaults("games", "darts")
    ring_generation, _rendering, _prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__darts__ring_count",
    )
    threshold_generation, _rendering, _prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__darts__threshold_score_count",
    )

    assert bool(ring_generation["balanced_target_answer_sampling"]) is True
    assert bool(ring_generation["balanced_target_ring_sampling"]) is True
    assert list(ring_generation["count_target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(ring_generation["count_query_dart_count_support"]) == [5, 6, 7, 8]
    assert set(ring_generation["target_ring_weights"].keys()) == {"single", "double", "triple", "bull"}
    assert bool(threshold_generation["balanced_target_answer_sampling"]) is True
    assert bool(threshold_generation["balanced_target_threshold_sampling"]) is True
    assert list(threshold_generation["count_target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(threshold_generation["count_query_dart_count_support"]) == [5, 6, 7, 8]
    assert list(threshold_generation["target_threshold_support"]) == [20, 25, 30, 40, 50]
