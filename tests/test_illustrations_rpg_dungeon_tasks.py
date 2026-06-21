from __future__ import annotations

from trace.tasks.registry import create_task
from trace.tasks.illustrations.rpg_dungeon.reachable_chest_count import TASK_ID
from trace.tasks.illustrations.rpg_dungeon.shared.relations import reachable_tiles
from trace.tasks.illustrations.rpg_dungeon.shared.rendering import (
    MAX_REACHABLE_CHEST_COUNT,
    MAX_TOTAL_CHEST_COUNT,
    MIN_REACHABLE_CHEST_COUNT,
    MIN_TOTAL_CHEST_COUNT,
    draw_rpg_dungeon_debug_overlay,
    render_rpg_dungeon_scene,
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= float(width)
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= float(height)


def test_rpg_dungeon_renderer_is_deterministic_and_profile_safe() -> None:
    for width, height, total_count in ((1296, 864, 6), (1008, 1008, 5), (864, 1296, 4)):
        first = render_rpg_dungeon_scene(
            2026062001,
            width=width,
            height=height,
            total_chest_count=total_count,
            reachable_chest_count=3,
        )
        second = render_rpg_dungeon_scene(
            2026062001,
            width=width,
            height=height,
            total_chest_count=total_count,
            reachable_chest_count=3,
        )
        assert first.image.size == (width, height)
        assert first.image.tobytes() == second.image.tobytes()
        assert draw_rpg_dungeon_debug_overlay(first).size == first.image.size
        assert len(first.chest_entity_ids) == total_count
        assert first.trace["total_chest_count"] == total_count
        assert len(first.reachable_chest_ids) == 3
        assert first.trace["layout_orientation"] in {"top_bottom", "left_right"}
        assert sorted(first.trace["side_counts"].values()) in ([2, 2], [2, 3], [3, 3])
        assert sum(first.trace["side_counts"].values()) == total_count
        assert first.player_entity_id == "player_00"
        assert len(first.floor_tiles) > 0
        assert len(first.corridor_tiles) > 0
        assert len(first.blocked_tiles) == len(first.blockers)
        assert len(first.blocked_tiles) == len(set(first.blocked_tiles))
        assert sum(1 for edge_id in first.trace["edge_ids"] if str(edge_id).startswith("edge_start_")) == total_count
        assert any(not str(edge_id).startswith("edge_start_") for edge_id in first.trace["edge_ids"])
        assert set(first.trace["blocked_edge_ids"]) == {
            str(blocker.metadata["edge_id"])
            for blocker in first.blockers
        }
        for chamber in first.chambers:
            _assert_bbox_inside_canvas(list(chamber.bbox_xyxy), width=width, height=height)
        for blocker in first.blockers:
            _assert_bbox_inside_canvas(list(blocker.bbox_xyxy), width=width, height=height)
            assert blocker.blocker_type == "boulder"
            assert blocker.metadata["passable"] is False
        for entity in first.entities:
            _assert_bbox_inside_canvas(list(entity.bbox_xyxy), width=width, height=height)
            assert entity.object_type in {"chest", "person"}


def test_rpg_dungeon_renderer_samples_reachable_count_range() -> None:
    seen_counts = set()
    seen_totals = set()
    seen_orientations = set()
    for seed in range(120):
        scene = render_rpg_dungeon_scene(7000 + seed, width=1296, height=864)
        total = len(scene.chest_entity_ids)
        seen_counts.add(len(scene.reachable_chest_ids))
        seen_totals.add(total)
        seen_orientations.add(str(scene.trace["layout_orientation"]))
        assert MIN_TOTAL_CHEST_COUNT <= total <= MAX_TOTAL_CHEST_COUNT
        assert MIN_REACHABLE_CHEST_COUNT <= len(scene.reachable_chest_ids) <= MAX_REACHABLE_CHEST_COUNT
        assert len(scene.reachable_chest_ids) <= total
    assert seen_counts == set(range(MIN_REACHABLE_CHEST_COUNT, MAX_REACHABLE_CHEST_COUNT + 1))
    assert seen_totals == set(range(MIN_TOTAL_CHEST_COUNT, MAX_TOTAL_CHEST_COUNT + 1))
    assert {"top_bottom", "left_right"}.issubset(seen_orientations)


def test_rpg_dungeon_reachable_chest_count_contract() -> None:
    task = create_task(TASK_ID)
    for profile, total_count, count, seed in (
        ("landscape", 4, 0, 2026062011),
        ("square", 5, 2, 2026062012),
        ("portrait", 6, 6, 2026062013),
    ):
        out = task.generate(
            seed,
            params={
                "canvas_profile": profile,
                "total_chest_count": total_count,
                "reachable_chest_count": count,
            },
            max_attempts=20,
        )
        assert out.scene_id == "rpg_dungeon"
        assert out.query_id == "single"
        assert out.answer_gt.type == "integer"
        assert out.answer_gt.value == count
        assert out.annotation_gt.type == "point_set_map"
        assert sorted(out.annotation_gt.value) == ["player", "reachable_chests"]
        assert len(out.annotation_gt.value["player"]) == 1
        assert len(out.annotation_gt.value["reachable_chests"]) == count
        assert "red-outlined" not in out.prompt
        assert "lettered candidate" not in out.prompt
        width, height = out.image.size
        for points in out.annotation_gt.value.values():
            for point in points:
                assert 0 <= float(point[0]) <= float(width)
                assert 0 <= float(point[1]) <= float(height)

        trace = out.trace_payload
        assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_rpg_dungeon_v0"
        assert trace["query_spec"]["prompt_variant"]["prompt_scene_id"] == "rpg_dungeon"
        assert trace["projected_annotation"]["type"] == "point_set_map"
        assert trace["projected_annotation"]["point_set_map"] == out.annotation_gt.value
        assert trace["render_map"]["reachable_count"] == count
        assert trace["render_map"]["total_chest_count"] == total_count
        assert len(trace["render_map"]["chest_entity_ids"]) == total_count
        assert trace["query_spec"]["params"]["total_chest_count"] == total_count

        scene_ir = trace["scene_ir"]
        reached = reachable_tiles(
            (tuple(tile) for tile in scene_ir["floor_tiles"]),
            blocked_tiles=(tuple(tile) for tile in scene_ir["blocked_tiles"]),
            start_tile=tuple(trace["execution_trace"]["renderer"]["player_tile"]),
        )
        reachable_tile_set = set(reached)
        chest_tile_map = {
            str(entity_id): tuple(tile)
            for entity_id, tile in trace["execution_trace"]["renderer"]["chest_tile_map"].items()
        }
        expected_ids = sorted(
            entity_id
            for entity_id, tile in chest_tile_map.items()
            if tuple(tile) in reachable_tile_set
        )
        assert expected_ids == sorted(trace["render_map"]["reachable_chest_ids"])
        assert expected_ids == sorted(trace["scene_ir"]["relations"]["reachable_chest_ids"])
