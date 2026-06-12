"""Tests for the synthetic 3D reference-nearest task."""

from __future__ import annotations

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.object_scene.camera_distance_extremum_label import LARGE_CONTEXT_SHAPE_TYPES
from trace.tasks.three_d.object_scene.reference_nearest_label import TASK_ID
from tests.three_d_option_panel_helpers import assert_option_panel_matches_candidates


def test_reference_nearest_answer_and_annotation() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260521,
        params={
            "query_id": "closest_to_reference",
            "scene_variant": "floor_grid_room",
            "point_count": 6,
            "large_candidate_count": 2,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=200,
    )

    trace = output.trace_payload["execution_trace"]
    point_specs = list(trace["point_specs"])
    context_specs = list(trace["context_object_specs"])
    gaps_by_label = dict(trace["candidate_reference_gaps_by_label"])
    sorted_labels = sorted(gaps_by_label, key=lambda label: (float(gaps_by_label[label]), str(label)))
    expected_label = str(sorted_labels[0])
    reference_id = str(trace["reference_object_id"])
    assert output.scene_id == "object_scene"
    assert output.query_id == "closest_to_reference"
    assert output.answer_gt.type == "option_letter"
    assert output.answer_gt.value == expected_label
    assert len(point_specs) == 6
    assert len(context_specs) == 1
    assert all(spec["is_answer_candidate"] for spec in point_specs)
    assert not context_specs[0]["is_answer_candidate"]
    assert reference_id == str(context_specs[0]["object_id"])
    assert reference_id not in {str(spec["object_id"]) for spec in point_specs}
    assert context_specs[0]["nameable_for_prompt"]
    assert str(context_specs[0]["prompt_name"]) == str(trace["reference_object_name"])
    assert str(context_specs[0]["prompt_name"]) not in {str(spec["prompt_name"]) for spec in point_specs}
    assert sum(1 for spec in point_specs if str(spec["shape_type"]) in set(LARGE_CONTEXT_SHAPE_TYPES)) == 2
    answer_spec = next(spec for spec in point_specs if str(spec["point_label"]) == expected_label)
    assert output.annotation_gt.type == "bbox_set"
    assert output.trace_payload["render_map"]["point_bboxes_px"][expected_label] == (
        output.trace_payload["render_map"]["object_bboxes_px"][str(answer_spec["object_id"])]
    )
    assert_option_panel_matches_candidates(
        output,
        point_specs,
        answer_label=expected_label,
        answer_object_id=str(answer_spec["object_id"]),
        expected_image_size=(1180, 1068),
    )
    assert trace["solver_trace"]["reference_nearest_order"][0] == expected_label
    assert trace["solver_trace"]["reference_excluded_from_options"] is True
    assert float(trace["solver_trace"]["reference_nearest_margin"]) >= 0.24


def test_reference_nearest_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_scene"
    assert taxonomy.source_scene_id == "object_scene"
