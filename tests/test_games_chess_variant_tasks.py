"""Contract tests for games chess-variant tasks."""

from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.games.chess_variant.board_tasks import (
    GamesChessVariantMarkedPieceDestinationCountTask,
    _evaluate_board,
    _with_query_evidence,
)
from trace.tasks.games.shared.chess_common import ChessPiece, freeze_board


def _board_from_execution(execution: dict) -> tuple[tuple[ChessPiece | None, ...], ...]:
    rows = []
    for row in execution["board_rows"]:
        parsed = []
        for value in row:
            if value is None:
                parsed.append(None)
                continue
            color, kind = str(value).split("_", 1)
            parsed.append(ChessPiece(color=color, kind=kind))
        rows.append(parsed)
    return freeze_board(rows)


def test_games_chess_variant_move_count_contract_and_rule_match() -> None:
    out = GamesChessVariantMarkedPieceDestinationCountTask().generate(
        26052401,
        params={
            "query_variant": "marked_piece_move_count",
            "rule_family": "straight_range",
            "range_k": 3,
            "target_answer": 4,
        },
        max_attempts=128,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    board = _board_from_execution(execution)
    marked = tuple(int(v) for v in execution["marked_coord"])
    evaluated = _with_query_evidence(
        board,
        _evaluate_board(
            board,
            marked_coord=marked,
            rule_family=str(execution["rule_family"]),
            range_k=int(execution["range_k"]),
        ),
        query_variant="marked_piece_move_count",
    )

    assert out.scene_id == "chess_variant"
    assert out.query_variant == "default"
    assert out.query_id == "marked_piece_move_count"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == int(evaluated.answer) == 4
    assert len(out.evidence_gt.value) == int(out.answer_gt.value)
    assert trace["query_spec"]["params"]["query_variant"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == "marked_piece_move_count"


def test_games_chess_variant_capture_count_contract_and_rule_match() -> None:
    out = GamesChessVariantMarkedPieceDestinationCountTask().generate(
        26052411,
        params={"query_variant": "marked_piece_capture_count", "rule_family": "leaper_2_1", "target_answer": 3},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    marked = tuple(int(v) for v in execution["marked_coord"])
    evaluated = _with_query_evidence(
        board,
        _evaluate_board(
            board,
            marked_coord=marked,
            rule_family=str(execution["rule_family"]),
            range_k=int(execution["range_k"]),
        ),
        query_variant="marked_piece_capture_count",
    )

    assert out.scene_id == "chess_variant"
    assert out.query_variant == "default"
    assert out.query_id == "marked_piece_capture_count"
    assert int(out.answer_gt.value) == int(evaluated.answer) == 3
    assert len(out.evidence_gt.value) == int(out.answer_gt.value)
    assert execution["evidence_kind"] == "cell"


def test_games_chess_variant_taxonomy() -> None:
    assert resolve_task_taxonomy("task_games__chess_variant__marked_piece_destination_count").scene_id == "chess_variant"
