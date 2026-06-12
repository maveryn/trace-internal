"""Contract tests for games chess-variant tasks."""

from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.games.chess_variant.marked_piece_destination_count import GamesChessVariantMarkedPieceDestinationCountTask
from trace.tasks.games.chess_variant.shared.mechanics import (
    evaluate_marked_piece_board,
    evaluate_target_square_reachers,
    with_destination_annotation,
)
from trace.tasks.games.chess_variant.shared.prompts import prompt_defaults
from trace.tasks.games.chess_variant.target_square_reacher_count import GamesChessVariantTargetSquareReacherCountTask
from trace.tasks.games.shared.piece_board_rules import ChessPiece, freeze_board, validate_square_chess_material


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


def _bbox_center(bbox: list[float]) -> list[float]:
    return [
        round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
        round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
    ]


def _assert_point_annotation_matches_piece_ids(trace: dict, annotation: list[list[float]]) -> None:
    execution = trace["execution_trace"]
    expected = [
        _bbox_center(trace["render_map"]["piece_bboxes_px"][str(entity_id)])
        for entity_id in execution["annotation_entity_ids"]
    ]
    assert annotation == expected
    assert trace["projected_annotation"]["type"] == "point_set"
    assert trace["projected_annotation"]["point_set"] == annotation
    assert trace["projected_annotation"]["pixel_point_set"] == annotation


