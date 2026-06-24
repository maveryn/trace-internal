"""Tests for the synthetic 3D height-extremum task."""

from __future__ import annotations

import pytest

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.object_scene.height_extremum_label import SUPPORTED_QUERY_IDS, TASK_ID
from tests.three_d_option_panel_helpers import assert_option_panel_matches_candidates


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_height_extremum_answer_and_annotation(query_id: str) -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260521,
        params={
            "query_id": query_id,
            "scene_variant": "floor_grid_room",
            "point_count": 5,
            "context_object_count": 4,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=220,
    )

    trace = output.trace_payload["execution_trace"]
    point_specs = list(trace["point_specs"])
    context_specs = list(trace["context_object_specs"])
    height_by_label = {str(label): float(value) for label, value in trace["height_by_label"].items()}
    sorted_labels = [str(label) for label, _value in sorted(height_by_label.items(), key=lambda item: (float(item[1]), str(item[0])))]
    expected_label = sorted_labels[-1] if query_id == "highest_above_floor" else sorted_labels[0]
    assert output.scene_id == "object_scene"
    assert output.query_id == query_id
    assert output.answer_gt.type == "option_letter"
    assert output.answer_gt.value == expected_label
    assert len(point_specs) == 5
    assert len(context_specs) == 4
    assert all(spec["is_answer_candidate"] for spec in point_specs)
    assert all(not spec["is_answer_candidate"] for spec in context_specs)
    answer_spec = next(spec for spec in point_specs if str(spec["point_label"]) == expected_label)
    expected_bbox = output.trace_payload["render_map"]["object_bboxes_px"][str(answer_spec["object_id"])]
    assert output.annotation_gt.type == "bbox"
    assert output.annotation_gt.value == expected_bbox
    assert output.trace_payload["render_map"]["point_bboxes_px"][expected_label] == expected_bbox
    assert_option_panel_matches_candidates(
        output,
        point_specs,
        answer_label=expected_label,
        answer_object_id=str(answer_spec["object_id"]),
        expected_image_size=(1180, 1068),
    )
    assert trace["height_order_low_to_high"] == sorted_labels
    assert trace["solver_trace"]["height_order_low_to_high"] == sorted_labels
    assert trace["solver_trace"]["unique_height_extremum_answer"] is True
    assert float(trace["solver_trace"]["height_margin"]) >= 0.18


def test_height_extremum_answer_color_and_shape_vary_across_seeds() -> None:
    task = create_task(TASK_ID)
    answer_colors = set()
    answer_shapes = set()
    for seed in range(20260600, 20260608):
        output = task.generate(
            seed,
            params={
                "query_id": "highest_above_floor",
                "scene_variant": "floor_grid_room",
                "point_count": 5,
                "context_object_count": 4,
                "post_image_noise_apply_prob": 0.0,
            },
            max_attempts=220,
        )
        trace = output.trace_payload["execution_trace"]
        answer_spec = next(spec for spec in trace["point_specs"] if str(spec["point_label"]) == str(trace["answer_label"]))
        answer_colors.add(str(answer_spec["option_color_name"]))
        answer_shapes.add(str(answer_spec["shape_type"]))

    assert len(answer_colors) >= 3
    assert len(answer_shapes) >= 4


def test_height_extremum_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_scene"
    assert not taxonomy.source_scene_id
