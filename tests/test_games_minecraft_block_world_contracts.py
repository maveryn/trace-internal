"""Contract tests for Minecraft-like games tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.minecraft.block_world_tasks import (
    ORE_BLOCK_QUERY_ID,
    RESOURCE_ROUTE_QUERY_ID,
    TUNNEL_CLEARANCE_QUERY_ID,
    GamesMinecraftOreBlockCountTask,
    GamesMinecraftRouteBlockCountTask,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "target_answer", "expected_query", "extra_params"),
    (
        (GamesMinecraftOreBlockCountTask, 4, ORE_BLOCK_QUERY_ID, {}),
        (GamesMinecraftRouteBlockCountTask, 5, TUNNEL_CLEARANCE_QUERY_ID, {"query_id": TUNNEL_CLEARANCE_QUERY_ID}),
        (GamesMinecraftRouteBlockCountTask, 5, RESOURCE_ROUTE_QUERY_ID, {"query_id": RESOURCE_ROUTE_QUERY_ID}),
    ),
)
def test_games_minecraft_public_tasks_emit_expected_contract(
    task_cls,
    target_answer: int,
    expected_query: str,
    extra_params: dict[str, str],
) -> None:
    out = task_cls().generate(
        2026052201,
        params={"target_answer": int(target_answer), "style_variant": "grass", **extra_params},
        max_attempts=512,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_id == expected_query
    assert out.scene_id == "minecraft"
    assert trace["query_spec"]["query_id"] == expected_query
    assert execution["query_id"] == expected_query
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(out.evidence_gt.value) >= 1
    assert "panel_scene_style" in trace["render_spec"]
    assert trace["render_spec"]["text_style"]["font_family"]


def test_games_minecraft_ore_count_evidence_matches_target_kind() -> None:
    out = GamesMinecraftOreBlockCountTask().generate(
        2026052202,
        params={"target_answer": 5, "resource_kind": "diamond_ore"},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    evidence_ids = {str(entity_id) for entity_id in execution["evidence_entity_ids"]}
    target_kind = str(execution["counted_resource_kind"])
    counted_ids = {str(block["block_id"]) for block in execution["blocks"] if str(block["kind"]) == target_kind}

    assert target_kind == "diamond_ore"
    assert int(out.answer_gt.value) == 5
    assert evidence_ids == counted_ids


def test_games_minecraft_tunnel_clearance_evidence_is_on_marked_path() -> None:
    out = GamesMinecraftRouteBlockCountTask().generate(
        2026052203,
        params={
            "target_answer": 6,
            "grid_width": 10,
            "grid_depth": 10,
            "query_id": TUNNEL_CLEARANCE_QUERY_ID,
        },
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    evidence_ids = [str(entity_id) for entity_id in execution["evidence_entity_ids"]]
    evidence_blocks = [block for block in execution["blocks"] if str(block["block_id"]) in set(evidence_ids)]

    assert int(out.answer_gt.value) == len(evidence_ids) == 6
    assert all(entity_id.startswith("tunnel_block_") for entity_id in evidence_ids)
    assert all(str(block["kind"]) in {"stone", "dirt"} for block in evidence_blocks)


def test_games_minecraft_resource_route_cost_matches_queried_route() -> None:
    out = GamesMinecraftRouteBlockCountTask().generate(
        2026052204,
        params={
            "target_answer": 5,
            "grid_width": 11,
            "grid_depth": 10,
            "query_id": RESOURCE_ROUTE_QUERY_ID,
        },
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    route_costs = [(str(label), int(cost)) for label, cost in execution["route_costs"]]
    queried_label = str(execution["selected_route_label"])
    queried_cost = dict(route_costs)[queried_label]

    assert int(out.answer_gt.value) == queried_cost == 5
    assert len(execution["evidence_entity_ids"]) == int(out.answer_gt.value)
    assert any(str(entity_id).startswith(f"route_{queried_label.lower()}_") for entity_id in execution["evidence_entity_ids"])
    assert all(
        str(entity_id).startswith(f"route_{queried_label.lower()}_obstacle_")
        for entity_id in execution["evidence_entity_ids"]
    )


def test_games_minecraft_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__minecraft"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__minecraft",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__minecraft__ore_block_count", count=1, params={}),
            BuildTaskConfig(
                task_id="task_games__minecraft__route_block_count",
                count=2,
                params={},
            ),
        ],
        max_attempts_per_instance=512,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-minecraft-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 3
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["task_group"] == "minecraft" for row in rows)
    assert {row["scene_id"] for row in rows} == {"minecraft"}
