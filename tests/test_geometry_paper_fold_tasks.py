from __future__ import annotations

import pytest

from trace.tasks.registry import create_task

TASK_ID = "task_geometry__paper_fold__paper_fold_angle_value"
ANNOTATION_KEYS = {"target_angle_cue", "given_angle_label"}


def test_paper_fold_angle_value_uses_single_query_number_answer_and_bbox_map() -> None:
    out = create_task(TASK_ID).generate(
        instance_seed=2026062301,
        params={},
        max_attempts=50,
    )

    assert out.scene_id == "paper_fold"
    assert out.query_id == "single"
    assert out.answer_gt.type == "number"
    assert isinstance(out.answer_gt.value, float)
    assert round(float(out.answer_gt.value), 1) == float(out.answer_gt.value)

    assert out.annotation_gt.type == "bbox_map"
    assert set(out.annotation_gt.value) == ANNOTATION_KEYS
    for bbox in out.annotation_gt.value.values():
        assert len(bbox) == 4
        assert bbox[0] <= bbox[2]
        assert bbox[1] <= bbox[3]

    projected = out.trace_payload["projected_annotation"]
    assert projected["type"] == "bbox_map"
    assert projected["bbox_map"] == out.annotation_gt.value
    assert projected["pixel_bbox_map"] == out.annotation_gt.value

    query_spec = out.trace_payload["query_spec"]
    assert query_spec["query_id"] == "single"
    assert query_spec["params"]["query_id"] == "single"
    assert query_spec["prompt_variant"]["prompt_schema_version"] == "v1"
    assert query_spec["template_id"] == "geometry_paper_fold_measurement_v1"


def test_paper_fold_rejects_retired_query_id() -> None:
    task = create_task(TASK_ID)
    assert task.generate(instance_seed=17, params={"query_id": "single"}, max_attempts=50).query_id == "single"

    with pytest.raises(ValueError, match="unsupported query_id"):
        task.generate(
            instance_seed=17,
            params={"query_id": "fold_angle_from_total_label"},
            max_attempts=50,
        )


def test_paper_fold_explicit_geometry_overrides_still_bind_same_trace() -> None:
    out = create_task(TASK_ID).generate(
        instance_seed=2026062302,
        params={"height_units": 16, "folded_offset_units": 10},
        max_attempts=50,
    )

    witness = out.trace_payload["witness_symbolic"]
    assert witness["height_units"] == 16.0
    assert witness["folded_offset_units"] == 10.0
    assert witness["answer_value"] == out.answer_gt.value
