from __future__ import annotations

from trace.tasks.registry import create_task
from trace.tasks.illustrations.rpg_tactical_map.movement_attack_range_tile_label import TASK_ID as ATTACK_TASK_ID
from trace.tasks.illustrations.rpg_tactical_map.movement_cost_value import TASK_ID as COST_VALUE_TASK_ID
from trace.tasks.illustrations.rpg_tactical_map.movement_reachable_tile_count import TASK_ID as COUNT_TASK_ID
from trace.tasks.illustrations.rpg_tactical_map.movement_reachable_tile_label import TASK_ID as LABEL_TASK_ID
from trace.tasks.illustrations.rpg_tactical_map.terrain_type_tile_count import TASK_ID as TERRAIN_COUNT_TASK_ID
from trace.tasks.illustrations.rpg_tactical_map.shared.relations import (
    TERRAIN_GRASS,
    TERRAIN_MOUNTAIN,
    TERRAIN_WATER,
    shortest_movement_costs,
)
from trace.tasks.illustrations.rpg_tactical_map.shared.rendering import (
    DEFAULT_TILE_PX,
    render_rpg_tactical_map_scene,
    resolve_tactical_map_render_params,
)
from trace.tasks.illustrations.rpg_tactical_map.shared.state import RpgTacticalTile


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= float(width)
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= float(height)


def _tile(tile_id: str, row: int, col: int, terrain: str, cost: int | None, passable: bool) -> RpgTacticalTile:
    return RpgTacticalTile(
        tile_id=tile_id,
        row=row,
        col=col,
        terrain=terrain,
        movement_cost=cost,
        passable=passable,
        bbox_xyxy=(float(col * 10), float(row * 10), float(col * 10 + 10), float(row * 10 + 10)),
        point_xy=(float(col * 10 + 5), float(row * 10 + 5)),
        metadata={},
    )


def test_rpg_tactical_map_pathfinding_uses_mountain_cost_three() -> None:
    tiles = {
        (0, 0): _tile("start", 0, 0, TERRAIN_GRASS, 1, True),
        (0, 1): _tile("mountain", 0, 1, TERRAIN_MOUNTAIN, 3, True),
        (0, 2): _tile("after", 0, 2, TERRAIN_GRASS, 1, True),
        (1, 0): _tile("water", 1, 0, TERRAIN_WATER, None, False),
    }
    costs = shortest_movement_costs(tiles, start_coord=(0, 0))
    assert costs["start"] == 0
    assert costs["mountain"] == 3
    assert costs["after"] == 4
    assert "water" not in costs


def test_rpg_tactical_map_renderer_is_deterministic_and_profile_safe() -> None:
    for profile, expected_size in (
        ("landscape", (960, 640)),
        ("square", (800, 800)),
        ("portrait", (640, 960)),
    ):
        params = resolve_tactical_map_render_params({"canvas_profile": profile}, {}, instance_seed=101)
        first = render_rpg_tactical_map_scene(
            12345,
            width=params["canvas_width"],
            height=params["canvas_height"],
            grid_cols=params["grid_cols"],
            grid_rows=params["grid_rows"],
            tile_px=params["tile_px"],
            candidate_tile_ids_by_label={"A": "r00_c00", "B": "r00_c01", "C": "r01_c00", "D": "r01_c01"},
            render_metadata=params,
        )
        second = render_rpg_tactical_map_scene(
            12345,
            width=params["canvas_width"],
            height=params["canvas_height"],
            grid_cols=params["grid_cols"],
            grid_rows=params["grid_rows"],
            tile_px=params["tile_px"],
            candidate_tile_ids_by_label={"A": "r00_c00", "B": "r00_c01", "C": "r01_c00", "D": "r01_c01"},
            render_metadata=params,
        )
        assert first.image.size == expected_size
        assert list(first.image.getdata()) == list(second.image.getdata())
        assert first.trace["tile_px"] == DEFAULT_TILE_PX
        assert first.trace["canvas_profile"] == profile
        assert first.trace["terrain_movement_costs"]["mountain"] == 3
        assert first.trace["blocked_terrain"] == ["water"]
        assert len(first.tiles) == int(params["grid_cols"]) * int(params["grid_rows"])
        assert len(first.units) == 1
        assert sorted(first.label_bboxes_by_tile_id) == ["r00_c00", "r00_c01", "r01_c00", "r01_c01"]
        width, height = first.image.size
        for tile in first.tiles:
            _assert_bbox_inside_canvas(list(tile.bbox_xyxy), width=width, height=height)
        for unit in first.units:
            _assert_bbox_inside_canvas(list(unit.bbox_xyxy), width=width, height=height)


