from __future__ import annotations

from trace.tasks.registry import create_task
from trace.tasks.illustrations.rpg_house.reachable_room_label import TASK_ID
from trace.tasks.illustrations.rpg_house.shared.rendering import (
    ROOM_IDS,
    draw_rpg_house_debug_overlay,
    reachable_room_ids,
    render_rpg_house_scene,
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= float(width)
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= float(height)


def test_rpg_house_renderer_is_deterministic_and_profile_safe() -> None:
    labels = {"kitchen": "A", "storage": "B", "study": "C", "parlor": "D"}
    door_states = {
        "bedroom_hall": "open",
        "kitchen_hall": "open",
        "storage_hall": "closed",
        "study_hall": "closed",
        "parlor_hall": "closed",
    }
    for width, height in ((1200, 800), (960, 960), (800, 1200)):
        first = render_rpg_house_scene(
            12345,
            width=width,
            height=height,
            start_room_id="bedroom",
            room_labels=labels,
            door_states=door_states,
        )
        second = render_rpg_house_scene(
            12345,
            width=width,
            height=height,
            start_room_id="bedroom",
            room_labels=labels,
            door_states=door_states,
        )
        assert first.image.size == (width, height)
        assert list(first.image.getdata()) == list(second.image.getdata())
        assert draw_rpg_house_debug_overlay(first).size == first.image.size
        assert {room.room_id for room in first.rooms} == set(ROOM_IDS) | {"hall"}
        assert len(first.doors) == len(ROOM_IDS)
        assert len(first.entities) >= 8
        for room in first.rooms:
            _assert_bbox_inside_canvas(list(room.bbox_xyxy), width=width, height=height)
        for door in first.doors:
            _assert_bbox_inside_canvas(list(door.bbox_xyxy), width=width, height=height)
        for entity in first.entities:
            _assert_bbox_inside_canvas(list(entity.bbox_xyxy), width=width, height=height)


def test_rpg_house_reachable_room_label_contract() -> None:
    task = create_task(TASK_ID)
    out = task.generate(
        2026061601,
        params={
            "canvas_profile": "landscape",
            "start_room_id": "bedroom",
            "answer_room_id": "kitchen",
        },
        max_attempts=20,
    )
    assert out.scene_id == "rpg_house"
    assert out.query_id == "single"
    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == "A"
    assert out.annotation_gt.type == "bbox"
    width, height = out.image.size
    _assert_bbox_inside_canvas(out.annotation_gt.value, width=width, height=height)
    trace = out.trace_payload
    assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_rpg_house_v0"
    assert trace["query_spec"]["prompt_variant"]["prompt_scene_id"] == "rpg_house"
    assert trace["projected_annotation"]["type"] == "bbox"
    assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
    render_map = trace["render_map"]
    assert render_map["answer_room_id"] == "kitchen"
    assert render_map["answer_room_bbox_px"] == out.annotation_gt.value
    assert set(render_map["candidate_room_ids"]) == {"kitchen", "storage", "study", "parlor"}
    rooms = {room["room_id"]: room for room in trace["scene_ir"]["rooms"]}
    assert rooms["kitchen"]["label"] == "A"
    assert rooms["bedroom"]["label"] is None
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
        start_room_id="bedroom",
    )
    reachable_candidates = [room_id for room_id in render_map["candidate_room_ids"] if room_id in set(reachable)]
    assert reachable_candidates == ["kitchen"]


def test_rpg_house_reachable_room_support_is_sampled() -> None:
    seen_starts: set[str] = set()
    seen_answers: set[str] = set()
    task = create_task(TASK_ID)
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
