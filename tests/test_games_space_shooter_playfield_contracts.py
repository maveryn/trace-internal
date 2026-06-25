"""Contract tests for games Space-shooter playfield tasks."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.space_shooter.enemy_ship_count import (
    GamesSpaceShooterEnemyShipCountTask,
)
from trace.tasks.games.space_shooter.safe_lane_count import (
    GamesSpaceShooterSafeLaneCountTask,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_prompt_query_key", "expected_answer"),
    (
        (
            GamesSpaceShooterEnemyShipCountTask,
            {"lane_count": 7, "enemy_count": 9, "style_variant": "deep_space"},
            "enemy_ship_count",
            9,
        ),
        (
            GamesSpaceShooterSafeLaneCountTask,
            {"target_answer": 2, "lane_count": 6, "enemy_count": 10, "style_variant": "terminal"},
            "safe_lane_count",
            2,
        ),
    ),
)
def test_games_space_shooter_public_tasks_emit_expected_contract(
    task_cls,
    params: dict[str, int | str],
    expected_prompt_query_key: str,
    expected_answer: int,
) -> None:
    out = task_cls().generate(88100, params=params, max_attempts=256)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.annotation_gt.type == "bbox_set"
    assert out.query_id == "single"
    assert out.scene_id == "space_shooter"
    assert trace["query_spec"]["query_id"] == "single"
    assert trace["query_spec"]["params"]["query_id"] == "single"
    assert trace["query_spec"]["params"]["prompt_query_key"] == expected_prompt_query_key
    assert execution["query_id"] == "single"
    assert execution["prompt_query_key"] == expected_prompt_query_key
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert trace["render_spec"]["panel_scene_style"]["treatment"]
    assert trace["render_spec"]["text_style"]["font_family"]
    assert trace["render_map"]["panel_bbox_px"] is not None
    assert len(execution["annotation_entity_ids"]) == len(out.annotation_gt.value)


def test_games_space_shooter_enemy_ship_count_matches_trace() -> None:
    out = GamesSpaceShooterEnemyShipCountTask().generate(
        88105,
        params={"lane_count": 7, "enemy_count": 11},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    enemy_ids = [str(enemy["enemy_id"]) for enemy in execution["enemies"]]
    enemy_projectile_counts_by_lane = Counter(
        int(projectile["lane"])
        for projectile in execution["projectiles"]
        if str(projectile["owner"]) == "enemy"
    )

    assert int(out.answer_gt.value) == len(enemy_ids) == 11
    assert list(execution["annotation_entity_ids"]) == enemy_ids
    assert out.trace_payload["render_map"]["show_enemy_labels"] is False
    enemy_entities = [
        entity
        for entity in out.trace_payload["scene_ir"]["entities"]
        if entity["entity_type"] == "enemy_ship"
    ]
    assert len(enemy_entities) == 11
    assert all(entity["text_visible"] is False for entity in enemy_entities)
    assert all(entity["display_text"] is None for entity in enemy_entities)
    assert len(out.annotation_gt.value) == len(enemy_ids)
    assert enemy_projectile_counts_by_lane
    assert max(enemy_projectile_counts_by_lane.values()) >= 2
    assert all(1 <= int(count) <= 3 for count in enemy_projectile_counts_by_lane.values())
    for bbox in out.annotation_gt.value:
        assert float(bbox[2]) - float(bbox[0]) >= 24.0
        assert float(bbox[3]) - float(bbox[1]) >= 24.0


def test_games_space_shooter_safe_lane_count_matches_trace() -> None:
    out = GamesSpaceShooterSafeLaneCountTask().generate(
        88140,
        params={"target_answer": 3, "lane_count": 6, "enemy_count": 10},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    enemy_projectile_counts_by_lane = Counter(
        int(projectile["lane"])
        for projectile in execution["projectiles"]
        if str(projectile["owner"]) == "enemy"
    )
    threatened_lanes = set(enemy_projectile_counts_by_lane)
    expected_ids = [
        f"lane_{int(lane)}"
        for lane in range(int(execution["lane_count"]))
        if int(lane) not in threatened_lanes
    ]

    assert int(out.answer_gt.value) == len(expected_ids) == 3
    assert list(execution["annotation_entity_ids"]) == expected_ids
    assert out.trace_payload["render_map"]["show_enemy_labels"] is False
    assert enemy_projectile_counts_by_lane
    assert max(enemy_projectile_counts_by_lane.values()) >= 2
    assert all(1 <= int(count) <= 3 for count in enemy_projectile_counts_by_lane.values())


def test_games_space_shooter_non_lane_entities_do_not_share_lane_slots() -> None:
    out = GamesSpaceShooterSafeLaneCountTask().generate(
        88150,
        params={"target_answer": 5, "lane_count": 8, "enemy_count": 16},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    occupied: list[tuple[int, int]] = []
    for key in ("enemies", "projectiles"):
        occupied.extend((int(row["lane"]), int(row["y_slot"])) for row in execution[key])

    assert len(occupied) == len(set(occupied))
    assert "blockers" not in execution


def test_games_space_shooter_ships_and_projectiles_are_centered_on_lane_pads() -> None:
    out = GamesSpaceShooterSafeLaneCountTask().generate(
        88155,
        params={"target_answer": 3, "lane_count": 8, "enemy_count": 14},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    render_map = out.trace_payload["render_map"]
    lane_bboxes = render_map["lane_bboxes_px"]
    enemy_bboxes = render_map["enemy_bboxes_px"]
    projectile_bboxes = render_map["projectile_bboxes_px"]
    for enemy in execution["enemies"]:
        enemy_bbox = enemy_bboxes[str(enemy["enemy_id"])]
        lane_bbox = lane_bboxes[f"lane_{int(enemy['lane'])}"]
        enemy_cx = 0.5 * (float(enemy_bbox[0]) + float(enemy_bbox[2]))
        lane_cx = 0.5 * (float(lane_bbox[0]) + float(lane_bbox[2]))
        assert abs(enemy_cx - lane_cx) <= 0.75
    for projectile in execution["projectiles"]:
        projectile_bbox = projectile_bboxes[str(projectile["projectile_id"])]
        lane_bbox = lane_bboxes[f"lane_{int(projectile['lane'])}"]
        projectile_cx = 0.5 * (float(projectile_bbox[0]) + float(projectile_bbox[2]))
        lane_cx = 0.5 * (float(lane_bbox[0]) + float(lane_bbox[2]))
        assert abs(projectile_cx - lane_cx) <= 0.75


@pytest.mark.parametrize(
    ("task_cls", "params"),
    (
        (GamesSpaceShooterEnemyShipCountTask, {"lane_count": 8, "enemy_count": 12}),
        (GamesSpaceShooterSafeLaneCountTask, {"target_answer": 3, "lane_count": 7, "enemy_count": 12}),
    ),
)
def test_games_space_shooter_enemy_projectiles_have_visible_same_lane_shooter(task_cls, params) -> None:
    out = task_cls().generate(88165, params=params, max_attempts=256)
    execution = out.trace_payload["execution_trace"]
    enemies = tuple(execution["enemies"])
    for projectile in execution["projectiles"]:
        if str(projectile["owner"]) != "enemy":
            continue
        assert any(
            int(enemy["lane"]) == int(projectile["lane"])
            and int(enemy["y_slot"]) < int(projectile["y_slot"])
            for enemy in enemies
        )


def test_games_space_shooter_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__space_shooter"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__space_shooter",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__space_shooter__enemy_ship_count", count=1, params={"enemy_count": 7}),
            BuildTaskConfig(task_id="task_games__space_shooter__safe_lane_count", count=1, params={"target_answer": 4}),
        ],
        max_attempts_per_instance=256,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-space-shooter-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 2
    assert all(row["domain"] == "games" for row in rows)
    assert all(row.get("scene_id") == "space_shooter" for row in rows)
