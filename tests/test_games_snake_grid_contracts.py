"""Contract tests for games Snake-grid tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.shared.snake_common import safe_next_directions, simulate_snake_moves
from trace.tasks.games.snake.grid_tasks import (
    GamesSnakeGridTask,
    GamesSnakeMoveSafetyTask,
    GamesSnakePathOutcomeTask,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query", "expected_type"),
    (
        (
            GamesSnakeMoveSafetyTask,
            {"query_id": "safe_direction_count", "target_safe_direction_count": 2, "board_size": 8},
            "safe_direction_count",
            "integer",
        ),
        (
            GamesSnakePathOutcomeTask,
            {"query_id": "path_result_option_label", "target_planned_outcome": "game_over", "board_size": 8},
            "path_result_option_label",
            "option_letter",
        ),
    ),
)
def test_games_snake_public_tasks_emit_expected_contract(
    task_cls: type[GamesSnakeGridTask],
    params: dict[str, int | str],
    expected_query: str,
    expected_type: str,
) -> None:
    out = task_cls().generate(98200, params=params, max_attempts=512)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == expected_type
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_id == "default"
    assert out.query_id == expected_query
    assert out.scene_id == "snake"
    assert trace["query_spec"]["query_id"] == expected_query
    assert trace["query_spec"]["query_id"] == "default"
    assert execution["query_id"] == expected_query
    assert execution["query_id"] == "default"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(out.evidence_gt.value) >= 1
    if expected_type == "option_letter":
        assert str(out.answer_gt.value) in {"A", "B", "C", "D"}
        assert len(execution["result_options"]) == 4
        assert [option["label"] for option in execution["result_options"]] == ["A", "B", "C", "D"]
        assert sum(1 for option in execution["result_options"] if option["kind"] == "game_over") == 1
        assert sum(1 for option in execution["result_options"] if option["is_answer"]) == 1
        answer_options = [option for option in execution["result_options"] if option["label"] == out.answer_gt.value]
        assert len(answer_options) == 1
        assert answer_options[0]["is_answer"] is True


def test_games_snake_safe_count_matches_trace() -> None:
    out = GamesSnakeMoveSafetyTask().generate(
        98210,
        params={"query_id": "safe_direction_count", "target_safe_direction_count": 3},
        max_attempts=512,
    )
    state_payload = out.trace_payload["execution_trace"]["state"]
    from trace.tasks.games.shared.snake_common import SnakeState

    state = SnakeState(
        board_size=int(state_payload["board_size"]),
        head=tuple(state_payload["head"]),
        body=tuple(tuple(coord) for coord in state_payload["body"]),
        food=tuple(state_payload["food"]),
        obstacles=tuple(tuple(coord) for coord in state_payload["obstacles"]),
    )
    assert int(out.answer_gt.value) == len(safe_next_directions(state)) == 3
    assert len(out.evidence_gt.value) == 3
    assert len(state.obstacles) >= 1


def test_games_snake_path_result_option_matches_simulation() -> None:
    out = GamesSnakePathOutcomeTask().generate(
        98230,
        params={"query_id": "path_result_option_label", "target_planned_outcome": "point"},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    state_payload = execution["state"]
    from trace.tasks.games.shared.snake_common import SnakeState

    state = SnakeState(
        board_size=int(state_payload["board_size"]),
        head=tuple(state_payload["head"]),
        body=tuple(tuple(coord) for coord in state_payload["body"]),
        food=tuple(state_payload["food"]),
        obstacles=tuple(tuple(coord) for coord in state_payload["obstacles"]),
    )
    simulation = simulate_snake_moves(state, tuple(execution["planned_moves"]))
    answer_option = next(option for option in execution["result_options"] if option["label"] == out.answer_gt.value)
    assert answer_option["kind"] == "point"
    assert tuple(answer_option["coord"]) == tuple(simulation.final_head)
    assert simulation.outcome not in {"body", "wall", "food"}


def test_games_snake_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__snake"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__snake",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__snake__safe_direction_count", count=1, params={}),
            BuildTaskConfig(task_id="task_games__snake__path_outcome_option_label", count=1, params={}),
        ],
        max_attempts_per_instance=512,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-snake-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 2
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["task_group"] == "snake" for row in rows)
