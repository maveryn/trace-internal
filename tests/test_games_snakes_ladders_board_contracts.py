"""Contract tests for games Snakes and Ladders board tasks."""

from __future__ import annotations

from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.shared.snakes_ladders_common import (
    SUPPORTED_SNAKES_LADDERS_STYLE_VARIANTS,
    apply_die_roll,
    best_final_square,
    square_to_cell_id,
)
from trace.tasks.games.snakes_ladders.board_tasks import (
    GamesSnakesLaddersBestRollValueTask,
    GamesSnakesLaddersMoveOutcomeValueTask,
)
from tests.helpers import read_jsonl


def _jumps_from_trace(execution: dict) -> tuple:
    """Return jump dataclasses from trace dictionaries."""

    from trace.tasks.games.shared.snakes_ladders_common import SnakesLaddersJump

    return tuple(
        SnakesLaddersJump(
            jump_id=str(jump["jump_id"]),
            kind=str(jump["kind"]),
            start_square=int(jump["start_square"]),
            end_square=int(jump["end_square"]),
        )
        for jump in execution["jumps"]
    )


def test_games_snakes_ladders_move_outcome_matches_trace() -> None:
    out = GamesSnakesLaddersMoveOutcomeValueTask().generate(
        68101,
        params={"target_answer": 31, "die_value": 5},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    jumps = _jumps_from_trace(execution)
    move = apply_die_roll(int(execution["start_square"]), 5, jumps, board_side=int(execution["board_side"]))

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(move.final_square) == 31
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_variant == "default"
    assert out.query_id == "move_outcome_value"
    assert out.scene_id == "snakes_ladders"
    assert execution["query_variant"] == "default"
    assert execution["board_side"] in {5, 6, 7}
    assert trace_value(out, "query_spec", "params", "query_variant") == "default"
    assert trace_value(out, "query_spec", "params", "query_id") == "move_outcome_value"
    assert trace_value(out, "projected_evidence", "bbox_set") == out.evidence_gt.value
    assert "die" in execution["evidence_entity_ids"]

def test_games_snakes_ladders_best_roll_returns_best_final_square() -> None:
    out = GamesSnakesLaddersBestRollValueTask().generate(
        68140,
        params={"target_answer": 49, "horizon_roll_count": 2},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    answer = best_final_square(
        int(execution["start_square"]),
        int(execution["horizon_roll_count"]),
        _jumps_from_trace(execution),
        board_side=int(execution["board_side"]),
    )

    assert int(out.answer_gt.value) == int(answer) == 49
    assert out.query_id == "best_roll_value"
    assert out.query_variant == "default"
    assert execution["board_side"] == 7
    assert len(execution["optimal_route"]) == 2
    assert execution["best_final_square"] == 49
    assert execution["evidence_entity_ids"] == [square_to_cell_id(49)]
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1


def test_games_snakes_ladders_sampling_cycles_cover_axes() -> None:
    move_task = GamesSnakesLaddersMoveOutcomeValueTask()
    best_task = GamesSnakesLaddersBestRollValueTask()
    move_answers: set[int] = set()
    best_answers: set[int] = set()
    horizons: set[int] = set()
    board_sides: set[int] = set()
    styles: set[str] = set()

    for index in range(96):
        out = move_task.generate(68200 + index, params={}, max_attempts=512)
        move_answers.add(int(out.answer_gt.value))
        board_sides.add(int(out.trace_payload["execution_trace"]["board_side"]))
        styles.add(str(out.trace_payload["execution_trace"]["style_variant"]))

    for index in range(96):
        out = best_task.generate(68400 + index, params={}, max_attempts=512)
        best_answers.add(int(out.answer_gt.value))
        horizons.add(int(out.trace_payload["execution_trace"]["horizon_roll_count"]))

    assert len(move_answers) >= 30
    assert len(best_answers) >= 25
    assert min(best_answers) >= 14
    assert max(best_answers) <= 49
    assert board_sides == {5, 6, 7}
    assert horizons == {1, 2}
    assert styles == set(SUPPORTED_SNAKES_LADDERS_STYLE_VARIANTS)


def test_games_snakes_ladders_generation_is_deterministic() -> None:
    params = {"target_answer": 49, "horizon_roll_count": 2, "style_variant": "paper"}
    task = GamesSnakesLaddersBestRollValueTask()
    out_a = task.generate(68500, params=params, max_attempts=512)
    out_b = task.generate(68500, params=params, max_attempts=512)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_snakes_ladders_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__snakes_ladders"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__snakes_ladders",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__snakes_ladders__move_outcome_value", count=1, params={}),
            BuildTaskConfig(task_id="task_games__snakes_ladders__best_roll_value", count=1, params={}),
        ],
        max_attempts_per_instance=512,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-snakes-ladders-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 2
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["scene_id"] == "snakes_ladders" for row in rows)


def trace_value(out, *keys):
    """Read a nested trace value in tests."""

    value = out.trace_payload
    for key in keys:
        value = value[key]
    return value
