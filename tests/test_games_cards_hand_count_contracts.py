"""Contract tests for the games cards hand-count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.registry import create_task
from trace.tasks.games.cards.hand_count import GamesCardsHandCountTask, GamesCardsReferenceConditionCountTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer", "expected_evidence_count"),
    (
        (
            {
                "query_variant": "same_suit_as_reference_count",
                "target_answer": 3,
                "card_count": 16,
            },
            3,
            3,
        ),
        (
            {
                "query_variant": "higher_than_reference_count",
                "target_answer": 4,
                "card_count": 17,
            },
            4,
            4,
        ),
        (
                {
                    "query_variant": "exact_triple_count",
                    "target_answer": 3,
                    "card_count": 22,
                },
            3,
            9,
        ),
        (
            {
                "query_variant": "longest_run_length",
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
    expected_evidence_count: int,
) -> None:
    out = GamesCardsHandCountTask().generate(25001, params=params, max_attempts=40)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == int(expected_evidence_count)
    assert trace["query_spec"]["params"]["query_variant"] == out.query_variant
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == int(expected_evidence_count)


def test_games_cards_hand_count_exact_triple_count_uses_exact_triples_only() -> None:
    out = GamesCardsHandCountTask().generate(
        25017,
        params={
            "query_variant": "exact_triple_count",
            "target_answer": 4,
            "card_count": 22,
        },
        max_attempts=40,
    )
    specs = out.trace_payload["execution_trace"]["card_specs"]
    rank_counts: dict[int, int] = {}
    evidence_ids = set(out.trace_payload["execution_trace"]["evidence_entity_ids"])
    for spec in specs:
        rank_counts[int(spec["rank_value"])] = rank_counts.get(int(spec["rank_value"]), 0) + 1
    assert sum(1 for count in rank_counts.values() if int(count) == 3) == 4
    for spec in specs:
        in_evidence = str(spec["card_id"]) in evidence_ids
        assert in_evidence == (int(rank_counts[int(spec["rank_value"])]) == 3)


def test_games_cards_hand_count_multi_row_run_emits_continuation_cue() -> None:
    out = GamesCardsHandCountTask().generate(
        25021,
        params={
            "query_variant": "longest_run_length",
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
        "query_variant": "higher_than_reference_count",
        "target_answer": 5,
        "card_count": 26,
    }
    task = GamesCardsHandCountTask()
    out_a = task.generate(25031, params=params, max_attempts=40)
    out_b = task.generate(25031, params=params, max_attempts=40)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


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


def test_games_cards_hand_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__cards__reference_condition_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__cards__reference_condition_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__cards__reference_condition_count",
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
    assert int(build_report["accepted_counts_by_task"]["task_games__cards__reference_condition_count"]) == 4

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
    out = GamesCardsReferenceConditionCountTask().generate(
        25041,
        params={
            "query_variant": query_id,
            "target_answer": target_answer,
            "card_count": card_count,
        },
        max_attempts=40,
    )
    trace = out.trace_payload

    assert out.query_variant == "default"
    assert out.query_id == query_id
    assert trace["query_spec"]["params"]["query_variant"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == query_id
    assert trace["execution_trace"]["query_variant"] == "default"
    assert trace["execution_trace"]["query_id"] == query_id
    assert int(out.answer_gt.value) == int(target_answer)


@pytest.mark.parametrize(
    ("task_id", "expected_query_id", "min_evidence_count"),
    (
        ("task_games__cards__blackjack_best_hand_label", "blackjack_best_hand_label", 3),
        ("task_games__cards__poker_best_hand_label", "poker_best_hand_label", 5),
        ("task_games__cards__trick_taking_winner_label", "trick_taking_winner_label", 1),
    ),
)
def test_games_cards_rule_tasks_emit_label_contracts(
    task_id: str,
    expected_query_id: str,
    min_evidence_count: int,
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
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) >= int(min_evidence_count)
    assert out.query_variant == "default"
    assert out.query_id == expected_query_id
    assert trace["query_spec"]["query_id"] == expected_query_id
    assert trace["query_spec"]["params"]["query_variant"] == "default"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value


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
    assert len(execution["evidence_entity_ids"]) in {3, 4}


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
    assert len(execution["evidence_entity_ids"]) == 5


def test_games_cards_trick_taking_prompt_and_trace_expose_rule() -> None:
    out = create_task("task_games__cards__trick_taking_winner_label").generate(25131, params={}, max_attempts=80)
    execution = out.trace_payload["execution_trace"]

    assert "leftmost card is the led card" in out.prompt
    assert "Trump suit:" in out.prompt or "no trump suit" in out.prompt
    assert execution["led_suit"] in {"spades", "hearts", "diamonds", "clubs"}
    assert str(execution["winning_label"]) in execution["trick_scores"]
    assert execution["winning_option"] == out.answer_gt.value
    assert len(execution["evidence_entity_ids"]) == 1
