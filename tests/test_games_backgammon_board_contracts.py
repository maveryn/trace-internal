"""Contract tests for games Backgammon board tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.backgammon.board_tasks import (
    GamesBackgammonBlockedDestinationCountTask,
    GamesBackgammonBoardTask,
    GamesBackgammonLegalMoveCountTask,
    GamesBackgammonPointStateCountTask,
)
from trace.tasks.games.shared.backgammon_common import (
    BACKGAMMON_QUERY_IDS,
    BACKGAMMON_POINT_STATE_QUERY_IDS,
    BACKGAMMON_STYLE_VARIANTS,
    PLAYER_BLACK,
    PLAYER_WHITE,
    BackgammonPoint,
    compute_single_die_destinations,
    point_entity_id,
    target_destinations_for_query,
    target_points_for_state_query,
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
        (GamesBackgammonLegalMoveCountTask, {"target_answer": 4, "query_id": "legal_move_count"}, "legal_move_count"),
        (GamesBackgammonLegalMoveCountTask, {"target_answer": 3, "query_id": "hit_move_count"}, "hit_move_count"),
        (GamesBackgammonBlockedDestinationCountTask, {"target_answer": 4, "query_id": "blocked_destination_count"}, "blocked_destination_count"),
        (GamesBackgammonPointStateCountTask, {"target_answer": 5, "query_id": "black_single_checker_point_count"}, "black_single_checker_point_count"),
        (GamesBackgammonPointStateCountTask, {"target_answer": 6, "query_id": "white_two_or_more_checker_point_count"}, "white_two_or_more_checker_point_count"),
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
    assert out.annotation_gt.type == "bbox_set"
    assert out.query_id == expected_query
    assert out.scene_id == "backgammon"
    assert trace["query_spec"]["query_id"] == expected_query
    assert trace["query_spec"]["params"]["query_id"] == expected_query
    assert execution["query_id"] == expected_query
    assert execution["active_player"] in {PLAYER_BLACK, PLAYER_WHITE}
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert len(out.annotation_gt.value) == int(out.answer_gt.value)
    assert len(execution["target_points"]) == int(out.answer_gt.value)
    assert trace["render_spec"]["canvas_width"] <= 1000
    assert trace["render_spec"]["canvas_height"] <= 720
    assert float(trace["render_spec"]["effective_point_width_px"]) >= 28.0
    assert trace["render_spec"]["text_style"]["font_family"]
    assert trace["render_map"]["font_family"] == trace["render_spec"]["text_style"]["font_family"]
    for x0, y0, x1, y1 in out.annotation_gt.value:
        assert 0 <= float(x0) <= float(x1) <= float(trace["render_spec"]["canvas_width"])
        assert 0 <= float(y0) <= float(y1) <= float(trace["render_spec"]["canvas_height"])


@pytest.mark.parametrize(
    ("task_cls", "target_answer", "expected_query", "active_player"),
    (
        (GamesBackgammonLegalMoveCountTask, 4, "legal_move_count", PLAYER_BLACK),
        (GamesBackgammonLegalMoveCountTask, 5, "hit_move_count", PLAYER_WHITE),
        (GamesBackgammonBlockedDestinationCountTask, 4, "blocked_destination_count", PLAYER_WHITE),
    ),
)
def test_games_backgammon_answers_match_recomputed_destination_sets(
    task_cls: type[GamesBackgammonBoardTask],
    target_answer: int,
    expected_query: str,
    active_player: str,
) -> None:
    out = task_cls().generate(
        820100 + target_answer,
        params={"target_answer": int(target_answer), "query_id": str(expected_query), "active_player": str(active_player)},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    points = _points_from_trace(execution)
    dice = tuple(int(value) for value in execution["dice"])
    outcome = compute_single_die_destinations(
        points,
        dice=(dice[0], dice[1]),
        active_player=str(execution["active_player"]),
    )
    expected_destinations = target_destinations_for_query(outcome, query_id=expected_query)
    expected_entity_ids = {point_entity_id(point) for point in expected_destinations}

    assert int(out.answer_gt.value) == len(expected_destinations) == int(target_answer)
    assert tuple(int(value) for value in execution["target_destinations"]) == tuple(expected_destinations)
    assert set(execution["annotation_entity_ids"]) == expected_entity_ids


@pytest.mark.parametrize(
    ("expected_query", "target_answer"),
    (
        ("black_single_checker_point_count", 0),
        ("white_single_checker_point_count", 2),
        ("black_two_or_more_checker_point_count", 4),
        ("white_two_or_more_checker_point_count", 6),
    ),
)
def test_games_backgammon_point_state_answers_match_recomputed_points(
    expected_query: str,
    target_answer: int,
) -> None:
    out = GamesBackgammonPointStateCountTask().generate(
        820500 + target_answer,
        params={"target_answer": int(target_answer), "query_id": str(expected_query)},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    points = _points_from_trace(execution)
    expected_points = target_points_for_state_query(points, query_id=expected_query)
    expected_entity_ids = {point_entity_id(point) for point in expected_points}

    assert int(out.answer_gt.value) == len(expected_points) == int(target_answer)
    assert tuple(int(value) for value in execution["target_points"]) == tuple(expected_points)
    assert tuple(execution["target_destinations"]) == ()
    assert set(execution["annotation_entity_ids"]) == expected_entity_ids
    assert str(execution["construction_mode"]) == "exact_point_state_count"


def test_games_backgammon_query_cycle_covers_support_and_styles() -> None:
    task = GamesBackgammonBoardTask()
    queries: set[str] = set()
    counts: set[int] = set()
    styles: set[str] = set()
    active_players: set[str] = set()

    for sampling_index in range(420):
        out = task.generate(
            820300 + sampling_index,
            params={},
            max_attempts=512,
        )
        execution = out.trace_payload["execution_trace"]
        queries.add(str(out.query_id))
        counts.add(int(out.answer_gt.value))
        styles.add(str(execution["style_variant"]))
        active_players.add(str(execution["active_player"]))

    assert queries == set(BACKGAMMON_QUERY_IDS)
    assert counts >= {0, 1, 2, 3, 4, 5, 6}
    assert styles == set(BACKGAMMON_STYLE_VARIANTS)
    assert active_players == {PLAYER_BLACK, PLAYER_WHITE}
    assert set(BACKGAMMON_POINT_STATE_QUERY_IDS) <= queries


def test_games_backgammon_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__backgammon"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__backgammon",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__backgammon__legal_move_count", count=3, params={}),
            BuildTaskConfig(task_id="task_games__backgammon__point_state_count", count=3, params={}),
        ],
        max_attempts_per_instance=512,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-backgammon-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 6
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["task_group"] == "backgammon" for row in rows)
    assert {row["scene_id"] for row in rows} == {"backgammon"}
