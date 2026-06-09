"""Contract tests for the games bingo completed-line count task."""

from __future__ import annotations

import json
from pathlib import Path
import random

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.registry import create_task
from trace.tasks.games.bingo.completed_line_count import (
    GamesBingoCalledNumberMarkCountTask,
    GamesBingoCompletedLineCountTask,
    GamesBingoNearCompleteLineCountTask,
)
from trace.tasks.games.shared.bingo_common import build_bingo_card_state
from tests.helpers import read_jsonl


def _near_complete_row_indices(mark_grid: list[list[bool]]) -> tuple[int, ...]:
    return tuple(
        int(row_index)
        for row_index, row in enumerate(mark_grid)
        if sum(1 for value in row if not bool(value)) == 1
    )


def _near_complete_column_indices(mark_grid: list[list[bool]]) -> tuple[int, ...]:
    indices: list[int] = []
    for column_index in range(5):
        if sum(1 for row_index in range(5) if not bool(mark_grid[row_index][column_index])) == 1:
            indices.append(int(column_index))
    return tuple(indices)


def _near_complete_gap_cell_ids(mark_grid: list[list[bool]], *, query_id: str) -> tuple[str, ...]:
    if str(query_id) == "near_complete_row_count":
        ids: list[str] = []
        for row_index in _near_complete_row_indices(mark_grid):
            gap_columns = [
                int(column_index)
                for column_index in range(5)
                if not bool(mark_grid[int(row_index)][column_index])
            ]
            assert len(gap_columns) == 1
            ids.append(f"cell_r{int(row_index)}_c{int(gap_columns[0])}")
        return tuple(ids)
    if str(query_id) == "near_complete_column_count":
        ids = []
        for column_index in _near_complete_column_indices(mark_grid):
            gap_rows = [
                int(row_index)
                for row_index in range(5)
                if not bool(mark_grid[row_index][int(column_index)])
            ]
            assert len(gap_rows) == 1
            ids.append(f"cell_r{int(gap_rows[0])}_c{int(column_index)}")
        return tuple(ids)
    raise AssertionError(f"unsupported near-complete query: {query_id}")


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        (
            {
                "query_id": "completed_axis_line_count",
                "line_axis": "row",
                "target_answer": 0,
            },
            0,
        ),
        (
            {
                "query_id": "completed_axis_line_count",
                "line_axis": "row",
                "target_answer": 3,
            },
            3,
        ),
        (
            {
                "query_id": "completed_column_count",
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
    cells = execution["cell_specs"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.annotation_gt.type == "bbox_set"
    assert trace["query_spec"]["params"]["query_id"] == out.query_id
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert len(execution["annotation_entity_ids"]) == len(out.annotation_gt.value)
    assert trace["render_spec"]["canvas_width"] <= 1180
    assert trace["render_spec"]["canvas_height"] <= 760
    assert float(trace["render_spec"]["effective_cell_size_px"]) >= 28.0
    assert trace["render_spec"]["text_style"]["font_family"]
    assert trace["render_map"]["font_family"] == trace["render_spec"]["text_style"]["font_family"]
    assert any(not bool(cell["is_marked"]) for cell in cells)
    for x0, y0, x1, y1 in out.annotation_gt.value:
        assert 0 <= float(x0) <= float(x1) <= float(trace["render_spec"]["canvas_width"])
        assert 0 <= float(y0) <= float(y1) <= float(trace["render_spec"]["canvas_height"])

    if str(out.query_id) == "completed_axis_line_count":
        if str(execution["line_axis"]) == "row":
            assert len(execution["completed_row_indices"]) == int(expected_answer)
            assert len(out.annotation_gt.value) == 5 * int(expected_answer)
        else:
            assert str(execution["line_axis"]) == "column"
            assert len(execution["completed_column_indices"]) == int(expected_answer)
            assert len(out.annotation_gt.value) == 5 * int(expected_answer)
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
            "query_id": "line_sum_extremum_value",
            "line_axis": line_axis,
            "extremum": extremum,
            "target_answer": completed_line_count,
        },
        max_attempts=100,
    )
    execution = out.trace_payload["execution_trace"]
    cells = execution["cell_specs"]

    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 5
    assert execution["completed_line_count_target"] == completed_line_count
    assert execution["line_sum_extremum"] == extremum
    assert execution["line_sum_target_axis"] == line_axis
    assert execution["annotation_entity_ids"] == execution["line_sum_target_cell_ids"]
    assert any(not bool(cell["is_marked"]) for cell in cells)

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
    assert execution["annotation_entity_ids"] == expected_ids


def test_games_bingo_line_sum_extremum_public_wrapper_uses_default_variant() -> None:
    out = create_task("task_games__bingo__line_sum_extremum_value").generate(27024, params={}, max_attempts=100)
    assert out.query_id == "line_sum_extremum_value"
    assert out.trace_payload["query_spec"]["params"]["query_id"] == "line_sum_extremum_value"


@pytest.mark.parametrize(
    ("query_id", "target_answer", "line_axis"),
    (
        ("near_complete_row_count", 3, "row"),
        ("near_complete_column_count", 4, "column"),
    ),
)
def test_games_bingo_near_complete_line_count_matches_gap_cells(
    query_id: str,
    target_answer: int,
    line_axis: str,
) -> None:
    out = GamesBingoNearCompleteLineCountTask().generate(
        27051 + int(target_answer),
        params={
            "query_id": str(query_id),
            "target_answer": int(target_answer),
        },
        max_attempts=48,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    mark_grid = execution["mark_grid"]
    expected_gap_ids = _near_complete_gap_cell_ids(mark_grid, query_id=str(query_id))
    expected_bboxes = [
        list(trace["render_map"]["cell_bboxes_px"][str(cell_id)])
        for cell_id in expected_gap_ids
    ]

    assert out.scene_id == "bingo"
    assert out.query_id == str(query_id)
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == len(expected_gap_ids) == int(target_answer)
    assert out.annotation_gt.type == "bbox_set"
    assert out.annotation_gt.value == expected_bboxes
    assert execution["line_axis"] == str(line_axis)
    assert execution["near_complete_gap_cell_ids"] == list(expected_gap_ids)
    assert execution["annotation_entity_ids"] == list(expected_gap_ids)
    assert trace["projected_annotation"]["bbox_set"] == expected_bboxes
    if str(line_axis) == "row":
        assert tuple(execution["near_complete_row_indices"]) == _near_complete_row_indices(mark_grid)
    else:
        assert tuple(execution["near_complete_column_indices"]) == _near_complete_column_indices(mark_grid)


def test_games_bingo_near_complete_zero_answer_emits_empty_annotation() -> None:
    out = GamesBingoNearCompleteLineCountTask().generate(
        27061,
        params={
            "query_id": "near_complete_row_count",
            "target_answer": 0,
        },
        max_attempts=48,
    )
    execution = out.trace_payload["execution_trace"]

    assert int(out.answer_gt.value) == 0
    assert out.annotation_gt.type == "bbox_set"
    assert out.annotation_gt.value == []
    assert execution["near_complete_row_indices"] == []
    assert execution["near_complete_gap_cell_ids"] == []
    assert execution["annotation_entity_ids"] == []


def test_games_bingo_called_number_mark_count_matches_marked_called_cells() -> None:
    out = GamesBingoCalledNumberMarkCountTask().generate(
        27071,
        params={
            "target_answer": 3,
            "called_number_count": 7,
        },
        max_attempts=48,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    cell_specs = {str(cell["cell_id"]): dict(cell) for cell in execution["cell_specs"]}
    called_cell_ids = tuple(str(value) for value in execution["called_number_cell_ids"])
    called_marked_cell_ids = tuple(str(value) for value in execution["called_marked_cell_ids"])
    expected_bboxes = [
        list(trace["render_map"]["cell_bboxes_px"][str(cell_id)])
        for cell_id in called_marked_cell_ids
    ]

    assert out.scene_id == "bingo"
    assert out.query_id == "called_marked_number_count"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == len(called_marked_cell_ids) == 3
    assert out.annotation_gt.type == "bbox_set"
    assert out.annotation_gt.value == expected_bboxes
    assert trace["projected_annotation"]["bbox_set"] == expected_bboxes
    assert execution["annotation_entity_ids"] == list(called_marked_cell_ids)
    assert len(called_cell_ids) == int(execution["called_number_count"]) == 7
    assert len(trace["render_map"]["called_number_bboxes_px"]) == 7
    assert execution["called_numbers"] == [int(cell_specs[cell_id]["number"]) for cell_id in called_cell_ids]
    assert all(bool(cell_specs[cell_id]["is_marked"]) for cell_id in called_marked_cell_ids)
    assert all(
        not bool(cell_specs[cell_id]["is_marked"])
        for cell_id in called_cell_ids
        if cell_id not in called_marked_cell_ids
    )


def test_games_bingo_called_number_mark_count_zero_answer_emits_empty_annotation() -> None:
    out = GamesBingoCalledNumberMarkCountTask().generate(
        27072,
        params={
            "target_answer": 0,
            "called_number_count": 5,
        },
        max_attempts=48,
    )
    execution = out.trace_payload["execution_trace"]

    assert int(out.answer_gt.value) == 0
    assert out.annotation_gt.type == "bbox_set"
    assert out.annotation_gt.value == []
    assert execution["called_marked_cell_ids"] == []
    assert execution["annotation_entity_ids"] == []


def test_games_bingo_near_complete_line_count_taxonomy() -> None:
    assert resolve_task_taxonomy("task_games__bingo__near_complete_line_count").scene_id == "bingo"


def test_games_bingo_called_number_mark_count_taxonomy() -> None:
    assert resolve_task_taxonomy("task_games__bingo__called_number_mark_count").scene_id == "bingo"


def test_games_bingo_completed_line_count_is_deterministic() -> None:
    params = {
        "query_id": "completed_axis_line_count",
        "line_axis": "column",
        "target_answer": 2,
    }
    task = GamesBingoCompletedLineCountTask()
    out_a = task.generate(27031, params=params, max_attempts=24)
    out_b = task.generate(27031, params=params, max_attempts=24)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_bingo_builder_rejects_all_marked_card_state() -> None:
    with pytest.raises(ValueError, match="at least one unmarked cell"):
        build_bingo_card_state(
            rng=random.Random(27041),
            query_id="completed_axis_line_count",
            line_axis="row",
            target_answer=5,
        )


def test_games_bingo_completed_line_count_prompt_bundle_requires_rule_text_by_variant() -> None:
    bundle = json.loads(Path("prompts/games/bingo/games_bingo_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:completed_axis_line_count"] == ["completed_axis_rule_text", "line_axis"]
    assert required["query:line_sum_extremum_value"] == [
        "line_sum_extremum_rule_text",
        "line_axis",
        "extremum",
    ]
    assert required["query:near_complete_row_count"] == ["near_complete_line_rule_text"]
    assert required["query:near_complete_column_count"] == ["near_complete_line_rule_text"]
    assert required["query:called_marked_number_count"] == ["called_marked_number_rule_text"]


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
            ),
            BuildTaskConfig(
                task_id="task_games__bingo__near_complete_line_count",
                count=2,
                params={},
            ),
            BuildTaskConfig(
                task_id="task_games__bingo__called_number_mark_count",
                count=2,
                params={},
            ),
        ],
        strict_repro=False,
        max_attempts_per_instance=24,
        sampling_seed=61,
    )
    final_path = build_dataset(config, code_hash="games-bingo-completed-line-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 8
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record["task_group"] == "bingo" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games__bingo__completed_line_count"]) == 4
    assert int(build_report["accepted_counts_by_task"]["task_games__bingo__near_complete_line_count"]) == 2
    assert int(build_report["accepted_counts_by_task"]["task_games__bingo__called_number_mark_count"]) == 2

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
