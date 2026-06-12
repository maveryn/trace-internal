"""Contract tests for games lane-crossing tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.games.crossing.moving_object_count import GamesCrossingMovingObjectCountTask
from trace.tasks.games.crossing.moving_object_direction_count import GamesCrossingMovingObjectDirectionCountTask
from trace.tasks.games.crossing.shared.mechanics import route_collision_vehicle_ids
from trace.tasks.games.crossing.shared.state import (
    CrossingRouteOption,
    CrossingVehicle,
)
from tests.helpers import read_jsonl


def _vehicles(execution: dict) -> tuple[CrossingVehicle, ...]:
    return tuple(
        CrossingVehicle(
            vehicle_id=str(row["vehicle_id"]),
            row=int(row["row"]),
            start_col=int(row["start_col"]),
            direction=int(row["direction"]),
            color_index=int(row["color_index"]),
        )
        for row in execution["vehicles"]
    )


def _routes(execution: dict) -> tuple[CrossingRouteOption, ...]:
    return tuple(
        CrossingRouteOption(
            route_id=str(row["route_id"]),
            label=str(row["label"]),
            path_cols=tuple(int(col) for col in row["path_cols"]),
            color_index=int(row["color_index"]),
        )
        for row in execution["route_options"]
    )


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query", "expected_answer", "expected_answer_type", "expected_annotation_type", "annotation_count"),
    (
        (
            GamesCrossingMovingObjectCountTask,
            {"target_answer": 3, "lane_count": 6, "row_count": 6, "style_variant": "retro"},
            "moving_object_count",
            3,
            "integer",
            "bbox_set",
            3,
        ),
        (
            GamesCrossingMovingObjectDirectionCountTask,
            {"query_id": "left_moving_object_count", "target_answer": 4, "lane_count": 6, "row_count": 6},
            "left_moving_object_count",
            4,
            "integer",
            "bbox_set",
            4,
        ),
    ),
)
def test_games_crossing_public_tasks_emit_expected_contract(
    task_cls: type,
    params: dict[str, int | str],
    expected_query: str,
    expected_answer: int | str,
    expected_answer_type: str,
    expected_annotation_type: str,
    annotation_count: int,
) -> None:
    out = task_cls().generate(77100, params=params, max_attempts=512)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == expected_answer_type
    assert out.answer_gt.value == expected_answer
    assert out.annotation_gt.type == expected_annotation_type
    assert len(out.annotation_gt.value) == annotation_count
    assert out.query_id == expected_query
    assert out.scene_id == "crossing"
    assert trace["query_spec"]["query_id"] == expected_query
    assert trace["query_spec"]["params"]["query_id"] == expected_query
    assert execution["query_id"] == expected_query
    assert trace["projected_annotation"]["type"] == expected_annotation_type
    assert trace["projected_annotation"][expected_annotation_type] == out.annotation_gt.value
    assert len(execution["annotation_entity_ids"]) == len(out.annotation_gt.value)


def test_games_crossing_moving_object_count_matches_trace() -> None:
    out = GamesCrossingMovingObjectCountTask().generate(
        77130,
        params={"target_answer": 5, "lane_count": 8, "row_count": 7},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    route = _routes(execution)[0]
    vehicles = _vehicles(execution)
    hit_ids = route_collision_vehicle_ids(route, vehicles, lane_count=int(execution["lane_count"]))

    assert int(out.answer_gt.value) == len(hit_ids) == 5
    assert tuple(execution["intersecting_vehicle_ids"]) == hit_ids
    assert tuple(execution["annotation_entity_ids"]) == hit_ids


@pytest.mark.parametrize(
    ("query_id", "target_answer", "direction"),
    (
        ("left_moving_object_count", 6, -1),
        ("right_moving_object_count", 5, 1),
    ),
)
def test_games_crossing_direction_count_matches_trace(query_id: str, target_answer: int, direction: int) -> None:
    out = GamesCrossingMovingObjectDirectionCountTask().generate(
        77140 + int(target_answer),
        params={"query_id": query_id, "target_answer": target_answer, "lane_count": 7, "row_count": 7},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    matching_ids = tuple(
        str(vehicle["vehicle_id"])
        for vehicle in execution["vehicles"]
        if int(vehicle["direction"]) == int(direction)
    )

    assert out.query_id == query_id
    assert int(out.answer_gt.value) == len(matching_ids) == int(target_answer)
    assert set(execution["annotation_entity_ids"]) == set(matching_ids)
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == int(target_answer)
    assert execution["route_options"] == []
    assert execution["marked_route_label"] is None


def test_games_crossing_direction_count_taxonomy() -> None:
    assert resolve_task_taxonomy("task_games__crossing__moving_object_direction_count").scene_id == "crossing"


def test_games_crossing_lane_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__crossing"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__crossing",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__crossing__moving_object_count", count=1, params={"target_answer": 2}),
            BuildTaskConfig(
                task_id="task_games__crossing__moving_object_direction_count",
                count=1,
                params={"query_id": "right_moving_object_count", "target_answer": 3},
            ),
        ],
        max_attempts_per_instance=512,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-crossing-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 2
    assert all(row["domain"] == "games" for row in rows)
    assert all(row.get("scene_id") == "crossing" for row in rows)
