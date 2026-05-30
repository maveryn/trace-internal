"""Contracts for compass-bearing route geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.measurement.bearing_route import (
    GeometryBearingRouteEndpointPositionLabelTask,
    GeometryBearingRouteFinalDisplacementValueTask,
    SCENE_ID,
)


TASK_CLASSES = (
    GeometryBearingRouteFinalDisplacementValueTask,
    GeometryBearingRouteEndpointPositionLabelTask,
)

QUERY_ID_BY_TASK = {
    GeometryBearingRouteFinalDisplacementValueTask: "final_displacement_value",
    GeometryBearingRouteEndpointPositionLabelTask: "endpoint_position_label",
}

ANSWER_TYPE_BY_TASK = {
    GeometryBearingRouteFinalDisplacementValueTask: "number",
    GeometryBearingRouteEndpointPositionLabelTask: "option_letter",
}

EVIDENCE_TYPE_BY_TASK = {
    GeometryBearingRouteFinalDisplacementValueTask: "keyed_point_map",
    GeometryBearingRouteEndpointPositionLabelTask: "keyed_point_map",
}

EVIDENCE_KEYS_BY_TASK = {
    GeometryBearingRouteFinalDisplacementValueTask: {
        "start_point",
        "turn_point",
        "finish_point",
    },
    GeometryBearingRouteEndpointPositionLabelTask: {
        "start_point",
        "reached_endpoint",
    },
}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_bearing_route_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(78001, params={}, max_attempts=20)
    query_id = QUERY_ID_BY_TASK[task_cls]

    assert out.scene_id == SCENE_ID
    assert out.query_id == query_id
    assert out.answer_gt.type == ANSWER_TYPE_BY_TASK[task_cls]
    assert out.evidence_gt.type == EVIDENCE_TYPE_BY_TASK[task_cls]
    assert set(out.evidence_gt.value) == EVIDENCE_KEYS_BY_TASK[task_cls]
    assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["scene_ir"]["scene_id"] == SCENE_ID
    assert trace["witness_symbolic"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_id"] == query_id
    assert trace["execution_trace"]["query_id"] == query_id
    assert trace["projected_evidence"]["type"] == EVIDENCE_TYPE_BY_TASK[task_cls]
    if out.evidence_gt.type == "keyed_bbox_map":
        assert trace["projected_evidence"]["keyed_bbox_map"] == out.evidence_gt.value
        assert trace["projected_evidence"]["pixel_keyed_bbox_map"] == out.evidence_gt.value
    else:
        assert trace["projected_evidence"]["keyed_point_map"] == out.evidence_gt.value
        assert trace["projected_evidence"]["pixel_keyed_point_map"] == out.evidence_gt.value
    assert trace["render_spec"]["font_family"]["font_family"]


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_bearing_route_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    out_a = task.generate(78011, params={}, max_attempts=20)
    out_b = task.generate(78011, params={}, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_bearing_route_displacement_uses_right_triangle_case() -> None:
    task = GeometryBearingRouteFinalDisplacementValueTask()
    out = task.generate(78021, params={"target_displacement": 13}, max_attempts=20)
    trace = out.trace_payload["execution_trace"]

    assert out.answer_gt.value == 13
    assert out.evidence_gt.type == "keyed_point_map"
    assert set(out.evidence_gt.value) == {"start_point", "turn_point", "finish_point"}
    assert "compass_rose" not in out.evidence_gt.value
    assert int(trace["displacement"]) == 13
    assert int(trace["leg_a"]) ** 2 + int(trace["leg_b"]) ** 2 == 13**2


def test_bearing_endpoint_uses_selected_candidate_label() -> None:
    task = GeometryBearingRouteEndpointPositionLabelTask()
    out = task.generate(78031, params={"target_index": 2}, max_attempts=20)
    trace = out.trace_payload["execution_trace"]
    labels = trace["option_labels"]

    assert out.answer_gt.value == labels[2]
    assert trace["answer_value"] == labels[2]
    assert out.evidence_gt.type == "keyed_point_map"
    assert set(out.evidence_gt.value) == {"start_point", "reached_endpoint"}
    assert "route_instructions" not in out.evidence_gt.value
    assert "instruction_panel_bbox" in out.trace_payload["render_map"]
    selected_label_bbox = out.trace_payload["render_map"]["selected_candidate_label_bbox"]
    assert out.evidence_gt.value["reached_endpoint"] != selected_label_bbox


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_bearing_route_evidence_stays_inside_canvas(task_cls) -> None:
    task = task_cls()
    out = task.generate(78041, params={}, max_attempts=20)
    width, height = out.image.size
    if out.evidence_gt.type == "keyed_bbox_map":
        for x0, y0, x1, y1 in out.evidence_gt.value.values():
            assert 0.0 <= x0 < x1 <= float(width)
            assert 0.0 <= y0 < y1 <= float(height)
            assert (x1 - x0) > 8.0
            assert (y1 - y0) > 8.0
    else:
        for x, y in out.evidence_gt.value.values():
            assert 0.0 <= x <= float(width)
            assert 0.0 <= y <= float(height)
