"""Contract tests for Minecraft-like games tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.minecraft.resource_route_cost import (
    AT_LEAST_HEIGHT_QUERY_ID,
    EXACT_HEIGHT_QUERY_ID,
    REACHABLE_ORE_STACK_QUERY_ID,
    RESOURCE_ROUTE_QUERY_ID,
    GamesMinecraftReachableOreStackCountTask,
    GamesMinecraftResourceRouteCostTask,
    GamesMinecraftStackHeightConditionCountTask,
    GamesMinecraftTopOreStackCountTask,
    TOP_ORE_STACK_QUERY_ID,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "target_answer", "expected_query", "extra_params"),
    (
        (GamesMinecraftTopOreStackCountTask, 4, TOP_ORE_STACK_QUERY_ID, {}),
        (GamesMinecraftReachableOreStackCountTask, 3, REACHABLE_ORE_STACK_QUERY_ID, {}),
        (GamesMinecraftResourceRouteCostTask, 5, RESOURCE_ROUTE_QUERY_ID, {"query_id": RESOURCE_ROUTE_QUERY_ID}),
        (GamesMinecraftStackHeightConditionCountTask, 4, EXACT_HEIGHT_QUERY_ID, {"query_id": EXACT_HEIGHT_QUERY_ID}),
        (GamesMinecraftStackHeightConditionCountTask, 4, AT_LEAST_HEIGHT_QUERY_ID, {"query_id": AT_LEAST_HEIGHT_QUERY_ID}),
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
    assert out.annotation_gt.type == "point_set"
    assert out.query_id == expected_query
    assert out.scene_id == "minecraft"
    assert trace["query_spec"]["query_id"] == expected_query
    assert execution["query_id"] == expected_query
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_point_set"] == out.annotation_gt.value
    assert len(out.annotation_gt.value) >= 1
    assert "panel_scene_style" in trace["render_spec"]
    assert trace["render_spec"]["text_style"]["font_family"]


def test_games_minecraft_top_ore_stack_annotation_matches_target_kind() -> None:
    out = GamesMinecraftTopOreStackCountTask().generate(
        2026052202,
        params={"target_answer": 5, "resource_kind": "iron_ore"},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    annotation_ids = {str(entity_id) for entity_id in execution["annotation_entity_ids"]}
    target_kind = str(execution["counted_resource_kind"])
    top_by_coord: dict[tuple[int, int], tuple[int, str]] = {}
    for block in execution["blocks"]:
        coord = (int(block["x"]), int(block["y"]))
        z = int(block["z"])
        if coord not in top_by_coord or z > top_by_coord[coord][0]:
            top_by_coord[coord] = (z, str(block["kind"]))
    counted_ids = {
        f"stack_{x:02d}_{y:02d}"
        for (x, y), (_z, kind) in top_by_coord.items()
        if str(kind) == target_kind
    }

    assert target_kind == "iron_ore"
    assert int(out.answer_gt.value) == 5
    assert annotation_ids == counted_ids
    assert all(entity_id.startswith("stack_") for entity_id in annotation_ids)


@pytest.mark.parametrize("resource_kind", ("iron_ore", "gold_ore", "diamond_ore"))
def test_games_minecraft_reachable_ore_stack_count_matches_line_rule(resource_kind: str) -> None:
    out = GamesMinecraftReachableOreStackCountTask().generate(
        2026060803,
        params={
            "target_answer": 4,
            "resource_kind": str(resource_kind),
            "line_length": 8,
        },
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    line_cells = tuple((int(x), int(y)) for x, y in execution["stack_line_cells"])
    annotation_ids = {str(entity_id) for entity_id in execution["annotation_entity_ids"]}
    target_kind = str(execution["counted_resource_kind"])

    top_by_coord: dict[tuple[int, int], tuple[int, str]] = {}
    z_values_by_coord: dict[tuple[int, int], set[int]] = {}
    for block in execution["blocks"]:
        coord = (int(block["x"]), int(block["y"]))
        z = int(block["z"])
        if str(block["kind"]).endswith("_ore"):
            assert str(block["kind"]) == target_kind
        z_values_by_coord.setdefault(coord, set()).add(z)
        if coord not in top_by_coord or z > top_by_coord[coord][0]:
            top_by_coord[coord] = (z, str(block["kind"]))

    heights = [len(z_values_by_coord[coord]) for coord in line_cells]
    assert heights == sorted(heights)
    reachable_prefix_length = 1
    for left_height, right_height in zip(heights, heights[1:]):
        if int(right_height) <= int(left_height) + 1:
            reachable_prefix_length += 1
        else:
            break
    expected_ids = {
        f"stack_{x:02d}_{y:02d}"
        for x, y in line_cells[:reachable_prefix_length]
        if str(top_by_coord[(x, y)][1]) == target_kind
    }
    unreachable_target_ids = {
        f"stack_{x:02d}_{y:02d}"
        for x, y in line_cells[reachable_prefix_length:]
        if str(top_by_coord[(x, y)][1]) == target_kind
    }

    assert target_kind == str(resource_kind)
    assert 6 <= int(execution["line_length"]) <= 10
    assert int(execution["reachable_prefix_length"]) == reachable_prefix_length
    assert execution["first_blocker_index"] == reachable_prefix_length
    assert execution["stack_heights"] == heights
    assert heights[0] == 1
    assert int(out.answer_gt.value) == len(expected_ids) == 4
    assert annotation_ids == expected_ids
    assert unreachable_target_ids
    assert execution["player_cell"] is None
    assert execution["target_cell"] is None
    assert "START" not in out.prompt
    assert out.trace_payload["render_map"]["view_projection"] == "isometric_block_world"


def test_games_minecraft_reachable_ore_stack_count_allows_zero_answer() -> None:
    out = GamesMinecraftReachableOreStackCountTask().generate(
        2026060804,
        params={"target_answer": 0, "resource_kind": "gold_ore", "line_length": 6},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]

    assert int(out.answer_gt.value) == 0
    assert out.annotation_gt.value == []
    assert execution["annotation_entity_ids"] == []
    assert str(execution["counted_resource_kind"]) == "gold_ore"
    assert int(execution["reachable_prefix_length"]) < int(execution["line_length"])
    assert execution["player_cell"] is None
    assert execution["target_cell"] is None


def test_games_minecraft_reachable_ore_stack_count_answer_six_is_feasible() -> None:
    out = GamesMinecraftReachableOreStackCountTask().generate(
        2026060806,
        params={"target_answer": 6, "resource_kind": "diamond_ore", "line_length": 8},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]

    assert int(out.answer_gt.value) == 6
    assert int(execution["line_length"]) == 8
    assert int(execution["reachable_prefix_length"]) >= 6
    assert len(execution["annotation_entity_ids"]) == 6


def test_games_minecraft_reachable_ore_stack_count_tall_stacks_do_not_clip() -> None:
    out = GamesMinecraftReachableOreStackCountTask().generate(
        501110198081843,
        params={},
        max_attempts=512,
    )
    width, height = out.image.size
    bboxes = out.trace_payload["render_map"]["entity_bboxes_px"].values()
    points = out.trace_payload["render_map"]["entity_points_px"].values()

    assert out.trace_payload["render_map"]["view_projection"] == "isometric_block_world"
    assert all(0 <= float(bbox[0]) <= float(width) for bbox in bboxes)
    assert all(0 <= float(bbox[2]) <= float(width) for bbox in bboxes)
    assert all(0 <= float(bbox[1]) <= float(height) for bbox in bboxes)
    assert all(0 <= float(bbox[3]) <= float(height) for bbox in bboxes)
    assert all(0 <= float(point[0]) <= float(width) for point in points)
    assert all(0 <= float(point[1]) <= float(height) for point in points)


def test_games_minecraft_resource_route_cost_matches_queried_route() -> None:
    out = GamesMinecraftResourceRouteCostTask().generate(
        2026052204,
        params={
            "target_answer": 5,
            "grid_width": 11,
            "grid_depth": 10,
            "query_id": RESOURCE_ROUTE_QUERY_ID,
            "route_option_count": 3,
        },
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    route_costs = [(str(label), int(cost)) for label, cost in execution["route_costs"]]
    queried_label = str(execution["selected_route_label"])
    queried_cost = dict(route_costs)[queried_label]

    assert int(out.answer_gt.value) == queried_cost == 5
    assert len(route_costs) == int(execution["route_option_count"]) == 3
    assert set(label for label, _cost in route_costs) == {"A", "B", "C"}
    assert len(execution["annotation_entity_ids"]) == int(out.answer_gt.value)
    assert any(str(entity_id).startswith(f"route_{queried_label.lower()}_") for entity_id in execution["annotation_entity_ids"])
    assert all(
        str(entity_id).startswith(f"route_{queried_label.lower()}_obstacle_")
        for entity_id in execution["annotation_entity_ids"]
    )


def test_games_minecraft_resource_route_option_count_varies() -> None:
    seen_counts: set[int] = set()
    for seed in range(2026052250, 2026052268):
        out = GamesMinecraftResourceRouteCostTask().generate(
            seed,
            params={"query_id": RESOURCE_ROUTE_QUERY_ID},
            max_attempts=512,
        )
        execution = out.trace_payload["execution_trace"]
        seen_counts.add(int(execution["route_option_count"]))
        assert 2 <= int(execution["route_option_count"]) <= 3
        assert int(execution["route_option_count"]) == len(execution["route_costs"])

    assert seen_counts == {2, 3}


@pytest.mark.parametrize(
    ("query_id", "target_height"),
    (
        (EXACT_HEIGHT_QUERY_ID, 4),
        (AT_LEAST_HEIGHT_QUERY_ID, 3),
    ),
)
def test_games_minecraft_stack_height_condition_matches_trace(query_id: str, target_height: int) -> None:
    out = GamesMinecraftStackHeightConditionCountTask().generate(
        2026060801,
        params={
            "query_id": str(query_id),
            "target_answer": 5,
            "target_stack_height": int(target_height),
            "grid_width": 9,
            "grid_depth": 9,
        },
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    heights: dict[tuple[int, int], set[int]] = {}
    for block in execution["blocks"]:
        heights.setdefault((int(block["x"]), int(block["y"])), set()).add(int(block["z"]))

    if str(query_id) == EXACT_HEIGHT_QUERY_ID:
        expected = {
            f"stack_{x:02d}_{y:02d}"
            for (x, y), z_values in heights.items()
            if len(z_values) == int(target_height)
        }
        assert execution["stack_height_condition"] == "exact"
    else:
        expected = {
            f"stack_{x:02d}_{y:02d}"
            for (x, y), z_values in heights.items()
            if len(z_values) >= int(target_height)
        }
        assert execution["stack_height_condition"] == "at_least"

    assert execution["target_stack_height"] == int(target_height)
    assert int(out.answer_gt.value) == len(expected) == 5
    assert set(execution["annotation_entity_ids"]) == expected
    assert len(out.annotation_gt.value) == len(expected)
    assert all(entity_id.startswith("stack_") for entity_id in execution["annotation_entity_ids"])


def test_games_minecraft_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__minecraft"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__minecraft",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__minecraft__top_ore_stack_count", count=1, params={}),
            BuildTaskConfig(task_id="task_games__minecraft__reachable_ore_stack_count", count=1, params={}),
            BuildTaskConfig(
                task_id="task_games__minecraft__resource_route_cost",
                count=2,
                params={},
            ),
            BuildTaskConfig(
                task_id="task_games__minecraft__stack_height_condition_count",
                count=2,
                params={},
            ),
        ],
        max_attempts_per_instance=512,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-minecraft-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 6
    assert all(row["domain"] == "games" for row in rows)
    assert all(row.get("scene_id") == "minecraft" for row in rows)
    assert {row["scene_id"] for row in rows} == {"minecraft"}
