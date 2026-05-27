"""Contract tests for games Sudoku-grid tasks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.shared.sudoku_common import (
    candidate_digits,
    coord_to_cell_id,
    missing_digits_in_unit,
    repeated_digits_in_unit,
    unit_coords,
)
from trace.tasks.games.shared.style import SUPPORTED_SUDOKU_STYLE_VARIANTS
from trace.tasks.games.sudoku.grid_tasks import (
    GamesSudokuGridTask,
    GamesSudokuMarkedCellCandidateCountTask,
    GamesSudokuMarkedCellValueTask,
    GamesSudokuRepeatedDigitCountTask,
    GamesSudokuUnitMissingDigitsCountTask,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query"),
    (
        (
            GamesSudokuMarkedCellValueTask,
            {"target_answer": 7, "scene_variant": "sparse_grid"},
            "marked_cell_value",
        ),
        (
            GamesSudokuMarkedCellCandidateCountTask,
            {"target_answer": 4, "scene_variant": "filled_grid"},
            "marked_cell_candidate_count",
        ),
        (
            GamesSudokuUnitMissingDigitsCountTask,
            {"target_answer": 4, "unit_type": "row", "scene_variant": "filled_grid"},
            "unit_missing_digits_count",
        ),
        (
            GamesSudokuRepeatedDigitCountTask,
            {"target_answer": 3, "unit_type": "box", "scene_variant": "sparse_grid"},
            "repeated_digit_count",
        ),
    ),
)
def test_games_sudoku_grid_emits_expected_contract(
    task_cls: type[GamesSudokuGridTask],
    params: dict[str, int | str],
    expected_query: str,
) -> None:
    out = task_cls().generate(40201, params=params, max_attempts=64)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_id == "default"
    assert out.query_id == str(expected_query)
    assert trace["query_spec"]["params"]["query_id"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == str(expected_query)
    assert execution["query_id"] == str(expected_query)
    assert execution["query_id"] == "default"
    assert int(execution["target_answer"]) == int(out.answer_gt.value)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value)


def test_games_sudoku_marked_cell_value_has_unique_candidate() -> None:
    out = GamesSudokuMarkedCellValueTask().generate(
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
    assert str(coord_to_cell_id(marked_cell)) in set(execution["evidence_entity_ids"])


def test_games_sudoku_marked_cell_candidate_count_matches_candidates() -> None:
    out = GamesSudokuMarkedCellCandidateCountTask().generate(
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
    assert set(int(value) for value in execution["candidate_digit_values"]) == set(candidates)
    assert str(coord_to_cell_id(marked_cell)) in set(execution["evidence_entity_ids"])


def test_games_sudoku_missing_digits_match_highlighted_unit() -> None:
    out = GamesSudokuUnitMissingDigitsCountTask().generate(
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
    evidence_coords = {tuple(coord) for coord in execution["evidence_coords"]}

    assert len(missing) == int(out.answer_gt.value) == 5
    assert set(int(value) for value in execution["missing_digit_values"]) == set(missing)
    assert evidence_coords <= unit
    assert all(int(board[row][col]) != 0 for row, col in evidence_coords)


def test_games_sudoku_repeated_digits_match_highlighted_unit() -> None:
    out = GamesSudokuRepeatedDigitCountTask().generate(
        40231,
        params={"target_answer": 2, "unit_type": "box"},
        max_attempts=64,
    )
    execution = out.trace_payload["execution_trace"]
    board = tuple(tuple(int(value) for value in row) for row in execution["board_rows"])
    unit_type = str(execution["highlighted_unit_type"])
    unit_index = int(execution["highlighted_unit_index"])
    repeated = repeated_digits_in_unit(board, unit_type=unit_type, unit_index=unit_index)
    unit = set(unit_coords(unit_type, unit_index))
    evidence_coords = {tuple(coord) for coord in execution["evidence_coords"]}

    assert len(repeated) == int(out.answer_gt.value) == 2
    assert set(int(value) for value in execution["repeated_digit_values"]) == set(repeated)
    assert evidence_coords <= unit
    assert all(int(board[row][col]) in set(repeated) for row, col in evidence_coords)


def test_games_sudoku_grid_query_cycle_covers_answer_scene_unit_and_style_support() -> None:
    task = GamesSudokuGridTask()
    answers_by_query: dict[str, set[int]] = {
        "marked_cell_value": set(),
        "marked_cell_candidate_count": set(),
        "unit_missing_digits_count": set(),
        "repeated_digit_count": set(),
    }
    scenes_by_query: dict[str, set[str]] = {key: set() for key in answers_by_query}
    units_by_query: dict[str, set[str]] = {key: set() for key in answers_by_query}
    styles_by_query: dict[str, set[str]] = {key: set() for key in answers_by_query}

    for sampling_index in range(135):
        out = task.generate(
            40301 + int(sampling_index),
            params={},
            max_attempts=64,
        )
        execution = out.trace_payload["execution_trace"]
        query = str(out.query_id or out.query_id)
        answers_by_query[query].add(int(out.answer_gt.value))
        scenes_by_query[query].add(str(execution["scene_variant"]))
        styles_by_query[query].add(str(execution["style_variant"]))
        if execution["highlighted_unit_type"] is not None:
            units_by_query[query].add(str(execution["highlighted_unit_type"]))

    assert answers_by_query == {
        "marked_cell_value": set(range(1, 10)),
        "marked_cell_candidate_count": {1, 2, 3, 4, 5},
        "unit_missing_digits_count": {2, 3, 4, 5, 6},
        "repeated_digit_count": {1, 2, 3, 4},
    }
    assert all(values == {"sparse_grid", "filled_grid"} for values in scenes_by_query.values())
    assert all(values == set(SUPPORTED_SUDOKU_STYLE_VARIANTS) for values in styles_by_query.values())
    assert units_by_query["unit_missing_digits_count"] == {"row", "column", "box"}
    assert units_by_query["repeated_digit_count"] == {"row", "column", "box"}


def test_games_sudoku_grid_is_deterministic() -> None:
    params = {
        "query_id": "repeated_digit_count",
        "target_answer": 3,
        "unit_type": "row",
        "scene_variant": "filled_grid",
    }
    task = GamesSudokuGridTask()
    out_a = task.generate(40241, params=params, max_attempts=64)
    out_b = task.generate(40241, params=params, max_attempts=64)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_sudoku_grid_prompt_bundle_requires_rule_texts() -> None:
    bundle = json.loads(Path("prompts/games/sudoku/games_sudoku_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:marked_cell_value"] == ["sudoku_rule_text", "marked_cell_rule_text"]
    assert required["query:marked_cell_candidate_count"] == ["sudoku_rule_text", "marked_cell_rule_text"]
    assert required["query:unit_missing_digits_count"] == ["highlighted_unit_rule_text", "unit_scope_text"]
    assert required["query:repeated_digit_count"] == ["highlighted_unit_rule_text", "unit_scope_text"]


def test_games_sudoku_grid_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__sudoku__marked_cell_value"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__sudoku__marked_cell_value",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__sudoku__marked_cell_value",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=64,
        sampling_seed=97,
    )
    final_path = build_dataset(config, code_hash="games-sudoku-grid-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record["task_group"] == "sudoku" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games__sudoku__marked_cell_value"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
