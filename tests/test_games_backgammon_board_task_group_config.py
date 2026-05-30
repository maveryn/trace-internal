"""Config regression tests for games Backgammon defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.backgammon_common import BACKGAMMON_QUERY_IDS, BACKGAMMON_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_backgammon_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "backgammon")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__backgammon__destination_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_active_player_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"standard_board"}
    assert set(generation["query_id_weights"].keys()) == set(BACKGAMMON_QUERY_IDS)
    assert set(generation["style_variant_weights"].keys()) == set(BACKGAMMON_STYLE_VARIANTS)
    assert set(generation["active_player_weights"].keys()) == {"black", "white"}
    assert list(generation["legal_count_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["hit_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["blocked_count_support"]) == [0, 1, 2, 3, 4]
    assert int(rendering["canvas_width"]) == 1000
    assert int(rendering["canvas_height"]) == 720
    assert float(rendering["unit_size_scale_min"]) == 0.5
    assert float(rendering["unit_size_scale_max"]) == 1.0
    assert bool(rendering["dynamic_canvas_size_enabled"]) is True
    assert int(rendering["checker_radius_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_backgammon_v0"
    assert "active-player point" in str(prompt["backgammon_rule_text"])
    assert "Count each distinct destination number once" in str(prompt["backgammon_rule_text"])
    assert "bounding boxes" in str(prompt["evidence_hint_legal_move_count"])
