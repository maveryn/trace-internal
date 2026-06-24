from __future__ import annotations

from trace.tasks.registry import create_task
from trace.tasks.illustrations.rpg_tactical_map.movement_reachable_tile_label import TASK_ID
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
    task = create_task(TASK_ID)
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


def test_rpg_tactical_map_movement_distractors_stay_near_answer() -> None:
    task = create_task(TASK_ID)
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
            answer_tile = tiles_by_id[str(render_map["candidate_tile_ids_by_label"][answer_label])]

            reachable_labels = [
                label
                for label, cost in render_map["candidate_shortest_costs_by_label"].items()
                if cost is not None and int(cost) <= int(render_map["movement_budget"])
            ]
            assert reachable_labels == [answer_label]

            distractor_distances = []
            for label, tile_id in render_map["candidate_tile_ids_by_label"].items():
                if str(label) == answer_label:
                    continue
                tile = tiles_by_id[str(tile_id)]
                distractor_distances.append(
                    abs(int(tile["row"]) - int(answer_tile["row"]))
                    + abs(int(tile["col"]) - int(answer_tile["col"]))
                )
            assert max(distractor_distances) <= 4
