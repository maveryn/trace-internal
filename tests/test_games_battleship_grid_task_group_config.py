"""Config regression tests for games Battleship-grid defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.style import SUPPORTED_BATTLESHIP_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_battleship_grid_defaults_expose_scene_query_target_board_and_style_axes() -> None:
    cfg = get_task_group_defaults("games", "battleship")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__battleship__ship_status_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_board_size_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"standard_fleet"}
    assert set(generation["query_variant_weights"].keys()) == {"sunk_ship_count", "partial_ship_count"}
    assert float(generation["query_variant_weights"]["sunk_ship_count"]) == 1.0
    assert float(generation["query_variant_weights"]["partial_ship_count"]) == 1.0
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_BATTLESHIP_STYLE_VARIANTS)
    assert list(generation["board_size_support"]) == [8, 9, 10]
    assert list(generation["sunk_ship_count_support"]) == [1, 2, 3, 4]
    assert list(generation["partial_ship_count_support"]) == [1, 2, 3, 4]
    assert int(rendering["canvas_width"]) == 1100
    assert int(rendering["canvas_height"]) == 820
    assert int(rendering["fleet_panel_width_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_battleship_v0"
    assert "Battleship board" in str(prompt["object_description_standard_fleet"])
    assert "placed exactly once" in str(prompt["battleship_rule_text"])
    assert "red hit marker" in str(prompt["answer_hint_sunk_ship_count"])
    assert "not sunk" in str(prompt["answer_hint_partial_ship_count"])
