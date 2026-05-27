"""Contract tests for the games bingo completed-line count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.registry import create_task
from trace.tasks.games.bingo.completed_line_count import GamesBingoCompletedLineCountTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        (
            {
                "query_variant": "completed_axis_line_count",
                "line_axis": "row",
                "target_answer": 3,
            },
            3,
        ),
        (
            {
                "query_variant": "completed_column_count",
                "target_answer": 4,
            },
            4,
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
    assert trace["query_spec"]["params"]["query_variant"] == out.query_variant
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value)

    if str(out.query_variant) == "completed_axis_line_count":
        if str(execution["line_axis"]) == "row":
            assert len(execution["completed_row_indices"]) == int(expected_answer)
            assert len(out.evidence_gt.value) == 5 * int(expected_answer)
        else:
            assert str(execution["line_axis"]) == "column"
            assert len(execution["completed_column_indices"]) == int(expected_answer)
            assert len(out.evidence_gt.value) == 5 * int(expected_answer)
@pytest.mark.parametrize(
    ("line_axis", "extremum", "completed_line_count"),
    (
        ("row", "max", 3),
        ("column", "min", 2),
    ),
)
def test_games_bingo_line_sum_extremum_value_has_unique_extremum_line(
    line_axis: str,
    extremum: str,
    completed_line_count: int,
) -> None:
    out = GamesBingoCompletedLineCountTask().generate(
        27023,
        params={
            "query_variant": "line_sum_extremum_value",
            "line_axis": line_axis,
            "extremum": extremum,
            "target_answer": completed_line_count,
        },
        max_attempts=100,
    )
    execution = out.trace_payload["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 5
    assert execution["completed_line_count_target"] == completed_line_count
    assert execution["line_sum_extremum"] == extremum
    assert execution["line_sum_target_axis"] == line_axis
    assert execution["evidence_entity_ids"] == execution["line_sum_target_cell_ids"]

    line_sums = [int(record["sum"]) for record in execution["completed_line_sums"]]
    assert len(line_sums) == completed_line_count
    expected_answer = max(line_sums) if extremum == "max" else min(line_sums)
    assert line_sums.count(expected_answer) == 1
    assert int(out.answer_gt.value) == int(expected_answer)

    numbers = execution["numbers_grid"]
    target_line_index = int(execution["line_sum_target_line_index"])
    if line_axis == "row":
        expected_ids = [f"cell_r{target_line_index}_c{column_index}" for column_index in range(5)]
        assert sum(int(numbers[target_line_index][column_index]) for column_index in range(5)) == expected_answer
    else:
        expected_ids = [f"cell_r{row_index}_c{target_line_index}" for row_index in range(5)]
        assert sum(int(numbers[row_index][target_line_index]) for row_index in range(5)) == expected_answer
    assert execution["evidence_entity_ids"] == expected_ids


def test_games_bingo_line_sum_extremum_public_wrapper_uses_default_variant() -> None:
    out = create_task("task_games__bingo__line_sum_extremum_value").generate(27024, params={}, max_attempts=100)
    assert out.query_variant == "default"
    assert out.query_id == "line_sum_extremum_value"
    assert out.trace_payload["query_spec"]["params"]["query_variant"] == "default"


def test_games_bingo_completed_line_count_is_deterministic() -> None:
    params = {
        "query_variant": "completed_axis_line_count",
        "line_axis": "column",
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
    bundle = json.loads(Path("prompts/games/bingo/games_bingo_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:completed_axis_line_count"] == ["completed_axis_rule_text", "line_axis"]
    assert required["query:line_sum_extremum_value"] == [
        "line_sum_extremum_rule_text",
        "line_axis",
        "extremum",
    ]


def test_games_bingo_completed_line_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__bingo__completed_line_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__bingo__completed_line_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__bingo__completed_line_count",
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
    assert int(build_report["accepted_counts_by_task"]["task_games__bingo__completed_line_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
