"""Config regression tests for games Go liberty-count defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_go_group_liberty_count_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "go")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games_go_group_liberty_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"open_board", "crowded_board"}
    assert set(generation["query_variant_weights"].keys()) == {
        "marked_black_group_liberty_count",
        "marked_white_group_liberty_count",
    }
    assert list(generation["liberty_count_support"]) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert int(generation["board_size"]) == 7
    assert int(rendering["max_board_size_px"]) > 0
    assert float(rendering["stone_radius_fraction"]) > 0.0
    assert str(prompt["bundle_id"]) == "games_go_v1"
    assert "liberty" in str(prompt["liberty_rule_text"]).lower()
