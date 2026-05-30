"""Config regression tests for games darts defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_darts_score_count_defaults_expose_scene_query_and_score_axes() -> None:
    cfg = get_task_group_defaults("games", "darts")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__darts__total_score_option_label",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert bool(generation["balanced_dart_count_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"single_board"}
    assert set(generation["query_id_weights"].keys()) == {
        "total_score",
        "ring_count",
        "threshold_score_count",
    }
    assert set(generation["style_variant_weights"].keys()) == {
        "classic",
        "soft",
        "outlined",
        "league_blue",
        "parchment",
        "neon",
    }
    assert list(generation["count_target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["total_score_dart_count_support"]) == [1]
    assert list(generation["count_query_dart_count_support"]) == [5, 6, 7, 8]
    assert list(generation["target_threshold_support"]) == [20, 25, 30, 40, 50]
    assert int(rendering["board_radius_px"]) > 0
    assert int(rendering["marker_radius_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_darts_v0"
    assert "dartboard" in str(prompt["object_description_single_board"])
    assert "double ring" in str(prompt["scoring_rule_text"])
    assert "outer bull scores 25" in str(prompt["scoring_rule_text"])
    assert "pixel points" in str(prompt["evidence_hint_total_score"])
    assert "pixel points" in str(prompt["evidence_hint_ring_count"])
