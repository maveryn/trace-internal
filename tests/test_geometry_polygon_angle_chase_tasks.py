"""Regression tests for polygon angle-chase geometry tasks."""

from __future__ import annotations

import json

import pytest

from trace.tasks import TASK_REGISTRY
from trace.tasks.geometry.polygon_angle_chase.parallel_line_angle_value import GeometryPolygonAngleChaseParallelLineAngleValueTask
from trace.tasks.geometry.polygon_angle_chase.polygon_interior_angle_value import (
    PARALLEL_TASK_ID,
    SYMMETRY_TASK_ID,
    TASK_ID,
    GeometryPolygonAngleChaseInteriorAngleValueTask,
)
from trace.tasks.geometry.polygon_angle_chase.symmetry_angle_value import GeometryPolygonAngleChaseSymmetryAngleValueTask


def _generate(seed: int, **params):
    task = GeometryPolygonAngleChaseInteriorAngleValueTask()
    return task.generate(seed, params=dict(params), max_attempts=80)


def _generate_parallel(seed: int, **params):
    task = GeometryPolygonAngleChaseParallelLineAngleValueTask()
    return task.generate(seed, params=dict(params), max_attempts=120)


def _generate_symmetry(seed: int, **params):
    task = GeometryPolygonAngleChaseSymmetryAngleValueTask()
    return task.generate(seed, params=dict(params), max_attempts=160)


def test_polygon_angle_chase_registered_public_task() -> None:
    assert TASK_ID in TASK_REGISTRY
    assert TASK_REGISTRY[TASK_ID] is GeometryPolygonAngleChaseInteriorAngleValueTask
    assert PARALLEL_TASK_ID in TASK_REGISTRY
    assert TASK_REGISTRY[PARALLEL_TASK_ID] is GeometryPolygonAngleChaseParallelLineAngleValueTask
    assert SYMMETRY_TASK_ID in TASK_REGISTRY
    assert TASK_REGISTRY[SYMMETRY_TASK_ID] is GeometryPolygonAngleChaseSymmetryAngleValueTask


@pytest.mark.parametrize(
    ("query_id", "side_count", "polygon_sum"),
    [
        ("triangle_interior_angle", 3, 180),
        ("quadrilateral_interior_angle", 4, 360),
        ("pentagon_interior_angle", 5, 540),
        ("hexagon_interior_angle", 6, 720),
    ],
)
@pytest.mark.parametrize("label_style", ["target_expression_mixed", "all_expression"])
def test_polygon_angle_chase_contract_branches(query_id: str, side_count: int, polygon_sum: int, label_style: str) -> None:
    out = _generate(20260604, query_id=query_id, label_style=label_style)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == "polygon_angle_chase"
    assert out.query_id == query_id
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == execution["numeric_angles"][execution["target_index"]]
    assert sum(execution["numeric_angles"]) == polygon_sum
    assert len(execution["numeric_angles"]) == side_count
    assert execution["label_style"] == label_style
    expression_labels = [label for label in execution["display_angle_labels"] if "x" in label]
    numeric_labels = [label for label in execution["display_angle_labels"] if "x" not in label]
    assert "x" in execution["display_angle_labels"][execution["target_index"]]
    if label_style == "all_expression":
        assert len(expression_labels) == side_count
        assert not numeric_labels
    else:
        assert len(expression_labels) == (2 if side_count <= 4 else 3)
        assert len(numeric_labels) == side_count - len(expression_labels)
    assert execution["x"] > 0
    assert execution["answer"] == execution["expression_values"][execution["target_vertex"]]

    assert out.annotation_gt.type == "keyed_point_map"
    annotation = out.annotation_gt.value
    assert set(annotation) == {"target_vertex"} | {
        f"known_angle_{index}_vertex" for index in range(1, side_count)
    }
    width, height = out.image.size
    for point in annotation.values():
        assert isinstance(point, list)
        assert len(point) == 2
        assert 0.0 <= float(point[0]) <= width
        assert 0.0 <= float(point[1]) <= height

    vertices = {
        tuple(round(float(coord), 3) for coord in point)
        for point in trace["render_map"]["polygon_vertices"].values()
    }
    assert {tuple(point) for point in annotation.values()} <= vertices
    assert "task_variant" not in json.dumps(trace)


def test_polygon_angle_chase_generation_is_deterministic() -> None:
    params = {"query_id": "pentagon_interior_angle", "label_style": "all_expression"}
    first = _generate(314159, **params)
    second = _generate(314159, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]


