"""Contract tests for games Hex-board tasks."""

from __future__ import annotations

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.hex.connection_tasks import (
    GamesHexBoardTask,
    GamesHexConnectionGapCountTask,
    GamesHexWinningMoveCellLabelTask,
)
from trace.tasks.games.shared.hex_common import (
    EMPTY,
    coord_to_cell_id,
    immediate_winning_moves,
    minimum_connection_gap_sets,
    minimum_connection_path,
    sorted_coords,
    winning_path_after_move,
)
from trace.tasks.games.shared.style import SUPPORTED_HEX_STYLE_VARIANTS
from tests.helpers import read_jsonl


def _coords(values: list[list[int]]) -> tuple[tuple[int, int], ...]:
    """Return trace coordinate lists as stable coordinate tuples."""

    return tuple((int(row), int(col)) for row, col in values)


def test_games_hex_winning_move_cell_label_emits_expected_contract() -> None:
    out = GamesHexWinningMoveCellLabelTask().generate(
        51201,
        params={"target_label": "D", "candidate_count": 6, "board_size": 6, "player_color": "red"},
        max_attempts=128,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == "D"
    assert out.evidence_gt.type == "point_set"
    assert out.query_id == "winning_move_cell_label"
    assert out.scene_id == "hex"
    assert trace["query_spec"]["params"]["query_id"] == "winning_move_cell_label"
    assert execution["query_id"] == "winning_move_cell_label"
    assert trace["projected_evidence"]["type"] == "point_set"
    assert trace["projected_evidence"]["point_set"] == out.evidence_gt.value
    assert trace["projected_evidence"]["pixel_point_set"] == out.evidence_gt.value
    assert trace["render_spec"]["panel_scene_style"]["treatment"]
    assert trace["render_spec"]["text_style"]["font_family"]
    assert len(out.evidence_gt.value) == 1
    assert len(execution["evidence_entity_ids"]) == 1


def test_games_hex_winning_move_cell_label_has_unique_immediate_winning_cell() -> None:
    out = GamesHexWinningMoveCellLabelTask().generate(
        51211,
        params={"target_label": "F", "candidate_count": 8, "board_size": 7, "player_color": "blue"},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    board = tuple(tuple(int(value) for value in row) for row in execution["board_rows"])
    player_value = int(execution["player_value"])
    winning_coord = tuple(int(value) for value in execution["winning_move_coord"])
    answer_candidates = [spec for spec in execution["candidate_specs"] if bool(spec["is_answer"])]
    evidence_coords = _coords(execution["evidence_coords"])
    completed_path_coords = _coords(execution["completed_winning_path_coords"])

    assert int(board[winning_coord[0]][winning_coord[1]]) == EMPTY
    assert immediate_winning_moves(board, player_value=player_value) == (winning_coord,)
    assert len(answer_candidates) == 1
    assert answer_candidates[0]["label"] == out.answer_gt.value == "F"
    assert tuple(answer_candidates[0]["coord"]) == winning_coord
    assert evidence_coords == (winning_coord,)
    assert completed_path_coords == winning_path_after_move(
        board,
        player_value=player_value,
        move_coord=winning_coord,
    )
    assert set(execution["evidence_entity_ids"]) == {coord_to_cell_id(winning_coord)}


def test_games_hex_connection_gap_count_emits_expected_contract() -> None:
    out = GamesHexConnectionGapCountTask().generate(
        51221,
        params={"target_answer": 4, "board_size": 7, "player_color": "red"},
        max_attempts=128,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 4
    assert out.evidence_gt.type == "point_set"
    assert out.query_id == "connection_gap_count"
    assert out.scene_id == "hex"
    assert trace["query_spec"]["params"]["query_id"] == "connection_gap_count"
    assert execution["query_id"] == "connection_gap_count"
    assert trace["projected_evidence"]["type"] == "point_set"
    assert trace["projected_evidence"]["point_set"] == out.evidence_gt.value
    assert trace["projected_evidence"]["pixel_point_set"] == out.evidence_gt.value


def test_games_hex_connection_gap_count_matches_shortest_path_cost() -> None:
    out = GamesHexConnectionGapCountTask().generate(
        51231,
        params={"target_answer": 5, "board_size": 8, "player_color": "blue"},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    board = tuple(tuple(int(value) for value in row) for row in execution["board_rows"])
    player_value = int(execution["player_value"])
    gap_count, path = minimum_connection_path(board, player_value=player_value)
    gap_search = minimum_connection_gap_sets(board, player_value=player_value, max_sets=2)
    evidence_coords = _coords(execution["evidence_coords"])
    empty_on_path = tuple(coord for coord in path if int(board[coord[0]][coord[1]]) == EMPTY)

    assert int(out.answer_gt.value) == int(gap_count) == 5
    assert gap_search.exhaustive
    assert len(gap_search.gap_sets) == 1
    assert sorted_coords(empty_on_path) == gap_search.gap_sets[0]
    assert sorted_coords(evidence_coords) == gap_search.gap_sets[0]
    assert len(evidence_coords) == int(out.answer_gt.value)
    assert set(execution["evidence_entity_ids"]) == {coord_to_cell_id(coord) for coord in evidence_coords}


def test_games_hex_board_query_cycle_covers_answer_board_player_and_style_support() -> None:
    task = GamesHexBoardTask()
    queries: set[str] = set()
    boards: set[int] = set()
    players: set[str] = set()
    styles: set[str] = set()
    labels: set[str] = set()
    counts: set[int] = set()

    for sampling_index in range(160):
        out = task.generate(
            51301 + int(sampling_index),
            params={},
            max_attempts=128,
        )
        execution = out.trace_payload["execution_trace"]
        queries.add(str(out.query_id))
        boards.add(int(execution["board_size"]))
        players.add(str(execution["player_color"]))
        styles.add(str(execution["style_variant"]))
        if str(out.query_id) == "winning_move_cell_label":
            labels.add(str(out.answer_gt.value))
        else:
            counts.add(int(out.answer_gt.value))

    assert queries == {"winning_move_cell_label", "connection_gap_count"}
    assert boards == {5, 6, 7, 8}
    assert players == {"red", "blue"}
    assert styles == set(SUPPORTED_HEX_STYLE_VARIANTS)
    assert labels == set("ABCDEFGH")
    assert counts == {1, 2, 3, 4, 5}


def test_games_hex_board_is_deterministic() -> None:
    params = {"query_id": "winning_move_cell_label", "target_label": "C", "board_size": 6}
    task = GamesHexBoardTask()
    out_a = task.generate(51241, params=params, max_attempts=128)
    out_b = task.generate(51241, params=params, max_attempts=128)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_hex_board_build_smoke(tmp_path) -> None:
    output_root = tmp_path / "task_games__hex__winning_move_cell_label"
    cfg = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games_hex_board",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__hex__winning_move_cell_label",
                count=1,
                params={"target_label": "B", "board_size": 6},
            ),
            BuildTaskConfig(
                task_id="task_games__hex__connection_gap_count",
                count=1,
                params={"target_answer": 3, "board_size": 6},
            ),
        ],
        max_attempts_per_instance=128,
        workers=1,
    )
    final_path = build_dataset(cfg, code_hash="games-hex-board-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 2
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["task_group"] == "hex" for row in rows)
