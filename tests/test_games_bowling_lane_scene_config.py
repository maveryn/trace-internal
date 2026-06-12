"""Config regression tests for games Bowling lane defaults."""

from __future__ import annotations

from trace.tasks.games.bowling.shared.common import (
    SUPPORTED_BOWLING_SCENE_VARIANTS,
    SUPPORTED_BOWLING_STYLE_VARIANTS,
)
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults


def test_games_bowling_lane_defaults_present() -> None:
    first_pin_generation, rendering, prompt = load_scene_generation_rendering_prompt_defaults(
        "games",
        "bowling",
        task_id="task_games__bowling__first_pin_hit_label",
    )
    spare_path_generation, _spare_rendering, spare_prompt = load_scene_generation_rendering_prompt_defaults(
        "games",
        "bowling",
        task_id="task_games__bowling__spare_path_label",
    )

    assert bool(first_pin_generation["balanced_scene_variant_sampling"]) is True
    assert bool(first_pin_generation["balanced_style_variant_sampling"]) is True
    assert bool(first_pin_generation["balanced_visible_pin_count_sampling"]) is True
    assert bool(first_pin_generation["balanced_target_pin_sampling"]) is True
    assert "query_id_weights" not in first_pin_generation
    assert "balanced_query_id_sampling" not in first_pin_generation
    assert set(first_pin_generation["scene_variant_weights"].keys()) == set(SUPPORTED_BOWLING_SCENE_VARIANTS)
    assert set(first_pin_generation["style_variant_weights"].keys()) == set(SUPPORTED_BOWLING_STYLE_VARIANTS)
    assert len(SUPPORTED_BOWLING_STYLE_VARIANTS) >= 5
    assert list(first_pin_generation["visible_pin_count_support"]) == [4, 5, 6, 7, 8, 9]
    assert list(first_pin_generation["target_pin_index_support"]) == list(range(10))

    assert bool(spare_path_generation["balanced_path_option_count_sampling"]) is True
    assert bool(spare_path_generation["balanced_target_path_sampling"]) is True
    assert "query_id_weights" not in spare_path_generation
    assert "balanced_query_id_sampling" not in spare_path_generation
    assert list(spare_path_generation["path_option_count_support"]) == [4, 5, 6]
    assert list(spare_path_generation["target_path_index_support"]) == list(range(6))

    assert int(rendering["canvas_width"]) == 1000
    assert int(rendering["canvas_height"]) == 740
    assert int(rendering["pin_radius_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_bowling_v1"
    assert str(spare_prompt["bundle_id"]) == "games_bowling_v1"
    assert {"bundle_id", "scene_key", "task_key"}.issubset(prompt.keys())
    assert "bowling_motion_rule_text" not in prompt
    assert "spare_path_rule_text" not in prompt
    assert "annotation_hint_first_pin_hit_label" not in prompt
    assert "annotation_hint_spare_path_label" not in prompt