def test_rpg_tactical_map_movement_reachable_tile_contract() -> None:
    task = create_task(LABEL_TASK_ID)
    out = task.generate(
        2026062401,
        params={
            "canvas_profile": "square",
            "movement_budget": 5,
        },
        max_attempts=30,
    )
    assert out.scene_id == "rpg_tactical_map"
    assert out.query_id == "single"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value in {"A", "B", "C", "D"}
    assert out.annotation_gt.type == "bbox"
    width, height = out.image.size
    _assert_bbox_inside_canvas(out.annotation_gt.value, width=width, height=height)
    assert "mountains cost 3" in out.prompt
    assert "water cannot be entered" in out.prompt
    assert "up, down, left, or right" in out.prompt

    trace = out.trace_payload
    render_map = trace["render_map"]
    answer_label = str(out.answer_gt.value)
    assert trace["projected_annotation"]["type"] == "bbox"
    assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
    assert render_map["selected_label"] == answer_label
    assert render_map["selected_tile_bbox_px"] == out.annotation_gt.value
    assert render_map["movement_budget"] == 5
    assert trace["execution_trace"]["selected_tile_cost"] <= 5
    assert trace["scene_ir"]["relations"]["terrain_movement_costs"]["mountain"] == 3

    reachable_labels = [
        label
        for label, cost in render_map["candidate_shortest_costs_by_label"].items()
        if cost is not None and int(cost) <= int(render_map["movement_budget"])
    ]
    assert reachable_labels == [answer_label]
    assert sorted(render_map["candidate_tile_ids_by_label"]) == ["A", "B", "C", "D"]
    assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_rpg_tactical_map_v0"
    assert trace["query_spec"]["prompt_variant"]["prompt_scene_id"] == "rpg_tactical_map"


def test_rpg_tactical_map_movement_distractors_are_plausible_and_spread() -> None:
    task = create_task(LABEL_TASK_ID)
    for seed in (2026062401, 2026062402, 2026062403, 23, 93):
        for profile in ("landscape", "square", "portrait"):
            out = task.generate(
                seed,
                params={
                    "canvas_profile": profile,
                    "movement_budget": 5,
                },
                max_attempts=30,
            )
            render_map = out.trace_payload["render_map"]
            tiles_by_id = {str(tile["tile_id"]): tile for tile in out.trace_payload["scene_ir"]["tiles"]}
            answer_label = str(out.answer_gt.value)

            reachable_labels = [
                label
                for label, cost in render_map["candidate_shortest_costs_by_label"].items()
                if cost is not None and int(cost) <= int(render_map["movement_budget"])
            ]
            assert reachable_labels == [answer_label]

            candidate_coords: list[tuple[int, int]] = []
            for label, tile_id in render_map["candidate_tile_ids_by_label"].items():
                tile = tiles_by_id[str(tile_id)]
                candidate_coords.append((int(tile["row"]), int(tile["col"])))
                cost = render_map["candidate_shortest_costs_by_label"][str(label)]
                if str(label) != answer_label and cost is not None:
                    assert int(render_map["movement_budget"]) < int(cost) <= int(render_map["movement_budget"]) + 5

            pairwise_distances = []
            for index, first in enumerate(candidate_coords):
                for second in candidate_coords[index + 1 :]:
                    pairwise_distances.append(abs(first[0] - second[0]) + abs(first[1] - second[1]))
            assert pairwise_distances
            assert min(pairwise_distances) >= 2


