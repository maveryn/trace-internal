"""Tests for the synthetic 3D view-relation count task."""

from __future__ import annotations

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.spatial.view_relation_count import MIN_REFERENCE_X_MARGIN_PX, TASK_ID


def test_view_relation_count_answer_and_evidence() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260529,
        params={
            "query_id": "left_of_reference_in_view_count",
            "scene_variant": "floor_grid_room",
            "object_count": 11,
            "target_count": 4,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=220,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    target_object_ids = [str(object_id) for object_id in trace["target_object_ids"]]
    reference_object_id = str(trace["reference_object_id"])
    reference_spec = next(spec for spec in trace["object_specs"] if str(spec["object_id"]) == reference_object_id)
    reference_x = float(reference_spec["screen_xy"][0])
    target_set = set(target_object_ids)

    assert output.scene_id == "object_scene"
    assert output.query_id == "left_of_reference_in_view_count"
    assert output.answer_gt.type == "integer"
    assert output.answer_gt.value == 4
    assert output.evidence_gt.type == "bbox_set"
    assert reference_object_id not in target_set
    assert int(trace["reference_prompt_name_count"]) == 1
    assert str(trace["reference_object_name"]) in output.prompt
    assert "in the image" in output.prompt
    assert len(output.evidence_gt.value) == int(output.answer_gt.value)
    assert output.evidence_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in target_object_ids]
    assert output.trace_payload["projected_evidence"]["bbox_set"] == output.evidence_gt.value

    for spec in trace["object_specs"]:
        object_id = str(spec["object_id"])
        if object_id == reference_object_id:
            continue
        dx = float(spec["screen_xy"][0]) - reference_x
        assert abs(dx) >= MIN_REFERENCE_X_MARGIN_PX
        assert (object_id in target_set) == (dx < 0.0)
        assert bool(trace["view_relation_status_by_object_id"][object_id]) == (object_id in target_set)
    assert output.image.size == (1180, 900)


def test_view_relation_count_query_variants_generate() -> None:
    task = create_task(TASK_ID)
    for offset, query_id in enumerate(("left_of_reference_in_view_count", "right_of_reference_in_view_count")):
        output = task.generate(
            20260530 + int(offset),
            params={
                "query_id": query_id,
                "scene_variant": "studio_platform",
                "object_count": 10,
                "target_count": 3,
                "post_image_noise_apply_prob": 0.0,
            },
            max_attempts=220,
        )
        trace = output.trace_payload["execution_trace"]
        reference_id = str(trace["reference_object_id"])
        reference_x = float(next(spec for spec in trace["object_specs"] if str(spec["object_id"]) == reference_id)["screen_xy"][0])
        target_ids = {str(object_id) for object_id in trace["target_object_ids"]}

        assert output.query_id == query_id
        assert output.answer_gt.type == "integer"
        assert len(output.evidence_gt.value) == int(output.answer_gt.value)
        for spec in trace["object_specs"]:
            object_id = str(spec["object_id"])
            if object_id == reference_id:
                continue
            dx = float(spec["screen_xy"][0]) - reference_x
            expected = dx < 0.0 if query_id == "left_of_reference_in_view_count" else dx > 0.0
            assert (object_id in target_ids) == expected


def test_view_relation_count_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_scene"
    assert taxonomy.source_task_group == "spatial"
