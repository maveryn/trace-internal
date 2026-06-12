"""Tests for the synthetic 3D spatial-relation count task."""

from __future__ import annotations

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.object_scene.relation_attribute_count import TASK_ID


def test_spatial_relation_count_answer_and_annotation() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260529,
        params={
            "query_id": "on_top_of_reference_count",
            "scene_variant": "floor_grid_room",
            "object_count": 10,
            "target_count": 3,
            "reference_shape_type": "table",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=180,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    target_object_ids = [str(object_id) for object_id in trace["target_object_ids"]]
    relation_status = dict(trace["relation_status_by_object_id"])

    assert output.scene_id == "object_scene"
    assert output.query_id == "on_top_of_reference_count"
    assert output.answer_gt.type == "integer"
    assert output.answer_gt.value == 3
    assert output.annotation_gt.type == "bbox_set"
    assert len(output.annotation_gt.value) == int(output.answer_gt.value)
    assert output.annotation_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in target_object_ids]
    assert all(bool(relation_status[object_id]) for object_id in target_object_ids)
    assert sum(1 for value in relation_status.values() if bool(value)) == int(output.answer_gt.value)
    assert trace["reference_shape_type"] == "table"
    assert render_map["reference_object_bbox_px"] == render_map["object_bboxes_px"][trace["reference_object_id"]]
    assert output.trace_payload["projected_annotation"]["bbox_set"] == output.annotation_gt.value
    assert output.image.size == (1180, 900)


def test_spatial_relation_count_query_variants_generate() -> None:
    task = create_task(TASK_ID)
    params_by_query = {
        "under_reference_count": {"reference_shape_type": "table"},
        "inside_reference_count": {"reference_shape_type": "open_box"},
    }
    for offset, (query_id, extra_params) in enumerate(params_by_query.items()):
        output = task.generate(
            20260530 + int(offset),
            params={
                "query_id": query_id,
                "scene_variant": "studio_platform",
                "object_count": 10,
                "target_count": 2,
                "post_image_noise_apply_prob": 0.0,
                **extra_params,
            },
            max_attempts=180,
        )

        assert output.query_id == query_id
        assert output.answer_gt.type == "integer"
        assert len(output.annotation_gt.value) == int(output.answer_gt.value)


def test_spatial_relation_count_supports_zero_and_four_targets() -> None:
    task = create_task(TASK_ID)
    params_by_query = {
        "on_top_of_reference_count": {"reference_shape_type": "table"},
        "under_reference_count": {"reference_shape_type": "table"},
        "inside_reference_count": {"reference_shape_type": "open_box"},
    }
    cases = [(0, "empty"), (4, "full")]
    for offset, (query_id, extra_params) in enumerate(params_by_query.items()):
        for target_count, case_name in cases:
            output = task.generate(
                20260609 + int(offset) * 10 + int(target_count),
                params={
                    "query_id": query_id,
                    "scene_variant": "floor_grid_room",
                    "object_count": 11,
                    "target_count": int(target_count),
                    "post_image_noise_apply_prob": 0.0,
                    **extra_params,
                },
                max_attempts=260,
            )

            assert output.query_id == query_id
            assert output.answer_gt.value == int(target_count), case_name
            assert len(output.annotation_gt.value) == int(target_count), case_name


def test_spatial_relation_count_default_answer_range_covers_distribution_gate() -> None:
    task = create_task(TASK_ID)
    observed = set()
    for sample_index in range(80):
        output = task.generate(
            20260690 + int(sample_index),
            params={"post_image_noise_apply_prob": 0.0},
            max_attempts=260,
        )
        observed.add(int(output.answer_gt.value))
    assert observed == {0, 1, 2, 3, 4}


def test_spatial_relation_count_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_scene"
    assert taxonomy.source_scene_id == "object_scene"