def test_rpg_tactical_map_movement_reachable_tile_count_contract() -> None:
    task = create_task(COUNT_TASK_ID)
    out = task.generate(
        2026062404,
        params={
            "canvas_profile": "square",
            "movement_budget": 3,
        },
        max_attempts=30,
    )
    assert out.scene_id == "rpg_tactical_map"
    assert out.query_id == "single"
    assert out.answer_gt.type == "integer"
    assert 3 <= int(out.answer_gt.value) <= 15
    assert out.annotation_gt.type == "bbox_set"
    width, height = out.image.size
    for bbox in out.annotation_gt.value:
        _assert_bbox_inside_canvas(bbox, width=width, height=height)
    assert "mountains cost 3" in out.prompt
    assert "water cannot be entered" in out.prompt
    assert "Do not count the tile the unit starts on" in out.prompt or "excluding" in out.prompt

    trace = out.trace_payload
    render_map = trace["render_map"]
    relations = trace["scene_ir"]["relations"]
    start_tile_id = str(relations["start_tile_id"])
    counted_tile_ids = [str(tile_id) for tile_id in render_map["counted_tile_ids"]]
    assert start_tile_id not in set(counted_tile_ids)
    assert int(render_map["answer_count"]) == int(out.answer_gt.value)
    assert len(counted_tile_ids) == int(out.answer_gt.value)
    assert trace["projected_annotation"]["type"] == "bbox_set"
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert render_map["counted_tile_bboxes_px"] == out.annotation_gt.value
    assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_rpg_tactical_map_v0"
    assert trace["query_spec"]["prompt_variant"]["prompt_scene_id"] == "rpg_tactical_map"

    costs_by_tile_id = trace["execution_trace"]["movement_costs_by_tile_id"]
    movement_budget = int(render_map["movement_budget"])
    for tile_id in counted_tile_ids:
        assert int(costs_by_tile_id[tile_id]) <= movement_budget
    for tile in trace["scene_ir"]["tiles"]:
        tile_id = str(tile["tile_id"])
        if tile_id == start_tile_id:
            continue
        cost = costs_by_tile_id.get(tile_id)
        if cost is not None and int(cost) <= movement_budget:
            assert tile_id in set(counted_tile_ids)


def test_rpg_tactical_map_terrain_type_tile_count_contract() -> None:
    task = create_task(TERRAIN_COUNT_TASK_ID)
    out = task.generate(
        2026062405,
        params={
            "canvas_profile": "square",
            "target_terrain": "forest",
        },
        max_attempts=30,
    )
    assert out.scene_id == "rpg_tactical_map"
    assert out.query_id == "single"
    assert out.answer_gt.type == "integer"
    assert 1 <= int(out.answer_gt.value) <= 18
    assert out.annotation_gt.type == "bbox_set"
    width, height = out.image.size
    for bbox in out.annotation_gt.value:
        _assert_bbox_inside_canvas(bbox, width=width, height=height)
    assert "forest" in out.prompt

    trace = out.trace_payload
    render_map = trace["render_map"]
    target_terrain = str(render_map["target_terrain"])
    counted_tile_ids = [str(tile_id) for tile_id in render_map["counted_tile_ids"]]
    assert target_terrain == "forest"
    assert int(render_map["answer_count"]) == int(out.answer_gt.value)
    assert len(counted_tile_ids) == int(out.answer_gt.value)
    assert trace["projected_annotation"]["type"] == "bbox_set"
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert render_map["counted_tile_bboxes_px"] == out.annotation_gt.value
    assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_rpg_tactical_map_v0"
    assert trace["query_spec"]["prompt_variant"]["prompt_scene_id"] == "rpg_tactical_map"

    terrain_by_tile_id = trace["execution_trace"]["terrain_by_tile_id"]
    assert set(counted_tile_ids) == {
        str(tile_id)
        for tile_id, terrain in terrain_by_tile_id.items()
        if str(terrain) == target_terrain
    }


