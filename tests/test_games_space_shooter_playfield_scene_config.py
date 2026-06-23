"""Config regression tests for games Space-shooter defaults."""

from __future__ import annotations

import json
from pathlib import Path

from trace.core.scene_config import get_scene_defaults
from trace.tasks.games.space_shooter.shared.state import (
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_STYLE_VARIANTS,
)
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_space_shooter_defaults_present() -> None:
    cfg = get_scene_defaults("games", "space_shooter")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__space_shooter__clear_shot_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_lane_count_sampling"]) is True
    assert bool(generation["balanced_enemy_count_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert "query_id_weights" not in generation
    assert set(generation["scene_variant_weights"].keys()) == set(SUPPORTED_SCENE_VARIANTS)
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_STYLE_VARIANTS)
    assert list(generation["lane_count_support"]) == [4, 5, 6, 7, 8]
    assert list(generation["enemy_count_support"]) == [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    assert list(generation["clear_shot_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["clear_shot_score_enemy_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["clear_shot_score_value_support"]) == [1, 2, 3, 5, 10]
    assert list(generation["projectile_intercept_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["safe_lane_count_support"]) == [1, 2, 3, 4, 5]
    assert int(rendering["canvas_width"]) == 1060
    assert int(rendering["canvas_height"]) == 820
    assert int(rendering["enemy_width_px"]) > 0
    assert int(rendering["projectile_width_px"]) == 28
    assert set(generation["style_variant_weights"].keys()) == {
        "neon",
        "deep_space",
        "vector",
        "amber",
        "terminal",
    }
    assert str(prompt["bundle_id"]) == "games_space_shooter_v1"
    bundle = json.loads(Path("prompts/games/space_shooter/games_space_shooter_v1.json").read_text(encoding="utf-8"))
    code_defaults = bundle["code_prompt_defaults"]
    assert "bottom lane pads" in str(code_defaults["space_shooter_lane_rule_text"]).lower()
    assert "total score" in str(code_defaults["answer_hint_clear_shot_score_value"]).lower()
    assert "bounding boxes" in str(code_defaults["annotation_hint_safe_lane_count"])
