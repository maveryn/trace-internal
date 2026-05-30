"""Tests for the 3D room wall-object same-wall reference task."""

from __future__ import annotations

import pytest

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.room.wall_object_camera_distance import (
    LETTERED_WALL_OBJECT_MIN_VISIBLE_PX,
)
from trace.tasks.three_d.room.wall_object_same_wall_reference import (
    SCENE_ID,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
)


@pytest.mark.parametrize("reference_wall", ["back", "left", "right"])
def test_room_wall_object_same_wall_reference_answer_evidence_and_unique_reference(
    reference_wall: str,
) -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260522,
        params={
            "query_id": "same_wall_as_reference",
            "scene_variant": "studio_room",
            "candidate_count": 6,
            "context_wall_count": 4,
            "floor_context_count": 6,
            "reference_wall": reference_wall,
            "reference_object_type": "mirror",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=180,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    candidates = list(trace["candidate_object_specs"])
    reference = dict(trace["reference_object"])
    answer_label = str(trace["answer_label"])
    answer_spec = next(
        spec for spec in candidates if str(spec["point_label"]) == answer_label
    )
    expected_bbox = render_map["object_bboxes_px"][str(answer_spec["object_id"])]
    same_wall_labels = [
        label
        for label, is_same_wall in trace["same_wall_as_reference_by_label"].items()
        if bool(is_same_wall)
    ]
    assert output.scene_id == SCENE_ID
    assert output.query_id == "same_wall_as_reference"
    assert output.answer_gt.type == "option_letter"
    assert output.answer_gt.value == answer_label
    assert output.evidence_gt.type == "bbox_set"
    assert output.evidence_gt.value == [expected_bbox]
    assert trace["target_object_ids"] == [str(answer_spec["object_id"])]
    assert same_wall_labels == [answer_label]
    assert str(reference["wall"]) == reference_wall
    assert int(reference["prompt_name_count"]) == 1
    assert str(reference["object_id"]) not in trace["target_object_ids"]
    assert str(reference["object_type"]) not in {
        str(spec["object_type"]) for spec in candidates
    }
    assert str(answer_spec["wall"]) == reference_wall
    assert all(bool(spec["is_wall_mounted"]) for spec in candidates)
    assert all(bool(spec["is_answer_candidate"]) for spec in candidates)
    assert sorted(str(spec["point_label"]) for spec in candidates) == list("ABCDEF")
    assert {str(spec["wall"]) for spec in candidates} == {"back", "left", "right"}
    assert sum(1 for spec in candidates if str(spec["wall"]) == reference_wall) == 1
    assert trace["candidate_walls_by_label"][answer_label] == reference_wall
    for bbox in trace["candidate_visible_bboxes_by_label"].values():
        width = float(bbox[2]) - float(bbox[0])
        height = float(bbox[3]) - float(bbox[1])
        assert width >= LETTERED_WALL_OBJECT_MIN_VISIBLE_PX
        assert height >= LETTERED_WALL_OBJECT_MIN_VISIBLE_PX
    assert (
        render_map["reference_object_bbox_px"]
        == render_map["object_bboxes_px"][str(reference["object_id"])]
    )
    assert output.image.size == (1180, 900)


def test_room_wall_object_same_wall_reference_registered() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == SCENE_ID
    assert taxonomy.source_task_group == "room"
    assert SUPPORTED_QUERY_IDS == ("same_wall_as_reference",)
