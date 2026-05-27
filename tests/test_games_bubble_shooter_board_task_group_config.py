"""Config regression tests for games Bubble-shooter defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import resolve_task_group_section_defaults


def test_games_bubble_shooter_defaults_expose_scene_query_answer_and_style_axes() -> None:
    cfg = get_task_group_defaults("games", "bubble_shooter")
    generation = resolve_task_group_section_defaults(
        cfg,
        "generation",
        task_id="task_games__bubble_shooter__shot_effect_count",
    )
    rendering = resolve_task_group_section_defaults(
        cfg,
        "rendering",
        task_id="task_games__bubble_shooter__shot_effect_count",
    )
    prompt = resolve_task_group_section_defaults(
        cfg,
        "prompt",
        task_id="task_games__bubble_shooter__shot_effect_count",
    )

    assert set(generation["query_variant_weights"].keys()) == {"pop_count", "drop_count", "pop_color_label"}
    assert set(generation["scene_variant_weights"].keys()) == {"open_pack", "dense_pack"}
    assert set(generation["style_variant_weights"].keys()) == {"classic", "pastel", "neon", "paper", "arcade"}
    assert generation["row_count_support"] == [7, 8, 9]
    assert generation["col_count_support"] == [8, 9, 10]
    assert generation["pop_count_support"] == [0, 2, 3, 4, 5]
    assert generation["drop_count_support"] == [0, 1, 2, 3, 4]
    assert generation["count_query_max_row_count"] == 7
    assert generation["option_count_support"] == [4, 5, 6]
    assert rendering["canvas_width"] == 980
    assert rendering["canvas_height"] == 820
    assert str(prompt["bundle_id"]) == "games_bubble_shooter_v0"
    assert "close-packed" in str(prompt["object_description_open_pack"])
