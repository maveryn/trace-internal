"""Config regression tests for games Pac-Man defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import resolve_task_group_section_defaults


def test_games_pacman_defaults_expose_scene_query_answer_and_style_axes() -> None:
    cfg = get_task_group_defaults("games", "pacman")
    generation = resolve_task_group_section_defaults(
        cfg,
        "generation",
        task_id="task_games__pacman__route_pellet_count",
    )
    rendering = resolve_task_group_section_defaults(
        cfg,
        "rendering",
        task_id="task_games__pacman__route_pellet_count",
    )
    prompt = resolve_task_group_section_defaults(
        cfg,
        "prompt",
        task_id="task_games__pacman__route_pellet_count",
    )

    assert set(generation["query_variant_weights"].keys()) == {
        "path_pellet_count",
        "next_item_label",
        "pellet_count_before_ghost",
    }
    assert set(generation["scene_variant_weights"].keys()) == {"compact_maze", "wide_maze"}
    assert set(generation["style_variant_weights"].keys()) == {"classic", "neon", "paper", "terminal", "pastel"}
    assert generation["row_count_support"] == [7, 8, 9]
    assert generation["col_count_support"] == [9, 11, 13]
    assert generation["path_pellet_count_support"] == [1, 2, 3, 4, 5]
    assert generation["pellet_count_before_ghost_support"] == [1, 2, 3, 4, 5]
    assert generation["item_count_support"] == [5, 6]
    assert rendering["ghost_radius_px"] == 18
    assert rendering["canvas_width"] == 980
    assert rendering["canvas_height"] == 760
    assert str(prompt["bundle_id"]) == "games_pacman_v0"
    assert "Pac-Man style maze" in str(prompt["object_description_compact_maze"])
