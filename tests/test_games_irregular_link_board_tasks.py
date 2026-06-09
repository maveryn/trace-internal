"""Contract tests for irregular link board games tasks."""

from __future__ import annotations

from pathlib import Path
import json

import trace.tasks  # noqa: F401
from trace.core.task_group_config import get_task_group_defaults
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.games.irregular_link_board.board_tasks import (
    CAPTURE_MOVE_TASK_ID,
    MARKED_DESTINATION_TASK_ID,
    _all_possible_edges,
    _capture_destinations,
    _edge,
    _legal_destinations,
    _neighbors,
)
from trace.tasks.registry import create_task, list_default_task_ids
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_irregular_link_board_defaults_and_prompt_bundle() -> None:
    cfg = get_task_group_defaults("games", "irregular_link_board")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(cfg)

    assert set(generation["scene_variant_weights"].keys()) == {
        "sparse_links",
        "mixed_links",
        "dense_links",
    }
    assert set(generation["style_variant_weights"].keys()) == {
        "woodcut",
        "ink_diagram",
        "garden_cloth",
        "night_lines",
        "parchment",
    }
    assert list(generation["board_size_support"]) == [4, 5, 6]
    assert list(generation["capture_board_size_support"]) == [5, 6]
    assert list(generation["target_answer_support"]) == list(range(9))
    assert int(rendering["max_board_size_px"]) == 560
    assert str(prompt["bundle_id"]) == "games_irregular_link_board_v0"


def test_games_irregular_link_board_prompt_bundle_has_query() -> None:
    bundle = json.loads(
        Path("prompts/games/irregular_link_board/games_irregular_link_board_v0.json").read_text(encoding="utf-8")
    )
    assert set(bundle["query_templates"].keys()) == {
        "marked_piece_destination_count",
        "capture_move_count",
    }
    assert bool(bundle["allow_empty_task_templates"])


def test_games_irregular_link_board_registry_and_taxonomy() -> None:
    default_ids = set(list_default_task_ids())
    assert MARKED_DESTINATION_TASK_ID in default_ids
    assert CAPTURE_MOVE_TASK_ID in default_ids
    for task_id in (MARKED_DESTINATION_TASK_ID, CAPTURE_MOVE_TASK_ID):
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "games"
        assert taxonomy.scene_id == "irregular_link_board"
        assert taxonomy.source_task_group == "irregular_link_board"


def test_games_irregular_link_board_answer_matches_trace() -> None:
    out = create_task(MARKED_DESTINATION_TASK_ID).generate(
        441003,
        params={"target_answer": 5, "board_size": 5},
        max_attempts=100,
    )
    trace = out.trace_payload["execution_trace"]
    marked = tuple(trace["marked_coord"])
    occupied = tuple(tuple(coord) for coord in trace["occupied_coords"])
    edges = tuple(_edge(tuple(edge[0]), tuple(edge[1])) for edge in trace["edge_coords"])
    expected = _legal_destinations(
        marked_coord=marked,  # type: ignore[arg-type]
        occupied_coords=occupied,  # type: ignore[arg-type]
        edges=edges,
        board_size=int(trace["board_size"]),
    )

    assert out.scene_id == "irregular_link_board"
    assert out.query_id == "marked_piece_destination_count"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 5
    assert len(out.annotation_gt.value) == 5
    assert tuple(tuple(coord) for coord in trace["annotation_coords"]) == expected
    assert out.trace_payload["projected_annotation"]["type"] == "point_set"


def test_games_irregular_link_board_capture_answer_matches_trace() -> None:
    out = create_task(CAPTURE_MOVE_TASK_ID).generate(
        443003,
        params={"target_answer": 5, "board_size": 5},
        max_attempts=100,
    )
    trace = out.trace_payload["execution_trace"]
    marked = tuple(trace["marked_coord"])
    occupied = tuple(tuple(coord) for coord in trace["occupied_coords"])
    edges = tuple(_edge(tuple(edge[0]), tuple(edge[1])) for edge in trace["edge_coords"])
    expected = _capture_destinations(
        marked_coord=marked,  # type: ignore[arg-type]
        occupied_coords=occupied,  # type: ignore[arg-type]
        edges=edges,
        board_size=int(trace["board_size"]),
    )

    assert out.scene_id == "irregular_link_board"
    assert out.query_id == "capture_move_count"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 5
    assert len(out.annotation_gt.value) == 5
    assert tuple(tuple(coord) for coord in trace["annotation_coords"]) == expected
    assert tuple(tuple(coord) for coord in trace["capture_destinations"]) == expected
    assert out.trace_payload["projected_annotation"]["type"] == "point_set"

    occupied_set = {tuple(coord) for coord in occupied}
    edge_set = set(edges)
    for destination in expected:
        step = (
            int(destination[0]) - int(marked[0]),
            int(destination[1]) - int(marked[1]),
        )
        assert step[0] % 2 == 0 and step[1] % 2 == 0
        captured = (
            int(marked[0]) + (step[0] // 2),
            int(marked[1]) + (step[1] // 2),
        )
        assert captured in occupied_set
        assert destination not in occupied_set
        assert _edge(marked, captured) in edge_set  # type: ignore[arg-type]
        assert _edge(captured, destination) in edge_set


def test_games_irregular_link_board_support_endpoints_are_constructible() -> None:
    task = create_task(MARKED_DESTINATION_TASK_ID)
    for target in (0, 8):
        out = task.generate(
            442000 + target,
            params={"target_answer": target, "board_size": 4},
            max_attempts=100,
        )
        assert int(out.answer_gt.value) == target
        assert len(out.annotation_gt.value) == target


def test_games_irregular_link_board_capture_support_endpoints_are_constructible() -> None:
    task = create_task(CAPTURE_MOVE_TASK_ID)
    for target in (0, 8):
        out = task.generate(
            443500 + target,
            params={"target_answer": target, "board_size": 5},
            max_attempts=100,
        )
        assert int(out.answer_gt.value) == target
        assert len(out.annotation_gt.value) == target


def test_games_irregular_link_board_lattice_has_no_non_node_diagonal_crossings() -> None:
    for board_size in (4, 5, 6):
        edges = set(_all_possible_edges(board_size))
        for row in range(board_size - 1):
            for col in range(board_size - 1):
                down_right = _edge((row, col), (row + 1, col + 1))
                up_right = _edge((row + 1, col), (row, col + 1))
                assert not (down_right in edges and up_right in edges)

    assert len(_neighbors((1, 1), 4)) == 8
    assert len(_neighbors((1, 2), 4)) == 4
