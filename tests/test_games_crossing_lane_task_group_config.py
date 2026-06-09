"""Config regression tests for games lane-crossing defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.crossing_common import (
    SUPPORTED_CROSSING_QUERY_IDS,
    SUPPORTED_CROSSING_SCENE_VARIANTS,
    SUPPORTED_CROSSING_STYLE_VARIANTS,
)
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_crossing_lane_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "crossing")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__crossing__moving_object_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_lane_count_sampling"]) is True
    assert bool(generation["balanced_row_count_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == set(SUPPORTED_CROSSING_SCENE_VARIANTS)
    assert set(generation["query_id_weights"].keys()) == set(SUPPORTED_CROSSING_QUERY_IDS)
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_CROSSING_STYLE_VARIANTS)
    assert list(generation["lane_count_support"]) == [5, 6, 7, 8]
    assert list(generation["row_count_support"]) == [5, 6, 7]
    assert list(generation["moving_object_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["left_moving_object_count_support"]) == [1, 2, 3, 4, 5, 6]
    assert list(generation["right_moving_object_count_support"]) == [1, 2, 3, 4, 5, 6]
    assert int(generation["moving_object_max_extra_per_row"]) == 1
    assert int(rendering["canvas_width"]) == 1000
    assert int(rendering["canvas_height"]) == 780
    assert int(rendering["vehicle_width_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_crossing_v0"
    assert "tick 1" in str(prompt["crossing_motion_rule_text"]).lower()
    assert "bounding boxes" in str(prompt["annotation_hint_moving_object_count"])
    assert "arrow points left" in str(prompt["annotation_hint_left_moving_object_count"])
    assert "between 1 and 6" in str(prompt["answer_hint_right_moving_object_count"])
