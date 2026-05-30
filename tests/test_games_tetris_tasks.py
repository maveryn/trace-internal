"""Contract tests for games Tetris tasks."""

from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.games.tetris.board_tasks import (
    GamesTetrisDropResultLabelTask,
    GamesTetrisLineClearCountTask,
    _Placement,
    _best_clear_outcomes,
    _evaluate_outcome,
    _freeze,
)


def _board_from_execution(execution: dict) -> tuple[tuple[str, ...], ...]:
    return _freeze(execution["board_rows"])


def test_games_tetris_line_clear_contract_and_rule_match() -> None:
    out = GamesTetrisLineClearCountTask().generate(
        26052401,
        params={"query_id": "max_clear_with_next_piece", "target_clear_count": 4, "board_rows": 14, "board_cols": 9},
        max_attempts=240,
    )
    execution = out.trace_payload["execution_trace"]
    placement_raw = execution["placement"]
    assert placement_raw is not None
    placement = _Placement(
        piece=str(placement_raw["piece"]),
        orientation_index=int(placement_raw["orientation_index"]),
        col=int(placement_raw["col"]),
        top=int(placement_raw["top"]),
    )
    board = _board_from_execution(execution)
    outcome = _evaluate_outcome(board, placement)
    best_clear, _best_outcomes = _best_clear_outcomes(board, piece=str(execution["piece"]))

    assert out.scene_id == "tetris"
    assert out.query_id == "max_clear_with_next_piece"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "keyed_bbox_map"
    assert int(out.answer_gt.value) == int(outcome.clear_count) == int(best_clear) == 4
    assert set(out.evidence_gt.value) == {"board", "next_piece"}
    assert out.trace_payload["projected_evidence"]["type"] == "keyed_bbox_map"
    assert set(out.trace_payload["projected_evidence"]["keyed_bbox_map"]) == {"board", "next_piece"}
    render_spec = out.trace_payload["render_spec"]
    assert render_spec["tetris_board_style"]["style_variant"]
    assert render_spec["text_style"]["font_family"]


def test_games_tetris_drop_result_contract() -> None:
    out = GamesTetrisDropResultLabelTask().generate(
        26052421,
        params={"query_id": "single_clear_result"},
        max_attempts=240,
    )
    execution = out.trace_payload["execution_trace"]
    answer = str(out.answer_gt.value)
    options = {str(option["label"]): option for option in execution["options"]}
    falling = execution["falling_placement"]

    assert out.scene_id == "tetris"
    assert out.query_id == "single_clear_result"
    assert out.answer_gt.type == "string"
    assert answer in options
    assert bool(options[answer]["is_answer"])
    assert execution["target_clear_count"] == 1
    assert falling is not None
    assert int(falling["top"]) == 0
    assert all(option["placement"] is None for option in execution["options"])
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert out.trace_payload["projected_evidence"]["type"] == "bbox_set"


def test_games_tetris_taxonomy() -> None:
    assert resolve_task_taxonomy("task_games__tetris__line_clear_count").scene_id == "tetris"
    assert resolve_task_taxonomy("task_games__tetris__drop_result_label").scene_id == "tetris"
