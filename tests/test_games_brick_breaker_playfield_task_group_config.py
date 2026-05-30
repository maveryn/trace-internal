"""Config regression tests for games Brick-breaker defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.brick_breaker_common import (
    SUPPORTED_BRICK_BREAKER_QUERY_IDS,
    SUPPORTED_BRICK_BREAKER_SCENE_VARIANTS,
    SUPPORTED_BRICK_BREAKER_STYLE_VARIANTS,
)
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_brick_breaker_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "brick_breaker")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__brick_breaker__trajectory_target_label",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_brick_row_sampling"]) is True
    assert bool(generation["balanced_brick_col_sampling"]) is True
    assert bool(generation["balanced_lane_count_sampling"]) is True
    assert bool(generation["balanced_row_remaining_count_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == set(SUPPORTED_BRICK_BREAKER_SCENE_VARIANTS)
    assert set(generation["query_id_weights"].keys()) == set(SUPPORTED_BRICK_BREAKER_QUERY_IDS)
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_BRICK_BREAKER_STYLE_VARIANTS)
    assert len(SUPPORTED_BRICK_BREAKER_STYLE_VARIANTS) >= 5
    assert list(generation["brick_row_count_support"]) == [4, 5]
    assert list(generation["brick_col_count_support"]) == [5, 6]
    assert list(generation["catch_lane_count_support"]) == [5, 6, 7, 8]
    assert list(generation["row_remaining_count_support"]) == [1, 2, 3, 4, 5]
    assert int(rendering["canvas_width"]) == 980
    assert int(rendering["canvas_height"]) == 740
    assert bool(rendering["dynamic_canvas_size_enabled"]) is True
    assert int(rendering["ball_radius_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_brick_breaker_v0"
    assert "dashed arrow" in str(prompt["brick_breaker_motion_rule_text"]).lower()
    assert "bounding box" in str(prompt["evidence_hint_next_hit_label"])
    assert "row" in str(prompt["answer_hint_hit_row_remaining_count"])
