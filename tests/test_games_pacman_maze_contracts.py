"""Contract tests for games Pac-Man maze tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.pacman.maze_tasks import (
    GamesPacmanMazeTask,
    GamesPacmanNextItemLabelTask,
    GamesPacmanRoutePelletCountTask,
)
from trace.tasks.games.shared.pacman_common import (
    PACMAN_ITEM_LABELS,
    coord_from_entity_id,
    item_entity_id,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query", "answer_type"),
    (
        (GamesPacmanRoutePelletCountTask, {"query_variant": "path_pellet_count", "target_answer": 5, "row_count": 8, "col_count": 11}, "path_pellet_count", "integer"),
        (GamesPacmanNextItemLabelTask, {"target_label": "E", "item_count": 6}, "next_item_label", "string"),
        (GamesPacmanRoutePelletCountTask, {"query_variant": "pellet_count_before_ghost", "target_answer": 4, "row_count": 9, "col_count": 13}, "pellet_count_before_ghost", "integer"),
    ),
)
def test_games_pacman_public_tasks_emit_expected_contract(
    task_cls: type[GamesPacmanMazeTask],
    params: dict[str, int | str],
    expected_query: str,
    answer_type: str,
) -> None:
    out = task_cls().generate(120000, params=params, max_attempts=256)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == answer_type
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_variant == "default"
    assert out.query_id == expected_query
    assert out.scene_id == "pacman"
    assert trace["query_spec"]["query_id"] == expected_query
    assert trace["query_spec"]["query_variant"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == expected_query
    assert trace["query_spec"]["params"]["query_variant"] == "default"
    assert execution["query_id"] == expected_query
    assert execution["query_variant"] == "default"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value)


def test_games_pacman_path_pellet_count_evidence_is_on_route() -> None:
    out = GamesPacmanRoutePelletCountTask().generate(
        120010,
        params={"query_variant": "path_pellet_count", "target_answer": 5, "row_count": 9, "col_count": 13},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    route = {tuple(coord) for coord in execution["route_coords"]}
    evidence_coords = {
        coord_from_entity_id(entity_id)
        for entity_id in execution["evidence_entity_ids"]
        if str(entity_id).startswith("pellet_r")
    }

    assert int(out.answer_gt.value) == 5
    assert len(evidence_coords) == 5
    assert evidence_coords.issubset(route)


def test_games_pacman_next_item_label_is_first_route_item() -> None:
    out = GamesPacmanNextItemLabelTask().generate(
        120020,
        params={"target_label": "F", "item_count": 6, "row_count": 8, "col_count": 11},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    route_order = {tuple(coord): index for index, coord in enumerate(execution["route_coords"])}
    item_steps = [
        (route_order[tuple(item["coord"])], str(item["label"]))
        for item in execution["items"]
        if tuple(item["coord"]) in route_order
    ]

    assert out.answer_gt.value == "F"
    assert execution["evidence_entity_ids"] == [item_entity_id("F")]
    assert min(item_steps)[1] == "F"


def test_games_pacman_pellet_count_before_ghost_stops_at_first_route_ghost() -> None:
    out = GamesPacmanRoutePelletCountTask().generate(
        120030,
        params={"query_variant": "pellet_count_before_ghost", "target_answer": 5, "row_count": 9, "col_count": 13},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    route_order = {tuple(coord): index for index, coord in enumerate(execution["route_coords"])}
    stop_ghosts = [ghost for ghost in execution["ghosts"] if bool(ghost["is_stop_ghost"])]
    evidence_coords = {
        coord_from_entity_id(entity_id)
        for entity_id in execution["evidence_entity_ids"]
        if str(entity_id).startswith("pellet_r")
    }
    evidence_ghosts = [entity_id for entity_id in execution["evidence_entity_ids"] if str(entity_id).startswith("ghost_")]

    assert int(out.answer_gt.value) == 5
    assert len(stop_ghosts) == 1
    assert evidence_ghosts == [stop_ghosts[0]["entity_id"]]
    stop_index = route_order[tuple(stop_ghosts[0]["coord"])]
    assert len(evidence_coords) == 5
    assert all(route_order[coord] < stop_index for coord in evidence_coords)


def test_games_pacman_query_cycle_covers_support() -> None:
    task = GamesPacmanRoutePelletCountTask()
    queries: set[str] = set()
    rows: set[int] = set()
    cols: set[int] = set()
    counts: set[int] = set()

    for sampling_index in range(144):
        out = task.generate(
            120100 + sampling_index,
            params={},
            max_attempts=256,
        )
        execution = out.trace_payload["execution_trace"]
        queries.add(str(out.query_id))
        rows.add(int(execution["row_count"]))
        cols.add(int(execution["col_count"]))
        counts.add(int(out.answer_gt.value))

    assert queries == {"path_pellet_count", "pellet_count_before_ghost"}
    assert rows == {7, 8, 9}
    assert cols == {9, 11, 13}
    assert counts == {1, 2, 3, 4, 5}


def test_games_pacman_next_item_label_cycle_covers_labels() -> None:
    task = GamesPacmanNextItemLabelTask()
    labels: set[str] = set()

    for sampling_index in range(72):
        out = task.generate(
            120300 + sampling_index,
            params={},
            max_attempts=256,
        )
        labels.add(str(out.answer_gt.value))

    assert labels == set(PACMAN_ITEM_LABELS)


def test_games_pacman_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__pacman"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__pacman",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__pacman__route_pellet_count", count=2, params={}),
            BuildTaskConfig(task_id="task_games__pacman__next_item_label", count=1, params={}),
        ],
        max_attempts_per_instance=256,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-pacman-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 3
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["task_group"] == "pacman" for row in rows)
