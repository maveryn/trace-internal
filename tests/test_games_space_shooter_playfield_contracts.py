"""Contract tests for games Space-shooter playfield tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.space_shooter.playfield_tasks import (
    GamesSpaceShooterClearShotCountTask,
    GamesSpaceShooterHighestThreatLabelTask,
    GamesSpaceShooterPlayfieldTask,
    GamesSpaceShooterProjectileInterceptCountTask,
    GamesSpaceShooterSafeLaneCountTask,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query", "expected_answer", "expected_answer_type"),
    (
        (
            GamesSpaceShooterClearShotCountTask,
            {"target_answer": 3, "lane_count": 7, "enemy_count": 12, "style_variant": "deep_space"},
            "clear_shot_count",
            3,
            "integer",
        ),
        (
            GamesSpaceShooterProjectileInterceptCountTask,
            {"target_answer": 4, "lane_count": 8, "enemy_count": 13, "style_variant": "vector"},
            "projectile_intercept_count",
            4,
            "integer",
        ),
        (
            GamesSpaceShooterHighestThreatLabelTask,
            {"lane_count": 8, "enemy_count": 14, "style_variant": "amber"},
            "highest_threat_label",
            None,
            "string",
        ),
        (
            GamesSpaceShooterSafeLaneCountTask,
            {"target_answer": 2, "lane_count": 6, "enemy_count": 10, "style_variant": "terminal"},
            "safe_lane_count",
            2,
            "integer",
        ),
    ),
)
def test_games_space_shooter_public_tasks_emit_expected_contract(
    task_cls: type[GamesSpaceShooterPlayfieldTask],
    params: dict[str, int | str],
    expected_query: str,
    expected_answer: int | None,
    expected_answer_type: str,
) -> None:
    out = task_cls().generate(88100, params=params, max_attempts=256)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == expected_answer_type
    if expected_answer is not None:
        assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_variant == "default"
    assert out.query_id == expected_query
    assert out.scene_id == "space_shooter"
    assert trace["query_spec"]["query_id"] == expected_query
    assert trace["query_spec"]["query_variant"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == expected_query
    assert trace["query_spec"]["params"]["query_variant"] == "default"
    assert execution["query_id"] == expected_query
    assert execution["query_variant"] == "default"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value)


def test_games_space_shooter_clear_shot_count_matches_trace() -> None:
    out = GamesSpaceShooterClearShotCountTask().generate(
        88110,
        params={"target_answer": 5, "lane_count": 8, "enemy_count": 16},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    blockers = execution["blockers"]
    enemies = execution["enemies"]
    expected_ids = []
    for enemy in enemies:
        lane = int(enemy["lane"])
        y_slot = int(enemy["y_slot"])
        lower_enemy_exists = any(
            int(other["lane"]) == lane and int(other["y_slot"]) > y_slot
            for other in enemies
        )
        lower_blocker_exists = any(
            int(blocker["lane"]) == lane and int(blocker["y_slot"]) > y_slot
            for blocker in blockers
        )
        if not lower_enemy_exists and not lower_blocker_exists:
            expected_ids.append(str(enemy["enemy_id"]))

    assert int(out.answer_gt.value) == len(execution["clear_enemy_ids"]) == 5
    assert list(execution["clear_enemy_ids"]) == expected_ids
    assert list(execution["evidence_entity_ids"]) == list(execution["clear_enemy_ids"])


def test_games_space_shooter_projectile_intercept_count_matches_trace() -> None:
    out = GamesSpaceShooterProjectileInterceptCountTask().generate(
        88120,
        params={"target_answer": 4, "lane_count": 8, "enemy_count": 12},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    player_lane = int(execution["player_lane"])
    aligned = [
        str(projectile["projectile_id"])
        for projectile in execution["projectiles"]
        if int(projectile["lane"]) == player_lane
    ]

    assert int(out.answer_gt.value) == len(aligned) == 4
    assert list(execution["intercept_projectile_ids"]) == aligned
    assert list(execution["evidence_entity_ids"]) == aligned


def test_games_space_shooter_highest_threat_label_matches_unique_lowest_enemy() -> None:
    out = GamesSpaceShooterHighestThreatLabelTask().generate(
        88130,
        params={"lane_count": 7, "enemy_count": 11},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    target_id = str(execution["highest_threat_enemy_id"])
    target_enemy = next(enemy for enemy in execution["enemies"] if str(enemy["enemy_id"]) == target_id)
    other_slots = [
        int(enemy["y_slot"])
        for enemy in execution["enemies"]
        if str(enemy["enemy_id"]) != target_id
    ]

    assert str(out.answer_gt.value) == str(target_enemy["label"]) == str(execution["highest_threat_label"])
    assert int(target_enemy["y_slot"]) == 5
    assert all(slot < 5 for slot in other_slots)
    assert list(execution["evidence_entity_ids"]) == [target_id]


def test_games_space_shooter_safe_lane_count_matches_trace() -> None:
    out = GamesSpaceShooterSafeLaneCountTask().generate(
        88140,
        params={"target_answer": 3, "lane_count": 6, "enemy_count": 10},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    expected_ids = [f"lane_{int(lane)}" for lane in execution["safe_lane_indices"]]

    assert int(out.answer_gt.value) == len(expected_ids) == 3
    assert list(execution["evidence_entity_ids"]) == expected_ids


def test_games_space_shooter_non_lane_entities_do_not_share_lane_slots() -> None:
    out = GamesSpaceShooterPlayfieldTask().generate(
        88150,
        params={"query_variant": "safe_lane_count", "target_answer": 5, "lane_count": 8, "enemy_count": 16},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    occupied: list[tuple[int, int]] = []
    for key in ("enemies", "projectiles", "blockers"):
        occupied.extend((int(row["lane"]), int(row["y_slot"])) for row in execution[key])

    assert len(occupied) == len(set(occupied))


def test_games_space_shooter_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__space_shooter"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__space_shooter",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__space_shooter__clear_shot_count", count=1, params={"target_answer": 3}),
            BuildTaskConfig(task_id="task_games__space_shooter__projectile_intercept_count", count=1, params={"target_answer": 2}),
            BuildTaskConfig(task_id="task_games__space_shooter__highest_threat_label", count=1, params={}),
            BuildTaskConfig(task_id="task_games__space_shooter__safe_lane_count", count=1, params={"target_answer": 4}),
        ],
        max_attempts_per_instance=256,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-space-shooter-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 4
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["task_group"] == "space_shooter" for row in rows)
