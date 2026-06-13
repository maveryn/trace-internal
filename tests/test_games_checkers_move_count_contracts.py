"""Contract tests for the games Checkers move-count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.games.checkers.max_capture_chain_length import GamesCheckersMaxCaptureChainLengthTask
from trace.tasks.games.checkers.move_count import GamesCheckersMoveCountPublicTask
from trace.tasks.games.checkers.piece_mobility_count import GamesCheckersPieceMobilityCountTask
from trace.tasks.games.checkers.piece_state_count import GamesCheckersPieceStateCountTask
from trace.tasks.games.checkers.shared.rules import BLACK, BOARD_SIZE, RED, piece_to_entity_id, playable_coords
from tests.helpers import read_jsonl


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


def _expected_piece_state_coords(board_rows: list[list[int]], query_id: str) -> set[tuple[int, int]]:
    target = RED if str(query_id).startswith("red_") else BLACK
    edge_only = "_edge_" in str(query_id)
    expected: set[tuple[int, int]] = set()
    for row, col in playable_coords():
        if int(board_rows[int(row)][int(col)]) != int(target):
            continue
        if edge_only and int(row) not in {0, BOARD_SIZE - 1} and int(col) not in {0, BOARD_SIZE - 1}:
            continue
        expected.add((int(row), int(col)))
    return expected


@pytest.mark.parametrize(
    ("params", "expected_answer", "expected_annotation_count"),
    (
        (
            {
                "scene_variant": "midgame_board",
                "query_id": "legal_move_count",
                "target_answer": 3,
            },
            3,
            3,
        ),
        (
            {
                "scene_variant": "crowded_board",
                "query_id": "capture_move_count",
                "target_answer": 2,
            },
            2,
            2,
        ),
        (
            {
                "scene_variant": "midgame_board",
                "query_id": "max_capture_chain_length",
                "target_answer": 4,
            },
            4,
            4,
        ),
    ),
)
def test_games_checkers_move_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
    expected_annotation_count: int,
) -> None:
    task_params = dict(params)
    task = GamesCheckersMoveCountPublicTask()
    if str(task_params.get("query_id")) == "max_capture_chain_length":
        task_params.pop("query_id", None)
        task = GamesCheckersMaxCaptureChainLengthTask()
    out = task.generate(33001, params=task_params, max_attempts=96)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == int(expected_annotation_count)
    assert trace["query_spec"]["params"]["query_id"] == out.query_id
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert len(execution["annotation_entity_ids"]) == int(expected_annotation_count)
    if str(params["query_id"]) == "max_capture_chain_length":
        assert all(str(entity_id).startswith("piece_") for entity_id in execution["annotation_entity_ids"])
        assert execution["annotation_kind"] == "piece"
        assert execution["max_capture_chain_length"] == int(expected_answer)
    else:
        assert all(str(entity_id).startswith("cell_r") for entity_id in execution["annotation_entity_ids"])


def test_games_checkers_move_count_legal_annotation_tracks_unique_landing_squares() -> None:
    out = GamesCheckersMoveCountPublicTask().generate(
        33011,
        params={
            "scene_variant": "midgame_board",
            "query_id": "legal_move_count",
            "target_answer": 5,
        },
        max_attempts=96,
    )
    execution = out.trace_payload["execution_trace"]
    annotation_coords = {tuple(coord) for coord in execution["annotation_coords"]}
    landing_coords = {tuple(move["landing"]) for move in execution["legal_move_specs"]}

    assert annotation_coords == landing_coords
    assert len(annotation_coords) == 5


def test_games_checkers_move_count_capture_annotation_tracks_capture_landings_only() -> None:
    out = GamesCheckersMoveCountPublicTask().generate(
        33021,
        params={
            "scene_variant": "crowded_board",
            "query_id": "capture_move_count",
            "target_answer": 4,
        },
        max_attempts=96,
    )
    execution = out.trace_payload["execution_trace"]
    annotation_coords = {tuple(coord) for coord in execution["annotation_coords"]}
    capture_landings = {
        tuple(move["landing"])
        for move in execution["legal_move_specs"]
        if move["captured"] is not None
    }

    assert annotation_coords == capture_landings
    assert len(annotation_coords) == 4


def test_games_checkers_max_capture_chain_annotation_tracks_captured_pieces() -> None:
    out = GamesCheckersMaxCaptureChainLengthTask().generate(
        33041,
        params={
            "scene_variant": "crowded_board",
            "target_answer": 5,
        },
        max_attempts=160,
    )
    execution = out.trace_payload["execution_trace"]
    annotation_coords = {tuple(coord) for coord in execution["annotation_coords"]}
    chain = execution["max_capture_chain_specs"][0]
    captured_coords = {tuple(coord) for coord in chain["captured"]}

    assert out.query_id == "default"
    assert out.trace_payload["query_spec"]["query_id"] == "default"
    assert out.trace_payload["query_spec"]["params"]["query_id"] == "default"
    assert out.trace_payload["query_spec"]["params"]["prompt_query_key"] == "max_capture_chain_length"
    assert int(out.answer_gt.value) == 5
    assert annotation_coords == captured_coords
    assert len(annotation_coords) == 5


def test_games_checkers_piece_mobility_legal_annotation_tracks_source_pieces() -> None:
    out = GamesCheckersPieceMobilityCountTask().generate(
        33051,
        params={
            "scene_variant": "midgame_board",
            "query_id": "piece_with_legal_move_count",
            "target_answer": 4,
        },
        max_attempts=160,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    annotation_coords = {tuple(coord) for coord in execution["annotation_coords"]}
    source_coords = {tuple(move["origin"]) for move in execution["legal_move_specs"]}

    assert out.scene_id == "checkers"
    assert out.query_id == "piece_with_legal_move_count"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "point_set"
    assert int(out.answer_gt.value) == 4
    assert annotation_coords == source_coords
    assert len(out.annotation_gt.value) == 4
    assert execution["annotation_kind"] == "piece_point"
    _assert_point_annotation_matches_piece_ids(trace, out.annotation_gt.value)


def test_games_checkers_piece_mobility_capture_annotation_tracks_source_pieces() -> None:
    out = GamesCheckersPieceMobilityCountTask().generate(
        33061,
        params={
            "scene_variant": "crowded_board",
            "query_id": "piece_with_capture_move_count",
            "target_answer": 3,
        },
        max_attempts=160,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    annotation_coords = {tuple(coord) for coord in execution["annotation_coords"]}
    capture_sources = {
        tuple(move["origin"])
        for move in execution["legal_move_specs"]
        if move["captured"] is not None
    }

    assert out.query_id == "piece_with_capture_move_count"
    assert out.annotation_gt.type == "point_set"
    assert int(out.answer_gt.value) == 3
    assert annotation_coords == capture_sources
    assert len(out.annotation_gt.value) == 3
    assert execution["annotation_kind"] == "piece_point"
    _assert_point_annotation_matches_piece_ids(trace, out.annotation_gt.value)


def test_games_checkers_piece_mobility_zero_answer_uses_empty_point_set() -> None:
    out = GamesCheckersPieceMobilityCountTask().generate(
        33071,
        params={
            "scene_variant": "midgame_board",
            "query_id": "piece_with_capture_move_count",
            "target_answer": 0,
        },
        max_attempts=160,
    )
    execution = out.trace_payload["execution_trace"]

    assert int(out.answer_gt.value) == 0
    assert out.annotation_gt.type == "point_set"
    assert out.annotation_gt.value == []
    assert execution["annotation_entity_ids"] == []
    assert execution["annotation_coords"] == []
    assert out.trace_payload["projected_annotation"]["point_set"] == []
    assert out.trace_payload["projected_annotation"]["pixel_point_set"] == []


@pytest.mark.parametrize(
    ("query_id", "target_answer"),
    (
        ("red_piece_count", 6),
        ("black_piece_count", 0),
        ("red_edge_piece_count", 5),
        ("black_edge_piece_count", 2),
    ),
)
def test_games_checkers_piece_state_annotation_tracks_matching_pieces(query_id: str, target_answer: int) -> None:
    out = GamesCheckersPieceStateCountTask().generate(
        33081 + int(target_answer),
        params={
            "scene_variant": "crowded_board",
            "query_id": str(query_id),
            "target_answer": int(target_answer),
        },
        max_attempts=192,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    expected_coords = _expected_piece_state_coords(execution["board_rows"], query_id)
    target_player = RED if str(query_id).startswith("red_") else BLACK
    expected_entity_ids = {
        piece_to_entity_id(coord, player=int(target_player))
        for coord in expected_coords
    }

    assert out.scene_id == "checkers"
    assert out.query_id == query_id
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "point_set"
    assert int(out.answer_gt.value) == len(expected_coords) == int(target_answer)
    assert {tuple(coord) for coord in execution["annotation_coords"]} == expected_coords
    assert set(execution["annotation_entity_ids"]) == expected_entity_ids
    assert execution["annotation_kind"] == "piece_point"
    assert execution["construction_mode"] == "piece_state_count_templates"
    _assert_point_annotation_matches_piece_ids(trace, out.annotation_gt.value)


def test_games_checkers_piece_mobility_taxonomy() -> None:
    assert resolve_task_taxonomy("task_games__checkers__piece_mobility_count").scene_id == "checkers"
    assert resolve_task_taxonomy("task_games__checkers__piece_state_count").scene_id == "checkers"


def test_games_checkers_move_count_query_cycle_covers_legal_answer_support() -> None:
    observed: dict[str, set[int]] = {
        "legal_move_count": set(),
        "capture_move_count": set(),
        "max_capture_chain_length": set(),
        "piece_with_legal_move_count": set(),
        "piece_with_capture_move_count": set(),
        "red_piece_count": set(),
        "black_piece_count": set(),
        "red_edge_piece_count": set(),
        "black_edge_piece_count": set(),
    }
    scenes_by_branch: dict[str, set[str]] = {key: set() for key in observed}
    styles_by_branch: dict[str, set[str]] = {key: set() for key in observed}

    task_runs = (
        (GamesCheckersMoveCountPublicTask(), 72),
        (GamesCheckersMaxCaptureChainLengthTask(), 36),
        (GamesCheckersPieceMobilityCountTask(), 72),
        (GamesCheckersPieceStateCountTask(), 140),
    )
    for task, count in task_runs:
        for sampling_index in range(count):
            out = task.generate(
                33101 + int(sampling_index),
                params={"_sample_cursor": sampling_index},
                max_attempts=160,
            )
            execution = out.trace_payload["execution_trace"]
            branch = str(execution.get("prompt_query_key") or out.query_id)
            observed[branch].add(int(out.answer_gt.value))
            scenes_by_branch[branch].add(str(execution["scene_variant"]))
            styles_by_branch[branch].add(str(execution["style_variant"]))

    assert observed["legal_move_count"] == {0, 1, 2, 3, 4, 5}
    assert observed["capture_move_count"] == {0, 1, 2, 3, 4}
    assert observed["max_capture_chain_length"] == {1, 2, 3, 4, 5}
    assert observed["piece_with_legal_move_count"] == {0, 1, 2, 3, 4, 5}
    assert observed["piece_with_capture_move_count"] == {0, 1, 2, 3, 4}
    assert observed["red_piece_count"] == {0, 1, 2, 3, 4, 5, 6}
    assert observed["black_piece_count"] == {0, 1, 2, 3, 4, 5, 6}
    assert observed["red_edge_piece_count"] == {0, 1, 2, 3, 4, 5, 6}
    assert observed["black_edge_piece_count"] == {0, 1, 2, 3, 4, 5, 6}
    assert all(values == {"crowded_board", "midgame_board"} for values in scenes_by_branch.values())
    assert all(values == {"classic", "soft", "outlined", "wood_token", "blue_table", "charcoal"} for values in styles_by_branch.values())


def test_games_checkers_move_count_is_deterministic() -> None:
    params = {
        "scene_variant": "crowded_board",
        "query_id": "capture_move_count",
        "target_answer": 1,
    }
    task = GamesCheckersMoveCountPublicTask()
    out_a = task.generate(33031, params=params, max_attempts=96)
    out_b = task.generate(33031, params=params, max_attempts=96)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_checkers_move_count_prompt_bundle_requires_rule_text_for_query_specific_prompts() -> None:
    bundle = json.loads(Path("prompts/games/checkers/games_checkers_v1.json").read_text(encoding="utf-8"))
    assert bundle["schema_version"] == "v1"
    required = bundle["required_slots_by_key"]
    assert required["query:legal_move_count"] == [
        "current_player_name",
        "movement_rule_text",
    ]
    assert required["query:capture_move_count"] == [
        "current_player_name",
        "movement_rule_text",
    ]
    assert required["query:max_capture_chain_length"] == [
        "current_player_name",
    ]
    static_slots = bundle["static_slots_by_key"]
    assert "capture_rule_text" in static_slots["query:legal_move_count"]
    assert "king_chain_rule_text" in static_slots["query:max_capture_chain_length"]
    assert "answer_hint" in static_slots["query:red_piece_count"]
    assert "annotation_hint" in static_slots["query:black_edge_piece_count"]


def test_games_checkers_move_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__checkers__move_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__checkers__move_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__checkers__move_count",
                count=4,
                params={},
            ),
            BuildTaskConfig(
                task_id="task_games__checkers__piece_state_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=96,
        sampling_seed=83,
    )
    final_path = build_dataset(config, code_hash="games-checkers-move-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 8
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record.get("scene_id") == "checkers" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games__checkers__move_count"]) == 4
    assert int(build_report["accepted_counts_by_task"]["task_games__checkers__piece_state_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
