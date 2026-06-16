"""Tests for the synthetic 3D marked-point vertical-relation task."""

from __future__ import annotations

import math

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.object_scene.marked_point_vertical_relation_label import (
    MIN_DISTRACTOR_REFERENCE_XY_OFFSET,
    REFERENCE_SHAPE_TYPES,
    TASK_ID,
)
from tests.three_d_canvas_helpers import assert_three_d_canvas_contract


def test_marked_point_vertical_relation_answer_and_annotation() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260531,
        params={
            "query_id": "directly_above_reference",
            "scene_variant": "floor_grid_room",
            "point_count": 6,
            "object_count": 8,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=260,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    reference_id = str(trace["reference_object_id"])
    reference_spec = next(spec for spec in trace["object_specs"] if str(spec["object_id"]) == reference_id)
    reference_xy = tuple(float(value) for value in reference_spec["base_xyz"][:2])
    marked_points = list(trace["marked_points"])
    answer_marker = next(point for point in marked_points if str(point["marker_id"]) == str(trace["answer_marker_id"]))
    answer_label = str(answer_marker["point_label"])

    assert output.scene_id == "object_scene"
    assert output.query_id == "directly_above_reference"
    assert_three_d_canvas_contract(output)
    assert output.answer_gt.type == "option_letter"
    assert output.answer_gt.value == answer_label
    assert output.annotation_gt.type == "keyed_point_map"
    assert output.annotation_gt.value == {"selected_point": render_map["selected_point_px"]}
    assert output.annotation_gt.value["selected_point"] == render_map["marked_point_centers_px"][answer_label]
    assert render_map["marked_point_label_bboxes_px"][answer_label] == render_map["marked_point_glyph_bboxes_px"][answer_label]
    assert output.trace_payload["projected_annotation"]["type"] == "keyed_point_map"
    assert output.trace_payload["projected_annotation"]["keyed_point_map"] == output.annotation_gt.value
    assert output.trace_payload["projected_annotation"]["pixel_keyed_point_map"] == output.annotation_gt.value

    assert len(marked_points) == 6
    assert set(point["point_label"] for point in marked_points) == {"A", "B", "C", "D", "E", "F"}
    assert len(trace["object_specs"]) == 8
    assert str(trace["reference_shape_type"]) in set(REFERENCE_SHAPE_TYPES)
    assert int(trace["reference_prompt_name_count"]) == 1
    assert str(trace["reference_object_name"]) in output.prompt
    assert "above" in output.prompt.lower()
    assert output.trace_payload["query_spec"]["params"]["answer_support"] == ["A", "B", "C", "D", "E", "F"]
    assert output.trace_payload["scene_ir"]["relations"]["answer_point_id"] == str(answer_marker["point_id"])
    assert output.trace_payload["witness_symbolic"]["ids_by_role"]["selected_point"] == str(answer_marker["point_id"])
    assert output.trace_payload["witness_symbolic"]["ids_by_role"]["reference_object"] == reference_id
    assert render_map["reference_object_bbox_px"] == render_map["object_bboxes_px"][reference_id]

    answer_xy = tuple(float(value) for value in answer_marker["world_xyz"][:2])
    assert math.hypot(answer_xy[0] - reference_xy[0], answer_xy[1] - reference_xy[1]) < 1e-6
    assert float(answer_marker["world_xyz"][2]) > float(reference_spec["base_xyz"][2]) + float(reference_spec["dimensions_xyz"][2])
    for point in marked_points:
        if str(point["marker_id"]) == str(trace["answer_marker_id"]):
            continue
        point_xy = tuple(float(value) for value in point["world_xyz"][:2])
        assert math.hypot(point_xy[0] - reference_xy[0], point_xy[1] - reference_xy[1]) >= MIN_DISTRACTOR_REFERENCE_XY_OFFSET


def test_marked_point_vertical_relation_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_scene"
    assert taxonomy.source_scene_id == "object_scene"
