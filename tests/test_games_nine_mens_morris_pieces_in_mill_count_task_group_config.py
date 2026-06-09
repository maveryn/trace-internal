"""Config regression tests for games nine-men's-morris defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.games.shared.style import SUPPORTED_NINE_MENS_MORRIS_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_nine_mens_morris_pieces_in_mill_count_defaults_present() -> None:
    cfg = get_task_group_defaults("games", "nine_mens_morris")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__nine_mens_morris__pieces_in_mill_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"single_board"}
    assert set(generation["query_id_weights"].keys()) == {
        "all_pieces_in_mill_count",
        "white_mill_completion_point_count",
        "black_mill_completion_point_count",
    }
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_NINE_MENS_MORRIS_STYLE_VARIANTS)
    assert list(generation["all_pieces_in_mill_count_support"]) == [0, 3, 5, 6, 7, 8, 9]
    assert list(generation["white_mill_completion_point_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["black_mill_completion_point_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert int(rendering["board_width_px"]) > 0
    assert int(rendering["piece_radius_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_nine_mens_morris_v0"
    assert "mill" in str(prompt["mill_rule_text"]).lower()
    assert "empty point" in str(prompt["answer_hint_white_mill_completion_point_count"]).lower()
    assert "white piece" in str(prompt["annotation_hint_white_mill_completion_point_count"]).lower()
    assert "black piece" in str(prompt["annotation_hint_black_mill_completion_point_count"]).lower()
