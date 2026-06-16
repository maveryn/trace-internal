"""Tests for the synthetic 3D marked-point depth task."""

from __future__ import annotations

import pytest

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.object_scene.marked_point_depth_extremum_label import TASK_ID
from tests.three_d_canvas_helpers import assert_three_d_canvas_contract


@pytest.mark.parametrize("query_id", ["closest_marked_point", "farthest_marked_point"])
def test_marked_point_depth_answer_and_annotation(query_id: str) -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260531,
        params={
            "query_id": query_id,
            "scene_variant": "floor_grid_room",
            "point_count": 6,
            "context_object_count": 6,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=220,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    marked_points = list(trace["marked_points"])
    sorted_points = sorted(marked_points, key=lambda point: (float(point["camera_distance"]), str(point["point_label"])))
    expected = sorted_points[0] if query_id == "closest_marked_point" else sorted_points[-1]
    expected_label = str(expected["point_label"])

    assert output.scene_id == "object_scene"
    assert output.query_id == query_id
    assert_three_d_canvas_contract(output)
    assert output.answer_gt.type == "option_letter"
    assert output.answer_gt.value == expected_label
    assert output.annotation_gt.type == "keyed_point_map"
    assert set(output.annotation_gt.value) == {"selected_point"}
    assert output.annotation_gt.value["selected_point"] == render_map["selected_point_px"]
    assert output.annotation_gt.value["selected_point"] == render_map["marked_point_centers_px"][expected_label]
    assert output.trace_payload["projected_annotation"]["type"] == "keyed_point_map"
    assert output.trace_payload["projected_annotation"]["keyed_point_map"] == output.annotation_gt.value
    assert output.trace_payload["projected_annotation"]["pixel_keyed_point_map"] == output.annotation_gt.value
    assert trace["point_specs"] == []
    assert len(marked_points) == 6
    assert len(trace["context_object_specs"]) == 6
    assert set(point["point_label"] for point in marked_points) == {"A", "B", "C", "D", "E", "F"}
    assert output.trace_payload["query_spec"]["params"]["answer_support"] == ["A", "B", "C", "D", "E", "F"]
    assert {str(point["surface_kind"]) for point in marked_points} == {"floor", "object_top"}
    assert output.trace_payload["scene_ir"]["relations"]["answer_point_id"] == str(expected["point_id"])
    assert output.trace_payload["witness_symbolic"]["ids_by_role"]["selected_point"] == str(expected["point_id"])
    assert render_map["marked_point_label_bboxes_px"][expected_label] == render_map["marked_point_glyph_bboxes_px"][expected_label]
    assert render_map["marked_point_circle_bboxes_px"][expected_label] == render_map["marked_point_glyph_bboxes_px"][expected_label]
    assert "marked" in output.prompt.lower()


def test_marked_point_depth_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_scene"
    assert taxonomy.source_scene_id == "object_scene"
