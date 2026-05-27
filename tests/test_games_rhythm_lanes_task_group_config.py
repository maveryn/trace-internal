"""Config regression tests for games Rhythm-lanes defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.rhythm_common import (
    SUPPORTED_RHYTHM_QUERY_VARIANTS,
    SUPPORTED_RHYTHM_SCENE_VARIANTS,
    SUPPORTED_RHYTHM_STYLE_VARIANTS,
)
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_rhythm_lanes_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "rhythm")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__rhythm__hit_window_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_lane_count_sampling"]) is True
    assert bool(generation["balanced_row_count_sampling"]) is True
    assert bool(generation["balanced_beat_window_sampling"]) is True
    assert bool(generation["balanced_hit_count_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == set(SUPPORTED_RHYTHM_SCENE_VARIANTS)
    assert set(generation["query_variant_weights"].keys()) == set(SUPPORTED_RHYTHM_QUERY_VARIANTS)
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_RHYTHM_STYLE_VARIANTS)
    assert list(generation["lane_count_support"]) == [5, 6, 7, 8]
    assert list(generation["row_count_support"]) == [10, 11, 12, 13, 14]
    assert list(generation["beat_window_support"]) == [5, 6, 7]
    assert list(generation["hit_count_support"]) == [1, 2, 3, 4, 5]
    assert int(rendering["canvas_width"]) == 760
    assert int(rendering["canvas_height"]) == 900
    assert str(prompt["bundle_id"]) == "games_rhythm_v0"
    assert "one row per beat" in str(prompt["rhythm_motion_rule_text"])
    assert "bounding boxes" in str(prompt["evidence_hint_lane_hit_count"])
