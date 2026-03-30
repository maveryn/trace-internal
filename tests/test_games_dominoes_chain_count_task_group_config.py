"""Config regression tests for games dominoes defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_dominoes_chain_count_defaults_expose_scene_query_and_candidate_axes() -> None:
    cfg = get_task_group_defaults("games", "dominoes")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games_dominoes_chain_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert bool(generation["balanced_candidate_count_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"single_row", "two_row"}
    assert set(generation["query_variant_weights"].keys()) == {
        "matching_end_count",
        "higher_sum_than_reference_count",
        "sum_to_target_count",
        "double_count",
    }
    assert set(generation["style_variant_weights"].keys()) == {"classic", "soft", "outlined"}
    assert list(generation["matching_end_target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["higher_sum_target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["sum_to_target_answer_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["double_target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["single_row_candidate_count_support"]) == [7, 8, 9]
    assert list(generation["two_row_candidate_count_support"]) == [10, 11, 12]
    assert list(generation["sum_target_total_support"]) == [2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert int(rendering["tile_width_px"]) > 0
    assert int(rendering["tile_height_px"]) > 0
    assert int(rendering["reference_tag_font_size_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_dominoes_v1"
    assert "domino chain" in str(prompt["object_description_single_row"])
    assert "open right end" in str(prompt["evidence_hint_matching_end_count"])
    assert "doubles" in str(prompt["answer_hint_double_count"])
