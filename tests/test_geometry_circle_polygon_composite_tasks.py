"""Regression tests for circle-polygon composite geometry tasks."""

from __future__ import annotations

import json

import pytest

from trace.tasks import TASK_REGISTRY
from trace.tasks.geometry.measurement.circle_polygon_composite import (
    QUERY_ID,
    SQUARE_CIRCLE_TANGENT_ANGLE_QUERY_IDS,
    SQUARE_CIRCLE_TANGENT_ANGLE_TASK_ID,
    TASK_ID,
    GeometryCirclePolygonCompositeSquareCircleTangentAngleValueTask,
    GeometryCirclePolygonCompositeTangentialQuadrilateralSideSumValueTask,
)


def _generate(seed: int, **params):
    task = GeometryCirclePolygonCompositeTangentialQuadrilateralSideSumValueTask()
    return task.generate(seed, params=dict(params), max_attempts=80)


def _generate_angle(seed: int, **params):
    task = GeometryCirclePolygonCompositeSquareCircleTangentAngleValueTask()
    return task.generate(seed, params=dict(params), max_attempts=80)


def test_circle_polygon_composite_registered_public_task() -> None:
    assert TASK_ID in TASK_REGISTRY
    assert TASK_REGISTRY[TASK_ID] is GeometryCirclePolygonCompositeTangentialQuadrilateralSideSumValueTask
    assert SQUARE_CIRCLE_TANGENT_ANGLE_TASK_ID in TASK_REGISTRY
    assert TASK_REGISTRY[SQUARE_CIRCLE_TANGENT_ANGLE_TASK_ID] is GeometryCirclePolygonCompositeSquareCircleTangentAngleValueTask


@pytest.mark.parametrize(
    ("target_pair", "expected"),
    [
        ("AB_CD", 18),
        ("BC_DA", 18),
    ],
)
def test_tangential_quadrilateral_side_sum_formula(target_pair: str, expected: int) -> None:
    out = _generate(
        20260604,
        query_id=QUERY_ID,
        target_pair=target_pair,
        tangent_lengths=(3, 4, 5, 6),
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == "circle_polygon_composite"
    assert out.query_id == QUERY_ID
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == expected == execution["answer"]
    side_lengths = execution["side_lengths"]
    assert side_lengths["AB"] + side_lengths["CD"] == side_lengths["BC"] + side_lengths["DA"]
    assert execution["answer"] == side_lengths[target_pair[:2]] + side_lengths[target_pair[-2:]]

    assert out.annotation_gt.type == "keyed_point_map"
    annotation = out.annotation_gt.value
    assert set(annotation) == {
        "vertex_A",
        "vertex_B",
        "vertex_C",
        "vertex_D",
        "tangent_AB",
        "tangent_BC",
        "tangent_CD",
        "tangent_DA",
        "incircle_center",
    }
    _assert_point_map_inside_image(annotation, out.image.size)
    assert "task_variant" not in json.dumps(trace)


def test_tangential_quadrilateral_generation_is_deterministic() -> None:
    params = {
        "query_id": QUERY_ID,
        "target_pair": "AB_CD",
        "tangent_lengths": (5, 6, 7, 8),
    }
    first = _generate(314159, **params)
    second = _generate(314159, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]


def test_tangential_quadrilateral_rejects_invalid_params() -> None:
    task = GeometryCirclePolygonCompositeTangentialQuadrilateralSideSumValueTask()
    with pytest.raises(ValueError):
        task.generate(1, params={"query_id": "bad_query"}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(1, params={"target_pair": "AB_BC"}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(1, params={"tangent_lengths": (3, 4, 5)}, max_attempts=1)


@pytest.mark.parametrize("query_id", SQUARE_CIRCLE_TANGENT_ANGLE_QUERY_IDS)
@pytest.mark.parametrize("side_sign", [-1, 1])
def test_square_circle_tangent_angle_contract(query_id: str, side_sign: int) -> None:
    out = _generate_angle(
        20260606,
        query_id=query_id,
        target_angle=45,
        side_sign=side_sign,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == "circle_polygon_composite"
    assert out.query_id == query_id
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 45 == execution["answer"]
    assert execution["known_angle_degrees"] == execution["target_angle_degrees"] == 45
    assert execution["side_sign"] == side_sign

    assert out.annotation_gt.type == "keyed_point_map"
    annotation = out.annotation_gt.value
    assert set(annotation) == {
        "shape_corner_A",
        "shape_corner_B",
        "shape_corner_C",
        "shape_corner_D",
        "circle_center",
        "tangent_point",
        "known_angle_vertex",
        "known_angle_reference_point",
        "target_angle_vertex",
        "target_reference_point",
    }
    assert annotation["target_angle_vertex"] == annotation["circle_center"]
    _assert_point_map_inside_image(annotation, out.image.size)
    assert "task_variant" not in json.dumps(trace)


def test_square_circle_tangent_angle_generation_is_deterministic() -> None:
    params = {
        "query_id": "square_semicircle_tangent_angle",
        "target_angle": 60,
        "side_sign": 1,
    }
    first = _generate_angle(271828, **params)
    second = _generate_angle(271828, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]


def test_square_circle_tangent_angle_rejects_invalid_params() -> None:
    task = GeometryCirclePolygonCompositeSquareCircleTangentAngleValueTask()
    with pytest.raises(ValueError):
        task.generate(1, params={"query_id": "bad_query"}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(1, params={"target_angle": 17}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(1, params={"side_sign": 0}, max_attempts=1)


def _assert_point_map_inside_image(annotation: dict[str, list[float]], image_size: tuple[int, int]) -> None:
    width, height = image_size
    for point in annotation.values():
        assert isinstance(point, list)
        assert len(point) == 2
        x, y = [float(value) for value in point]
        assert 0.0 <= x <= float(width)
        assert 0.0 <= y <= float(height)
