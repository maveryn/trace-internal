"""Tests for the 3D warehouse robot nearest-reference task."""

from __future__ import annotations

import pytest

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.warehouse.robot_forward_path import SCENE_ID, SUPPORTED_ROBOT_DESIGNS
from trace.tasks.three_d.warehouse.robot_nearest_object import (
    MIN_NEAREST_OBJECT_MARGIN,
    MIN_NEAREST_ROBOT_MARGIN,
    SUPPORTED_AISLE_HEADINGS,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
)


@pytest.mark.parametrize(
    ("scene_variant", "aisle_heading"),
    [
        ("storage_aisle", "east"),
        ("loading_zone", "north"),
        ("packing_floor", "west"),
    ],
)
def test_warehouse_robot_nearest_object_answer_evidence_and_geometry(
    scene_variant: str,
    aisle_heading: str,
) -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260524,
        params={
            "query_id": "closest_robot_to_reference",
            "scene_variant": scene_variant,
            "aisle_heading": aisle_heading,
            "candidate_count": 5,
            "context_object_count": 10,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=600,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    entities = output.trace_payload["scene_ir"]["entities"]
    candidates = list(trace["candidate_robot_specs"])
    reference = dict(trace["reference_object"])
    answer_label = str(trace["answer_label"])
    answer_spec = next(spec for spec in candidates if str(spec["point_label"]) == answer_label)
    expected_bbox = render_map["object_bboxes_px"][str(answer_spec["object_id"])]
    nearest_labels = [
        str(label)
        for label, flag in trace["nearest_robot_by_label"].items()
        if bool(flag)
    ]

    assert output.query_id == "default"
    assert output.scene_id == SCENE_ID
    assert output.query_id == "closest_robot_to_reference"
    assert output.answer_gt.type == "option_letter"
    assert output.answer_gt.value == answer_label
    assert output.evidence_gt.type == "bbox_set"
    assert output.evidence_gt.value == [expected_bbox]
    assert trace["target_object_ids"] == [str(answer_spec["object_id"])]
    assert nearest_labels == [answer_label]
    assert trace["nearest_robot_candidate_labels"] == [answer_label]
    assert trace["distance_order_near_to_far"][0] == answer_label
    assert float(trace["nearest_robot_margin"]) >= MIN_NEAREST_ROBOT_MARGIN
    assert bool(answer_spec["is_nearest_robot_to_reference"]) is True
    assert str(reference["object_type"]) == "red_sphere"
    assert str(reference["object_role"]) == "warehouse_reference_object"
    assert str(trace["reference_object_name"]) == "red sphere"
    assert str(trace["aisle_heading"]) == str(aisle_heading)
    assert sorted(str(spec["point_label"]) for spec in candidates) == list("ABCDE")
    assert len(candidates) == 5
    assert len(trace["context_object_specs"]) == 10
    assert len(trace["reference_object_specs"]) == 1
    assert len(trace["candidate_specs"]) == 5
    assert all(str(spec["object_type"]) == "warehouse_robot" for spec in candidates)
    assert all(str(spec["object_role"]) == "warehouse_robot_candidate" for spec in candidates)
    assert all(str(spec["robot_design"]) in SUPPORTED_ROBOT_DESIGNS for spec in candidates)
    assert all(str(spec["robot_heading"]) in SUPPORTED_AISLE_HEADINGS for spec in candidates)
    assert all(len(spec["robot_base_rgb"]) == 3 for spec in candidates)
    assert all(len(spec["robot_accent_rgb"]) == 3 for spec in candidates)
    assert all(len(spec["gripper_tip_xyz"]) == 3 for spec in candidates)
    robot_entities = [
        entity
        for entity in entities
        if str(entity["entity_type"]) == "three_d_warehouse_robot_candidate"
    ]
    reference_entities = [
        entity
        for entity in entities
        if str(entity["entity_type"]) == "three_d_warehouse_reference_object"
    ]
    assert len(robot_entities) == 5
    assert len(reference_entities) == 1
    assert output.image.size == (1180, 920)
    assert "red sphere" in output.prompt
    assert "gripper" not in output.prompt
    assert "lettered robot" in output.prompt or "robot letter" in output.prompt
    assert "{answer_hint}" not in output.prompt


@pytest.mark.parametrize(
    ("scene_variant", "aisle_heading"),
    [
        ("storage_aisle", "south"),
        ("loading_zone", "east"),
        ("packing_floor", "north"),
    ],
)
def test_warehouse_object_nearest_robot_answer_evidence_and_geometry(
    scene_variant: str,
    aisle_heading: str,
) -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260525,
        params={
            "query_id": "closest_object_to_robot",
            "scene_variant": scene_variant,
            "aisle_heading": aisle_heading,
            "candidate_count": 5,
            "context_object_count": 10,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=700,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    entities = output.trace_payload["scene_ir"]["entities"]
    candidates = list(trace["candidate_object_specs"])
    references = list(trace["reference_robot_specs"])
    answer_label = str(trace["answer_label"])
    answer_spec = next(spec for spec in candidates if str(spec["point_label"]) == answer_label)
    expected_bbox = render_map["object_bboxes_px"][str(answer_spec["object_id"])]
    nearest_labels = [
        str(label)
        for label, flag in trace["nearest_object_by_label"].items()
        if bool(flag)
    ]

    assert output.query_id == "default"
    assert output.scene_id == SCENE_ID
    assert output.query_id == "closest_object_to_robot"
    assert output.answer_gt.type == "option_letter"
    assert output.answer_gt.value == answer_label
    assert output.evidence_gt.type == "bbox_set"
    assert output.evidence_gt.value == [expected_bbox]
    assert trace["target_object_ids"] == [str(answer_spec["object_id"])]
    assert nearest_labels == [answer_label]
    assert trace["nearest_object_candidate_labels"] == [answer_label]
    assert trace["distance_order_near_to_far"][0] == answer_label
    assert float(trace["nearest_object_margin"]) >= MIN_NEAREST_OBJECT_MARGIN
    assert bool(answer_spec["is_nearest_object_to_reference_robot"]) is True
    assert len(references) == 1
    assert str(references[0]["object_type"]) == "warehouse_robot"
    assert str(references[0]["object_role"]) == "warehouse_reference_robot"
    assert len(candidates) == 5
    assert sorted(str(spec["point_label"]) for spec in candidates) == list("ABCDE")
    assert all(str(spec["object_type"]) != "warehouse_robot" for spec in candidates)
    assert all(str(spec["object_role"]) == "warehouse_object_candidate" for spec in candidates)
    assert len(trace["candidate_robot_specs"]) == 0
    assert len(trace["context_object_specs"]) == 10
    assert len([spec for spec in trace["context_object_specs"] if str(spec["object_type"]) == "shelf_rack"]) == 4
    candidate_entities = [
        entity
        for entity in entities
        if str(entity["entity_type"]) == "three_d_warehouse_candidate_object"
    ]
    reference_entities = [
        entity
        for entity in entities
        if str(entity["entity_type"]) == "three_d_warehouse_reference_robot"
    ]
    assert len(candidate_entities) == 5
    assert len(reference_entities) == 1
    assert output.image.size == (1180, 920)
    assert "robot" in output.prompt
    assert "lettered warehouse object" in output.prompt or "object letter" in output.prompt
    assert "gripper" not in output.prompt
    assert "red sphere" not in output.prompt
    assert "{answer_hint}" not in output.prompt


def test_warehouse_robot_nearest_object_registered() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == SCENE_ID
    assert taxonomy.source_task_group == "warehouse"
    assert SUPPORTED_QUERY_IDS == ("closest_robot_to_reference", "closest_object_to_robot")
    assert SUPPORTED_AISLE_HEADINGS == ("east", "north", "west", "south")
