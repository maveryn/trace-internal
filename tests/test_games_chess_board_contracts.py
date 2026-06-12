"""Contract tests for games Chess-board tasks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image, ImageDraw

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.chess.checkmate_move_label import GamesChessCheckmateMoveLabelTask
from trace.tasks.games.chess.colored_piece_kind_count import GamesChessColoredPieceKindCountTask
from trace.tasks.games.chess.king_escape_square_count import GamesChessKingEscapeSquareCountTask
from trace.tasks.games.chess.marked_piece_blocker_count import GamesChessMarkedPieceBlockerCountTask
from trace.tasks.games.chess.marked_piece_destination_count import GamesChessMarkedPieceDestinationCountTask
from trace.tasks.games.chess.piece_kind_count import GamesChessPieceKindCountTask
from trace.tasks.games.chess.player_capture_piece_count import GamesChessPlayerCapturePieceCountTask
from trace.tasks.games.chess.target_square_attacker_count import GamesChessTargetSquareAttackerCountTask
from trace.tasks.games.shared.piece_board_rules import (
    ChessPiece,
    attackers_to_square,
    capturable_opponent_coords,
    coord_to_cell_id,
    freeze_board,
    king_escape_squares,
    move_checkmates,
    opponent,
    piece_attacks_square,
    piece_capture_targets,
    piece_move_destinations,
    piece_to_entity_id,
    validate_square_chess_material,
)
from trace.tasks.games.shared.piece_board_renderer import _FILLED_PIECE_CODEPOINTS, _fit_chess_symbol_font
from trace.tasks.shared.text_rendering import temporary_default_font_family
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query"),
    (
        (
            GamesChessMarkedPieceDestinationCountTask,
            {"query_id": "marked_piece_move_count", "target_answer": 4, "scene_variant": "sparse_board"},
            "marked_piece_move_count",
        ),
        (
            GamesChessMarkedPieceDestinationCountTask,
            {"query_id": "marked_piece_capture_count", "target_answer": 2, "scene_variant": "crowded_board"},
            "marked_piece_capture_count",
        ),
        (
            GamesChessPlayerCapturePieceCountTask,
            {"target_answer": 3, "player_color": "white"},
            "player_capture_piece_count",
        ),
        (
            GamesChessTargetSquareAttackerCountTask,
            {"query_id": "king_square_attacker_count", "target_answer": 2},
            "king_square_attacker_count",
        ),
        (
            GamesChessMarkedPieceBlockerCountTask,
            {"query_id": "rook_line_blocker_count", "target_answer": 2},
            "rook_line_blocker_count",
        ),
        (
            GamesChessKingEscapeSquareCountTask,
            {"target_answer": 3},
            "king_escape_square_count",
        ),
        (
            GamesChessPieceKindCountTask,
            {"query_id": "piece_kind_count", "target_answer": 4, "target_piece_kind": "pawn"},
            "piece_kind_count",
        ),
        (
            GamesChessColoredPieceKindCountTask,
            {
                "query_id": "colored_piece_kind_count",
                "target_answer": 2,
                "target_piece_kind": "knight",
                "target_piece_color": "black",
            },
            "colored_piece_kind_count",
        ),
    ),
)
def test_games_chess_board_emits_expected_contract(
    task_cls: type[Any],
    params: dict[str, int | str],
    expected_query: str,
) -> None:
    out = task_cls().generate(50201, params=params, max_attempts=96)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert out.query_id == str(expected_query)
    assert trace["query_spec"]["query_id"] == str(expected_query)
    assert trace["query_spec"]["params"]["query_id"] == str(expected_query)
    assert execution["query_id"] == str(expected_query)
    assert int(execution["target_answer"]) == int(out.answer_gt.value)
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert len(execution["annotation_entity_ids"]) == len(out.annotation_gt.value)


def test_games_chess_marked_move_count_matches_rules() -> None:
    out = GamesChessMarkedPieceDestinationCountTask().generate(
        50211,
        params={"query_id": "marked_piece_move_count", "target_answer": 5},
        max_attempts=96,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    marked = tuple(int(value) for value in execution["marked_coord"])
    destinations = tuple(sorted(piece_move_destinations(board, marked)))

    assert len(destinations) == int(out.answer_gt.value) == 5
    assert [list(coord) for coord in destinations] == sorted(execution["destination_coords"])
    assert set(execution["annotation_entity_ids"]) == {coord_to_cell_id(coord) for coord in destinations}


def test_games_chess_legal_moves_exclude_opponent_king_but_attacks_detect_it() -> None:
    mutable = [[None for _ in range(8)] for _ in range(8)]
    mutable[4][1] = ChessPiece(color="white", kind="rook")
    mutable[4][4] = ChessPiece(color="black", kind="king")
    board = freeze_board(mutable)

    assert (4, 4) not in piece_move_destinations(board, (4, 1))
    assert piece_attacks_square(board, (4, 1), (4, 4))
    assert attackers_to_square(board, (4, 4), "white") == ((4, 1),)


def test_games_chess_marked_capture_count_matches_rules() -> None:
    out = GamesChessMarkedPieceDestinationCountTask().generate(
        50221,
        params={"query_id": "marked_piece_capture_count", "target_answer": 3},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    marked = tuple(int(value) for value in execution["marked_coord"])
    captures = tuple(sorted(piece_capture_targets(board, marked)))

    assert len(captures) == int(out.answer_gt.value) == 3
    assert [list(coord) for coord in captures] == sorted(execution["capture_coords"])
    assert set(execution["annotation_entity_ids"]) == {coord_to_cell_id(coord) for coord in captures}


def test_games_chess_player_capture_count_matches_rules() -> None:
    out = GamesChessPlayerCapturePieceCountTask().generate(
        50231,
        params={"target_answer": 4, "player_color": "black"},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    captures = capturable_opponent_coords(board, str(execution["player_color"]))

    assert len(captures) == int(out.answer_gt.value) == 4
    assert [list(coord) for coord in captures] == sorted(execution["capture_coords"])


def test_games_chess_king_square_attacker_count_matches_rules() -> None:
    out = GamesChessTargetSquareAttackerCountTask().generate(
        50241,
        params={"query_id": "king_square_attacker_count", "target_answer": 3},
        max_attempts=96,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    marked = tuple(int(value) for value in execution["marked_coord"])
    attacker_color = "black" if str(execution["player_color"]) == "white" else "white"
    attackers = attackers_to_square(board, marked, attacker_color)

    assert len(attackers) == int(out.answer_gt.value) == 3
    assert [list(coord) for coord in attackers] == sorted(execution["attacker_coords"])


@pytest.mark.parametrize(
    ("query_id", "attacker_color", "target_answer"),
    (
        ("white_piece_attacks_target_square_count", "white", 3),
        ("black_piece_attacks_target_square_count", "black", 2),
    ),
)
def test_games_chess_empty_target_square_attacker_count_matches_rules(
    query_id: str,
    attacker_color: str,
    target_answer: int,
) -> None:
    out = GamesChessTargetSquareAttackerCountTask().generate(
        50242 + int(target_answer),
        params={"query_id": str(query_id), "target_answer": int(target_answer)},
        max_attempts=160,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    marked = tuple(int(value) for value in execution["marked_coord"])
    attackers = attackers_to_square(board, marked, str(attacker_color))

    assert board[int(marked[0])][int(marked[1])] is None
    assert len(attackers) == int(out.answer_gt.value) == int(target_answer)
    assert [list(coord) for coord in attackers] == sorted(execution["attacker_coords"])
    assert set(execution["annotation_entity_ids"]) == {
        piece_to_entity_id(coord, board[int(coord[0])][int(coord[1])])
        for coord in attackers
    }


@pytest.mark.parametrize(
    ("query_id", "piece_kind", "target_answer"),
    (
        ("rook_line_blocker_count", "rook", 3),
        ("bishop_diagonal_blocker_count", "bishop", 2),
        ("queen_line_blocker_count", "queen", 4),
    ),
)
def test_games_chess_marked_piece_blocker_count_matches_rules(
    query_id: str,
    piece_kind: str,
    target_answer: int,
) -> None:
    out = GamesChessMarkedPieceBlockerCountTask().generate(
        50270 + int(target_answer),
        params={"query_id": str(query_id), "target_answer": int(target_answer)},
        max_attempts=160,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    marked = tuple(int(value) for value in execution["marked_coord"])
    target = tuple(int(value) for value in execution["target_coord"])
    marked_piece = board[int(marked[0])][int(marked[1])]
    target_piece = board[int(target[0])][int(target[1])]
    blockers = tuple(coord for coord in _coords_between_test(marked, target) if board[int(coord[0])][int(coord[1])] is not None)

    assert marked_piece is not None
    assert str(marked_piece.kind) == str(piece_kind)
    assert target_piece is None
    assert _line_allowed_for_query_test(str(query_id), marked, target)
    assert len(blockers) == int(out.answer_gt.value) == int(target_answer)
    assert sorted([list(coord) for coord in blockers]) == sorted(execution["blocker_coords"])
    assert set(execution["annotation_entity_ids"]) == {
        piece_to_entity_id(coord, board[int(coord[0])][int(coord[1])])
        for coord in blockers
    }


def test_games_chess_king_escape_square_count_matches_rules() -> None:
    out = GamesChessKingEscapeSquareCountTask().generate(
        50246,
        params={"target_answer": 4},
        max_attempts=96,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    marked = tuple(int(value) for value in execution["marked_coord"])
    escapes = tuple(sorted(king_escape_squares(board, marked)))

    assert len(escapes) == int(out.answer_gt.value) == 4
    assert [list(coord) for coord in escapes] == sorted(execution["destination_coords"])
    assert set(execution["annotation_entity_ids"]) == {coord_to_cell_id(coord) for coord in escapes}


def test_games_chess_king_escape_sampler_uses_opponent_attacks_not_only_blockers() -> None:
    for target_answer in range(0, 6):
        out = GamesChessKingEscapeSquareCountTask().generate(
            60246 + int(target_answer),
            params={"target_answer": int(target_answer)},
            max_attempts=256,
        )
        execution = out.trace_payload["execution_trace"]
        board = _board_from_execution(execution)
        marked = tuple(int(value) for value in execution["marked_coord"])
        king = board[int(marked[0])][int(marked[1])]
        assert king is not None
        king_color = str(king.color)
        escapes = {tuple(int(value) for value in coord) for coord in execution["destination_coords"]}
        adjacent = {
            (int(marked[0]) + dr, int(marked[1]) + dc)
            for dr in (-1, 0, 1)
            for dc in (-1, 0, 1)
            if not (int(dr) == 0 and int(dc) == 0)
        }

        attacked_open_unsafe = []
        for coord in sorted(adjacent - escapes):
            occupant = board[int(coord[0])][int(coord[1])]
            if occupant is not None and str(occupant.color) == king_color:
                continue
            moved = [list(row) for row in board]
            moved[int(marked[0])][int(marked[1])] = None
            moved[int(coord[0])][int(coord[1])] = king
            if attackers_to_square(freeze_board(moved), coord, opponent(king_color)):
                attacked_open_unsafe.append(coord)
        assert attacked_open_unsafe

        for row in range(8):
            for col in range(8):
                coord = (row, col)
                piece = board[row][col]
                if piece is None or str(piece.color) != king_color or str(piece.kind) not in {"queen", "rook", "bishop"}:
                    continue
                assert not any(piece_attacks_square(board, coord, escape_coord) for escape_coord in escapes)


def test_games_chess_piece_type_count_matches_visible_pieces() -> None:
    out = GamesChessColoredPieceKindCountTask().generate(
        50261,
        params={
            "query_id": "colored_piece_kind_count",
            "target_answer": 3,
            "target_piece_kind": "bishop",
            "target_piece_color": "white",
            "piece_count_distractor_count": 8,
        },
        max_attempts=96,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    matches = []
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece is not None and str(piece.color) == "white" and str(piece.kind) == "bishop":
                matches.append((row, col))

    assert int(out.answer_gt.value) == 3
    assert matches == [tuple(coord) for coord in execution["annotation_coords"]]
    assert len(out.annotation_gt.value) == 3


def test_games_chess_piece_type_count_zero_answer_uses_empty_annotation() -> None:
    out = GamesChessPieceKindCountTask().generate(
        50262,
        params={
            "query_id": "piece_kind_count",
            "target_answer": 0,
            "target_piece_kind": "queen",
            "piece_count_distractor_count": 5,
        },
        max_attempts=96,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)

    assert int(out.answer_gt.value) == 0
    assert out.annotation_gt.value == []
    assert not any(piece is not None and str(piece.kind) == "queen" for row in board for piece in row)


def test_games_chess_checkmate_move_label_has_unique_mating_option() -> None:
    out = GamesChessCheckmateMoveLabelTask().generate(
        50263,
        params={"option_count": 6, "answer_option_label": "D", "player_color": "white"},
        max_attempts=128,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    board = _board_from_execution(execution)

    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert out.answer_gt.value == "D"
    assert execution["answer_option_label"] == out.answer_gt.value
    assert trace["query_spec"]["params"]["answer_support"] == ["A", "B", "C", "D", "E", "F"]
    assert set(out.annotation_gt.value) == {"from", "to", "king"}
    assert trace["projected_annotation"]["type"] == "keyed_bbox_map"
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_keyed_bbox_map"] == out.annotation_gt.value
    assert trace["render_map"]["coordinate_label_bboxes_px"]["files"]
    assert set(trace["render_map"]["move_option_panel"]["option_bboxes_px"]) == {"A", "B", "C", "D", "E", "F"}

    mating_labels = []
    for option in execution["move_options"]:
        assert "White " not in str(option["text"])
        assert "Black " not in str(option["text"])
        source = tuple(int(value) for value in option["source_coord"])
        destination = tuple(int(value) for value in option["destination_coord"])
        is_mate = move_checkmates(board, source, destination)
        assert bool(option["is_checkmate"]) is bool(is_mate)
        if is_mate:
            mating_labels.append(str(option["label"]))

    assert mating_labels == [str(out.answer_gt.value)]


@pytest.mark.parametrize(
    ("task_cls", "params"),
    (
        (GamesChessMarkedPieceDestinationCountTask, {"query_id": "marked_piece_move_count", "target_answer": 4}),
        (GamesChessMarkedPieceDestinationCountTask, {"query_id": "marked_piece_capture_count", "target_answer": 2}),
        (GamesChessPlayerCapturePieceCountTask, {"target_answer": 3, "player_color": "white"}),
        (GamesChessTargetSquareAttackerCountTask, {"query_id": "king_square_attacker_count", "target_answer": 2}),
        (GamesChessTargetSquareAttackerCountTask, {"query_id": "white_piece_attacks_target_square_count", "target_answer": 2}),
        (GamesChessMarkedPieceBlockerCountTask, {"query_id": "queen_line_blocker_count", "target_answer": 3}),
        (GamesChessKingEscapeSquareCountTask, {"target_answer": 3}),
    ),
)
def test_games_chess_movement_rule_boards_are_material_plausible(
    task_cls: type[Any],
    params: dict[str, int | str],
) -> None:
    for offset in range(8):
        out = task_cls().generate(62200 + int(offset), params=params, max_attempts=256)
        board = _board_from_execution(out.trace_payload["execution_trace"])
        assert validate_square_chess_material(board)


def test_games_chess_checkmate_board_is_material_plausible() -> None:
    for offset in range(6):
        out = GamesChessCheckmateMoveLabelTask().generate(
            62300 + int(offset),
            params={"option_count": 4 if int(offset) % 2 == 0 else 6},
            max_attempts=160,
        )
        board = _board_from_execution(out.trace_payload["execution_trace"])
        assert validate_square_chess_material(board)


@pytest.mark.parametrize(
    ("task_cls", "query_id", "support"),
    (
        (GamesChessMarkedPieceDestinationCountTask, "marked_piece_move_count", (1, 2, 3, 4, 5, 6, 7, 8)),
        (GamesChessMarkedPieceDestinationCountTask, "marked_piece_capture_count", (0, 1, 2, 3, 4)),
        (GamesChessPlayerCapturePieceCountTask, "player_capture_piece_count", (1, 2, 3, 4, 5, 6)),
        (GamesChessTargetSquareAttackerCountTask, "king_square_attacker_count", (0, 1, 2, 3, 4)),
        (GamesChessTargetSquareAttackerCountTask, "white_piece_attacks_target_square_count", (0, 1, 2, 3, 4)),
        (GamesChessTargetSquareAttackerCountTask, "black_piece_attacks_target_square_count", (0, 1, 2, 3, 4)),
        (GamesChessMarkedPieceBlockerCountTask, "rook_line_blocker_count", (0, 1, 2, 3, 4)),
        (GamesChessMarkedPieceBlockerCountTask, "bishop_diagonal_blocker_count", (0, 1, 2, 3, 4)),
        (GamesChessMarkedPieceBlockerCountTask, "queen_line_blocker_count", (0, 1, 2, 3, 4)),
        (GamesChessKingEscapeSquareCountTask, "king_escape_square_count", (0, 1, 2, 3, 4, 5)),
        (GamesChessPieceKindCountTask, "piece_kind_count", (0, 1, 2, 3, 4, 5, 6)),
        (GamesChessColoredPieceKindCountTask, "colored_piece_kind_count", (0, 1, 2, 3, 4, 5, 6)),
    ),
)
def test_games_chess_public_tasks_cover_declared_integer_answer_support(
    task_cls: type[Any],
    query_id: str,
    support: tuple[int, ...],
) -> None:
    seen = set()
    for index, target_answer in enumerate(support):
        params: dict[str, Any] = {"query_id": str(query_id), "target_answer": int(target_answer)}
        if str(query_id) == "piece_kind_count":
            params["target_piece_kind"] = "pawn"
        if str(query_id) == "colored_piece_kind_count":
            params["target_piece_kind"] = "bishop"
            params["target_piece_color"] = "white"
        out = task_cls().generate(50301 + (37 * int(index)), params=params, max_attempts=256)
        assert out.query_id == str(query_id)
        assert out.trace_payload["query_spec"]["params"]["query_id"] == str(query_id)
        seen.add(int(out.answer_gt.value))

    assert seen == set(int(value) for value in support)


def test_games_chess_board_is_deterministic() -> None:
    params = {
        "query_id": "white_piece_attacks_target_square_count",
        "target_answer": 2,
        "scene_variant": "crowded_board",
        "style_variant": "outlined",
    }
    task = GamesChessTargetSquareAttackerCountTask()
    out_a = task.generate(50251, params=params, max_attempts=96)
    out_b = task.generate(50251, params=params, max_attempts=96)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_chess_piece_symbols_ignore_sampled_readout_font() -> None:
    image = Image.new("RGB", (96, 96), "white")
    draw = ImageDraw.Draw(image)

    with temporary_default_font_family("georama"):
        font = _fit_chess_symbol_font(
            draw,
            glyph="♔",
            max_width=84,
            max_height=84,
            min_size_px=18,
            max_size_px=78,
            fill_ratio=0.98,
        )

    assert getattr(font, "getname")()[0] == "DejaVu Sans"


def test_games_chess_uses_filled_piece_symbol_set_for_both_sides() -> None:
    assert _FILLED_PIECE_CODEPOINTS == {
        "king": 0x265A,
        "queen": 0x265B,
        "rook": 0x265C,
        "bishop": 0x265D,
        "knight": 0x265E,
        "pawn": 0x265F,
    }


def test_games_chess_board_prompt_bundle_requires_rule_texts() -> None:
    bundle = json.loads(Path("prompts/games/chess/games_chess_v1.json").read_text(encoding="utf-8"))
    assert bundle["schema_version"] == "v1"
    assert bundle["required_slots_by_key"] == {}
    static = bundle["static_slots_by_key"]
    assert "normal chess" in static["query:marked_piece_move_count"]["standard_rule_text"].lower()
    assert "red outlined square" in static["query:marked_piece_move_count"]["marked_piece_rule_text"].lower()
    assert "blue outlined square" in static["query:rook_line_blocker_count"]["blocker_rule_text"].lower()
    assert "from" in static["query:checkmate_move_label"]["annotation_hint"]
    dynamic = bundle["dynamic_slots"]
    assert set(dynamic) >= {
        "player_color_name",
        "opponent_color_name",
        "defender_color_name",
        "target_color_name",
        "target_piece_kind",
        "target_piece_kind_plural",
    }


def test_games_chess_board_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__chess__marked_piece_destination_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__chess__marked_piece_destination_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__chess__marked_piece_destination_count",
                count=4,
                params={},
            )
        ],
        max_attempts_per_instance=96,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-chess-board-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")
    report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))

    assert int(report["accepted_counts_by_task"]["task_games__chess__marked_piece_destination_count"]) == 4
    assert len(rows) == 4
    assert all(row["domain"] == "games" for row in rows)
    assert all(row.get("scene_id") == "chess" for row in rows)


def test_games_chess_retries_transient_construction_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import trace.tasks.games.chess.marked_piece_destination_count as task_module

    real_sampler = task_module.sample_marked_piece_destination_scene
    calls = {"count": 0}

    def flaky_sampler(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise ValueError("forced transient construction failure")
        return real_sampler(*args, **kwargs)

    monkeypatch.setattr(task_module, "sample_marked_piece_destination_scene", flaky_sampler)

    out = task_module.GamesChessMarkedPieceDestinationCountTask().generate(
        50201,
        params={"query_id": "marked_piece_move_count", "target_answer": 4, "scene_variant": "sparse_board"},
        max_attempts=96,
    )

    assert calls["count"] >= 2
    assert out.answer_gt.type == "integer"
    assert out.query_id == "marked_piece_move_count"


def _board_from_execution(execution: dict):
    from trace.tasks.games.shared.piece_board_rules import ChessPiece

    rows = []
    for row in execution["board_rows"]:
        parsed_row = []
        for cell in row:
            if cell is None:
                parsed_row.append(None)
            else:
                color, kind = str(cell).split("_", 1)
                parsed_row.append(ChessPiece(color=color, kind=kind))
        rows.append(parsed_row)
    return tuple(tuple(row) for row in rows)


def _coords_between_test(a: tuple[int, int], b: tuple[int, int]) -> tuple[tuple[int, int], ...]:
    ar, ac = int(a[0]), int(a[1])
    br, bc = int(b[0]), int(b[1])
    if ar == br:
        dr, dc = 0, 1 if bc > ac else -1
    elif ac == bc:
        dr, dc = 1 if br > ar else -1, 0
    elif abs(ar - br) == abs(ac - bc):
        dr, dc = 1 if br > ar else -1, 1 if bc > ac else -1
    else:
        return ()
    coords = []
    row, col = ar + dr, ac + dc
    while (row, col) != (br, bc):
        coords.append((int(row), int(col)))
        row += dr
        col += dc
    return tuple(coords)


def _line_allowed_for_query_test(query_id: str, a: tuple[int, int], b: tuple[int, int]) -> bool:
    ar, ac = int(a[0]), int(a[1])
    br, bc = int(b[0]), int(b[1])
    same_line = ar == br or ac == bc
    same_diag = abs(ar - br) == abs(ac - bc)
    if str(query_id) == "rook_line_blocker_count":
        return same_line
    if str(query_id) == "bishop_diagonal_blocker_count":
        return same_diag
    if str(query_id) == "queen_line_blocker_count":
        return same_line or same_diag
    return False
