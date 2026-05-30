"""Config regression tests for games Mini-golf course defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.minigolf_common import (
    SUPPORTED_MINIGOLF_QUERY_IDS,
    SUPPORTED_MINIGOLF_SCENE_VARIANTS,
    SUPPORTED_MINIGOLF_STYLE_VARIANTS,
)
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_minigolf_course_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "minigolf")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__minigolf__first_obstacle_label",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_obstacle_count_sampling"]) is True
    assert bool(generation["balanced_path_option_count_sampling"]) is True
    assert bool(generation["balanced_target_obstacle_label_sampling"]) is True
    assert bool(generation["balanced_target_path_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == set(SUPPORTED_MINIGOLF_SCENE_VARIANTS)
    assert set(generation["query_id_weights"].keys()) == set(SUPPORTED_MINIGOLF_QUERY_IDS)
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_MINIGOLF_STYLE_VARIANTS)
    assert list(generation["obstacle_count_support"]) == [4, 5, 6, 7, 8]
    assert list(generation["path_option_count_support"]) == [4, 5, 6]
    assert list(generation["target_obstacle_label_support"]) == list("ABCDEFGH")
    assert list(generation["target_path_index_support"]) == list(range(6))
    assert int(rendering["canvas_width"]) == 1000
    assert int(rendering["canvas_height"]) == 740
    assert int(rendering["obstacle_radius_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_minigolf_v0"
    assert "straight line" in str(prompt["minigolf_cue_rule_text"]).lower()
    assert "[x, y] pixel point" in str(prompt["evidence_hint_first_obstacle_label"])
    assert "point-pair" in str(prompt["evidence_hint_shot_path_label"])
