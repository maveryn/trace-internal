"""Config regression tests for games Pool-table scene defaults."""

from __future__ import annotations

from trace.tasks.games.shared.style import SUPPORTED_POOL_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults


def test_games_pool_table_defaults_present() -> None:
    generation, rendering, prompt = load_scene_generation_rendering_prompt_defaults(
        "games",
        "pool",
        task_id="task_games__pool__group_ball_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_object_ball_count_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"standard_table"}
    assert set(generation["query_id_weights"].keys()) == {
        "current_group_ball_count",
        "blocking_ball_count",
    }
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_POOL_STYLE_VARIANTS)
    assert list(generation["object_ball_count_support"]) == [7, 8, 9, 10]
    assert list(generation["current_group_ball_count_support"]) == [2, 3, 4, 5, 6]
    assert list(generation["blocking_ball_count_support"]) == [0, 1, 2, 3, 4]
    assert int(rendering["canvas_width"]) == 1120
    assert int(rendering["canvas_height"]) == 760
    assert int(rendering["ball_radius_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_pool_v0"
    assert "two straight segments" in str(prompt["marked_shot_rule_text"])
    assert "current player" in str(prompt["answer_hint_current_group_ball_count"])
    assert "pixel point" in str(prompt["annotation_hint_blocking_ball_count"])
