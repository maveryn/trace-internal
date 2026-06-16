from __future__ import annotations

from trace.tasks.registry import create_task
from trace.tasks.illustrations.rpg_house.reachable_room_label import TASK_ID as REACHABLE_TASK_ID
from trace.tasks.illustrations.rpg_house.room_count import TASK_ID as ROOM_COUNT_TASK_ID
from trace.tasks.illustrations.rpg_house.shared.rendering import (
    MAX_ROOM_COUNT,
    MIN_ROOM_COUNT,
    draw_rpg_house_debug_overlay,
    reachable_room_ids,
    render_rpg_house_scene,
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= float(width)
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= float(height)


def test_rpg_house_renderer_is_deterministic_and_profile_safe() -> None:
    for width, height in ((1200, 800), (960, 960), (800, 1200)):
        first = render_rpg_house_scene(
            12345,
            width=width,
            height=height,
            room_count=6,
        )
        second = render_rpg_house_scene(
            12345,
            width=width,
            height=height,
            room_count=6,
        )
        assert first.image.size == (width, height)
        assert list(first.image.getdata()) == list(second.image.getdata())
        assert draw_rpg_house_debug_overlay(first).size == first.image.size
        assert len(first.rooms) == 6
        assert MIN_ROOM_COUNT <= len(first.rooms) <= MAX_ROOM_COUNT
        assert len(first.doors) >= len(first.rooms) - 1
        assert len(first.entities) >= len(first.rooms)
        for room in first.rooms:
            _assert_bbox_inside_canvas(list(room.bbox_xyxy), width=width, height=height)
        wide_door_seen = False
        for door in first.doors:
            _assert_bbox_inside_canvas(list(door.bbox_xyxy), width=width, height=height)
            door_width = float(door.bbox_xyxy[2]) - float(door.bbox_xyxy[0])
            door_height = float(door.bbox_xyxy[3]) - float(door.bbox_xyxy[1])
            assert min(door_width, door_height) >= first.trace["tile_px"] * 0.25
            assert max(door_width, door_height) >= first.trace["tile_px"] * 0.70
            if int(door.metadata.get("span_tiles", 1)) >= 2:
                wide_door_seen = True
                assert max(door_width, door_height) >= first.trace["tile_px"] * 1.70
        assert wide_door_seen
        for entity in first.entities:
            _assert_bbox_inside_canvas(list(entity.bbox_xyxy), width=width, height=height)


def test_rpg_house_renderer_samples_room_count_range() -> None:
    seen_counts = set()
    for seed in range(30):
        scene = render_rpg_house_scene(5000 + seed, width=960, height=720)
        seen_counts.add(len(scene.rooms))
        assert MIN_ROOM_COUNT <= len(scene.rooms) <= MAX_ROOM_COUNT
    assert seen_counts == set(range(MIN_ROOM_COUNT, MAX_ROOM_COUNT + 1))


def test_rpg_house_reachable_room_label_contract() -> None:
    task = create_task(REACHABLE_TASK_ID)
    out = task.generate(
        2026061601,
        params={
            "canvas_profile": "landscape",
        },
        max_attempts=20,
    )
    assert out.scene_id == "rpg_house"
    assert out.query_id == "single"
    assert out.answer_gt.type == "string"
    assert out.answer_gt.value in {"A", "B", "C", "D"}
    assert out.annotation_gt.type == "bbox"
    width, height = out.image.size
    _assert_bbox_inside_canvas(out.annotation_gt.value, width=width, height=height)
    trace = out.trace_payload
    assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_rpg_house_v0"
    assert trace["query_spec"]["prompt_variant"]["prompt_scene_id"] == "rpg_house"
    assert trace["projected_annotation"]["type"] == "bbox"
    assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
    render_map = trace["render_map"]
    assert render_map["answer_room_id"] == trace["query_spec"]["params"]["answer_room_id"]
    assert render_map["answer_room_bbox_px"] == out.annotation_gt.value
    assert len(render_map["candidate_room_ids"]) == 4
    rooms = {room["room_id"]: room for room in trace["scene_ir"]["rooms"]}
    assert rooms[render_map["answer_room_id"]]["label"] == out.answer_gt.value
    assert rooms[render_map["start_room_id"]]["label"] is None
    doors = trace["scene_ir"]["doors"]
    reachable = reachable_room_ids(
        tuple(
            type(
                "Door",
                (),
                {
                    "room_a_id": door["room_a_id"],
                    "room_b_id": door["room_b_id"],
                    "door_id": door["door_id"],
                    "state": door["state"],
                },
            )()
            for door in doors
        ),
        start_room_id=render_map["start_room_id"],
    )
    reachable_candidates = [room_id for room_id in render_map["candidate_room_ids"] if room_id in set(reachable)]
    assert reachable_candidates == [render_map["answer_room_id"]]


def test_rpg_house_room_count_contract() -> None:
    task = create_task(ROOM_COUNT_TASK_ID)
    out = task.generate(
        2026061603,
        params={
            "canvas_profile": "square",
            "room_count": 7,
        },
        max_attempts=20,
    )
    assert out.scene_id == "rpg_house"
    assert out.query_id == "single"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 7
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == 7
    width, height = out.image.size
    for point in out.annotation_gt.value:
        assert 0 <= float(point[0]) <= float(width)
        assert 0 <= float(point[1]) <= float(height)
    trace = out.trace_payload
    assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_rpg_house_v0"
    assert trace["query_spec"]["prompt_variant"]["prompt_scene_id"] == "rpg_house"
    assert trace["projected_annotation"]["type"] == "point_set"
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["render_map"]["counted_room_count"] == 7
    assert len(trace["render_map"]["counted_room_ids"]) == 7


def test_rpg_house_reachable_room_support_is_sampled() -> None:
    seen_starts: set[str] = set()
    seen_answers: set[str] = set()
    task = create_task(REACHABLE_TASK_ID)
    for seed in range(20):
        out = task.generate(1000 + seed, params={"canvas_profile": "square"}, max_attempts=20)
        params = out.trace_payload["query_spec"]["params"]
        seen_starts.add(params["start_room_id"])
        seen_answers.add(params["answer_room_id"])
        assert params["answer_room_id"] in params["candidate_room_ids"]
        assert params["start_room_id"] not in params["candidate_room_ids"]
        assert params["reachable_candidate_room_ids"] == [params["answer_room_id"]]
    assert len(seen_starts) >= 4
    assert len(seen_answers) >= 4
