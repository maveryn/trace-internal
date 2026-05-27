"""Contract tests for games lane-crossing tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.crossing.lane_tasks import (
    GamesCrossingCollisionTimeValueTask,
    GamesCrossingLaneTask,
    GamesCrossingMovingObjectCountTask,
    GamesCrossingSafeRouteLabelTask,
)
from trace.tasks.games.shared.crossing_common import (
    CrossingRouteOption,
    CrossingVehicle,
    route_collision_vehicle_ids,
    route_first_collision_tick,
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
    ("task_cls", "params", "expected_query", "expected_answer", "expected_answer_type", "evidence_count"),
    (
        (
            GamesCrossingSafeRouteLabelTask,
            {
                "query_variant": "safe_start_label",
                "target_label_index": 2,
                "lane_count": 6,
                "row_count": 5,
                "style_variant": "day",
            },
            "safe_start_label",
            "C",
            "string",
            1,
        ),
        (
            GamesCrossingCollisionTimeValueTask,
            {"target_answer": 4, "lane_count": 6, "row_count": 6, "style_variant": "night"},
            "collision_time_value",
            4,
            "integer",
            2,
        ),
        (
            GamesCrossingMovingObjectCountTask,
            {"target_answer": 3, "lane_count": 6, "row_count": 6, "style_variant": "retro"},
            "moving_object_count",
            3,
            "integer",
            3,
        ),
        (
            GamesCrossingSafeRouteLabelTask,
            {
                "query_variant": "goal_reachable_label",
                "target_label_index": 2,
                "route_option_count": 5,
                "lane_count": 6,
                "row_count": 6,
                "style_variant": "paper",
            },
            "goal_reachable_label",
            "C",
            "string",
            1,
        ),
    ),
)
def test_games_crossing_public_tasks_emit_expected_contract(
    task_cls: type[GamesCrossingLaneTask],
    params: dict[str, int | str],
    expected_query: str,
    expected_answer: int | str,
    expected_answer_type: str,
    evidence_count: int,
) -> None:
    out = task_cls().generate(77100, params=params, max_attempts=512)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == expected_answer_type
    assert out.answer_gt.value == expected_answer
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == evidence_count
    assert out.query_variant == "default"
    assert out.query_id == expected_query
    assert out.scene_id == "crossing"
    assert trace["query_spec"]["query_id"] == expected_query
    assert trace["query_spec"]["query_variant"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == expected_query
    assert trace["query_spec"]["params"]["query_variant"] == "default"
    assert execution["query_id"] == expected_query
    assert execution["query_variant"] == "default"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value)


def test_games_crossing_safe_start_label_is_unique_straight_safe_start() -> None:
    out = GamesCrossingSafeRouteLabelTask().generate(
        77110,
        params={"query_variant": "safe_start_label", "target_label_index": 4, "lane_count": 6, "row_count": 6},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    vehicles = _vehicles(execution)
    lane_count = int(execution["lane_count"])
    row_count = int(execution["row_count"])
    safe_labels = []
    for index, label in enumerate(execution["start_labels"]):
        route = CrossingRouteOption(
            route_id=f"straight_{index}",
            label=str(label),
            path_cols=tuple(index for _ in range(row_count)),
            color_index=index,
        )
        if not route_collision_vehicle_ids(route, vehicles, lane_count=lane_count):
            safe_labels.append(str(label))

    assert safe_labels == [str(out.answer_gt.value)] == ["E"]
    assert execution["evidence_entity_ids"] == ["start_4"]


def test_games_crossing_collision_time_matches_trace() -> None:
    out = GamesCrossingCollisionTimeValueTask().generate(
        77120,
        params={"target_answer": 5, "lane_count": 7, "row_count": 7},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    route = _routes(execution)[0]
    vehicles = _vehicles(execution)

    assert int(out.answer_gt.value) == 5
    assert route_first_collision_tick(route, vehicles, lane_count=int(execution["lane_count"])) == 5
    assert execution["evidence_entity_ids"][1] == "route_M_cell_4"


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
    assert tuple(execution["evidence_entity_ids"]) == hit_ids


def test_games_crossing_goal_reachable_label_is_unique_safe_route() -> None:
    out = GamesCrossingSafeRouteLabelTask().generate(
        77140,
        params={
            "query_variant": "goal_reachable_label",
            "target_label_index": 5,
            "route_option_count": 6,
            "lane_count": 8,
            "row_count": 7,
        },
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    vehicles = _vehicles(execution)
    safe_labels = [
        str(route.label)
        for route in _routes(execution)
        if not route_collision_vehicle_ids(route, vehicles, lane_count=int(execution["lane_count"]))
    ]

    assert safe_labels == [str(out.answer_gt.value)] == ["F"]
    assert execution["evidence_entity_ids"] == ["route_F"]


def test_games_crossing_lane_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__crossing"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__crossing",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__crossing__safe_route_label",
                count=1,
                params={"query_variant": "safe_start_label", "target_label_index": 1},
            ),
            BuildTaskConfig(task_id="task_games__crossing__collision_time_value", count=1, params={"target_answer": 3}),
            BuildTaskConfig(task_id="task_games__crossing__moving_object_count", count=1, params={"target_answer": 2}),
        ],
        max_attempts_per_instance=512,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-crossing-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 3
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["task_group"] == "crossing" for row in rows)


def test_games_crossing_safe_route_task_balances_label_query_modes() -> None:
    queries = [
        GamesCrossingSafeRouteLabelTask().generate(
            77180 + index,
            params={"lane_count": 6, "row_count": 6, "route_option_count": 5},
            max_attempts=512,
        ).query_id
        for index in range(8)
    ]

    assert set(queries) == {"safe_start_label", "goal_reachable_label"}
    assert all(query in {"safe_start_label", "goal_reachable_label"} for query in queries)
