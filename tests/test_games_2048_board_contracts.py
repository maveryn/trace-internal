"""Contract tests for games 2048-board tasks."""

from __future__ import annotations

import pytest

from trace.tasks.games.shared.twenty_forty_eight_common import (
    SUPPORTED_2048_STYLE_VARIANTS,
    board_max_tile,
    coord_to_cell_id,
    goal_cell_name_to_coord,
    simulate_2048_move,
)
from trace.tasks.games.twenty_forty_eight.board_tasks import (
    Games2048BestMoveLabelTask,
    Games2048MoveResultValueTask,
)


def _board(rows: list[list[int]]) -> tuple[tuple[int, ...], ...]:
    """Return a trace board as immutable rows."""

    return tuple(tuple(int(value) for value in row) for row in rows)


def _source_ids_for_max(result) -> tuple[str, ...]:
    """Return source cell ids for the unique max tile after a move."""

    max_value = board_max_tile(result.after)
    max_cells = [
        coord
        for coord, sources in result.result_sources.items()
        if int(result.after[coord[0]][coord[1]]) == int(max_value) and sources
    ]
    return tuple(coord_to_cell_id(coord) for cell in max_cells for coord in result.result_sources[cell])


@pytest.mark.parametrize(
    ("params", "expected_query", "expected_answer"),
    (
        ({"query_id": "merge_count", "target_answer": 3}, "merge_count", 3),
        ({"query_id": "score_value", "target_answer": 40}, "score_value", 40),
        ({"query_id": "max_tile_value", "target_answer": 128}, "max_tile_value", 128),
    ),
)
def test_games_2048_move_result_value_emits_expected_contract(
    params: dict[str, int | str],
    expected_query: str,
    expected_answer: int,
) -> None:
    out = Games2048MoveResultValueTask().generate(204801, params=params, max_attempts=128)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_id == "default"
    assert out.query_id == expected_query
    assert out.scene_id == "2048"
    assert trace["query_spec"]["params"]["query_id"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == expected_query
    assert execution["query_id"] == "default"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value)


def test_games_2048_move_result_value_matches_standard_move_simulation() -> None:
    out = Games2048MoveResultValueTask().generate(
        204811,
        params={"query_id": "score_value", "target_answer": 24, "move_direction": "left"},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    result = simulate_2048_move(_board(execution["board_before"]), str(execution["move_direction"]))
    expected_ids = tuple(coord_to_cell_id(coord) for pair in result.merge_pairs for coord in pair)

    assert int(out.answer_gt.value) == int(result.score) == 24
    assert tuple(execution["evidence_entity_ids"]) == expected_ids
    assert execution["move_result"]["after"] == [[int(value) for value in row] for row in result.after]


def test_games_2048_max_tile_evidence_uses_source_cells_for_unique_max() -> None:
    out = Games2048MoveResultValueTask().generate(
        204812,
        params={"query_id": "max_tile_value", "target_answer": 256, "move_direction": "up"},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    result = simulate_2048_move(_board(execution["board_before"]), str(execution["move_direction"]))

    assert int(out.answer_gt.value) == board_max_tile(result.after) == 256
    assert tuple(execution["evidence_entity_ids"]) == _source_ids_for_max(result)
    assert len(out.evidence_gt.value) == 2


def test_games_2048_best_move_label_has_unique_goal_cell_winner() -> None:
    out = Games2048BestMoveLabelTask().generate(
        204821,
        params={"target_label": "H", "goal_cell": "bottom_right"},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board(execution["board_before"])
    goal_cell = tuple(int(value) for value in execution["goal_cell"])
    label_by_direction = {str(key): str(value) for key, value in execution["move_label_by_direction"].items()}
    values = {
        direction: int(simulate_2048_move(board, direction).after[goal_cell[0]][goal_cell[1]])
        for direction in label_by_direction
    }
    best_value = max(values.values())
    best_directions = [direction for direction, value in values.items() if int(value) == int(best_value)]
    best_direction = best_directions[0]
    result = simulate_2048_move(board, best_direction)
    expected_ids = tuple(coord_to_cell_id(coord) for coord in result.result_sources[goal_cell])

    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == "H"
    assert len(best_directions) == 1
    assert int(best_value) > 0
    assert label_by_direction[best_direction] == out.answer_gt.value
    assert tuple(execution["evidence_entity_ids"]) == expected_ids


def test_games_2048_query_cycles_cover_supports() -> None:
    value_task = Games2048MoveResultValueTask()
    label_task = Games2048BestMoveLabelTask()
    queries: set[str] = set()
    answers_by_query: dict[str, set[int]] = {"merge_count": set(), "score_value": set(), "max_tile_value": set()}
    styles: set[str] = set()
    labels: set[str] = set()
    goals: set[tuple[int, int]] = set()

    for sampling_index in range(240):
        out = value_task.generate(
            204900 + int(sampling_index),
            params={},
            max_attempts=128,
        )
        execution = out.trace_payload["execution_trace"]
        queries.add(str(out.query_id))
        answers_by_query[str(out.query_id)].add(int(out.answer_gt.value))
        styles.add(str(execution["style_variant"]))

    for sampling_index in range(96):
        out = label_task.generate(
            205300 + int(sampling_index),
            params={},
            max_attempts=128,
        )
        execution = out.trace_payload["execution_trace"]
        labels.add(str(out.answer_gt.value))
        goals.add(tuple(int(value) for value in execution["goal_cell"]))

    assert queries == {"merge_count", "score_value", "max_tile_value"}
    assert answers_by_query["merge_count"] == {0, 1, 2, 3, 4}
    assert answers_by_query["score_value"] == {0, 4, 8, 12, 16, 24, 32, 40}
    assert answers_by_query["max_tile_value"] == {16, 32, 64, 128, 256}
    assert styles == set(SUPPORTED_2048_STYLE_VARIANTS)
    assert labels == set("ABCDEFGH")
    assert goals == {goal_cell_name_to_coord(name) for name in ("top_left", "top_right", "bottom_left", "bottom_right")}


def test_games_2048_generation_is_deterministic() -> None:
    params = {"query_id": "max_tile_value", "target_answer": 64, "move_direction": "down"}
    task = Games2048MoveResultValueTask()
    out_a = task.generate(204831, params=params, max_attempts=128)
    out_b = task.generate(204831, params=params, max_attempts=128)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
