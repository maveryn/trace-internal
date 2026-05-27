"""Config regression tests for games cards defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_cards_hand_count_defaults_expose_scene_query_and_card_axes() -> None:
    cfg = get_task_group_defaults("games", "cards")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__cards__reference_condition_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert bool(generation["balanced_card_count_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"multi_row"}
    assert set(generation["query_id_weights"].keys()) == {
        "same_suit_as_reference_count",
        "higher_than_reference_count",
        "exact_triple_count",
        "longest_run_length",
    }
    assert set(generation["style_variant_weights"].keys()) == {"classic", "soft", "outlined"}
    assert list(generation["same_suit_target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["higher_rank_target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["exact_triple_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["longest_run_length_support"]) == [2, 3, 4, 5, 6]
    assert list(generation["card_count_support"]) == list(range(16, 41))
    assert bool(generation["balanced_option_count_sampling"]) is True
    assert list(generation["blackjack_hand_count_support"]) == [4, 5, 6]
    assert list(generation["blackjack_cards_per_hand_support"]) == [3, 4]
    assert list(generation["poker_hand_count_support"]) == [4, 5, 6]
    assert list(generation["trick_player_count_support"]) == [4, 5, 6]
    assert int(rendering["card_width_px"]) > 0
    assert int(rendering["card_height_px"]) > 0
    assert int(rendering["max_cards_per_row"]) == 8
    assert int(rendering["group_label_font_size_px"]) > 0
    assert int(rendering["continuation_font_size_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_cards_v0"
    assert "multiple rows" in str(prompt["object_description_multi_row"])
    assert "blackjack" in str(prompt["object_description_blackjack_multi_hand"])
    assert "poker" in str(prompt["answer_hint_poker_best_hand_label"])
    assert "same suit" in str(prompt["evidence_hint_same_suit_as_reference_count"])
    assert "exactly three" in str(prompt["answer_hint_exact_triple_count"])
