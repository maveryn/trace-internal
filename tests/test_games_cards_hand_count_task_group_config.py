"""Config regression tests for games cards defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_cards_hand_count_defaults_expose_scene_query_and_card_axes() -> None:
    cfg = get_task_group_defaults("games", "cards")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games_cards_hand_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert bool(generation["balanced_card_count_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"single_row", "two_row"}
    assert set(generation["query_variant_weights"].keys()) == {
        "same_suit_as_reference_count",
        "higher_than_reference_count",
        "pair_count",
        "longest_run_length",
    }
    assert set(generation["style_variant_weights"].keys()) == {"classic", "soft", "outlined"}
    assert list(generation["same_suit_target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["higher_rank_target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["pair_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["longest_run_length_support"]) == [2, 3, 4, 5, 6]
    assert list(generation["single_row_card_count_support"]) == [7, 8, 9, 10]
    assert list(generation["two_row_card_count_support"]) == [11, 12, 13, 14]
    assert int(rendering["card_width_px"]) > 0
    assert int(rendering["card_height_px"]) > 0
    assert int(rendering["continuation_font_size_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_cards_v1"
    assert "single row" in str(prompt["object_description_single_row"])
    assert "same suit" in str(prompt["evidence_hint_same_suit_as_reference_count"])
    assert "exactly twice" in str(prompt["answer_hint_pair_count"])
