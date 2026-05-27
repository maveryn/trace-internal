"""Tests for the 3D room wall-object wall-side relation task."""

from __future__ import annotations

import pytest

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.room.wall_object_camera_distance import (
    LETTERED_WALL_OBJECT_MIN_VISIBLE_PX,
)
from trace.tasks.three_d.room.wall_object_side_relation import (
    REFERENCE_OBJECT_TYPE,
    SCENE_ID,
    SUPPORTED_QUERY_VARIANTS,
    TASK_ID,
)


@pytest.mark.parametrize(
    ("query_variant", "relation_key"),
    [
        ("left_of_reference_on_wall", "left_of_reference_on_wall_by_label"),
        ("right_of_reference_on_wall", "right_of_reference_on_wall_by_label"),
    ],
)
@pytest.mark.parametrize("reference_wall", ["back", "left", "right"])
def test_room_wall_object_side_relation_answer_evidence_and_unique_reference(
    reference_wall: str,
    query_variant: str,
    relation_key: str,
) -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260522,
        params={
            "query_variant": query_variant,
            "scene_variant": "studio_room",
            "candidate_count": 5,
            "context_wall_count": 4,
            "floor_context_count": 6,
            "reference_wall": reference_wall,
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
    selected_relation_labels = [
        label
        for label, is_selected in trace[relation_key].items()
        if bool(is_selected)
    ]
    generic_relation_labels = [
        label
        for label, is_selected in trace["selected_side_relation_by_label"].items()
        if bool(is_selected)
    ]
    reference_left_coord = float(reference["wall_left_coordinate"])
    candidate_left_coords = {
        str(label): float(value)
        for label, value in trace[
            "candidate_wall_left_coordinates_by_label"
        ].items()
    }

    assert output.query_variant == "default"
    assert output.scene_id == SCENE_ID
    assert output.query_id == query_variant
    assert output.answer_gt.type == "option_letter"
    assert output.answer_gt.value == answer_label
    assert output.evidence_gt.type == "bbox_set"
    assert output.evidence_gt.value == [expected_bbox]
    assert trace["target_object_ids"] == [str(answer_spec["object_id"])]
    assert selected_relation_labels == [answer_label]
    assert generic_relation_labels == [answer_label]
    assert str(reference["wall"]) == reference_wall
    assert str(reference["object_type"]) == REFERENCE_OBJECT_TYPE
    assert str(reference["prompt_name"]) == "TV"
    assert int(reference["prompt_name_count"]) == 1
    assert str(reference["object_id"]) not in trace["target_object_ids"]
    assert str(reference["object_type"]) not in {
        str(spec["object_type"]) for spec in candidates
    }
    assert str(answer_spec["wall"]) == reference_wall
    assert all(bool(spec["is_wall_mounted"]) for spec in candidates)
    assert all(bool(spec["is_answer_candidate"]) for spec in candidates)
    assert sorted(str(spec["point_label"]) for spec in candidates) == list("ABCDE")
    assert {str(spec["wall"]) for spec in candidates} == {reference_wall}
    assert len(candidates) == 5
    assert trace["candidate_walls_by_label"][answer_label] == reference_wall
    if query_variant == "left_of_reference_on_wall":
        assert candidate_left_coords[answer_label] > reference_left_coord
        for label, coord in candidate_left_coords.items():
            if label != answer_label:
                assert coord <= reference_left_coord
    else:
        assert candidate_left_coords[answer_label] < reference_left_coord
        for label, coord in candidate_left_coords.items():
            if label != answer_label:
                assert coord >= reference_left_coord
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


def test_room_wall_object_side_relation_registered() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == SCENE_ID
    assert taxonomy.source_task_group == "room"
    assert SUPPORTED_QUERY_VARIANTS == (
        "left_of_reference_on_wall",
        "right_of_reference_on_wall",
    )
