"""Contracts for right-triangle trigonometry geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.measurement.right_triangle_trig import (
    SCENE_ID,
    GeometryRightTriangleAngleValueTask,
    GeometryRightTriangleMissingSideValueTask,
)


TASK_CLASSES = (
    GeometryRightTriangleMissingSideValueTask,
    GeometryRightTriangleAngleValueTask,
)

QUERY_IDS_BY_TASK = {
    GeometryRightTriangleMissingSideValueTask: (
        "height_from_angle_and_ground",
        "ground_from_angle_and_height",
        "hypotenuse_from_angle_and_height",
        "height_from_angle_and_hypotenuse",
        "ground_from_angle_and_hypotenuse",
    ),
    GeometryRightTriangleAngleValueTask: (
        "angle_from_opposite_adjacent",
        "angle_from_opposite_hypotenuse",
        "angle_from_adjacent_hypotenuse",
        "angle_of_elevation_from_height_and_distance",
    ),
}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_right_triangle_trig_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(57001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_id == "default"
    assert out.query_id
    assert out.answer_gt.type == "number"
    assert out.evidence_gt.type == "bbox_set"
    assert 2 <= len(out.evidence_gt.value) <= 3
    assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_id"] == "default"
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_evidence"]["type"] == "bbox_set"
    assert trace["execution_trace"]["answer_rounding"] == "nearest_tenth"


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_right_triangle_trig_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(57011, params=params, max_attempts=20)
    out_b = task.generate(57011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_right_triangle_trig_tasks_support_every_explicit_query(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            57021 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        assert out.query_id == query_id
        assert out.answer_gt.type == "number"
        assert out.trace_payload["query_spec"]["params"]["query_id_probabilities"] == {
            query_id: 1.0
        }


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_right_triangle_trig_evidence_stays_inside_canvas(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            57041 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        width, height = out.image.size
        for x0, y0, x1, y1 in out.evidence_gt.value:
            assert 0.0 <= x0 < x1 <= float(width)
            assert 0.0 <= y0 < y1 <= float(height)
            assert (x1 - x0) > 8.0
            assert (y1 - y0) > 8.0


def test_right_triangle_trig_tasks_reject_unknown_query_id() -> None:
    task = GeometryRightTriangleMissingSideValueTask()
    with pytest.raises(ValueError):
        task.generate(57031, params={"query_id": "not_a_query"}, max_attempts=20)
