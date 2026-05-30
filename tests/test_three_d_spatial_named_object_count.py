"""Tests for the synthetic 3D named-object count task."""

from __future__ import annotations

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.spatial.named_object_count import TASK_ID


def test_named_object_count_answer_and_evidence() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260529,
        params={
            "query_id": "object_type_count",
            "scene_variant": "floor_grid_room",
            "object_count": 14,
            "target_count": 4,
            "target_shape_type": "cylinder",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=160,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    target_object_ids = [str(object_id) for object_id in trace["target_object_ids"]]
    object_specs = list(trace["object_specs"])

    assert output.scene_id == "object_scene"
    assert output.query_id == "object_type_count"
    assert output.answer_gt.type == "integer"
    assert output.answer_gt.value == 4
    assert output.evidence_gt.type == "bbox_set"
    assert len(output.evidence_gt.value) == int(output.answer_gt.value)
    assert output.evidence_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in target_object_ids]
    assert trace["shape_counts"]["cylinder"] == 4
    assert all(str(spec["shape_type"]) == "cylinder" for spec in object_specs if str(spec["object_id"]) in set(target_object_ids))
    assert all(not bool(spec.get("is_answer_candidate", False)) for spec in object_specs)
    assert all(bool(spec.get("is_countable_object", False)) for spec in object_specs)
    assert output.trace_payload["projected_evidence"]["bbox_set"] == output.evidence_gt.value
    assert output.image.size == (1180, 900)


def test_named_object_count_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_scene"
    assert taxonomy.source_task_group == "spatial"
