"""Config regression tests for games Go group-property defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.style import SUPPORTED_GO_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_go_group_property_count_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "go")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__go__group_liberty_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_player_color_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"open_board", "crowded_board"}
    assert set(generation["query_id_weights"].keys()) == {
        "marked_group_liberty_count",
        "marked_group_adjacent_enemy_count",
        "marked_group_shared_liberty_count",
    }
    assert set(generation["player_color_weights"].keys()) == {"black", "white"}
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_GO_STYLE_VARIANTS)
    assert list(generation["liberty_count_support"]) == [1, 2, 3, 4, 6]
    assert list(generation["adjacent_enemy_count_support"]) == [1, 2, 3, 4, 5, 6]
    assert list(generation["shared_liberty_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["board_size_support"]) == [6, 7, 8]
    assert int(rendering["max_board_size_px"]) > 0
    assert float(rendering["stone_radius_fraction"]) > 0.0
    assert rendering["dynamic_canvas_size_enabled"] is True
    assert int(rendering["canvas_min_width_px"]) >= 560
    assert int(rendering["canvas_min_height_px"]) >= 560
    assert str(prompt["bundle_id"]) == "games_go_v0"
    assert "liberty" in str(prompt["liberty_rule_text"]).lower()