@pytest.mark.parametrize("relation_id", ["corresponding_same", "supplementary"])
def test_parallel_line_angle_single_transversal_formula(relation_id: str) -> None:
    out = _generate_parallel(20260604, query_id="single_transversal_chain", relation_id=relation_id)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    support_angle = int(execution["support_angle"])
    expected = support_angle if relation_id == "corresponding_same" else 180 - support_angle

    assert out.scene_id == "polygon_angle_chase"
    assert out.query_id == "single_transversal_chain"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == expected == execution["answer"]
    assert execution["relation_id"] == relation_id

    assert out.annotation_gt.type == "keyed_point_map"
    annotation = out.annotation_gt.value
    assert set(annotation) == {"target_vertex", "support_vertex", "bridge_vertex"}
    intersections = {
        key: tuple(float(coord) for coord in point)
        for key, point in trace["render_map"]["intersections"].items()
    }
    for key, point in annotation.items():
        assert tuple(float(coord) for coord in point) == intersections[key]
    assert "task_variant" not in json.dumps(trace)


def test_parallel_line_angle_two_transversal_formula() -> None:
    out = _generate_parallel(12345, query_id="two_transversal_angle_sum")
    trace = out.trace_payload
    execution = trace["execution_trace"]
    support_angle_1, support_angle_2 = [int(value) for value in execution["support_angles"]]
    expected = 180 - support_angle_1 - support_angle_2

    assert out.scene_id == "polygon_angle_chase"
    assert out.query_id == "two_transversal_angle_sum"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == expected == execution["answer"]
    assert execution["relation_id"] == "angle_sum"

    assert out.annotation_gt.type == "keyed_point_map"
    annotation = out.annotation_gt.value
    assert set(annotation) == {"target_vertex", "support_vertex_1", "support_vertex_2"}
    width, height = out.image.size
    for point in annotation.values():
        assert len(point) == 2
        assert 0.0 <= float(point[0]) <= width
        assert 0.0 <= float(point[1]) <= height
    assert "task_variant" not in json.dumps(trace)


def test_parallel_line_angle_generation_is_deterministic() -> None:
    params = {"query_id": "two_transversal_angle_sum"}
    first = _generate_parallel(271828, **params)
    second = _generate_parallel(271828, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]


@pytest.mark.parametrize(
    ("query_id", "support_angle", "expected", "expected_keys"),
    [
        (
            "rectangle_diagonal_angle",
            35,
            55,
            {"target_vertex", "known_angle_vertex", "diagonal_endpoint_1", "diagonal_endpoint_2"},
        ),
        (
            "reflection_axis_angle",
            35,
            70,
            {"target_vertex", "support_vertex", "axis_point_1", "axis_point_2"},
        ),
    ],
)
def test_symmetry_angle_direct_formulas(
    query_id: str,
    support_angle: int,
    expected: int,
    expected_keys: set[str],
) -> None:
    out = _generate_symmetry(20260604, query_id=query_id, support_angle=support_angle)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == "polygon_angle_chase"
    assert out.query_id == query_id
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == expected == execution["answer"]
    assert execution["support_angle"] == support_angle

    assert out.annotation_gt.type == "keyed_point_map"
    annotation = out.annotation_gt.value
    assert set(annotation) == expected_keys
    width, height = out.image.size
    for point in annotation.values():
        assert len(point) == 2
        assert 0.0 <= float(point[0]) <= width
        assert 0.0 <= float(point[1]) <= height
    assert "task_variant" not in json.dumps(trace)


@pytest.mark.parametrize(
    ("target_role", "support_angle", "expected", "relation_id"),
    [
        ("base_angle", 50, 65, "isosceles_base_from_apex"),
        ("apex_angle", 55, 70, "isosceles_apex_from_base"),
    ],
)
def test_symmetry_angle_isosceles_formulas(
    target_role: str,
    support_angle: int,
    expected: int,
    relation_id: str,
) -> None:
    out = _generate_symmetry(
        123456,
        query_id="isosceles_base_angle_chain",
        target_role=target_role,
        support_angle=support_angle,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == "polygon_angle_chase"
    assert out.query_id == "isosceles_base_angle_chain"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == expected == execution["answer"]
    assert execution["relation_id"] == relation_id
    assert execution["target_role"] == target_role

    assert out.annotation_gt.type == "keyed_point_map"
    assert set(out.annotation_gt.value) == {
        "target_vertex",
        "support_vertex",
        "apex_vertex",
        "base_left_vertex",
        "base_right_vertex",
    }
    assert "task_variant" not in json.dumps(trace)


def test_symmetry_angle_generation_is_deterministic() -> None:
    params = {"query_id": "reflection_axis_angle", "support_angle": 40}
    first = _generate_symmetry(3141592, **params)
    second = _generate_symmetry(3141592, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
