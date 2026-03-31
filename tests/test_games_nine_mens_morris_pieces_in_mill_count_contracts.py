"""Contract tests for the games nine-men's-morris pieces-in-mill count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.nine_mens_morris.pieces_in_mill_count import GamesNineMensMorrisPiecesInMillCountTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        (
            {
                "query_variant": "white_pieces_in_mill_count",
                "target_answer": 5,
            },
            5,
        ),
        (
            {
                "task_variant": "black_pieces_in_mill_count",
                "target_answer": 6,
            },
            6,
        ),
        (
            {
                "query_variant": "all_pieces_in_mill_count",
                "target_answer": 11,
            },
            11,
        ),
    ),
)
def test_games_nine_mens_morris_pieces_in_mill_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
) -> None:
    out = GamesNineMensMorrisPiecesInMillCountTask().generate(29101, params=params, max_attempts=64)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert trace["query_spec"]["params"]["task_variant"] == out.task_variant
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value) == int(expected_answer)

    if str(out.task_variant) == "white_pieces_in_mill_count":
        assert len(execution["white_piece_ids_in_mill"]) == int(expected_answer)
    elif str(out.task_variant) == "black_pieces_in_mill_count":
        assert len(execution["black_piece_ids_in_mill"]) == int(expected_answer)
    else:
        assert len(execution["all_piece_ids_in_mill"]) == int(expected_answer)


def test_games_nine_mens_morris_pieces_in_mill_count_zero_answer_emits_empty_evidence() -> None:
    out = GamesNineMensMorrisPiecesInMillCountTask().generate(
        29111,
        params={
            "query_variant": "all_pieces_in_mill_count",
            "target_answer": 0,
        },
        max_attempts=64,
    )
    assert int(out.answer_gt.value) == 0
    assert out.evidence_gt.value == []
    assert out.trace_payload["execution_trace"]["evidence_entity_ids"] == []


def test_games_nine_mens_morris_pieces_in_mill_count_counts_overlapping_pieces_once() -> None:
    out = GamesNineMensMorrisPiecesInMillCountTask().generate(
        29121,
        params={
            "query_variant": "white_pieces_in_mill_count",
            "target_answer": 5,
        },
        max_attempts=64,
    )
    execution = out.trace_payload["execution_trace"]
    overlapping = set(str(value) for value in execution["overlapping_piece_ids"])
    evidence_ids = set(str(value) for value in execution["evidence_entity_ids"])
    assert overlapping <= evidence_ids or not overlapping
    assert len(evidence_ids) == len(execution["white_piece_ids_in_mill"])


def test_games_nine_mens_morris_pieces_in_mill_count_is_deterministic() -> None:
    params = {
        "query_variant": "all_pieces_in_mill_count",
        "target_answer": 12,
    }
    task = GamesNineMensMorrisPiecesInMillCountTask()
    out_a = task.generate(29131, params=params, max_attempts=64)
    out_b = task.generate(29131, params=params, max_attempts=64)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_nine_mens_morris_pieces_in_mill_count_prompt_bundle_requires_rule_text() -> None:
    bundle = json.loads(Path("prompts/games/nine_mens_morris/games_nine_mens_morris_v1.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["task_variant:white_pieces_in_mill_count"] == ["mill_rule_text"]
    assert required["task_variant:black_pieces_in_mill_count"] == ["mill_rule_text"]
    assert required["task_variant:all_pieces_in_mill_count"] == ["mill_rule_text"]


def test_games_nine_mens_morris_pieces_in_mill_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games_nine_mens_morris_pieces_in_mill_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games_nine_mens_morris_pieces_in_mill_count",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games_nine_mens_morris_pieces_in_mill_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=64,
        sampling_seed=81,
    )
    final_path = build_dataset(config, code_hash="games-nine-mens-morris-pieces-in-mill-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record["task_group"] == "nine_mens_morris" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games_nine_mens_morris_pieces_in_mill_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
