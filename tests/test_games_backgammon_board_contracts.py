"""Contract tests for games Backgammon board tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.backgammon.board_tasks import (
    GamesBackgammonBoardTask,
    GamesBackgammonDestinationCountTask,
)
from trace.tasks.games.shared.backgammon_common import (
    BACKGAMMON_STYLE_VARIANTS,
    BackgammonPoint,
    compute_black_single_die_destinations,
    point_entity_id,
    target_destinations_for_query,
)
from tests.helpers import read_jsonl


def _points_from_trace(execution: dict) -> dict[int, BackgammonPoint]:
    return {
        int(row["point_id"]): BackgammonPoint(
            owner=None if row["owner"] is None else str(row["owner"]),
            count=int(row["count"]),
        )
        for row in execution["points"]
    }


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query"),
    (
        (GamesBackgammonDestinationCountTask, {"target_answer": 4, "query_id": "legal_move_count"}, "legal_move_count"),
        (GamesBackgammonDestinationCountTask, {"target_answer": 3, "query_id": "hit_move_count"}, "hit_move_count"),
        (GamesBackgammonDestinationCountTask, {"target_answer": 4, "query_id": "blocked_destination_count"}, "blocked_destination_count"),
    ),
)
def test_games_backgammon_public_tasks_emit_expected_contract(
    task_cls: type[GamesBackgammonBoardTask],
    params: dict[str, int],
    expected_query: str,
) -> None:
    out = task_cls().generate(820000, params=params, max_attempts=256)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_id == "default"
    assert out.query_id == expected_query
    assert out.scene_id == "backgammon"
    assert trace["query_spec"]["query_id"] == expected_query
    assert trace["query_spec"]["query_id"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == expected_query
    assert trace["query_spec"]["params"]["query_id"] == "default"
    assert execution["query_id"] == expected_query
    assert execution["query_id"] == "default"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(out.evidence_gt.value) == int(out.answer_gt.value)


@pytest.mark.parametrize(
    ("task_cls", "target_answer", "expected_query"),
    (
        (GamesBackgammonDestinationCountTask, 4, "legal_move_count"),
        (GamesBackgammonDestinationCountTask, 5, "hit_move_count"),
        (GamesBackgammonDestinationCountTask, 4, "blocked_destination_count"),
    ),
)
def test_games_backgammon_answers_match_recomputed_destination_sets(
    task_cls: type[GamesBackgammonBoardTask],
    target_answer: int,
    expected_query: str,
) -> None:
    out = task_cls().generate(
        820100 + target_answer,
        params={"target_answer": int(target_answer), "query_id": str(expected_query)},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    points = _points_from_trace(execution)
    dice = tuple(int(value) for value in execution["dice"])
    outcome = compute_black_single_die_destinations(points, dice=(dice[0], dice[1]))
    expected_destinations = target_destinations_for_query(outcome, query_id=expected_query)
    expected_entity_ids = {point_entity_id(point) for point in expected_destinations}

    assert int(out.answer_gt.value) == len(expected_destinations) == int(target_answer)
    assert tuple(int(value) for value in execution["target_destinations"]) == tuple(expected_destinations)
    assert set(execution["evidence_entity_ids"]) == expected_entity_ids


def test_games_backgammon_query_cycle_covers_support_and_styles() -> None:
    task = GamesBackgammonBoardTask()
    queries: set[str] = set()
    counts: set[int] = set()
    styles: set[str] = set()

    for sampling_index in range(210):
        out = task.generate(
            820300 + sampling_index,
            params={},
            max_attempts=512,
        )
        execution = out.trace_payload["execution_trace"]
        queries.add(str(out.query_id))
        counts.add(int(out.answer_gt.value))
        styles.add(str(execution["style_variant"]))

    assert queries == {"legal_move_count", "hit_move_count", "blocked_destination_count"}
    assert counts >= {0, 1, 2, 3, 4, 5}
    assert styles == set(BACKGAMMON_STYLE_VARIANTS)


def test_games_backgammon_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__backgammon"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__backgammon",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__backgammon__destination_count", count=3, params={}),
        ],
        max_attempts_per_instance=512,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-backgammon-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 3
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["task_group"] == "backgammon" for row in rows)
    assert {row["scene_id"] for row in rows} == {"backgammon"}
