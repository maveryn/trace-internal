"""Tests for the synthetic 3D multi-view object-match task."""

from __future__ import annotations

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.object_scene.multiview_object_match_label import (
    CANDIDATE_VIEW_KEY,
    REFERENCE_VIEW_KEY,
    TASK_ID,
)


def test_multiview_object_match_answer_and_annotation() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260529,
        params={
            "query_id": "same_object_in_second_view",
            "scene_variant": "floor_grid_room",
            "point_count": 6,
            "context_object_count": 0,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=160,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    solver_trace = dict(trace["solver_trace"])
    answer_label = str(output.answer_gt.value)
    target_object_id = str(trace["target_object_id"])
    candidate_labels = dict(solver_trace["candidate_labels_by_object_id"])

    assert output.scene_id == "object_scene"
    assert output.query_id == "same_object_in_second_view"
    assert output.answer_gt.type == "option_letter"
    assert answer_label == str(candidate_labels[target_object_id])
    assert output.annotation_gt.type == "keyed_bbox_map"
    assert set(output.annotation_gt.value) == {"reference_view_object", "second_view_match"}
    assert output.annotation_gt.value["reference_view_object"] == render_map["reference_view_object_bbox_px"]
    assert output.annotation_gt.value["second_view_match"] == render_map["second_view_match_bbox_px"]
    assert output.trace_payload["projected_annotation"]["type"] == "keyed_bbox_map"
    assert output.trace_payload["projected_annotation"]["keyed_bbox_map"] == output.annotation_gt.value
    assert output.trace_payload["projected_annotation"]["pixel_keyed_bbox_map"] == output.annotation_gt.value
    assert len(trace["canonical_point_specs"]) == 6
    assert len(trace["canonical_context_object_specs"]) == 0
    assert set(trace["views"]) == {REFERENCE_VIEW_KEY, CANDIDATE_VIEW_KEY}
    assert trace["views"][REFERENCE_VIEW_KEY]["camera"]["yaw_degrees"] != trace["views"][CANDIDATE_VIEW_KEY]["camera"]["yaw_degrees"]
    assert float(solver_trace["view_yaw_separation_degrees"]) >= 72.0
    assert solver_trace["same_object_unique_answer"] is True
    assert any(
        entity["entity_type"] == "red_reference_box"
        for entity in output.trace_payload["scene_ir"]["entities"]
        if str(entity["entity_id"]).startswith(f"{REFERENCE_VIEW_KEY}:")
    )
    assert output.image.size == (1480, 900)


def test_multiview_object_match_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_scene"
    assert taxonomy.source_scene_id == "object_scene"
