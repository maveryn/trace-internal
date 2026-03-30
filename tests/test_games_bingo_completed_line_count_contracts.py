"""Contract tests for the games bingo completed-line count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.bingo.completed_line_count import GamesBingoCompletedLineCountTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        (
            {
                "query_variant": "completed_row_count",
                "target_answer": 3,
            },
            3,
        ),
        (
            {
                "task_variant": "completed_column_count",
                "target_answer": 4,
            },
            4,
        ),
        (
            {
                "query_variant": "completed_straight_line_count",
                "target_answer": 5,
            },
            5,
        ),
    ),
)
def test_games_bingo_completed_line_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
) -> None:
    out = GamesBingoCompletedLineCountTask().generate(27001, params=params, max_attempts=24)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert trace["query_spec"]["params"]["task_variant"] == out.task_variant
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value)

    if str(out.task_variant) == "completed_row_count":
        assert len(execution["completed_row_indices"]) == int(expected_answer)
        assert len(out.evidence_gt.value) == 5 * int(expected_answer)
    elif str(out.task_variant) == "completed_column_count":
        assert len(execution["completed_column_indices"]) == int(expected_answer)
        assert len(out.evidence_gt.value) == 5 * int(expected_answer)
    else:
        total_completed = len(execution["completed_row_indices"]) + len(execution["completed_column_indices"])
        assert int(total_completed) == int(expected_answer)


def test_games_bingo_completed_line_count_zero_answer_emits_empty_evidence() -> None:
    out = GamesBingoCompletedLineCountTask().generate(
        27011,
        params={
            "query_variant": "completed_straight_line_count",
            "target_answer": 0,
        },
        max_attempts=24,
    )
    assert int(out.answer_gt.value) == 0
    assert out.evidence_gt.value == []
    assert out.trace_payload["execution_trace"]["evidence_entity_ids"] == []


def test_games_bingo_completed_line_count_straight_line_evidence_is_union_of_completed_rows_and_columns() -> None:
    out = GamesBingoCompletedLineCountTask().generate(
        27021,
        params={
            "query_variant": "completed_straight_line_count",
            "target_answer": 4,
        },
        max_attempts=24,
    )
    execution = out.trace_payload["execution_trace"]
    expected_ids = set()
    completed_rows = set(int(value) for value in execution["completed_row_indices"])
    completed_columns = set(int(value) for value in execution["completed_column_indices"])
    for spec in execution["cell_specs"]:
        include = int(spec["row_index"]) in completed_rows or int(spec["column_index"]) in completed_columns
        if include:
            expected_ids.add(str(spec["cell_id"]))
    assert set(str(value) for value in execution["evidence_entity_ids"]) == expected_ids


def test_games_bingo_completed_line_count_is_deterministic() -> None:
    params = {
        "query_variant": "completed_column_count",
        "target_answer": 2,
    }
    task = GamesBingoCompletedLineCountTask()
    out_a = task.generate(27031, params=params, max_attempts=24)
    out_b = task.generate(27031, params=params, max_attempts=24)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_bingo_completed_line_count_prompt_bundle_requires_rule_text_by_variant() -> None:
    bundle = json.loads(Path("prompts/games/bingo/games_bingo_v1.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["task_variant:completed_row_count"] == ["completed_row_rule_text"]
    assert required["task_variant:completed_column_count"] == ["completed_column_rule_text"]
    assert required["task_variant:completed_straight_line_count"] == ["completed_straight_line_rule_text"]


def test_games_bingo_completed_line_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games_bingo_completed_line_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games_bingo_completed_line_count",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games_bingo_completed_line_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=24,
        sampling_seed=61,
    )
    final_path = build_dataset(config, code_hash="games-bingo-completed-line-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record["task_group"] == "bingo" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games_bingo_completed_line_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
