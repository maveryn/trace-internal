"""Tests for the synthetic 3D height-extremum task."""

from __future__ import annotations

import pytest

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.spatial.height_extremum import SUPPORTED_QUERY_VARIANTS, TASK_ID


@pytest.mark.parametrize("query_variant", SUPPORTED_QUERY_VARIANTS)
def test_height_extremum_answer_and_evidence(query_variant: str) -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260521,
        params={
            "query_variant": query_variant,
            "scene_variant": "floor_grid_room",
            "point_count": 6,
            "context_object_count": 5,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=220,
    )

    trace = output.trace_payload["execution_trace"]
    point_specs = list(trace["point_specs"])
    context_specs = list(trace["context_object_specs"])
    height_by_label = {str(label): float(value) for label, value in trace["height_by_label"].items()}
    sorted_labels = [str(label) for label, _value in sorted(height_by_label.items(), key=lambda item: (float(item[1]), str(item[0])))]
    expected_label = sorted_labels[-1] if query_variant == "highest_above_floor" else sorted_labels[0]

    assert output.query_variant == "default"
    assert output.scene_id == "object_scene"
    assert output.query_id == query_variant
    assert output.answer_gt.type == "option_letter"
    assert output.answer_gt.value == expected_label
    assert len(point_specs) == 6
    assert len(context_specs) == 5
    assert all(spec["is_answer_candidate"] for spec in point_specs)
    assert all(not spec["is_answer_candidate"] for spec in context_specs)
    assert output.evidence_gt.type == "bbox_set"
    assert output.evidence_gt.value == [
        output.trace_payload["render_map"]["point_bboxes_px"][expected_label]
    ]
    assert trace["height_order_low_to_high"] == sorted_labels
    assert trace["solver_trace"]["height_order_low_to_high"] == sorted_labels
    assert trace["solver_trace"]["unique_height_extremum_answer"] is True
    assert float(trace["solver_trace"]["height_margin"]) >= 0.18
    assert output.image.size == (1180, 900)


def test_height_extremum_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_scene"
    assert taxonomy.source_task_group == "spatial"