def test_rpg_tactical_map_movement_attack_range_tile_contract() -> None:
    task = create_task(ATTACK_TASK_ID)
    out = task.generate(
        2026062501,
        params={
            "canvas_profile": "square",
            "movement_budget": 4,
            "attack_range": 2,
        },
        max_attempts=40,
    )
    assert out.scene_id == "rpg_tactical_map"
    assert out.query_id == "single"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value in {"A", "B", "C", "D"}
    assert out.annotation_gt.type == "bbox"
    width, height = out.image.size
    _assert_bbox_inside_canvas(out.annotation_gt.value, width=width, height=height)
    assert "attack" in out.prompt
    assert "horizontally or vertically" in out.prompt or "cardinal direction" in out.prompt or "up, down, left, or right" in out.prompt
    assert "ignores terrain cost" in out.prompt or "ignoring terrain cost" in out.prompt

    trace = out.trace_payload
    render_map = trace["render_map"]
    answer_label = str(out.answer_gt.value)
    assert render_map["selected_label"] == answer_label
    assert render_map["selected_tile_bbox_px"] == out.annotation_gt.value
    assert int(render_map["movement_budget"]) == 4
    assert int(render_map["attack_range"]) == 2
    assert trace["projected_annotation"]["type"] == "bbox"
    assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
    assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_rpg_tactical_map_v0"
    assert trace["query_spec"]["prompt_variant"]["prompt_scene_id"] == "rpg_tactical_map"

    attackable_labels = [
        label
        for label, is_attackable in render_map["candidate_attackable_by_label"].items()
        if bool(is_attackable)
    ]
    assert attackable_labels == [answer_label]
    assert sorted(render_map["candidate_start_manhattan_by_label"]) == ["A", "B", "C", "D"]
    assert render_map["minimum_candidate_start_manhattan"] == min(render_map["candidate_start_manhattan_by_label"].values())
    assert render_map["nearest_candidate_labels"]
    assert render_map["selected_start_manhattan"] == render_map["candidate_start_manhattan_by_label"][answer_label]
    assert trace["execution_trace"]["candidate_start_manhattan_by_label"] == render_map["candidate_start_manhattan_by_label"]
    tiles_by_id = {str(tile["tile_id"]): tile for tile in trace["scene_ir"]["tiles"]}
    selected_tile_id = str(render_map["selected_tile_id"])
    selected_tile = tiles_by_id[selected_tile_id]
    source_tile_ids = render_map["candidate_attack_source_tile_ids_by_label"][answer_label]
    assert source_tile_ids
    for source_tile_id in source_tile_ids:
        source_tile = tiles_by_id[str(source_tile_id)]
        same_row = int(source_tile["row"]) == int(selected_tile["row"])
        same_col = int(source_tile["col"]) == int(selected_tile["col"])
        distance = abs(int(source_tile["row"]) - int(selected_tile["row"])) + abs(int(source_tile["col"]) - int(selected_tile["col"]))
        assert same_row or same_col
        assert 1 <= distance <= int(render_map["attack_range"])
        assert str(source_tile_id) in set(render_map["reachable_move_tile_ids"])

    costs_by_tile_id = trace["execution_trace"]["movement_costs_by_tile_id"]
    for move_tile_id in render_map["reachable_move_tile_ids"]:
        assert int(costs_by_tile_id[str(move_tile_id)]) <= int(render_map["movement_budget"])


def test_rpg_tactical_map_attack_candidates_do_not_default_to_nearest_tile() -> None:
    task = create_task(ATTACK_TASK_ID)
    sample_count = 60
    unique_nearest_count = 0
    for seed_offset in range(sample_count):
        out = task.generate(
            202606260000 + seed_offset,
            params={},
            max_attempts=50,
        )
        render_map = out.trace_payload["render_map"]
        answer_label = str(out.answer_gt.value)
        distances = {
            str(label): int(distance)
            for label, distance in render_map["candidate_start_manhattan_by_label"].items()
        }
        assert sorted(distances) == ["A", "B", "C", "D"]
        assert render_map["candidate_attackable_by_label"][answer_label] is True
        assert [
            label
            for label, is_attackable in render_map["candidate_attackable_by_label"].items()
            if bool(is_attackable)
        ] == [answer_label]
        minimum_distance = min(distances.values())
        nearest_labels = sorted(label for label, distance in distances.items() if int(distance) == minimum_distance)
        assert render_map["nearest_candidate_labels"] == nearest_labels
        if nearest_labels == [answer_label]:
            unique_nearest_count += 1

    assert unique_nearest_count <= 12


