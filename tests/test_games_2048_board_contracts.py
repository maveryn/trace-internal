"""Contract tests for games 2048-board tasks."""

from __future__ import annotations

import pytest

from trace.tasks.games.shared.twenty_forty_eight_common import (
    SUPPORTED_2048_STYLE_VARIANTS,
    board_max_tile,
    coord_to_cell_id,
    simulate_2048_move,
)
from trace.tasks.games.twenty_forty_eight.board_tasks import (
    Games2048MaxTileValueTask,
    Games2048MergeCountTask,
    Games2048MoveResultBoardLabelTask,
    Games2048ScoreValueTask,
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


def _task_for_query(query_id: str):
    if query_id == "merge_count":
        return Games2048MergeCountTask()
    if query_id == "score_value":
        return Games2048ScoreValueTask()
    if query_id == "max_tile_value":
        return Games2048MaxTileValueTask()
    raise AssertionError(f"unexpected 2048 query_id={query_id!r}")


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
    out = _task_for_query(str(params["query_id"])).generate(204801, params=params, max_attempts=128)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.annotation_gt.type == "bbox_set"
    assert out.query_id == expected_query
    assert out.scene_id == "2048"
    assert trace["query_spec"]["params"]["query_id"] == expected_query
    assert execution["query_id"] == expected_query
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert len(execution["annotation_entity_ids"]) == len(out.annotation_gt.value)
    assert trace["render_spec"]["canvas_width"] <= 900
    assert trace["render_spec"]["canvas_height"] <= 900
    assert float(trace["render_spec"]["effective_cell_size_px"]) >= 28.0
    assert trace["render_spec"]["text_style"]["font_family"]
    assert trace["render_map"]["font_family"] == trace["render_spec"]["text_style"]["font_family"]


def test_games_2048_move_result_value_matches_standard_move_simulation() -> None:
    out = Games2048ScoreValueTask().generate(
        204811,
        params={"query_id": "score_value", "target_answer": 24, "move_direction": "left"},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    result = simulate_2048_move(_board(execution["board_before"]), str(execution["move_direction"]))
    expected_ids = tuple(coord_to_cell_id(coord) for pair in result.merge_pairs for coord in pair)

    assert int(out.answer_gt.value) == int(result.score) == 24
    assert tuple(execution["annotation_entity_ids"]) == expected_ids
    assert execution["move_result"]["after"] == [[int(value) for value in row] for row in result.after]


def test_games_2048_max_tile_annotation_uses_source_cells_for_unique_max() -> None:
    out = Games2048MaxTileValueTask().generate(
        204812,
        params={"query_id": "max_tile_value", "target_answer": 256, "move_direction": "up"},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    result = simulate_2048_move(_board(execution["board_before"]), str(execution["move_direction"]))

    assert int(out.answer_gt.value) == board_max_tile(result.after) == 256
    assert tuple(execution["annotation_entity_ids"]) == _source_ids_for_max(result)
    assert len(out.annotation_gt.value) == 2


def test_games_2048_move_result_board_label_has_unique_option_board() -> None:
    out = Games2048MoveResultBoardLabelTask().generate(
        204841,
        params={"target_label": "F", "move_direction": "left"},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board(execution["board_before"])
    result = simulate_2048_move(board, str(execution["move_direction"]))
    options = {
        str(label): _board(option_board)
        for label, option_board in execution["result_option_boards"].items()
    }
    matching_labels = [label for label, option_board in options.items() if option_board == result.after]

    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == "F"
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 1
    assert matching_labels == ["F"]
    assert tuple(execution["annotation_entity_ids"]) == ("result_option_F",)
    assert out.trace_payload["projected_annotation"]["bbox_set"] == out.annotation_gt.value


def test_games_2048_query_cycles_cover_supports() -> None:
    value_tasks = (Games2048MergeCountTask(), Games2048ScoreValueTask(), Games2048MaxTileValueTask())
    result_board_task = Games2048MoveResultBoardLabelTask()
    queries: set[str] = set()
    answers_by_query: dict[str, set[int]] = {"merge_count": set(), "score_value": set(), "max_tile_value": set()}
    styles: set[str] = set()
    result_labels: set[str] = set()

    for sampling_index in range(240):
        value_task = value_tasks[int(sampling_index) % len(value_tasks)]
        out = value_task.generate(
            204900 + int(sampling_index),
            params={},
            max_attempts=128,
        )
        execution = out.trace_payload["execution_trace"]
        queries.add(str(out.query_id))
        answers_by_query[str(out.query_id)].add(int(out.answer_gt.value))
        styles.add(str(execution["style_variant"]))

    for sampling_index in range(72):
        out = result_board_task.generate(
            205600 + int(sampling_index),
            params={},
            max_attempts=128,
        )
        result_labels.add(str(out.answer_gt.value))

    assert queries == {"merge_count", "score_value", "max_tile_value"}
    assert answers_by_query["merge_count"] == {0, 1, 2, 3, 4}
    assert answers_by_query["score_value"] == {0, 4, 8, 12, 16, 24, 32, 40}
    assert answers_by_query["max_tile_value"] == {16, 32, 64, 128, 256}
    assert styles == set(SUPPORTED_2048_STYLE_VARIANTS)
    assert result_labels == set("ABCDEF")


def test_games_2048_generation_is_deterministic() -> None:
    params = {"query_id": "max_tile_value", "target_answer": 64, "move_direction": "down"}
    task = Games2048MaxTileValueTask()
    out_a = task.generate(204831, params=params, max_attempts=128)
    out_b = task.generate(204831, params=params, max_attempts=128)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
