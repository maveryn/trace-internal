"""Tests for the synthetic 3D counterfactual attribute-count task."""

from __future__ import annotations

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.spatial.counterfactual_attribute_count import TASK_ID


def _spec_matches_predicate(spec: dict, predicate: dict) -> bool:
    shape_type = predicate.get("shape_type")
    color_name = predicate.get("color_name")
    if shape_type is not None and str(spec["shape_type"]) != str(shape_type):
        return False
    if color_name is not None and str(spec["color_name"]) != str(color_name):
        return False
    return True


def test_counterfactual_attribute_count_answer_and_evidence() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260529,
        params={
            "query_id": "attribute_count_after_edits",
            "scene_variant": "floor_grid_room",
            "object_count": 13,
            "target_count": 4,
            "edit_step_count": 3,
            "target_predicate_kind": "color_object",
            "target_shape_type": "cube",
            "target_color_name": "red",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=220,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    initial_target_ids = [str(object_id) for object_id in trace["initial_target_object_ids"]]
    target_delta = sum(int(step["target_delta"]) for step in trace["counterfactual_steps"])

    assert output.scene_id == "object_scene"
    assert output.query_id == "attribute_count_after_edits"
    assert output.answer_gt.type == "integer"
    assert output.evidence_gt.type == "bbox_set"
    assert trace["target_predicate_kind"] == "color_object"
    assert trace["target_shape_type"] == "cube"
    assert trace["target_color_name"] == "red"
    assert trace["target_property_phrase"] == "red cubes"
    assert trace["initial_target_count"] == 4
    assert output.answer_gt.value == int(trace["initial_target_count"]) + int(target_delta)
    assert output.answer_gt.value == trace["final_target_count"]
    assert output.answer_gt.value != len(output.evidence_gt.value)
    assert len(output.evidence_gt.value) == int(trace["initial_target_count"])
    assert output.evidence_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in initial_target_ids]
    assert output.trace_payload["projected_evidence"]["bbox_set"] == output.evidence_gt.value
    assert all(str(step["step_text"]) in output.prompt for step in trace["counterfactual_steps"])
    assert "red cubes" in output.prompt
    assert "clear prompt colors" not in output.prompt
    assert any(bool(step["affects_target_property"]) for step in trace["counterfactual_steps"])
    assert any(not bool(step["affects_target_property"]) for step in trace["counterfactual_steps"])
    assert {str(step["predicate_relation_to_target"]) for step in trace["counterfactual_steps"]} <= {
        "subset",
        "disjoint",
    }

    initial_target_set = set(initial_target_ids)
    for spec in trace["object_specs"]:
        is_initial_target = str(spec["object_id"]) in initial_target_set
        assert is_initial_target == _spec_matches_predicate(spec, trace["target_predicate"])
    assert output.image.size == (1180, 900)


def test_counterfactual_attribute_count_generates_object_only_target_with_two_steps() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260530,
        params={
            "query_id": "attribute_count_after_edits",
            "scene_variant": "studio_platform",
            "object_count": 12,
            "target_count": 3,
            "edit_step_count": 2,
            "target_predicate_kind": "object",
            "target_shape_type": "sphere",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=220,
    )

    trace = output.trace_payload["execution_trace"]
    target_delta = sum(int(step["target_delta"]) for step in trace["counterfactual_steps"])

    assert len(trace["counterfactual_steps"]) == 2
    assert output.answer_gt.value == int(trace["initial_target_count"]) + int(target_delta)
    assert len(output.evidence_gt.value) == int(trace["initial_target_count"])
    assert trace["target_predicate_kind"] == "object"
    assert trace["target_property_phrase"] == "balls"
    assert trace["target_color_name"] is None
    assert all(
        _spec_matches_predicate(spec, trace["target_predicate"])
        for spec in trace["object_specs"]
        if str(spec["object_id"]) in set(trace["initial_target_object_ids"])
    )


def test_counterfactual_attribute_count_generates_color_only_target_with_one_step() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260531,
        params={
            "query_id": "attribute_count_after_edits",
            "scene_variant": "tabletop_room",
            "object_count": 12,
            "target_count": 3,
            "edit_step_count": 1,
            "target_predicate_kind": "color",
            "target_color_name": "blue",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=220,
    )

    trace = output.trace_payload["execution_trace"]
    target_delta = sum(int(step["target_delta"]) for step in trace["counterfactual_steps"])

    assert len(trace["counterfactual_steps"]) == 1
    assert trace["target_predicate_kind"] == "color"
    assert trace["target_shape_type"] is None
    assert trace["target_property_phrase"] == "blue objects"
    assert output.answer_gt.value == int(trace["initial_target_count"]) + int(target_delta)
    assert len(output.evidence_gt.value) == int(trace["initial_target_count"])
    assert all(
        _spec_matches_predicate(spec, trace["target_predicate"])
        for spec in trace["object_specs"]
        if str(spec["object_id"]) in set(trace["initial_target_object_ids"])
    )


def test_counterfactual_attribute_count_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_scene"
    assert taxonomy.source_task_group == "spatial"
