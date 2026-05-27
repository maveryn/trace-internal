"""Config regression tests for games Platformer level defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.platformer_common import (
    SUPPORTED_PLATFORMER_QUERY_VARIANTS,
    SUPPORTED_PLATFORMER_SCENE_VARIANTS,
    SUPPORTED_PLATFORMER_STYLE_VARIANTS,
)
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_platformer_level_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "platformer")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__platformer__jump_landing_label",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_platform_count_sampling"]) is True
    assert bool(generation["balanced_hazard_count_sampling"]) is True
    assert bool(generation["balanced_target_collectible_count_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == set(SUPPORTED_PLATFORMER_SCENE_VARIANTS)
    assert set(generation["query_variant_weights"].keys()) == set(SUPPORTED_PLATFORMER_QUERY_VARIANTS)
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_PLATFORMER_STYLE_VARIANTS)
    assert list(generation["platform_count_support"]) == [4, 5, 6, 7]
    assert list(generation["hazard_count_support"]) == [4, 5, 6, 7, 8]
    assert list(generation["target_platform_label_support"]) == list("ABCDEFGH")
    assert list(generation["target_collectible_count_support"]) == [2, 3, 4, 5, 6, 7]
    assert int(rendering["canvas_width"]) == 1000
    assert int(rendering["canvas_height"]) == 740
    assert int(rendering["collectible_radius_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_platformer_v0"
    assert "smooth arc" in str(prompt["platformer_short_arc_rule_text"]).lower()
    assert "bounding box" in str(prompt["evidence_hint_jump_landing_label"])
