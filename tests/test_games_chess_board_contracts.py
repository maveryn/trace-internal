"""Contract tests for games Chess-board tasks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.chess.board_tasks import (
    GamesChessBoardTask,
    GamesChessCheckAttackerCountTask,
    GamesChessKingEscapeSquareCountTask,
    GamesChessMarkedPieceDestinationCountTask,
    GamesChessPlayerCapturePieceCountTask,
)
from trace.tasks.games.shared.chess_common import (
    attackers_to_square,
    capturable_opponent_coords,
    coord_to_cell_id,
    king_escape_squares,
    piece_capture_targets,
    piece_move_destinations,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query"),
    (
        (
            GamesChessMarkedPieceDestinationCountTask,
            {"query_variant": "marked_piece_move_count", "target_answer": 4, "scene_variant": "sparse_board"},
            "marked_piece_move_count",
        ),
        (
            GamesChessMarkedPieceDestinationCountTask,
            {"query_variant": "marked_piece_capture_count", "target_answer": 2, "scene_variant": "crowded_board"},
            "marked_piece_capture_count",
        ),
        (
            GamesChessPlayerCapturePieceCountTask,
            {"target_answer": 3, "player_color": "white"},
            "player_capture_piece_count",
        ),
        (
            GamesChessCheckAttackerCountTask,
            {"target_answer": 2},
            "check_attacker_count",
        ),
        (
            GamesChessKingEscapeSquareCountTask,
            {"target_answer": 3},
            "king_escape_square_count",
        ),
    ),
)
def test_games_chess_board_emits_expected_contract(
    task_cls: type[GamesChessBoardTask],
    params: dict[str, int | str],
    expected_query: str,
) -> None:
    out = task_cls().generate(50201, params=params, max_attempts=96)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_variant == "default"
    assert out.query_id == str(expected_query)
    assert trace["query_spec"]["params"]["query_variant"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == str(expected_query)
    assert execution["query_variant"] == "default"
    assert execution["query_id"] == str(expected_query)
    assert int(execution["target_answer"]) == int(out.answer_gt.value)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value)


def test_games_chess_marked_move_count_matches_rules() -> None:
    out = GamesChessMarkedPieceDestinationCountTask().generate(
        50211,
        params={"query_variant": "marked_piece_move_count", "target_answer": 5},
        max_attempts=96,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    marked = tuple(int(value) for value in execution["marked_coord"])
    destinations = tuple(sorted(piece_move_destinations(board, marked)))

    assert len(destinations) == int(out.answer_gt.value) == 5
    assert [list(coord) for coord in destinations] == sorted(execution["destination_coords"])
    assert set(execution["evidence_entity_ids"]) == {coord_to_cell_id(coord) for coord in destinations}


def test_games_chess_marked_capture_count_matches_rules() -> None:
    out = GamesChessMarkedPieceDestinationCountTask().generate(
        50221,
        params={"query_variant": "marked_piece_capture_count", "target_answer": 3},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    marked = tuple(int(value) for value in execution["marked_coord"])
    captures = tuple(sorted(piece_capture_targets(board, marked)))

    assert len(captures) == int(out.answer_gt.value) == 3
    assert [list(coord) for coord in captures] == sorted(execution["capture_coords"])
    assert set(execution["evidence_entity_ids"]) == {coord_to_cell_id(coord) for coord in captures}


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


def test_games_chess_check_attacker_count_matches_rules() -> None:
    out = GamesChessCheckAttackerCountTask().generate(
        50241,
        params={"target_answer": 3},
        max_attempts=96,
    )
    execution = out.trace_payload["execution_trace"]
    board = _board_from_execution(execution)
    marked = tuple(int(value) for value in execution["marked_coord"])
    attacker_color = "black" if str(execution["player_color"]) == "white" else "white"
    attackers = attackers_to_square(board, marked, attacker_color)

    assert len(attackers) == int(out.answer_gt.value) == 3
    assert [list(coord) for coord in attackers] == sorted(execution["attacker_coords"])


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
    assert set(execution["evidence_entity_ids"]) == {coord_to_cell_id(coord) for coord in escapes}


def test_games_chess_board_query_cycle_covers_answer_scene_and_style_support() -> None:
    task = GamesChessBoardTask()
    answers_by_query = {query: set() for query in (
        "marked_piece_move_count",
        "marked_piece_capture_count",
        "player_capture_piece_count",
        "check_attacker_count",
        "king_escape_square_count",
    )}
    scenes_by_query = {query: set() for query in answers_by_query}
    styles_by_query = {query: set() for query in answers_by_query}

    for sampling_index in range(300):
        out = task.generate(
            50301 + int(sampling_index),
            params={},
            max_attempts=256,
        )
        execution = out.trace_payload["execution_trace"]
        query = str(out.query_id or out.query_variant)
        answers_by_query[query].add(int(out.answer_gt.value))
        scenes_by_query[query].add(str(execution["scene_variant"]))
        styles_by_query[query].add(str(execution["style_variant"]))

    assert answers_by_query["marked_piece_move_count"] == {1, 2, 3, 4, 5, 6, 7, 8}
    assert answers_by_query["marked_piece_capture_count"] == {0, 1, 2, 3, 4}
    assert answers_by_query["player_capture_piece_count"] == {1, 2, 3, 4, 5, 6}
    assert answers_by_query["check_attacker_count"] == {1, 2, 3, 4}
    assert answers_by_query["king_escape_square_count"] == {0, 1, 2, 3, 4, 5}
    assert all(values == {"sparse_board", "crowded_board"} for values in scenes_by_query.values())
    assert all(
        values == {"classic", "soft", "outlined", "wood_token", "blue_glyph", "monochrome_glyph"}
        for values in styles_by_query.values()
    )


def test_games_chess_board_is_deterministic() -> None:
    params = {
        "query_variant": "check_attacker_count",
        "target_answer": 2,
        "scene_variant": "crowded_board",
        "style_variant": "outlined",
    }
    task = GamesChessBoardTask()
    out_a = task.generate(50251, params=params, max_attempts=96)
    out_b = task.generate(50251, params=params, max_attempts=96)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_chess_board_prompt_bundle_requires_rule_texts() -> None:
    bundle = json.loads(Path("prompts/games/chess/games_chess_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:marked_piece_move_count"] == ["standard_rule_text", "marked_piece_rule_text"]
    assert required["query:player_capture_piece_count"] == ["standard_rule_text", "player_rule_text", "player_color_name"]
    assert required["query:check_attacker_count"] == ["standard_rule_text", "check_rule_text"]
    assert required["query:king_escape_square_count"] == ["standard_rule_text", "king_escape_rule_text"]


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
    assert all(row["task_group"] == "chess" for row in rows)


def _board_from_execution(execution: dict):
    from trace.tasks.games.shared.chess_common import ChessPiece

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
