"""Contracts for refactored analytical measurement geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.measurement.composite_measurement import (
    GeometryMeasurementAlgebraicAngleValueTask,
    GeometryMeasurementAngleChainValueTask,
    GeometryMeasurementAngleBisectorSegmentValueTask,
    GeometryMeasurementCentroidMedianSegmentValueTask,
    GeometryMeasurementCompositeAreaValueTask,
    GeometryMeasurementCompositePerimeterValueTask,
    GeometryMeasurementParallelSectionLengthValueTask,
    GeometryMeasurementPythagoreanLengthValueTask,
)


TASK_CLASSES = (
    GeometryMeasurementAngleChainValueTask,
    GeometryMeasurementAlgebraicAngleValueTask,
    GeometryMeasurementParallelSectionLengthValueTask,
    GeometryMeasurementPythagoreanLengthValueTask,
    GeometryMeasurementAngleBisectorSegmentValueTask,
    GeometryMeasurementCentroidMedianSegmentValueTask,
    GeometryMeasurementCompositeAreaValueTask,
    GeometryMeasurementCompositePerimeterValueTask,
)


def _scene_point_lookup(trace_payload) -> dict[str, list[float]]:
    points: dict[str, list[float]] = {}
    for entity in trace_payload["scene_ir"]["entities"]:
        entity_points = entity.get("points")
        if isinstance(entity_points, dict):
            for label, point in entity_points.items():
                points[str(label)] = [float(point[0]), float(point[1])]
    return points


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_composite_measurement_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(44001, params={}, max_attempts=20)

    assert out.scene_id == task.scene_id
    assert out.query_id
    assert out.answer_gt.type == "integer"
    if task.scene_id == "angle_relations":
        assert out.evidence_gt.type == "keyed_point_map"
        assert 2 <= len(out.evidence_gt.value) <= 4
    elif task.scene_id == "composite_shape":
        assert out.evidence_gt.type == "keyed_bbox_map"
        assert 1 <= len(out.evidence_gt.value) <= 2
    else:
        assert out.evidence_gt.type == "bbox_set"
        assert 2 <= len(out.evidence_gt.value) <= 6
    assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == task.scene_id
    assert trace["scene_ir"]["scene_id"] == task.scene_id
    assert trace["witness_symbolic"]["scene_id"] == task.scene_id
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_evidence"]["type"] == out.evidence_gt.type


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_composite_measurement_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(44011, params=params, max_attempts=20)
    out_b = task.generate(44011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]


def test_composite_measurement_tasks_support_explicit_query_selection() -> None:
    task = GeometryMeasurementPythagoreanLengthValueTask()
    out = task.generate(
        44021,
        params={"query_id": "rectangle_triangle_shared_height_length", "case_index": 0},
        max_attempts=20,
    )

    assert out.query_id == "rectangle_triangle_shared_height_length"
    assert out.answer_gt.value == 15
    assert out.trace_payload["query_spec"]["params"]["query_id_probabilities"] == {
        "rectangle_triangle_shared_height_length": 1.0
    }


def test_parallel_section_scale_task_supports_every_query() -> None:
    task = GeometryMeasurementParallelSectionLengthValueTask()
    for query_id in ("similar_triangles_side_length", "parallel_section_base_length", "parallel_section_cross_length"):
        out = task.generate(44025, params={"query_id": query_id, "case_index": 0}, max_attempts=20)
        assert out.scene_id == "triangle_relations"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"


def test_algebraic_triangle_cases_keep_evidence_inside_canvas() -> None:
    task = GeometryMeasurementAlgebraicAngleValueTask()
    for query_id in ("triangle_single_extension_expression", "triangle_double_extension_expression"):
        for case_index in range(6):
            out = task.generate(
                44041 + case_index,
                params={"query_id": query_id, "case_index": case_index},
                max_attempts=20,
            )
            width, height = out.image.size
            assert out.evidence_gt.type == "keyed_point_map"
            for x, y in out.evidence_gt.value.values():
                assert 0.0 <= x <= float(width)
                assert 0.0 <= y <= float(height)


@pytest.mark.parametrize("task_cls", (GeometryMeasurementAngleChainValueTask, GeometryMeasurementAlgebraicAngleValueTask))
def test_angle_relations_public_evidence_uses_angle_primitives_not_label_boxes(task_cls) -> None:
    task = task_cls()
    for query_id in sorted({case.query_id for case in task.cases}):
        out = task.generate(44061, params={"query_id": query_id, "case_index": 0}, max_attempts=20)
        assert out.evidence_gt.type == "keyed_point_map"
        assert out.trace_payload["projected_evidence"]["type"] == "keyed_point_map"
        assert set(out.evidence_gt.value) == set(out.trace_payload["execution_trace"]["evidence_roles"])
        roles = out.trace_payload["execution_trace"]["evidence_roles"]
        assert all("label" not in str(role) for role in roles)
        assert all(str(role).isupper() and len(str(role)) == 3 for role in roles)
        assert "angle_label_bboxes" in out.trace_payload["render_map"]
        width, height = out.image.size
        scene_points = _scene_point_lookup(out.trace_payload)
        for point in out.evidence_gt.value.values():
            assert len(point) == 2
            assert 0.0 <= float(point[0]) <= float(width)
            assert 0.0 <= float(point[1]) <= float(height)
        for key, point in out.evidence_gt.value.items():
            if str(key).isupper() and len(str(key)) == 3:
                expected_vertex = scene_points[str(key)[1]]
                assert [float(point[0]), float(point[1])] == pytest.approx(expected_vertex, abs=1e-3)


def test_algebraic_angle_uses_varied_expression_forms() -> None:
    task = GeometryMeasurementAlgebraicAngleValueTask()
    expressions: set[str] = set()
    for query_id in ("triangle_single_extension_expression", "triangle_double_extension_expression"):
        for case_index in range(6):
            out = task.generate(
                44101 + case_index,
                params={"query_id": query_id, "case_index": case_index},
                max_attempts=20,
            )
            trace = out.trace_payload["execution_trace"]
            expressions.add(trace["expression_angle_ABC"])
            expressions.add(trace["expression_exterior_BCD"])

    assert any(expr.startswith("x+") for expr in expressions)
    assert any(expr.startswith("2x") for expr in expressions)
    assert any(expr.startswith("3x") for expr in expressions)
    assert any(expr.startswith("4x") for expr in expressions)


def test_composite_measurement_tasks_reject_unknown_query_id() -> None:
    task = GeometryMeasurementAngleChainValueTask()
    with pytest.raises(ValueError):
        task.generate(44031, params={"query_id": "not_a_query"}, max_attempts=20)


@pytest.mark.parametrize(
    "task_cls, expected_keys",
    (
        (GeometryMeasurementCompositeAreaValueTask, {"target_region"}),
        (GeometryMeasurementCompositePerimeterValueTask, {"target_boundary"}),
    ),
)
def test_rectilinear_composite_public_evidence_uses_shape_primitives(task_cls, expected_keys) -> None:
    task = task_cls()
    for query_id in sorted({case.query_id for case in task.cases}):
        out = task.generate(44121, params={"query_id": query_id, "case_index": 0}, max_attempts=20)
        assert out.evidence_gt.type == "keyed_bbox_map"
        assert expected_keys.issubset(set(out.evidence_gt.value))
        assert out.trace_payload["projected_evidence"]["type"] == "keyed_bbox_map"
        assert out.trace_payload["projected_evidence"]["keyed_bbox_map"] == out.evidence_gt.value
        assert set(out.evidence_gt.value) == set(out.trace_payload["execution_trace"]["evidence_roles"])
        assert all("label" not in str(role) for role in out.trace_payload["execution_trace"]["evidence_roles"])
        assert "measurement_label_bboxes" in out.trace_payload["render_map"]
