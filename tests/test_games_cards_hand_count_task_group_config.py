"""Config regression tests for games cards defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_cards_hand_count_defaults_expose_scene_query_and_card_axes() -> None:
    cfg = get_task_group_defaults("games", "cards")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__cards__same_suit_as_reference_count",
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
    assert set(generation["style_variant_weights"].keys()) == {"classic", "soft", "outlined", "ivory", "slate"}
    assert list(generation["same_suit_target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert bool(generation["same_suit_order_by_suit"]) is False
    assert list(generation["higher_rank_target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert bool(generation["higher_rank_order_by_rank"]) is False
    assert list(generation["exact_triple_count_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["longest_run_length_support"]) == [2, 3, 4, 5, 6]
    assert list(generation["card_count_support"]) == list(range(16, 41))
    assert bool(generation["balanced_option_count_sampling"]) is True
    assert list(generation["blackjack_hand_count_support"]) == [4, 6]
    assert list(generation["blackjack_cards_per_hand_support"]) == [3, 4]
    assert list(generation["poker_hand_count_support"]) == [4, 6]
    assert bool(generation["balanced_poker_winning_category_sampling"]) is True
    assert set(generation["poker_winning_category_weights"]) >= {
        "straight",
        "flush",
        "full_house",
        "four_of_a_kind",
        "straight_flush",
    }
    assert list(generation["poker_draw_candidate_count_support"]) == [4, 6]
    assert bool(generation["balanced_poker_draw_target_category_sampling"]) is True
    assert set(generation["poker_draw_target_category_weights"]) >= {
        "straight",
        "flush",
        "full_house",
        "four_of_a_kind",
        "straight_flush",
    }
    assert bool(generation["balanced_missing_card_query_id_sampling"]) is True
    assert set(generation["missing_card_query_id_weights"]) == {
        "missing_flush_card_label",
        "missing_straight_card_label",
        "missing_full_house_card_label",
        "missing_three_of_kind_card_label",
    }
    assert list(generation["missing_card_candidate_count_support"]) == [4, 6]
    assert list(generation["trick_player_count_support"]) == [4, 6]
    assert list(generation["trick_play_candidate_count_support"]) == [4, 6]
    assert list(generation["trick_play_played_count_support"]) == [3, 4]
    assert set(generation["trick_play_trump_mode_weights"]) == {"no_trump", "with_trump"}
    assert int(rendering["card_width_px"]) > 0
    assert int(rendering["card_height_px"]) > 0
    assert int(rendering["max_cards_per_row"]) == 8
    assert int(rendering["group_label_font_size_px"]) > 0
    assert int(rendering["continuation_font_size_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_cards_v0"
    assert "multiple rows" in str(prompt["object_description_multi_row"])
    assert "blackjack" in str(prompt["object_description_blackjack_multi_hand"])
    assert "poker" in str(prompt["answer_hint_poker_best_hand_label"])
    assert "candidate" in str(prompt["answer_hint_poker_draw_card_label"])
    assert "candidate" in str(prompt["answer_hint_trick_winning_play_label"])
    assert "candidate" in str(prompt["answer_hint_missing_flush_card_label"])
    assert "selected candidate card" in str(prompt["annotation_hint_missing_full_house_card_label"])
    assert "same suit" in str(prompt["annotation_hint_same_suit_as_reference_count"])
    assert "object mapping" in str(prompt["annotation_hint_exact_triple_count"])
    assert "exactly three" in str(prompt["answer_hint_exact_triple_count"])
