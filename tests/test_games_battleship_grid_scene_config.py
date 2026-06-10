"""Config regression tests for games Battleship-grid defaults."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.games.shared.style import SUPPORTED_BATTLESHIP_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_battleship_grid_defaults_expose_scene_target_board_and_style_axes() -> None:
    cfg = get_scene_defaults("games", "battleship")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__battleship__ship_status_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_board_size_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert bool(generation["balanced_target_ship_answer_pair_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"standard_fleet"}
    assert "query_id_weights" not in generation
    assert "balanced_query_id_sampling" not in generation
    assert bool(generation["balanced_target_ship_id_sampling"]) is True
    assert set(generation["target_ship_id_weights"].keys()) == {
        "line5",
        "line4",
        "line3",
        "square4",
        "elbow3",
    }
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_BATTLESHIP_STYLE_VARIANTS)
    assert list(generation["board_size_support"]) == [8, 9, 10]
    assert list(generation["sunk_ship_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["partial_ship_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["last_ship_cell_option_count_support"]) == [4, 5, 6]
    assert int(rendering["canvas_width"]) == 1100
    assert int(rendering["canvas_height"]) == 820
    assert int(rendering["fleet_panel_width_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_battleship_v0"
    assert "Battleship board" in str(prompt["object_description_standard_fleet"])
    assert "tracking board" in str(prompt["object_description_hidden_fleet"])
    assert "placed exactly once" in str(prompt["battleship_rule_text"])
    assert "red hit marker" in str(prompt["answer_hint_sunk_ship_count"])
    assert "not sunk" in str(prompt["answer_hint_partial_ship_count"])
    assert "JSON object" in str(prompt["annotation_hint_sunk_ship_count"])
    assert "JSON object" in str(prompt["annotation_hint_partial_ship_count"])
    assert "pixel-space points" in str(prompt["annotation_hint_sunk_ship_count"])
    assert "pixel-space" in str(prompt["annotation_hint_partial_ship_count"])
    assert "JSON array" in str(prompt["annotation_hint_named_ship_hit_cell_count"])
    assert "JSON array" in str(prompt["annotation_hint_named_ship_unhit_cell_count"])
    assert "named ship" in str(prompt["answer_hint_named_ship_hit_cell_count"])
    assert "named ship" in str(prompt["answer_hint_named_ship_unhit_cell_count"])
    assert "selected option" in str(prompt["answer_hint_last_ship_cell_label"])
    assert "[x, y]" in str(prompt["annotation_hint_sunk_ship_count"])
    assert "[x, y]" in str(prompt["annotation_hint_partial_ship_count"])
    assert "[x, y]" in str(prompt["annotation_hint_named_ship_hit_cell_count"])
    assert "[x, y]" in str(prompt["annotation_hint_named_ship_unhit_cell_count"])
    assert "[x, y]" in str(prompt["annotation_hint_last_ship_cell_label"])
    assert "empty object" in str(prompt["annotation_hint_sunk_ship_count"])
    assert "empty object" in str(prompt["annotation_hint_partial_ship_count"])
    assert "empty array" in str(prompt["annotation_hint_named_ship_hit_cell_count"])
    assert "empty array" in str(prompt["annotation_hint_named_ship_unhit_cell_count"])
