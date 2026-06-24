"""Contract tests for games Space-shooter playfield tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.space_shooter.clear_shot_count import (
    GamesSpaceShooterClearShotCountTask,
)
from trace.tasks.games.space_shooter.clear_shot_score_value import (
    GamesSpaceShooterClearShotScoreValueTask,
)
from trace.tasks.games.space_shooter.highest_threat_label import (
    GamesSpaceShooterHighestThreatLabelTask,
)
from trace.tasks.games.space_shooter.projectile_intercept_count import (
    GamesSpaceShooterProjectileInterceptCountTask,
)
from trace.tasks.games.space_shooter.safe_lane_count import (
    GamesSpaceShooterSafeLaneCountTask,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_prompt_query_key", "expected_answer", "expected_answer_type"),
    (
        (
            GamesSpaceShooterClearShotCountTask,
            {"target_answer": 3, "lane_count": 7, "enemy_count": 12, "style_variant": "deep_space"},
            "clear_shot_count",
            3,
            "integer",
        ),
        (
            GamesSpaceShooterClearShotScoreValueTask,
            {"target_answer": 3, "lane_count": 7, "enemy_count": 12, "style_variant": "neon"},
            "clear_shot_score_value",
            None,
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
    task_cls,
    params: dict[str, int | str],
    expected_prompt_query_key: str,
    expected_answer: int | None,
    expected_answer_type: str,
) -> None:
    out = task_cls().generate(88100, params=params, max_attempts=256)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == expected_answer_type
    if expected_answer is not None:
        assert int(out.answer_gt.value) == int(expected_answer)
    expected_annotation_type = "bbox" if expected_prompt_query_key == "highest_threat_label" else "bbox_set"
    assert out.annotation_gt.type == expected_annotation_type
    assert out.query_id == "single"
    assert out.scene_id == "space_shooter"
    assert trace["query_spec"]["query_id"] == "single"
    assert trace["query_spec"]["params"]["query_id"] == "single"
    assert trace["query_spec"]["params"]["prompt_query_key"] == expected_prompt_query_key
    assert execution["query_id"] == "single"
    assert execution["prompt_query_key"] == expected_prompt_query_key
    if expected_annotation_type == "bbox":
        assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
    else:
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert trace["render_spec"]["panel_scene_style"]["treatment"]
    assert trace["render_spec"]["text_style"]["font_family"]
    assert trace["render_map"]["panel_bbox_px"] is not None
    expected_count = 1 if expected_annotation_type == "bbox" else len(out.annotation_gt.value)
    assert len(execution["annotation_entity_ids"]) == expected_count


def test_games_space_shooter_clear_shot_count_matches_trace() -> None:
    out = GamesSpaceShooterClearShotCountTask().generate(
        88110,
        params={"target_answer": 5, "lane_count": 8, "enemy_count": 16},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    enemies = execution["enemies"]
    projectiles = execution["projectiles"]
    expected_ids = []
    for enemy in enemies:
        lane = int(enemy["lane"])
        y_slot = int(enemy["y_slot"])
        lower_enemy_exists = any(
            int(other["lane"]) == lane and int(other["y_slot"]) > y_slot
            for other in enemies
        )
        lower_player_projectile_exists = any(
            str(projectile["owner"]) == "player"
            and int(projectile["lane"]) == lane
            and int(projectile["y_slot"]) > y_slot
            for projectile in projectiles
        )
        if not lower_enemy_exists and not lower_player_projectile_exists:
            expected_ids.append(str(enemy["enemy_id"]))

    assert int(out.answer_gt.value) == len(execution["clear_enemy_ids"]) == 5
    assert list(execution["clear_enemy_ids"]) == expected_ids
    assert list(execution["annotation_entity_ids"]) == list(execution["clear_enemy_ids"])


def test_games_space_shooter_clear_shot_score_value_matches_trace() -> None:
    out = GamesSpaceShooterClearShotScoreValueTask().generate(
        88115,
        params={"target_answer": 4, "lane_count": 8, "enemy_count": 16},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    enemies = execution["enemies"]
    projectiles = execution["projectiles"]
    clear_ids = []
    for enemy in enemies:
        lane = int(enemy["lane"])
        y_slot = int(enemy["y_slot"])
        lower_enemy_exists = any(
            int(other["lane"]) == lane and int(other["y_slot"]) > y_slot
            for other in enemies
        )
        lower_player_projectile_exists = any(
            str(projectile["owner"]) == "player"
            and int(projectile["lane"]) == lane
            and int(projectile["y_slot"]) > y_slot
            for projectile in projectiles
        )
        if not lower_enemy_exists and not lower_player_projectile_exists:
            clear_ids.append(str(enemy["enemy_id"]))

    enemy_by_id = {str(enemy["enemy_id"]): enemy for enemy in enemies}
    expected_score = sum(int(enemy_by_id[enemy_id]["score_value"]) for enemy_id in clear_ids)
    blocked_scored = [
        enemy
        for enemy in enemies
        if str(enemy["enemy_id"]) not in set(clear_ids) and enemy["score_value"] is not None
    ]

    assert clear_ids == list(execution["clear_enemy_ids"])
    assert list(execution["annotation_entity_ids"]) == clear_ids
    assert int(out.answer_gt.value) == expected_score
    assert len(clear_ids) == 4
    assert blocked_scored
    assert all(str(enemy["display_text"]) == str(int(enemy["score_value"])) for enemy in enemies)
    assert "Clear-shot enemies score their printed value." in out.prompt


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
        if str(projectile["owner"]) == "enemy" and int(projectile["lane"]) == player_lane
    ]

    assert int(out.answer_gt.value) == len(aligned) == 4
    assert list(execution["intercept_projectile_ids"]) == aligned
    assert list(execution["annotation_entity_ids"]) == aligned
    for bbox in out.annotation_gt.value:
        assert float(bbox[2]) - float(bbox[0]) >= 24.0
        assert float(bbox[3]) - float(bbox[1]) >= 24.0


def test_games_space_shooter_highest_threat_label_matches_unique_lowest_enemy() -> None:
    out = GamesSpaceShooterHighestThreatLabelTask().generate(
        88130,
        params={"lane_count": 7, "enemy_count": 11},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    target_id = str(execution["lowest_enemy_id"])
    target_enemy = next(enemy for enemy in execution["enemies"] if str(enemy["enemy_id"]) == target_id)
    other_slots = [
        int(enemy["y_slot"])
        for enemy in execution["enemies"]
        if str(enemy["enemy_id"]) != target_id
    ]

    assert str(out.answer_gt.value) == str(target_enemy["label"]) == str(execution["lowest_enemy_label"])
    assert int(target_enemy["y_slot"]) == 5
    assert all(slot < 5 for slot in other_slots)
    assert list(execution["annotation_entity_ids"]) == [target_id]
    assert out.annotation_gt.type == "bbox"


def test_games_space_shooter_safe_lane_count_matches_trace() -> None:
    out = GamesSpaceShooterSafeLaneCountTask().generate(
        88140,
        params={"target_answer": 3, "lane_count": 6, "enemy_count": 10},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    threatened_lanes = {int(projectile["lane"]) for projectile in execution["projectiles"] if str(projectile["owner"]) == "enemy"}
    expected_ids = [f"lane_{int(lane)}" for lane in range(int(execution["lane_count"])) if int(lane) not in threatened_lanes]

    assert int(out.answer_gt.value) == len(expected_ids) == 3
    assert list(execution["annotation_entity_ids"]) == expected_ids


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
    out = GamesSpaceShooterProjectileInterceptCountTask().generate(
        88155,
        params={"target_answer": 5, "lane_count": 8, "enemy_count": 14},
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
        (GamesSpaceShooterClearShotCountTask, {"target_answer": 5, "lane_count": 8, "enemy_count": 16}),
        (GamesSpaceShooterClearShotScoreValueTask, {"target_answer": 4, "lane_count": 8, "enemy_count": 16}),
        (GamesSpaceShooterProjectileInterceptCountTask, {"target_answer": 5, "lane_count": 8, "enemy_count": 14}),
        (GamesSpaceShooterHighestThreatLabelTask, {"lane_count": 8, "enemy_count": 14}),
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
            BuildTaskConfig(task_id="task_games__space_shooter__clear_shot_count", count=1, params={"target_answer": 3}),
            BuildTaskConfig(task_id="task_games__space_shooter__clear_shot_score_value", count=1, params={"target_answer": 3}),
            BuildTaskConfig(task_id="task_games__space_shooter__projectile_intercept_count", count=1, params={"target_answer": 2}),
            BuildTaskConfig(task_id="task_games__space_shooter__highest_threat_label", count=1, params={}),
            BuildTaskConfig(task_id="task_games__space_shooter__safe_lane_count", count=1, params={"target_answer": 4}),
        ],
        max_attempts_per_instance=256,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-space-shooter-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 5
    assert all(row["domain"] == "games" for row in rows)
    assert all(row.get("scene_id") == "space_shooter" for row in rows)