def test_games_chess_variant_move_count_contract_and_rule_match() -> None:
    out = GamesChessVariantMarkedPieceDestinationCountTask().generate(
        26052401,
        params={
            "query_id": "marked_piece_move_count",
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
    evaluated = with_destination_annotation(
        evaluate_marked_piece_board(
            board,
            marked_coord=marked,
            rule_family=str(execution["rule_family"]),
            range_k=int(execution["range_k"]),
        ),
        destination_mode="move",
    )

    assert out.scene_id == "chess_variant"
    assert out.query_id == "marked_piece_move_count"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == int(evaluated.answer) == 4
    assert len(out.annotation_gt.value) == int(out.answer_gt.value)
    assert trace["query_spec"]["query_id"] == "marked_piece_move_count"
    assert trace["query_spec"]["params"]["query_id"] == "marked_piece_move_count"
    assert "panel_scene_style" in trace["render_spec"]
    assert "text_style" in trace["render_spec"]


def test_games_chess_variant_capture_count_contract_and_rule_match() -> None:
    out = GamesChessVariantMarkedPieceDestinationCountTask().generate(
        26052411,
        params={"query_id": "marked_piece_capture_count", "rule_family": "leaper_2_1", "target_answer": 3},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    marked = tuple(int(v) for v in execution["marked_coord"])
    evaluated = with_destination_annotation(
        evaluate_marked_piece_board(
            board,
            marked_coord=marked,
            rule_family=str(execution["rule_family"]),
            range_k=int(execution["range_k"]),
        ),
        destination_mode="capture",
    )

    assert out.scene_id == "chess_variant"
    assert out.query_id == "marked_piece_capture_count"
    assert int(out.answer_gt.value) == int(evaluated.answer) == 3
    assert len(out.annotation_gt.value) == int(out.answer_gt.value)
    assert execution["annotation_kind"] == "cell"


def test_games_chess_variant_white_target_square_reacher_count_contract_and_rule_match() -> None:
    out = GamesChessVariantTargetSquareReacherCountTask().generate(
        26052421,
        params={
            "query_id": "white_piece_reaches_target_count",
            "rule_family": "straight_range",
            "range_k": 3,
            "target_answer": 3,
        },
        max_attempts=256,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    board = _board_from_execution(execution)
    target = tuple(int(v) for v in execution["target_coord"])
    evaluated = evaluate_target_square_reachers(
        board,
        target_coord=target,
        target_color="white",
        rule_family=str(execution["rule_family"]),
        range_k=int(execution["range_k"]),
    )

    assert out.scene_id == "chess_variant"
    assert out.query_id == "white_piece_reaches_target_count"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "point_set"
    assert int(out.answer_gt.value) == int(evaluated.answer) == 3
    assert len(out.annotation_gt.value) == int(out.answer_gt.value)
    assert execution["marker_role"] == "target_square"
    assert execution["target_color"] == "white"
    assert execution["marked_piece"] is None
    assert execution["annotation_kind"] == "piece_point"
    assert set(execution["annotation_entity_ids"]) == set(evaluated.annotation_entity_ids)
    assert set(tuple(coord) for coord in execution["annotation_coords"]) == set(evaluated.annotation_coords)
    _assert_point_annotation_matches_piece_ids(trace, out.annotation_gt.value)


def test_games_chess_variant_black_target_square_reacher_count_contract_and_rule_match() -> None:
    out = GamesChessVariantTargetSquareReacherCountTask().generate(
        26052431,
        params={
            "query_id": "black_piece_reaches_target_count",
            "rule_family": "leaper_2_1",
            "target_answer": 2,
        },
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    target = tuple(int(v) for v in execution["target_coord"])
    evaluated = evaluate_target_square_reachers(
        board,
        target_coord=target,
        target_color="black",
        rule_family=str(execution["rule_family"]),
        range_k=int(execution["range_k"]),
    )

    assert out.query_id == "black_piece_reaches_target_count"
    assert out.annotation_gt.type == "point_set"
    assert int(out.answer_gt.value) == int(evaluated.answer) == 2
    assert len(out.annotation_gt.value) == int(out.answer_gt.value)
    assert execution["target_color"] == "black"
    assert set(execution["annotation_entity_ids"]) == set(evaluated.annotation_entity_ids)


def test_games_chess_variant_target_square_zero_count_uses_empty_point_set() -> None:
    out = GamesChessVariantTargetSquareReacherCountTask().generate(
        26052441,
        params={
            "query_id": "white_piece_reaches_target_count",
            "rule_family": "diagonal_range",
            "range_k": 2,
            "target_answer": 0,
        },
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]

    assert int(out.answer_gt.value) == 0
    assert out.annotation_gt.type == "point_set"
    assert out.annotation_gt.value == []
    assert execution["annotation_entity_ids"] == []
    assert execution["annotation_coords"] == []
    assert out.trace_payload["projected_annotation"]["point_set"] == []
    assert out.trace_payload["projected_annotation"]["pixel_point_set"] == []


def test_games_chess_variant_taxonomy() -> None:
    assert resolve_task_taxonomy("task_games__chess_variant__marked_piece_destination_count").scene_id == "chess_variant"
    assert resolve_task_taxonomy("task_games__chess_variant__target_square_reacher_count").scene_id == "chess_variant"


def test_games_chess_variant_prompt_is_marker_color_neutral() -> None:
    prompt = prompt_defaults()

    assert "outlined square" in str(prompt["marked_piece_rule_text"]).lower()
    assert "red outlined square" in str(prompt["marked_piece_rule_text"]).lower()
    assert "piece" in str(prompt["marked_piece_rule_text"]).lower()
    assert "token" not in str(prompt["marked_piece_rule_text"]).lower()
    assert "blue" not in str(prompt["marked_piece_rule_text"]).lower()
    assert "blue outlined square" in str(prompt["target_square_rule_text"]).lower()
    assert "pixel-space points" in str(prompt["annotation_hint_white_piece_reaches_target_count"])
    assert "pixel-space points" in str(prompt["annotation_hint_black_piece_reaches_target_count"])


def test_games_chess_variant_boards_are_material_plausible() -> None:
    task_params = (
        {
            "query_id": "marked_piece_move_count",
            "rule_family": "straight_range",
            "range_k": 3,
            "target_answer": 3,
        },
        {
            "query_id": "marked_piece_capture_count",
            "rule_family": "leaper_2_1",
            "target_answer": 2,
        },
        {
            "query_id": "white_piece_reaches_target_count",
            "rule_family": "diagonal_range",
            "range_k": 3,
            "target_answer": 2,
        },
        {
            "query_id": "black_piece_reaches_target_count",
            "rule_family": "straight_or_diagonal_range",
            "range_k": 2,
            "target_answer": 3,
        },
    )
    for offset, params in enumerate(task_params):
        task_cls = (
            GamesChessVariantTargetSquareReacherCountTask
            if str(params["query_id"]) in {"white_piece_reaches_target_count", "black_piece_reaches_target_count"}
            else GamesChessVariantMarkedPieceDestinationCountTask
        )
        out = task_cls().generate(26052500 + int(offset), params=params, max_attempts=256)
        board = _board_from_execution(out.trace_payload["execution_trace"])
        assert validate_square_chess_material(board)
