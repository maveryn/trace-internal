"""Tests for the synthetic lettered 3D object relation task."""

from __future__ import annotations

import pytest

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.spatial.object_relation import SUPPORTED_QUERY_VARIANTS


TASK_ID = "task_three_d__object_scene__object_relation_label"


@pytest.mark.parametrize("query_variant", SUPPORTED_QUERY_VARIANTS)
def test_object_relation_answer_and_evidence(query_variant: str) -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260521,
        params={
            "query_variant": query_variant,
            "scene_variant": "floor_grid_room",
            "point_count": 6,
            "context_object_count": 2,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=160,
    )

    trace = output.trace_payload["execution_trace"]
    point_specs = list(trace["point_specs"])
    context_specs = list(trace["context_object_specs"])
    relation_status = dict(trace["relation_status_by_label"])
    expected_labels = [str(label) for label, is_match in relation_status.items() if bool(is_match)]
    reference_id = str(trace["reference_object_id"])
    reference_spec = next(spec for spec in context_specs if str(spec["object_id"]) == reference_id)

    assert output.query_variant == "default"
    assert output.scene_id == "object_scene"
    assert output.query_id == query_variant
    assert output.answer_gt.type == "option_letter"
    assert output.answer_gt.value == expected_labels[0]
    assert len(expected_labels) == 1
    assert len(point_specs) == 6
    assert len(context_specs) == 2
    assert all(spec["is_answer_candidate"] for spec in point_specs)
    assert not any(spec["is_answer_candidate"] for spec in context_specs)
    assert reference_spec["nameable_for_prompt"]
    assert output.evidence_gt.type == "bbox_set"
    assert output.evidence_gt.value == [
        output.trace_payload["render_map"]["point_bboxes_px"][expected_labels[0]]
    ]
    assert output.image.size == (1180, 900)
    assert any(entity["entity_id"] == "open_floor_stage" for entity in output.trace_payload["scene_ir"]["entities"])
    assert not any(entity["entity_id"] == "room_shell" for entity in output.trace_payload["scene_ir"]["entities"])

    answer_spec = next(spec for spec in point_specs if str(spec["point_label"]) == expected_labels[0])
    if query_variant == "on_top_of_prop":
        assert float(answer_spec["base_xyz"][2]) > float(reference_spec["base_xyz"][2]) + 0.85 * float(reference_spec["dimensions_xyz"][2])
    elif query_variant == "under_prop":
        assert abs(float(answer_spec["world_xyz"][0]) - float(reference_spec["world_xyz"][0])) < float(reference_spec["dimensions_xyz"][0]) * 0.4
        assert abs(float(answer_spec["world_xyz"][1]) - float(reference_spec["world_xyz"][1])) < float(reference_spec["dimensions_xyz"][1]) * 0.4
    else:
        assert str(reference_spec["shape_type"]) == "open_box"
        assert float(reference_spec["dimensions_xyz"][2]) < 1.00
        assert float(answer_spec["base_xyz"][2]) > float(reference_spec["base_xyz"][2])
        assert answer_spec["contained_by_object_id"] == reference_id
        assert float(answer_spec["render_order_bias"]) < 0.0
        assert abs(float(answer_spec["world_xyz"][0]) - float(reference_spec["world_xyz"][0])) < float(reference_spec["dimensions_xyz"][0]) * 0.3
        assert abs(float(answer_spec["world_xyz"][1]) - float(reference_spec["world_xyz"][1])) < float(reference_spec["dimensions_xyz"][1]) * 0.3


def test_object_relation_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_scene"
    assert taxonomy.source_task_group == "spatial"
