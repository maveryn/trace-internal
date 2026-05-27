"""Tests for the 3D room wall-object camera-distance task."""

from __future__ import annotations

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.room.wall_object_camera_distance import (
    LETTERED_WALL_OBJECT_MIN_VISIBLE_PX,
    SCENE_ID,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
)


def test_room_wall_object_camera_distance_answer_and_evidence() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20261003,
        params={
            "query_id": "closest_to_camera",
            "scene_variant": "studio_room",
            "candidate_count": 6,
            "context_wall_count": 4,
            "floor_context_count": 6,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=160,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    candidates = list(trace["candidate_object_specs"])
    nearest = min(candidates, key=lambda spec: (float(spec["camera_distance"]), str(spec["point_label"])))
    expected_bbox = render_map["object_bboxes_px"][str(nearest["object_id"])]

    assert output.query_id == "default"
    assert output.scene_id == SCENE_ID
    assert output.query_id == "closest_to_camera"
    assert output.answer_gt.type == "option_letter"
    assert output.answer_gt.value == str(nearest["point_label"])
    assert output.evidence_gt.type == "bbox_set"
    assert output.evidence_gt.value == [expected_bbox]
    assert trace["answer_label"] == str(nearest["point_label"])
    assert trace["answer_object_id"] == str(nearest["object_id"])
    assert trace["target_object_ids"] == [str(nearest["object_id"])]
    assert trace["camera_distance_order_near_to_far"][0] == str(nearest["point_label"])
    assert len(candidates) == 6
    assert sorted(str(spec["point_label"]) for spec in candidates) == list("ABCDEF")
    assert {str(spec["wall"]) for spec in candidates} == {"back", "left", "right"}
    assert all(bool(spec["is_wall_mounted"]) for spec in candidates)
    assert all(bool(spec["is_answer_candidate"]) for spec in candidates)
    assert abs(float(trace["camera"]["yaw_degrees"])) <= 8.0
    for bbox in trace["candidate_visible_bboxes_by_label"].values():
        width = float(bbox[2]) - float(bbox[0])
        height = float(bbox[3]) - float(bbox[1])
        assert width >= LETTERED_WALL_OBJECT_MIN_VISIBLE_PX
        assert height >= LETTERED_WALL_OBJECT_MIN_VISIBLE_PX
    assert float(trace["camera_distance_margin"]) > 0.0
    assert any(entity["entity_id"] == "room_shell" for entity in output.trace_payload["scene_ir"]["entities"])
    assert output.image.size == (1180, 900)


def test_room_wall_object_camera_distance_registered() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == SCENE_ID
    assert taxonomy.source_task_group == "room"
    assert SUPPORTED_QUERY_IDS == ("closest_to_camera",)
