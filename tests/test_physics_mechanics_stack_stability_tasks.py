"""Contract tests for physics mechanics stack-stability tasks."""

from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.tasks.physics.mechanics.stack_stability import PhysicsMechanicsStackStabilityStatusLabelTask


def _assert_keyed_bbox_map_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "keyed_bbox_map"
    for bbox in out.annotation_gt.value.values():
        assert 0 <= bbox[0] < bbox[2] <= width
        assert 0 <= bbox[1] < bbox[3] <= height


def _assert_selected_geometry_matches_status(out, *, expected_status: str) -> None:
    render_map = out.trace_payload["render_map"]
    label = str(out.answer_gt.value)
    com_x = float(render_map["candidate_com_points_px"][label][0])
    support_bbox = render_map["candidate_support_bboxes_px"][label]
    support_left = float(support_bbox[0])
    support_right = float(support_bbox[2])

    assert render_map["candidate_statuses"][label] == expected_status
    if expected_status == "stable":
        assert support_left < com_x < support_right
    else:
        assert com_x < support_left or com_x > support_right


def test_stack_stability_stable_label_contract() -> None:
    out = PhysicsMechanicsStackStabilityStatusLabelTask().generate(
        94111,
        params={"query_id": "stable_stack_label", "correct_option_letter": "D"},
        max_attempts=10,
    )
    statuses = out.trace_payload["render_map"]["candidate_statuses"]

    assert out.scene_id == "stack_stability"
    assert out.query_id == "stable_stack_label"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "D"
    assert list(statuses.values()).count("stable") == 1
    assert statuses["D"] == "stable"
    assert set(out.annotation_gt.value) == {"center_of_mass", "projection", "support_footprint"}
    _assert_keyed_bbox_map_in_bounds(out)
    _assert_selected_geometry_matches_status(out, expected_status="stable")
    assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert out.prompt_variants["answer_only"]
    assert out.prompt_variants["answer_and_annotation"]


def test_stack_stability_tipping_label_contract() -> None:
    out = PhysicsMechanicsStackStabilityStatusLabelTask().generate(
        94121,
        params={"query_id": "tipping_stack_label", "correct_option_letter": "B"},
        max_attempts=10,
    )
    statuses = out.trace_payload["render_map"]["candidate_statuses"]

    assert out.scene_id == "stack_stability"
    assert out.query_id == "tipping_stack_label"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "B"
    assert list(statuses.values()).count("tipping") == 1
    assert statuses["B"] == "tipping"
    assert set(out.annotation_gt.value) == {"center_of_mass", "projection", "support_footprint"}
    _assert_keyed_bbox_map_in_bounds(out)
    _assert_selected_geometry_matches_status(out, expected_status="tipping")


def test_stack_stability_options_are_visual_not_annotation() -> None:
    out = PhysicsMechanicsStackStabilityStatusLabelTask().generate(94131, params={}, max_attempts=10)
    render_map = out.trace_payload["render_map"]

    assert set(render_map["candidate_statuses"]) == {"A", "B", "C", "D", "E", "F"}
    assert out.answer_gt.value in render_map["candidate_statuses"]
    assert out.annotation_gt.value["center_of_mass"] not in render_map["candidate_stack_bboxes_px"].values()
    assert out.annotation_gt.value["projection"] not in render_map["candidate_stack_bboxes_px"].values()
    assert out.annotation_gt.value["support_footprint"] not in render_map["candidate_stack_bboxes_px"].values()
