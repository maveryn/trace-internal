"""Tests for the synthetic 3D landmark correspondence task."""

from __future__ import annotations

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.object_scene.landmark_correspondence_label import (
    CANDIDATE_VIEW_KEY,
    LANDMARK_CORRESPONDENCE_SHAPE_TYPES,
    REFERENCE_VIEW_KEY,
    TASK_ID,
)
from tests.three_d_canvas_helpers import assert_three_d_canvas_contract


def test_landmark_correspondence_answer_and_annotation() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260531,
        params={
            "scene_variant": "floor_grid_room",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=180,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    solver_trace = dict(trace["solver_trace"])
    answer_label = str(output.answer_gt.value)
    right_view = trace["views"][CANDIDATE_VIEW_KEY]
    candidate_landmarks = dict(right_view["candidate_landmarks_by_label"])

    assert output.scene_id == "object_scene"
    assert output.query_id == "single"
    assert output.answer_gt.type == "option_letter"
    assert answer_label in {"A", "B", "C", "D"}
    assert output.annotation_gt.type == "point_map"
    assert set(output.annotation_gt.value) == {"reference_landmark", "matched_landmark"}
    assert output.annotation_gt.value["reference_landmark"] == render_map["reference_landmark_point_px"]
    assert output.annotation_gt.value["matched_landmark"] == render_map["matched_landmark_point_px"]
    assert output.trace_payload["projected_annotation"]["type"] == "point_map"
    assert output.trace_payload["projected_annotation"]["point_map"] == output.annotation_gt.value
    assert output.trace_payload["projected_annotation"]["pixel_point_map"] == output.annotation_gt.value
    assert set(candidate_landmarks) == {"A", "B", "C", "D"}
    assert output.trace_payload["query_spec"]["params"]["answer_support"] == ["A", "B", "C", "D"]
    assert candidate_landmarks[answer_label]["landmark_id"] == trace["target_landmark_id"]
    assert solver_trace["landmark_ids_by_label"][answer_label] == trace["target_landmark_id"]
    assert solver_trace["same_landmark_unique_answer"] is True
    assert str(trace["shape_type"]) in set(LANDMARK_CORRESPONDENCE_SHAPE_TYPES)
    assert trace["views"][REFERENCE_VIEW_KEY]["object_spec"]["shape_type"] == trace["shape_type"]
    assert trace["views"][CANDIDATE_VIEW_KEY]["object_spec"]["shape_type"] == trace["shape_type"]
    assert trace["views"][REFERENCE_VIEW_KEY]["camera"]["yaw_degrees"] != trace["views"][CANDIDATE_VIEW_KEY]["camera"]["yaw_degrees"]
    assert float(solver_trace["view_yaw_separation_degrees"]) >= 72.0
    assert render_map["candidate_landmark_points_px_by_label"][answer_label] == render_map["matched_landmark_point_px"]
    assert len(render_map["candidate_landmark_marker_bboxes_px_by_label"]) == 4
    assert any(entity["entity_id"] == "reference_landmark_marker" for entity in output.trace_payload["scene_ir"]["entities"])
    assert any(
        entity["entity_id"] == f"candidate_landmark_marker_{answer_label}"
        and entity["attrs"]["is_answer"] is True
        for entity in output.trace_payload["scene_ir"]["entities"]
    )
    assert "REF" in output.prompt
    assert_three_d_canvas_contract(output)


def test_landmark_correspondence_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_scene"
    assert not taxonomy.source_scene_id
