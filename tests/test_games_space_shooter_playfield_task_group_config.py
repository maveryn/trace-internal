"""Config regression tests for games Space-shooter defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.space_shooter_common import (
    SUPPORTED_SPACE_SHOOTER_QUERY_VARIANTS,
    SUPPORTED_SPACE_SHOOTER_SCENE_VARIANTS,
    SUPPORTED_SPACE_SHOOTER_STYLE_VARIANTS,
)
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_space_shooter_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "space_shooter")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__space_shooter__clear_shot_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_lane_count_sampling"]) is True
    assert bool(generation["balanced_enemy_count_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == set(SUPPORTED_SPACE_SHOOTER_SCENE_VARIANTS)
    assert set(generation["query_variant_weights"].keys()) == set(SUPPORTED_SPACE_SHOOTER_QUERY_VARIANTS)
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_SPACE_SHOOTER_STYLE_VARIANTS)
    assert list(generation["lane_count_support"]) == [4, 5, 6, 7, 8]
    assert list(generation["enemy_count_support"]) == [10, 11, 12, 13, 14, 15, 16]
    assert list(generation["clear_shot_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["projectile_intercept_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["safe_lane_count_support"]) == [1, 2, 3, 4, 5]
    assert int(rendering["canvas_width"]) == 1060
    assert int(rendering["canvas_height"]) == 820
    assert int(rendering["enemy_width_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_space_shooter_v0"
    assert "bottom lane pads" in str(prompt["space_shooter_lane_rule_text"]).lower()
    assert "bounding boxes" in str(prompt["evidence_hint_safe_lane_count"])
