"""Contracts for circle/square tangent-packing geometry tasks."""

from __future__ import annotations

import math

import pytest

from trace.tasks.geometry.tangent_packing.circle_in_square_gap_area import (
    SCENE_ID,
    GeometryCircleInSquareGapAreaTask,
)
from trace.tasks.geometry.tangent_packing.circle_in_square_radius_from_gap_area import GeometryCircleInSquareRadiusFromGapAreaTask
from trace.tasks.geometry.tangent_packing.square_in_circle_gap_area import GeometrySquareInCircleGapAreaTask
from trace.tasks.geometry.tangent_packing.square_in_circle_side_from_gap_area import GeometrySquareInCircleSideFromGapAreaTask
from trace.tasks.geometry.tangent_packing.two_circles_in_rectangle_gap_area import GeometryTwoCirclesInRectangleGapAreaTask
from trace.tasks.geometry.tangent_packing.two_circles_in_rectangle_radius_from_gap_area import GeometryTwoCirclesInRectangleRadiusFromGapAreaTask

TASK_CLASSES = (
    GeometryCircleInSquareRadiusFromGapAreaTask,
    GeometrySquareInCircleSideFromGapAreaTask,
    GeometryTwoCirclesInRectangleRadiusFromGapAreaTask,
    GeometryCircleInSquareGapAreaTask,
    GeometrySquareInCircleGapAreaTask,
    GeometryTwoCirclesInRectangleGapAreaTask,
)

QUERY_IDS_BY_TASK = {
    GeometryCircleInSquareRadiusFromGapAreaTask: ("circle_in_square_radius_from_gap_area",),
    GeometrySquareInCircleSideFromGapAreaTask: ("square_in_circle_side_from_gap_area",),
    GeometryTwoCirclesInRectangleRadiusFromGapAreaTask: ("two_circles_in_rectangle_radius_from_gap_area",),
    GeometryCircleInSquareGapAreaTask: ("circle_in_square_gap_area",),
    GeometrySquareInCircleGapAreaTask: ("square_in_circle_gap_area",),
    GeometryTwoCirclesInRectangleGapAreaTask: ("two_circles_in_rectangle_gap_area",),
}


def _round1(value: float) -> float:
    return round(float(value) + 1e-9, 1)


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_tangent_packing_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(65001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_id in QUERY_IDS_BY_TASK[task_cls]
    assert out.answer_gt.type == "number"
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 3
    assert "Annotation format:" in out.prompt_variants["answer_and_annotation"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["scene_ir"]["scene_id"] == SCENE_ID
    assert trace["witness_symbolic"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_annotation"]["type"] == "bbox_set"

    radius = int(trace["execution_trace"]["radius"])
    square_side = int(trace["execution_trace"]["square_side"])
    container_width = int(trace["execution_trace"]["container_width"])
    container_height = int(trace["execution_trace"]["container_height"])

    assert square_side == 2 * radius
    if out.query_id in {
        "two_circles_in_rectangle_radius_from_width",
        "two_circles_in_rectangle_gap_area",
    }:
        assert container_width == 4 * radius
        assert container_height == 2 * radius

    if out.query_id in {
        "circle_in_square_radius_from_side",
        "circle_in_square_radius_from_gap_area",
    }:
        assert out.answer_gt.value == pytest.approx(float(radius))
    elif out.query_id in {
        "square_in_circle_side_from_radius",
        "square_in_circle_side_from_gap_area",
    }:
        assert out.answer_gt.value == pytest.approx(_round1(radius * math.sqrt(2.0)))
    elif out.query_id in {
        "two_circles_in_rectangle_radius_from_width",
        "two_circles_in_rectangle_radius_from_gap_area",
    }:
        assert out.answer_gt.value == pytest.approx(float(radius))
    elif out.query_id == "circle_in_square_gap_area":
        assert out.answer_gt.value == pytest.approx(_round1((2 * radius) ** 2 - math.pi * radius * radius))
    elif out.query_id == "square_in_circle_gap_area":
        assert out.answer_gt.value == pytest.approx(_round1(math.pi * radius * radius - 2 * radius * radius))
    elif out.query_id == "two_circles_in_rectangle_gap_area":
        assert out.answer_gt.value == pytest.approx(_round1((4 * radius) * (2 * radius) - 2 * math.pi * radius * radius))
    else:
        raise AssertionError(f"unexpected query id: {out.query_id}")


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_tangent_packing_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(65011, params=params, max_attempts=20)
    out_b = task.generate(65011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_tangent_packing_tasks_support_every_explicit_query(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            65021 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        assert out.query_id == query_id
        assert out.answer_gt.type == "number"
        assert out.trace_payload["query_spec"]["params"][
            "query_id_probabilities"
        ] == {query_id: 1.0}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_tangent_packing_tasks_sample_all_query_ids(task_cls) -> None:
    task = task_cls()
    seen = set()
    for index in range(18):
        out = task.generate(
            65041 + index,
            params={"_sampling_index": index},
            max_attempts=20,
        )
        seen.add(out.query_id)

    assert seen == set(QUERY_IDS_BY_TASK[task_cls])


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_tangent_packing_annotation_stays_inside_canvas(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            65061 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        width, height = out.image.size
        for x0, y0, x1, y1 in out.annotation_gt.value:
            assert 0.0 <= x0 < x1 <= float(width)
            assert 0.0 <= y0 < y1 <= float(height)
            assert (x1 - x0) > 8.0
            assert (y1 - y0) > 8.0


def test_tangent_packing_tasks_reject_unknown_query_id() -> None:
    for task_cls in TASK_CLASSES:
        task = task_cls()
        with pytest.raises(ValueError):
            task.generate(65031, params={"query_id": "not_a_query"}, max_attempts=20)
