"""Config regression tests for games Bowling lane defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.bowling_common import (
    SUPPORTED_BOWLING_QUERY_IDS,
    SUPPORTED_BOWLING_SCENE_VARIANTS,
    SUPPORTED_BOWLING_STYLE_VARIANTS,
)
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_bowling_lane_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "bowling")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__bowling__first_pin_hit_label",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_visible_pin_count_sampling"]) is True
    assert bool(generation["balanced_path_option_count_sampling"]) is True
    assert bool(generation["balanced_target_pin_sampling"]) is True
    assert bool(generation["balanced_target_path_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == set(SUPPORTED_BOWLING_SCENE_VARIANTS)
    assert set(generation["query_id_weights"].keys()) == set(SUPPORTED_BOWLING_QUERY_IDS)
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_BOWLING_STYLE_VARIANTS)
    assert len(SUPPORTED_BOWLING_STYLE_VARIANTS) >= 5
    assert list(generation["visible_pin_count_support"]) == [4, 5, 6, 7, 8, 9]
    assert list(generation["path_option_count_support"]) == [4, 5, 6]
    assert list(generation["target_pin_index_support"]) == list(range(10))
    assert list(generation["target_path_index_support"]) == list(range(6))
    assert int(rendering["canvas_width"]) == 1000
    assert int(rendering["canvas_height"]) == 740
    assert int(rendering["pin_radius_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_bowling_v0"
    assert "dashed arrow" in str(prompt["bowling_motion_rule_text"]).lower()
    assert "extend each numbered dashed path" in str(prompt["spare_path_rule_text"]).lower()
    assert "bounding box" in str(prompt["annotation_hint_first_pin_hit_label"])
    assert "point-pair" in str(prompt["annotation_hint_spare_path_label"])
