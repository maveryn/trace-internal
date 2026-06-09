"""Contract tests for games Hex-board tasks."""

from __future__ import annotations

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.hex.connection_tasks import (
    GamesHexBoardTask,
    GamesHexCandidateNeighborCountTask,
    GamesHexConnectionGapCountTask,
    GamesHexWinningMoveCellLabelTask,
)
from trace.tasks.games.shared.hex_common import (
    BLUE,
    EMPTY,
    RED,
    coord_to_cell_id,
    immediate_winning_moves,
    minimum_connection_gap_sets,
    minimum_connection_path,
    neighbors,
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
    assert out.annotation_gt.type == "point_set"
    assert out.query_id == "winning_move_cell_label"
    assert out.scene_id == "hex"
    assert trace["query_spec"]["params"]["query_id"] == "winning_move_cell_label"
    assert execution["query_id"] == "winning_move_cell_label"
    assert trace["projected_annotation"]["type"] == "point_set"
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_point_set"] == out.annotation_gt.value
    assert trace["render_spec"]["panel_scene_style"]["treatment"]
    assert trace["render_spec"]["text_style"]["font_family"]
    assert len(out.annotation_gt.value) == 1
    assert len(execution["annotation_entity_ids"]) == 1


def test_games_hex_winning_move_cell_label_has_unique_immediate_winning_cell() -> None:
    out = GamesHexWinningMoveCellLabelTask().generate(
        51211,
        params={"target_label": "F", "candidate_count": 6, "board_size": 7, "player_color": "blue"},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    board = tuple(tuple(int(value) for value in row) for row in execution["board_rows"])
    player_value = int(execution["player_value"])
    winning_coord = tuple(int(value) for value in execution["winning_move_coord"])
    answer_candidates = [spec for spec in execution["candidate_specs"] if bool(spec["is_answer"])]
    annotation_coords = _coords(execution["annotation_coords"])
    completed_path_coords = _coords(execution["completed_winning_path_coords"])

    assert int(board[winning_coord[0]][winning_coord[1]]) == EMPTY
    assert immediate_winning_moves(board, player_value=player_value) == (winning_coord,)
    assert len(answer_candidates) == 1
    assert answer_candidates[0]["label"] == out.answer_gt.value == "F"
    assert tuple(answer_candidates[0]["coord"]) == winning_coord
    assert annotation_coords == (winning_coord,)
    assert completed_path_coords == winning_path_after_move(
        board,
        player_value=player_value,
        move_coord=winning_coord,
    )
    assert set(execution["annotation_entity_ids"]) == {coord_to_cell_id(winning_coord)}


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
    assert out.annotation_gt.type == "point_set"
    assert out.query_id == "connection_gap_count"
    assert out.scene_id == "hex"
    assert trace["query_spec"]["params"]["query_id"] == "connection_gap_count"
    assert execution["query_id"] == "connection_gap_count"
    assert trace["projected_annotation"]["type"] == "point_set"
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_point_set"] == out.annotation_gt.value


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
    annotation_coords = _coords(execution["annotation_coords"])
    empty_on_path = tuple(coord for coord in path if int(board[coord[0]][coord[1]]) == EMPTY)

    assert int(out.answer_gt.value) == int(gap_count) == 5
    assert gap_search.exhaustive
    assert len(gap_search.gap_sets) == 1
    assert sorted_coords(empty_on_path) == gap_search.gap_sets[0]
    assert sorted_coords(annotation_coords) == gap_search.gap_sets[0]
    assert len(annotation_coords) == int(out.answer_gt.value)
    assert set(execution["annotation_entity_ids"]) == {coord_to_cell_id(coord) for coord in annotation_coords}


def test_games_hex_candidate_neighbor_count_emits_expected_contract() -> None:
    out = GamesHexCandidateNeighborCountTask().generate(
        51251,
        params={"query_id": "red_neighbor_count", "target_answer": 4, "board_size": 6},
        max_attempts=128,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 4
    assert out.annotation_gt.type == "point_set"
    assert out.query_id == "red_neighbor_count"
    assert out.scene_id == "hex"
    assert trace["query_spec"]["params"]["query_id"] == "red_neighbor_count"
    assert execution["query_id"] == "red_neighbor_count"
    assert execution["reference_label"] == "C"
    assert execution["reference_cell_id"]
    assert trace["render_map"]["reference_labels_by_cell_id"] == {execution["reference_cell_id"]: "C"}
    assert trace["projected_annotation"]["type"] == "point_set"
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_point_set"] == out.annotation_gt.value


def test_games_hex_candidate_neighbor_count_matches_adjacent_cell_states() -> None:
    query_to_value = {
        "red_neighbor_count": RED,
        "blue_neighbor_count": BLUE,
        "empty_neighbor_count": EMPTY,
    }
    for index, (query_id, target_answer) in enumerate(
        (
            ("red_neighbor_count", 0),
            ("blue_neighbor_count", 6),
            ("empty_neighbor_count", 3),
        )
    ):
        out = GamesHexCandidateNeighborCountTask().generate(
            51261 + index,
            params={"query_id": query_id, "target_answer": target_answer, "board_size": 6},
            max_attempts=128,
        )
        execution = out.trace_payload["execution_trace"]
        board = tuple(tuple(int(value) for value in row) for row in execution["board_rows"])
        reference_coord = tuple(int(value) for value in execution["reference_coord"])
        expected = sorted_coords(
            coord
            for coord in neighbors(reference_coord, board_size=int(execution["board_size"]))
            if int(board[coord[0]][coord[1]]) == int(query_to_value[query_id])
        )
        annotation_coords = _coords(execution["annotation_coords"])

        assert int(out.answer_gt.value) == len(expected) == int(target_answer)
        assert len(neighbors(reference_coord, board_size=int(execution["board_size"]))) == 6
        assert sorted_coords(annotation_coords) == expected
        assert sorted_coords(_coords(execution["neighbor_match_coords"])) == expected
        assert set(execution["annotation_entity_ids"]) == {coord_to_cell_id(coord) for coord in annotation_coords}
        assert len(out.annotation_gt.value) == int(target_answer)


def test_games_hex_candidate_neighbor_count_samples_only_neighbor_queries() -> None:
    task = GamesHexCandidateNeighborCountTask()
    queries = {
        task.generate(51281 + index, params={}, max_attempts=128).query_id
        for index in range(18)
    }

    assert queries == {"red_neighbor_count", "blue_neighbor_count", "empty_neighbor_count"}


def test_games_hex_board_query_cycle_covers_answer_board_player_and_style_support() -> None:
    task = GamesHexBoardTask()
    queries: set[str] = set()
    boards: set[int] = set()
    players: set[str] = set()
    styles: set[str] = set()
    labels: set[str] = set()
    gap_counts: set[int] = set()
    neighbor_counts: set[int] = set()

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
        elif str(out.query_id) == "connection_gap_count":
            gap_counts.add(int(out.answer_gt.value))
        else:
            neighbor_counts.add(int(out.answer_gt.value))

    assert queries == {
        "winning_move_cell_label",
        "connection_gap_count",
        "red_neighbor_count",
        "blue_neighbor_count",
        "empty_neighbor_count",
    }
    assert boards == {5, 6, 7, 8}
    assert players == {"red", "blue"}
    assert styles == set(SUPPORTED_HEX_STYLE_VARIANTS)
    assert labels == set("ABCDEF")
    assert gap_counts == {1, 2, 3, 4, 5}
    assert neighbor_counts == {0, 1, 2, 3, 4, 5, 6}


def test_games_hex_board_is_deterministic() -> None:
    params = {"query_id": "winning_move_cell_label", "target_label": "C", "board_size": 6}
    task = GamesHexBoardTask()
    out_a = task.generate(51241, params=params, max_attempts=128)
    out_b = task.generate(51241, params=params, max_attempts=128)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
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
            BuildTaskConfig(
                task_id="task_games__hex__candidate_neighbor_count",
                count=1,
                params={"query_id": "empty_neighbor_count", "target_answer": 2, "board_size": 6},
            ),
        ],
        max_attempts_per_instance=128,
        workers=1,
    )
    final_path = build_dataset(cfg, code_hash="games-hex-board-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 3
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["task_group"] == "hex" for row in rows)