def test_rpg_tactical_map_movement_cost_value_contract() -> None:
    task = create_task(COST_VALUE_TASK_ID)
    out = task.generate(
        2026062601,
        params={
            "canvas_profile": "square",
            "min_movement_cost": 3,
            "max_movement_cost": 10,
        },
        max_attempts=40,
    )
    assert out.scene_id == "rpg_tactical_map"
    assert out.query_id == "single"
    assert out.answer_gt.type == "integer"
    assert 3 <= int(out.answer_gt.value) <= 10
    assert out.annotation_gt.type == "bbox_map"
    assert set(out.annotation_gt.value) == {"player_cell", "target_cell"}
    width, height = out.image.size
    for bbox in out.annotation_gt.value.values():
        _assert_bbox_inside_canvas(bbox, width=width, height=height)
    assert "marked" in out.prompt
    assert "movement" in out.prompt
    assert "water cannot be entered" in out.prompt

    trace = out.trace_payload
    render_map = trace["render_map"]
    assert trace["projected_annotation"]["type"] == "bbox_map"
    assert trace["projected_annotation"]["bbox_map"] == out.annotation_gt.value
    assert render_map["target_tile_bbox_px"] == out.annotation_gt.value["target_cell"]
    assert int(render_map["answer_value"]) == int(out.answer_gt.value)
    assert int(render_map["target_shortest_movement_cost"]) == int(out.answer_gt.value)
    assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_rpg_tactical_map_v0"
    assert trace["query_spec"]["prompt_variant"]["prompt_scene_id"] == "rpg_tactical_map"

    tiles_by_id = {str(tile["tile_id"]): tile for tile in trace["scene_ir"]["tiles"]}
    target_tile_id = str(render_map["target_tile_id"])
    start_tile_id = str(render_map["start_tile_id"])
    assert target_tile_id != start_tile_id
    assert target_tile_id in tiles_by_id
    assert start_tile_id in tiles_by_id
    assert out.annotation_gt.value["player_cell"] == tiles_by_id[start_tile_id]["bbox"]
    assert out.annotation_gt.value["target_cell"] == tiles_by_id[target_tile_id]["bbox"]
    assert trace["execution_trace"]["annotation_tile_id_map"] == {
        "player_cell": start_tile_id,
        "target_cell": target_tile_id,
    }
    assert trace["scene_ir"]["relations"]["annotation_tile_id_map"] == {
        "player_cell": start_tile_id,
        "target_cell": target_tile_id,
    }
    path_tile_ids = [str(tile_id) for tile_id in render_map["shortest_path_tile_ids"]]
    assert path_tile_ids[0] == start_tile_id
    assert path_tile_ids[-1] == target_tile_id
    assert trace["execution_trace"]["shortest_path_tile_ids"] == path_tile_ids
    assert len(path_tile_ids) == len(render_map["shortest_path_tile_bboxes_px"])
    for left_id, right_id in zip(path_tile_ids, path_tile_ids[1:]):
        left = tiles_by_id[left_id]
        right = tiles_by_id[right_id]
        step = abs(int(left["row"]) - int(right["row"])) + abs(int(left["col"]) - int(right["col"]))
        assert step == 1
    assert render_map["shortest_path_entry_costs"][0] == 0
    assert sum(int(cost) for cost in render_map["shortest_path_entry_costs"]) == int(out.answer_gt.value)
    assert trace["scene_ir"]["relations"]["target_tile_id"] == target_tile_id
    assert trace["execution_trace"]["target_tile_id"] == target_tile_id
    assert trace["execution_trace"]["movement_costs_by_tile_id"][target_tile_id] == int(out.answer_gt.value)

    target_tile = tiles_by_id[target_tile_id]
    start_tile = tiles_by_id[start_tile_id]
    manhattan = abs(int(target_tile["row"]) - int(start_tile["row"])) + abs(int(target_tile["col"]) - int(start_tile["col"]))
    assert render_map["target_manhattan_distance"] == manhattan
    assert int(out.answer_gt.value) >= manhattan
