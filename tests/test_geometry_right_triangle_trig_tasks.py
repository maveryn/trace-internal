"""Contracts for right-triangle trigonometry geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.triangle_relations.angle_of_elevation_value import GeometryAngleOfElevationValueTask
from trace.tasks.geometry.triangle_relations.right_triangle_inverse_trig_angle_angle_from_adjacent_hypotenuse import GeometryRightTriangleAngleAdjacentHypotenuseTask
from trace.tasks.geometry.triangle_relations.right_triangle_inverse_trig_angle_angle_from_opposite_adjacent import GeometryRightTriangleAngleOppositeAdjacentTask
from trace.tasks.geometry.triangle_relations.right_triangle_inverse_trig_angle_angle_from_opposite_hypotenuse import GeometryRightTriangleAngleOppositeHypotenuseTask
from trace.tasks.geometry.triangle_relations.right_triangle_missing_side_value_ground_from_angle_and_height import (
    SCENE_ID,
    GeometryRightTriangleGroundFromAngleAndHeightTask,
)
from trace.tasks.geometry.triangle_relations.right_triangle_missing_side_value_ground_from_angle_and_hypotenuse import GeometryRightTriangleGroundFromAngleAndHypotenuseTask
from trace.tasks.geometry.triangle_relations.right_triangle_missing_side_value_height_from_angle_and_ground import GeometryRightTriangleHeightFromAngleAndGroundTask
from trace.tasks.geometry.triangle_relations.right_triangle_missing_side_value_height_from_angle_and_hypotenuse import GeometryRightTriangleHeightFromAngleAndHypotenuseTask
from trace.tasks.geometry.triangle_relations.right_triangle_missing_side_value_hypotenuse_from_angle_and_height import GeometryRightTriangleHypotenuseFromAngleAndHeightTask


TASK_CLASSES = (
    GeometryRightTriangleHeightFromAngleAndGroundTask,
    GeometryRightTriangleGroundFromAngleAndHeightTask,
    GeometryRightTriangleHypotenuseFromAngleAndHeightTask,
    GeometryRightTriangleHeightFromAngleAndHypotenuseTask,
    GeometryRightTriangleGroundFromAngleAndHypotenuseTask,
    GeometryRightTriangleAngleOppositeAdjacentTask,
    GeometryRightTriangleAngleOppositeHypotenuseTask,
    GeometryRightTriangleAngleAdjacentHypotenuseTask,
    GeometryAngleOfElevationValueTask,
)

QUERY_IDS_BY_TASK = {
    GeometryRightTriangleHeightFromAngleAndGroundTask: ("single",),
    GeometryRightTriangleGroundFromAngleAndHeightTask: ("single",),
    GeometryRightTriangleHypotenuseFromAngleAndHeightTask: ("single",),
    GeometryRightTriangleHeightFromAngleAndHypotenuseTask: ("single",),
    GeometryRightTriangleGroundFromAngleAndHypotenuseTask: ("single",),
    GeometryRightTriangleAngleOppositeAdjacentTask: ("single",),
    GeometryRightTriangleAngleOppositeHypotenuseTask: ("single",),
    GeometryRightTriangleAngleAdjacentHypotenuseTask: ("single",),
    GeometryAngleOfElevationValueTask: ("single",),
}

ANGLE_TASK_CLASSES = (
    GeometryRightTriangleAngleOppositeAdjacentTask,
    GeometryRightTriangleAngleOppositeHypotenuseTask,
    GeometryRightTriangleAngleAdjacentHypotenuseTask,
    GeometryAngleOfElevationValueTask,
)


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_right_triangle_trig_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(57001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_id == "single"
    assert out.answer_gt.type == "number"
    if task_cls in ANGLE_TASK_CLASSES:
        assert out.annotation_gt.type == "point"
        assert len(out.annotation_gt.value) == 2
    else:
        assert out.annotation_gt.type == "segment"
        assert len(out.annotation_gt.value) == 2
    assert "Annotation format:" in out.prompt_variants["answer_and_annotation"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_annotation"]["type"] == out.annotation_gt.type
    assert trace["execution_trace"]["answer_rounding"] == "nearest_tenth"


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_right_triangle_trig_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(57011, params=params, max_attempts=20)
    out_b = task.generate(57011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
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
def test_right_triangle_trig_annotation_stays_inside_canvas(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            57041 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        width, height = out.image.size
        if out.annotation_gt.type == "point":
            x, y = out.annotation_gt.value
            assert 0.0 <= x <= float(width)
            assert 0.0 <= y <= float(height)
        else:
            for x, y in out.annotation_gt.value:
                assert 0.0 <= x <= float(width)
                assert 0.0 <= y <= float(height)


def test_right_triangle_trig_tasks_reject_unknown_query_id() -> None:
    task = GeometryRightTriangleHeightFromAngleAndGroundTask()
    with pytest.raises(ValueError):
        task.generate(57031, params={"query_id": "not_a_query"}, max_attempts=20)
