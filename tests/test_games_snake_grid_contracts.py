"""Contract tests for games Snake-grid tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.snake.shared.common import safe_next_directions, shortest_static_path_to_food, simulate_snake_moves
from trace.tasks.games.snake.safe_direction_count import (
    GamesSnakeGridTask,
    GamesSnakeMoveSafetyTask,
    GamesSnakePathOutcomeTask,
    GamesSnakeShortestFoodPathLengthTask,
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
            GamesSnakeShortestFoodPathLengthTask,
            {"query_id": "shortest_food_path_length", "target_shortest_food_path_length": 5, "board_size": 8},
            "shortest_food_path_length",
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
    assert out.annotation_gt.type == "bbox_set"
    assert out.query_id == expected_query
    assert out.scene_id == "snake"
    assert trace["query_spec"]["query_id"] == expected_query
    assert execution["query_id"] == expected_query
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert len(out.annotation_gt.value) >= 1
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
    from trace.tasks.games.snake.shared.common import SnakeState

    state = SnakeState(
        board_size=int(state_payload["board_size"]),
        head=tuple(state_payload["head"]),
        body=tuple(tuple(coord) for coord in state_payload["body"]),
        food=tuple(state_payload["food"]),
        obstacles=tuple(tuple(coord) for coord in state_payload["obstacles"]),
    )
    assert int(out.answer_gt.value) == len(safe_next_directions(state)) == 3
    assert len(out.annotation_gt.value) == 3
    assert len(state.obstacles) >= 1


def test_games_snake_path_result_option_matches_simulation() -> None:
    out = GamesSnakePathOutcomeTask().generate(
        98230,
        params={"query_id": "path_result_option_label", "target_planned_outcome": "point"},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    state_payload = execution["state"]
    from trace.tasks.games.snake.shared.common import SnakeState

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


@pytest.mark.parametrize("target_length", tuple(range(1, 9)))
def test_games_snake_shortest_food_path_length_matches_trace(target_length: int) -> None:
    out = GamesSnakeShortestFoodPathLengthTask().generate(
        98250 + int(target_length),
        params={"query_id": "shortest_food_path_length", "target_shortest_food_path_length": int(target_length)},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    state_payload = execution["state"]
    from trace.tasks.games.snake.shared.common import SnakeState

    state = SnakeState(
        board_size=int(state_payload["board_size"]),
        head=tuple(state_payload["head"]),
        body=tuple(tuple(coord) for coord in state_payload["body"]),
        food=tuple(state_payload["food"]),
        obstacles=tuple(tuple(coord) for coord in state_payload["obstacles"]),
    )
    shortest_path = shortest_static_path_to_food(state)
    assert shortest_path is not None
    assert len(shortest_path) == int(target_length)
    assert int(out.answer_gt.value) == int(target_length)
    assert tuple(tuple(coord) for coord in execution["shortest_path_coords"]) == tuple(shortest_path)
    assert len(out.annotation_gt.value) == int(target_length)
    expected_ids = [f"cell_r{int(row)}_c{int(col)}" for row, col in shortest_path]
    assert execution["annotation_cell_ids"] == expected_ids


def test_games_snake_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__snake"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__snake",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__snake__safe_direction_count", count=1, params={}),
            BuildTaskConfig(task_id="task_games__snake__shortest_food_path_length", count=1, params={}),
            BuildTaskConfig(task_id="task_games__snake__path_outcome_option_label", count=1, params={}),
        ],
        max_attempts_per_instance=512,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-snake-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 3
    assert all(row["domain"] == "games" for row in rows)
    assert all(row.get("scene_id") == "snake" for row in rows)
