"""Contract tests for the games cards hand-count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.cards.hand_count import GamesCardsHandCountTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer", "expected_evidence_count"),
    (
        (
            {
                "scene_variant": "single_row",
                "query_variant": "same_suit_as_reference_count",
                "target_answer": 3,
                "card_count": 8,
            },
            3,
            3,
        ),
        (
            {
                "scene_variant": "single_row",
                "query_variant": "higher_than_reference_count",
                "target_answer": 4,
                "card_count": 9,
            },
            4,
            4,
        ),
        (
            {
                "scene_variant": "two_row",
                "query_variant": "pair_count",
                "target_answer": 4,
                "card_count": 12,
            },
            4,
            8,
        ),
        (
            {
                "scene_variant": "two_row",
                "task_variant": "longest_run_length",
                "target_answer": 5,
                "card_count": 12,
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
    assert trace["query_spec"]["params"]["task_variant"] == out.task_variant
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == int(expected_evidence_count)


def test_games_cards_hand_count_pair_count_uses_exact_pairs_only() -> None:
    out = GamesCardsHandCountTask().generate(
        25011,
        params={
            "scene_variant": "two_row",
            "query_variant": "pair_count",
            "target_answer": 3,
            "card_count": 11,
        },
        max_attempts=40,
    )
    specs = out.trace_payload["execution_trace"]["card_specs"]
    rank_counts: dict[int, int] = {}
    evidence_ids = set(out.trace_payload["execution_trace"]["evidence_entity_ids"])
    for spec in specs:
        rank_counts[int(spec["rank_value"])] = rank_counts.get(int(spec["rank_value"]), 0) + 1
    assert sum(1 for count in rank_counts.values() if int(count) == 2) == 3
    assert all(int(count) in {1, 2} for count in rank_counts.values())
    for spec in specs:
        in_evidence = str(spec["card_id"]) in evidence_ids
        assert in_evidence == (int(rank_counts[int(spec["rank_value"])]) == 2)


def test_games_cards_hand_count_two_row_run_emits_continuation_cue() -> None:
    out = GamesCardsHandCountTask().generate(
        25021,
        params={
            "scene_variant": "two_row",
            "query_variant": "longest_run_length",
            "target_answer": 6,
            "card_count": 12,
        },
        max_attempts=40,
    )
    render_map = out.trace_payload["render_map"]
    assert render_map["continuation_cue_bbox_px"] is not None
    assert "continue" in out.prompt.lower()
    assert "top row" in out.prompt.lower()


def test_games_cards_hand_count_is_deterministic() -> None:
    params = {
        "scene_variant": "two_row",
        "query_variant": "higher_than_reference_count",
        "target_answer": 5,
        "card_count": 12,
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
    bundle = json.loads(Path("prompts/games/cards/games_cards_v1.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["task_variant:higher_than_reference_count"] == ["rank_order_text"]
    assert required["task_variant:longest_run_length"] == [
        "rank_order_text",
        "continuation_rule_text",
    ]


def test_games_cards_hand_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games_cards_hand_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games_cards_hand_count",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games_cards_hand_count",
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
    assert int(build_report["accepted_counts_by_task"]["task_games_cards_hand_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
