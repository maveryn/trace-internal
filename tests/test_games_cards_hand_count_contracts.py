"""Contract tests for the games cards hand-count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.registry import create_task
from trace.tasks.games.cards.hand_count import (
    GamesCardsHandCountTask,
    GamesCardsHigherThanReferenceCountTask,
    GamesCardsSameSuitAsReferenceCountTask,
    SUPPORTED_MISSING_CARD_QUERY_IDS,
    _poker_score,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer", "expected_annotation_count"),
    (
        (
            {
                "query_id": "same_suit_as_reference_count",
                "target_answer": 3,
                "card_count": 16,
            },
            3,
            3,
        ),
        (
            {
                "query_id": "higher_than_reference_count",
                "target_answer": 4,
                "card_count": 17,
            },
            4,
            4,
        ),
        (
                {
                    "query_id": "exact_triple_count",
                    "target_answer": 3,
                    "card_count": 22,
                },
            3,
            9,
        ),
        (
            {
                "query_id": "longest_run_length",
                "target_answer": 5,
                "card_count": 40,
            },
            5,
            5,
        ),
    ),
)
def test_games_cards_hand_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
    expected_annotation_count: int,
) -> None:
    out = GamesCardsHandCountTask().generate(25001, params=params, max_attempts=40)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    if str(params["query_id"]) == "exact_triple_count":
        assert out.annotation_gt.type == "keyed_bbox_set_map"
        assert len(out.annotation_gt.value) == int(expected_answer)
        assert sum(len(value) for value in out.annotation_gt.value.values()) == int(expected_annotation_count)
    else:
        assert out.annotation_gt.type == "bbox_set"
        assert len(out.annotation_gt.value) == int(expected_annotation_count)
    assert trace["query_spec"]["params"]["query_id"] == out.query_id
    assert int(execution["target_answer"]) == int(expected_answer)
    if str(params["query_id"]) == "exact_triple_count":
        assert trace["projected_annotation"]["keyed_bbox_set_map"] == out.annotation_gt.value
        assert trace["projected_annotation"]["pixel_keyed_bbox_set_map"] == out.annotation_gt.value
    else:
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert len(execution["annotation_entity_ids"]) == int(expected_annotation_count)


def test_games_cards_hand_count_exact_triple_count_uses_exact_triples_only() -> None:
    out = GamesCardsHandCountTask().generate(
        25017,
        params={
            "query_id": "exact_triple_count",
            "target_answer": 4,
            "card_count": 22,
        },
        max_attempts=40,
    )
    specs = out.trace_payload["execution_trace"]["card_specs"]
    rank_counts: dict[int, int] = {}
    annotation_ids = set(out.trace_payload["execution_trace"]["annotation_entity_ids"])
    annotation_rank_card_ids = out.trace_payload["execution_trace"]["annotation_rank_card_ids"]
    for spec in specs:
        rank_counts[int(spec["rank_value"])] = rank_counts.get(int(spec["rank_value"]), 0) + 1
    assert sum(1 for count in rank_counts.values() if int(count) == 3) == 4
    for spec in specs:
        in_annotation = str(spec["card_id"]) in annotation_ids
        assert in_annotation == (int(rank_counts[int(spec["rank_value"])]) == 3)
    assert set(annotation_rank_card_ids) == {
        str(spec["rank_label"])
        for spec in specs
        if int(rank_counts[int(spec["rank_value"])]) == 3
    }
    assert all(len(card_ids) == 3 for card_ids in annotation_rank_card_ids.values())
    assert out.annotation_gt.type == "keyed_bbox_set_map"
    assert set(out.annotation_gt.value) == set(annotation_rank_card_ids)


def test_games_cards_hand_count_multi_row_run_emits_continuation_cue() -> None:
    out = GamesCardsHandCountTask().generate(
        25021,
        params={
            "query_id": "longest_run_length",
            "target_answer": 6,
            "card_count": 40,
        },
        max_attempts=40,
    )
    render_map = out.trace_payload["render_map"]
    assert render_map["continuation_cue_bbox_px"] is not None
    assert int(render_map["row_count"]) == 5
    assert all(len(row) <= 8 for row in render_map["row_card_ids"])
    assert "continue" in out.prompt.lower()
    assert "top row" in out.prompt.lower()


def test_games_cards_hand_count_is_deterministic() -> None:
    params = {
        "query_id": "higher_than_reference_count",
        "target_answer": 5,
        "card_count": 26,
    }
    task = GamesCardsHandCountTask()
    out_a = task.generate(25031, params=params, max_attempts=40)
    out_b = task.generate(25031, params=params, max_attempts=40)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def _reference_condition_task(query_id: str):
    if query_id == "same_suit_as_reference_count":
        return GamesCardsSameSuitAsReferenceCountTask()
    if query_id == "higher_than_reference_count":
        return GamesCardsHigherThanReferenceCountTask()
    raise AssertionError(f"unexpected reference-condition query_id={query_id!r}")


@pytest.mark.parametrize(
    "query_id",
    ("same_suit_as_reference_count", "higher_than_reference_count"),
)
def test_games_cards_reference_condition_ref_is_leftmost_top_row_card(query_id: str) -> None:
    out = _reference_condition_task(query_id).generate(
        25037,
        params={"query_id": query_id, "target_answer": 3, "card_count": 17},
        max_attempts=40,
    )
    trace = out.trace_payload
    reference_card_id = str(trace["execution_trace"]["reference_card_id"])

    assert trace["render_map"]["row_card_ids"][0][0] == reference_card_id
    assert trace["execution_trace"]["card_ordering"] == "sampled"
    assert trace["query_spec"]["params"]["card_ordering"] == "sampled"


def test_games_cards_hand_count_prompt_bundle_requires_rank_order_for_rank_queries() -> None:
    bundle = json.loads(Path("prompts/games/cards/games_cards_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:higher_than_reference_count"] == ["rank_order_text"]
    assert required["query:longest_run_length"] == [
        "rank_order_text",
        "continuation_rule_text",
    ]
    assert required["query:blackjack_best_hand_label"] == ["blackjack_rule_text"]
    assert required["query:poker_best_hand_label"] == ["poker_rule_text"]
    assert required["query:trick_taking_winner_label"] == [
        "rank_order_text",
        "trick_rule_text",
        "trump_text",
    ]
    assert required["query:missing_straight_card_label"] == ["rank_order_text"]


def test_games_cards_hand_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__cards__same_suit_as_reference_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__cards__same_suit_as_reference_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__cards__same_suit_as_reference_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=40,
        sampling_seed=53,
    )
    final_path = build_dataset(config, code_hash="games-cards-hand-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record["task_group"] == "cards" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games__cards__same_suit_as_reference_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0


@pytest.mark.parametrize(
    ("query_id", "target_answer", "card_count"),
    (
        ("same_suit_as_reference_count", 3, 16),
        ("higher_than_reference_count", 4, 17),
    ),
)
def test_games_cards_reference_condition_public_task_records_query_id(
    query_id: str,
    target_answer: int,
    card_count: int,
) -> None:
    out = _reference_condition_task(query_id).generate(
        25041,
        params={
            "query_id": query_id,
            "target_answer": target_answer,
            "card_count": card_count,
        },
        max_attempts=40,
    )
    trace = out.trace_payload

    assert out.query_id == query_id
    assert trace["query_spec"]["query_id"] == query_id
    assert trace["query_spec"]["params"]["query_id"] == query_id
    assert trace["execution_trace"]["query_id"] == query_id
    assert int(out.answer_gt.value) == int(target_answer)


@pytest.mark.parametrize(
    ("task_id", "expected_query_id", "min_annotation_count"),
    (
        ("task_games__cards__blackjack_best_hand_label", "blackjack_best_hand_label", 3),
        ("task_games__cards__poker_best_hand_label", "poker_best_hand_label", 5),
        ("task_games__cards__trick_taking_winner_label", "trick_taking_winner_label", 1),
    ),
)
def test_games_cards_rule_tasks_emit_label_contracts(
    task_id: str,
    expected_query_id: str,
    min_annotation_count: int,
) -> None:
    out = create_task(task_id).generate(25101, params={}, max_attempts=80)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    answer = str(out.answer_gt.value)

    assert out.answer_gt.type == "string"
    label_key = "winning_label"
    option_key = "winning_option"
    label_prefix = "Player " if expected_query_id == "trick_taking_winner_label" else "Hand "
    assert len(answer) == 1
    assert "A" <= answer <= "H"
    assert str(execution[label_key]).startswith(label_prefix)
    assert str(execution[option_key]) == answer
    assert str(execution[label_key]).endswith(answer)
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) >= int(min_annotation_count)
    assert out.query_id == expected_query_id
    assert trace["query_spec"]["query_id"] == expected_query_id
    assert trace["query_spec"]["params"]["query_id"] == expected_query_id
    assert trace["query_spec"]["params"]["query_id_probabilities"] == {expected_query_id: 1.0}
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value


def test_games_cards_blackjack_best_hand_enforces_unique_non_bust_winner() -> None:
    out = create_task("task_games__cards__blackjack_best_hand_label").generate(
        25117,
        params={"option_count": 6, "cards_per_hand": 4},
        max_attempts=80,
    )
    execution = out.trace_payload["execution_trace"]
    scores = dict(execution["playable_scores"])
    best_score = max(int(value) for value in scores.values())
    winners = [label for label, value in scores.items() if int(value) == int(best_score)]

    assert winners == [execution["winning_label"]]
    assert execution["winning_option"] == out.answer_gt.value
    assert int(best_score) <= 21
    assert len(execution["annotation_entity_ids"]) in {3, 4}


def test_games_cards_poker_best_hand_enforces_unique_winner_score() -> None:
    out = create_task("task_games__cards__poker_best_hand_label").generate(
        25123,
        params={"option_count": 6},
        max_attempts=120,
    )
    execution = out.trace_payload["execution_trace"]
    scores = {
        str(label): (int(score[0]), tuple(int(value) for value in score[1]))
        for label, score in execution["hand_scores"].items()
    }
    best_score = max(scores.values())
    winners = [label for label, score in scores.items() if score == best_score]

    assert winners == [execution["winning_label"]]
    assert execution["winning_option"] == out.answer_gt.value
    assert len(execution["annotation_entity_ids"]) == 5


@pytest.mark.parametrize(
    ("category_key", "category_label"),
    (
        ("straight", "straight"),
        ("flush", "flush"),
        ("full_house", "full house"),
        ("four_of_a_kind", "four of a kind"),
        ("straight_flush", "straight flush"),
    ),
)
def test_games_cards_poker_best_hand_can_target_rare_categories(category_key: str, category_label: str) -> None:
    out = create_task("task_games__cards__poker_best_hand_label").generate(
        25127,
        params={"option_count": 6, "poker_winning_category": category_key},
        max_attempts=120,
    )
    execution = out.trace_payload["execution_trace"]

    assert execution["target_winning_category_key"] == category_key
    assert execution["winning_category"] == category_label
    assert execution["hand_categories"][execution["winning_label"]] == category_label
    assert execution["winning_option"] == out.answer_gt.value


def _card_payload_by_id(execution: dict) -> dict[str, dict]:
    return {str(spec["card_id"]): dict(spec) for spec in execution["card_specs"]}


def _is_ace_high_straight(cards: list[dict]) -> bool:
    ranks = sorted({int(card["rank_value"]) for card in cards})
    return len(ranks) == 5 and int(ranks[-1] - ranks[0]) == 4


def _missing_card_completion_matches(query_id: str, partial_cards: list[dict], candidate: dict) -> bool:
    cards = [dict(card) for card in partial_cards] + [dict(candidate)]
    if query_id == "missing_flush_card_label":
        return len({str(card["suit_name"]) for card in cards}) == 1
    if query_id == "missing_straight_card_label":
        return _is_ace_high_straight(cards)
    rank_counts: dict[int, int] = {}
    for card in cards:
        rank = int(card["rank_value"])
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
    counts = sorted(rank_counts.values(), reverse=True)
    if query_id == "missing_full_house_card_label":
        return counts == [3, 2]
    if query_id == "missing_three_of_kind_card_label":
        return counts == [3, 1, 1]
    raise AssertionError(f"unexpected missing-card query_id={query_id!r}")


@pytest.mark.parametrize("query_id", SUPPORTED_MISSING_CARD_QUERY_IDS)
def test_games_cards_missing_card_completion_has_one_valid_candidate(query_id: str) -> None:
    out = create_task("task_games__cards__missing_card_to_complete_hand_label").generate(
        25141,
        params={"query_id": query_id, "option_count": 6, "target_candidate_index": 3},
        max_attempts=120,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    card_by_id = _card_payload_by_id(execution)
    partial_cards = [card_by_id[str(card_id)] for card_id in execution["partial_card_ids"]]
    candidate_specs = dict(execution["candidate_specs_by_label"])
    completions = {
        str(label): _missing_card_completion_matches(query_id, partial_cards, dict(candidate))
        for label, candidate in candidate_specs.items()
    }

    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == "D"
    assert execution["correct_candidate_label"] == "D"
    assert [label for label, matches in completions.items() if matches] == ["D"]
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 1
    assert execution["annotation_entity_ids"] == [execution["candidate_card_ids_by_label"]["D"]]
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert trace["render_map"]["row_card_counts"] == [4, 6]
    assert out.query_id == query_id
    assert "candidate" in out.prompt.lower()


def test_games_cards_trick_taking_prompt_and_trace_expose_rule() -> None:
    out = create_task("task_games__cards__trick_taking_winner_label").generate(25131, params={}, max_attempts=80)
    execution = out.trace_payload["execution_trace"]

    assert "leftmost card is the led card" in out.prompt
    assert "Trump suit:" in out.prompt or "no trump suit" in out.prompt
    assert execution["led_suit"] in {"spades", "hearts", "diamonds", "clubs"}
    assert str(execution["winning_label"]) in execution["trick_scores"]
    assert execution["winning_option"] == out.answer_gt.value
    assert len(execution["annotation_entity_ids"]) == 1


def test_games_cards_trick_winning_play_has_one_winning_candidate() -> None:
    out = create_task("task_games__cards__trick_winning_play_label").generate(
        25161,
        params={"option_count": 6, "target_candidate_index": 2, "trick_play_trump_mode": "with_trump"},
        max_attempts=160,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    current_best = tuple(int(value) for value in execution["current_best_score"])
    candidate_specs = dict(execution["candidate_specs_by_label"])
    winning_labels = [
        str(label)
        for label, spec in candidate_specs.items()
        if tuple(int(value) for value in spec["trick_score"]) > current_best
    ]

    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == "C"
    assert execution["correct_candidate_label"] == "C"
    assert winning_labels == ["C"]
    assert execution["annotation_entity_ids"] == [execution["candidate_card_ids_by_label"]["C"]]
    assert trace["render_map"]["row_card_counts"] == [execution["played_count"], 6]
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert len(out.annotation_gt.value) == 1
    assert "candidate" in out.prompt.lower()


def test_games_cards_poker_draw_card_has_one_best_candidate() -> None:
    out = create_task("task_games__cards__poker_draw_card_label").generate(
        25167,
        params={"option_count": 6, "target_candidate_index": 3, "poker_draw_target_category": "flush"},
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    card_by_id = _card_payload_by_id(execution)
    partial_cards = [
        (int(card_by_id[str(card_id)]["rank_value"]), str(card_by_id[str(card_id)]["suit_name"]))
        for card_id in execution["partial_card_ids"]
    ]
    candidate_specs = dict(execution["candidate_specs_by_label"])
    scores = {}
    for label, spec in candidate_specs.items():
        candidate = (int(spec["rank_value"]), str(spec["suit_name"]))
        score = _poker_score([*partial_cards, candidate])
        scores[str(label)] = (int(score[0]), tuple(int(value) for value in score[1]))
        assert [int(score[0]), [int(value) for value in score[1]]] == spec["completed_score"]
    best_score = max(scores.values())
    winning_labels = [str(label) for label, score in scores.items() if score == best_score]

    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == "D"
    assert execution["correct_candidate_label"] == "D"
    assert winning_labels == ["D"]
    assert execution["winning_category"] == "flush"
    assert execution["annotation_entity_ids"] == [execution["candidate_card_ids_by_label"]["D"]]
    assert trace["render_map"]["row_card_counts"] == [4, 6]
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert len(out.annotation_gt.value) == 1
