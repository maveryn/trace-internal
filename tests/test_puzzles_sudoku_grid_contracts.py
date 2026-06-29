"""Contract tests for puzzle Sudoku-grid tasks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.puzzles.sudoku.marked_cell_candidate_count import (
    PuzzlesSudokuMarkedCellCandidateCountTask,
)
from trace.tasks.puzzles.sudoku.marked_cell_value import (
    PuzzlesSudokuMarkedCellValueTask,
)
from trace.tasks.puzzles.sudoku.repeated_digit_count import (
    PuzzlesSudokuRepeatedDigitCountTask,
)
from trace.tasks.puzzles.sudoku.shared.rules import (
    candidate_digits,
    coord_to_cell_id,
    missing_digits_in_unit,
    repeated_digits_in_unit,
    unit_coords,
)
from trace.tasks.puzzles.sudoku.unit_missing_digits_count import (
    PuzzlesSudokuUnitMissingDigitsCountTask,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_prompt_query", "expected_annotation_type"),
    (
        (
            PuzzlesSudokuMarkedCellValueTask,
            {"target_answer": 7, "scene_variant": "sparse_grid"},
            "marked_cell_value",
            "bbox_set_map",
        ),
        (
            PuzzlesSudokuMarkedCellCandidateCountTask,
            {"target_answer": 4, "scene_variant": "filled_grid"},
            "marked_cell_candidate_count",
            "bbox_set_map",
        ),
        (
            PuzzlesSudokuUnitMissingDigitsCountTask,
            {"target_answer": 4, "unit_type": "row", "scene_variant": "filled_grid"},
            "unit_missing_digits_count",
            "bbox_set",
        ),
        (
            PuzzlesSudokuRepeatedDigitCountTask,
            {"target_answer": 3, "unit_type": "box", "scene_variant": "sparse_grid"},
            "repeated_digit_count",
            "bbox_set",
        ),
    ),
)
def test_puzzles_sudoku_grid_emits_expected_contract(
    task_cls,
    params: dict[str, int | str],
    expected_prompt_query: str,
    expected_annotation_type: str,
) -> None:
    out = task_cls().generate(40201, params=params, max_attempts=64)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == str(expected_annotation_type)
    assert out.query_id == "single"
    assert trace["query_spec"]["params"]["query_id"] == "single"
    assert trace["query_spec"]["params"]["prompt_query_key"] == str(
        expected_prompt_query
    )
    assert execution["query_id"] == "single"
    assert int(execution["target_answer"]) == int(out.answer_gt.value)
    assert trace["projected_annotation"]["type"] == str(expected_annotation_type)
    assert (
        trace["projected_annotation"][str(expected_annotation_type)]
        == out.annotation_gt.value
    )
    if str(expected_annotation_type) == "bbox_set":
        assert len(execution["annotation_entity_ids"]) == len(out.annotation_gt.value)
    else:
        assert sorted(out.annotation_gt.value.keys()) == [
            "constraint_cells",
            "marked_cell",
        ]
        assert sorted(execution["annotation_entity_ids"].keys()) == [
            "constraint_cells",
            "marked_cell",
        ]
    assert trace["render_spec"]["panel_scene_style"]["style_pack"]
    assert trace["render_spec"]["text_style"]["font_family"]


def test_puzzles_sudoku_marked_cell_value_has_unique_candidate() -> None:
    out = PuzzlesSudokuMarkedCellValueTask().generate(
        40211,
        params={"target_answer": 5},
        max_attempts=64,
    )
    execution = out.trace_payload["execution_trace"]
    board = tuple(tuple(int(value) for value in row) for row in execution["board_rows"])
    marked_cell = tuple(int(value) for value in execution["marked_cell"])

    assert int(out.answer_gt.value) == 5
    assert int(board[marked_cell[0]][marked_cell[1]]) == 0
    assert candidate_digits(board, marked_cell) == (5,)
    assert str(coord_to_cell_id(marked_cell)) in set(
        execution["annotation_entity_ids"]["marked_cell"]
    )


def test_puzzles_sudoku_marked_cell_candidate_count_matches_candidates() -> None:
    out = PuzzlesSudokuMarkedCellCandidateCountTask().generate(
        40215,
        params={"target_answer": 5},
        max_attempts=64,
    )
    execution = out.trace_payload["execution_trace"]
    board = tuple(tuple(int(value) for value in row) for row in execution["board_rows"])
    marked_cell = tuple(int(value) for value in execution["marked_cell"])
    candidates = candidate_digits(board, marked_cell)

    assert int(out.answer_gt.value) == len(candidates) == 5
    assert int(board[marked_cell[0]][marked_cell[1]]) == 0
    assert set(int(value) for value in execution["candidate_digit_values"]) == set(
        candidates
    )
    assert str(coord_to_cell_id(marked_cell)) in set(
        execution["annotation_entity_ids"]["marked_cell"]
    )


def test_puzzles_sudoku_missing_digits_match_highlighted_unit() -> None:
    out = PuzzlesSudokuUnitMissingDigitsCountTask().generate(
        40221,
        params={"target_answer": 5, "unit_type": "column"},
        max_attempts=64,
    )
    execution = out.trace_payload["execution_trace"]
    board = tuple(tuple(int(value) for value in row) for row in execution["board_rows"])
    unit_type = str(execution["highlighted_unit_type"])
    unit_index = int(execution["highlighted_unit_index"])
    missing = missing_digits_in_unit(board, unit_type=unit_type, unit_index=unit_index)
    unit = set(unit_coords(unit_type, unit_index))
    annotation_coords = {tuple(coord) for coord in execution["annotation_coords"]}

    assert len(missing) == int(out.answer_gt.value) == 5
    assert set(int(value) for value in execution["missing_digit_values"]) == set(
        missing
    )
    assert annotation_coords <= unit
    assert all(int(board[row][col]) != 0 for row, col in annotation_coords)


def test_puzzles_sudoku_repeated_digits_match_highlighted_unit() -> None:
    out = PuzzlesSudokuRepeatedDigitCountTask().generate(
        40231,
        params={"target_answer": 2, "unit_type": "box"},
        max_attempts=64,
    )
    execution = out.trace_payload["execution_trace"]
    board = tuple(tuple(int(value) for value in row) for row in execution["board_rows"])
    unit_type = str(execution["highlighted_unit_type"])
    unit_index = int(execution["highlighted_unit_index"])
    repeated = repeated_digits_in_unit(
        board, unit_type=unit_type, unit_index=unit_index
    )
    unit = set(unit_coords(unit_type, unit_index))
    annotation_coords = {tuple(coord) for coord in execution["annotation_coords"]}

    assert len(repeated) == int(out.answer_gt.value) == 2
    assert set(int(value) for value in execution["repeated_digit_values"]) == set(
        repeated
    )
    assert annotation_coords <= unit
    assert all(int(board[row][col]) in set(repeated) for row, col in annotation_coords)


@pytest.mark.parametrize(
    ("task_cls", "support", "base_params"),
    (
        (PuzzlesSudokuMarkedCellValueTask, range(1, 10), {}),
        (PuzzlesSudokuMarkedCellCandidateCountTask, range(1, 6), {}),
        (PuzzlesSudokuUnitMissingDigitsCountTask, range(2, 7), {"unit_type": "row"}),
        (PuzzlesSudokuRepeatedDigitCountTask, range(0, 5), {"unit_type": "box"}),
    ),
)
def test_puzzles_sudoku_tasks_accept_declared_answer_support(
    task_cls,
    support,
    base_params: dict[str, int | str],
) -> None:
    task = task_cls()
    for answer_value in support:
        out = task.generate(
            40301 + int(answer_value),
            params={**base_params, "target_answer": int(answer_value)},
            max_attempts=64,
        )
        assert out.query_id == "single"
        assert int(out.answer_gt.value) == int(answer_value)


@pytest.mark.parametrize("unit_type", ("row", "column", "box"))
def test_puzzles_sudoku_highlighted_unit_tasks_accept_all_unit_types(
    unit_type: str,
) -> None:
    missing = PuzzlesSudokuUnitMissingDigitsCountTask().generate(
        40351,
        params={"target_answer": 4, "unit_type": unit_type},
        max_attempts=64,
    )
    repeated = PuzzlesSudokuRepeatedDigitCountTask().generate(
        40361,
        params={"target_answer": 2, "unit_type": unit_type},
        max_attempts=64,
    )
    assert (
        missing.trace_payload["execution_trace"]["highlighted_unit_type"] == unit_type
    )
    assert (
        repeated.trace_payload["execution_trace"]["highlighted_unit_type"] == unit_type
    )


def test_puzzles_sudoku_grid_is_deterministic() -> None:
    params = {
        "query_id": "single",
        "target_answer": 3,
        "unit_type": "row",
        "scene_variant": "filled_grid",
    }
    task = PuzzlesSudokuRepeatedDigitCountTask()
    out_a = task.generate(40241, params=params, max_attempts=64)
    out_b = task.generate(40241, params=params, max_attempts=64)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert (
        out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    )
    assert (
        out_a.trace_payload["query_spec"]["prompt_variant"]
        == out_b.trace_payload["query_spec"]["prompt_variant"]
    )
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzles_sudoku_grid_prompt_bundle_requires_rule_texts() -> None:
    bundle = json.loads(
        Path("prompts/puzzles/sudoku/puzzles_sudoku_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert bundle["schema_version"] == "v1"
    required = bundle["required_slots_by_key"]
    assert required["scene:visible_sudoku_grid"] == ["object_description"]
    assert required["query:unit_missing_digits_count"] == ["unit_scope_text"]
    assert required["query:repeated_digit_count"] == ["unit_scope_text"]
    static_slots = bundle["static_slots_by_key"]
    assert "marked_cell" in static_slots["query:marked_cell_value"]["annotation_hint"]
    assert (
        "constraint_cells"
        in static_slots["query:marked_cell_candidate_count"]["annotation_hint"]
    )


def test_puzzles_sudoku_grid_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_puzzles__sudoku__marked_cell_value"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_puzzles__sudoku__marked_cell_value",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_puzzles__sudoku__marked_cell_value",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=64,
        sampling_seed=97,
    )
    final_path = build_dataset(config, code_hash="puzzles-sudoku-grid-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "puzzles" for record in train_records)
    assert all(record["scene_id"] == "sudoku" for record in train_records)

    build_report = json.loads(
        (final_path / "build_report.json").read_text(encoding="utf-8")
    )
    assert (
        int(
            build_report["accepted_counts_by_task"][
                "task_puzzles__sudoku__marked_cell_value"
            ]
        )
        == 4
    )

    validation = json.loads(
        (final_path / "validation_report.json").read_text(encoding="utf-8")
    )
    assert validation["total_errors"] == 0
