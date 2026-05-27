"""Contract tests for games Platformer level tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.platformer.level_tasks import (
    GamesPlatformerCollectibleCountTask,
    GamesPlatformerJumpLandingLabelTask,
    GamesPlatformerLevelTask,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query", "expected_type"),
    (
        (
            GamesPlatformerJumpLandingLabelTask,
            {"target_platform_label": "F", "platform_count": 7, "style_variant": "snow"},
            "jump_landing_label",
            "string",
        ),
        (
            GamesPlatformerCollectibleCountTask,
            {"target_collectible_count": 6, "style_variant": "cave"},
            "collectible_count",
            "integer",
        ),
    ),
)
def test_games_platformer_public_tasks_emit_expected_contract(
    task_cls: type[GamesPlatformerLevelTask],
    params: dict[str, int | str],
    expected_query: str,
    expected_type: str,
) -> None:
    out = task_cls().generate(97200, params=params, max_attempts=512)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == expected_type
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_id == "default"
    assert out.query_id == expected_query
    assert out.scene_id == "platformer"
    assert trace["query_spec"]["query_id"] == expected_query
    assert trace["query_spec"]["query_id"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == expected_query
    assert trace["query_spec"]["params"]["query_id"] == "default"
    assert execution["query_id"] == expected_query
    assert execution["query_id"] == "default"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value)


def test_games_platformer_landing_answer_matches_target_platform() -> None:
    out = GamesPlatformerJumpLandingLabelTask().generate(
        97210,
        params={"target_platform_label": "H", "platform_count": 7},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    target_id = str(execution["target_platform_id"])
    target_platform = next(platform for platform in execution["platforms"] if str(platform["platform_id"]) == target_id)

    assert str(out.answer_gt.value) == str(target_platform["label"])
    assert list(execution["evidence_entity_ids"]) == [target_id]
    assert 4 <= len(execution["platforms"]) <= 7


def test_games_platformer_collectible_count_matches_on_path_coins() -> None:
    out = GamesPlatformerCollectibleCountTask().generate(
        97230,
        params={"target_collectible_count": 7},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    on_path_ids = [str(coin["collectible_id"]) for coin in execution["collectibles"] if bool(coin["on_path"])]

    assert int(out.answer_gt.value) == len(on_path_ids) == 7
    assert list(execution["evidence_entity_ids"]) == on_path_ids
    assert len(out.evidence_gt.value) == 7


def test_games_platformer_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__platformer"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__platformer",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__platformer__jump_landing_label", count=1, params={}),
            BuildTaskConfig(task_id="task_games__platformer__collectible_count", count=1, params={}),
        ],
        max_attempts_per_instance=512,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-platformer-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 2
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["task_group"] == "platformer" for row in rows)
