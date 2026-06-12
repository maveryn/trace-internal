"""Contracts for refactored analytical measurement geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.angle_relations.algebraic_angle_value import GeometryAngleRelationsAlgebraicAngleValueTask
from trace.tasks.geometry.angle_relations.parallel_supplement_angle import (
    GeometryAngleRelationsParallelSupplementAngleTask,
)
from trace.tasks.geometry.angle_relations.triangle_exterior_angle import (
    GeometryAngleRelationsTriangleExteriorAngleTask,
)
from trace.tasks.geometry.composite_shape.composite_area_value import GeometryMeasurementCompositeAreaValueTask
from trace.tasks.geometry.composite_shape.house_outline_perimeter import GeometryMeasurementCompositePerimeterValueTask
from trace.tasks.geometry.composite_shape.tabbed_rectilinear_perimeter import GeometryCompositeShapeTabbedRectilinearPerimeterTask
from trace.tasks.geometry.triangle_relations.angle_bisector_segment_value_angle_bisector_base_length import GeometryAngleBisectorBaseLengthTask
from trace.tasks.geometry.triangle_relations.angle_bisector_segment_value_angle_bisector_split_length import GeometryAngleBisectorSplitLengthTask
from trace.tasks.geometry.triangle_relations.centroid_median_segment_value_centroid_vertex_segment_length import GeometryCentroidMedianVertexSegmentLengthTask
from trace.tasks.geometry.triangle_relations.centroid_median_segment_value_centroid_whole_median_length import GeometryCentroidMedianWholeMedianLengthTask
from trace.tasks.geometry.triangle_relations.parallel_section_base_length import GeometryTriangleRelationsParallelSectionBaseLengthTask
from trace.tasks.geometry.triangle_relations.parallel_section_cross_length import GeometryTriangleRelationsParallelSectionCrossLengthTask
from trace.tasks.geometry.triangle_relations.pythagorean_length_value_chained_rectangle_diagonal_length import GeometryPythagoreanLengthChainedRectangleDiagonalTask
from trace.tasks.geometry.triangle_relations.pythagorean_length_value_rectangle_triangle_shared_height_length import GeometryPythagoreanLengthRectangleTriangleSharedHeightTask
from trace.tasks.geometry.triangle_relations.similar_triangles_side_length import GeometryTriangleRelationsSimilarTrianglesSideLengthTask


TASK_CLASSES = (
    GeometryAngleRelationsParallelSupplementAngleTask,
    GeometryAngleRelationsTriangleExteriorAngleTask,
    GeometryAngleRelationsAlgebraicAngleValueTask,
    GeometryTriangleRelationsParallelSectionBaseLengthTask,
    GeometryTriangleRelationsParallelSectionCrossLengthTask,
    GeometryTriangleRelationsSimilarTrianglesSideLengthTask,
    GeometryPythagoreanLengthChainedRectangleDiagonalTask,
    GeometryPythagoreanLengthRectangleTriangleSharedHeightTask,
    GeometryAngleBisectorBaseLengthTask,
    GeometryAngleBisectorSplitLengthTask,
    GeometryCentroidMedianVertexSegmentLengthTask,
    GeometryCentroidMedianWholeMedianLengthTask,
    GeometryMeasurementCompositeAreaValueTask,
    GeometryMeasurementCompositePerimeterValueTask,
    GeometryCompositeShapeTabbedRectilinearPerimeterTask,
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
        assert out.annotation_gt.type == "keyed_point_map"
        assert 2 <= len(out.annotation_gt.value) <= 4
    elif task.scene_id == "composite_shape":
        assert out.annotation_gt.type == "keyed_bbox_map"
        assert 1 <= len(out.annotation_gt.value) <= 2
    else:
        assert out.annotation_gt.type == "bbox_set"
        assert 2 <= len(out.annotation_gt.value) <= 6
    assert "Annotation format:" in out.prompt_variants["answer_and_annotation"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == task.scene_id
    assert trace["scene_ir"]["scene_id"] == task.scene_id
    assert trace["witness_symbolic"]["scene_id"] == task.scene_id
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_annotation"]["type"] == out.annotation_gt.type


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_composite_measurement_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(44011, params=params, max_attempts=20)
    out_b = task.generate(44011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]


def test_composite_measurement_tasks_support_explicit_query_selection() -> None:
    task = GeometryPythagoreanLengthRectangleTriangleSharedHeightTask()
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
    tasks = (
        (GeometryTriangleRelationsSimilarTrianglesSideLengthTask(), "similar_triangles_side_length"),
        (GeometryTriangleRelationsParallelSectionBaseLengthTask(), "parallel_section_base_length"),
        (GeometryTriangleRelationsParallelSectionCrossLengthTask(), "parallel_section_cross_length"),
    )
    for task, query_id in tasks:
        out = task.generate(44025, params={"query_id": query_id, "case_index": 0}, max_attempts=20)
        assert out.scene_id == "triangle_relations"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert out.annotation_gt.type == "bbox_set"


def test_algebraic_triangle_cases_keep_annotation_inside_canvas() -> None:
    task = GeometryAngleRelationsAlgebraicAngleValueTask()
    for query_id in task.supported_query_ids:
        for case_index in range(6):
            out = task.generate(
                44041 + case_index,
                params={"query_id": query_id, "case_index": case_index},
                max_attempts=20,
            )
            width, height = out.image.size
            assert out.annotation_gt.type == "keyed_point_map"
            for x, y in out.annotation_gt.value.values():
                assert 0.0 <= x <= float(width)
                assert 0.0 <= y <= float(height)


@pytest.mark.parametrize(
    "task_cls",
    (
        GeometryAngleRelationsParallelSupplementAngleTask,
        GeometryAngleRelationsTriangleExteriorAngleTask,
        GeometryAngleRelationsAlgebraicAngleValueTask,
    ),
)
def test_angle_relations_public_annotation_uses_angle_primitives_not_label_boxes(task_cls) -> None:
    task = task_cls()
    for query_id in task.supported_query_ids:
        out = task.generate(44061, params={"query_id": query_id, "case_index": 0}, max_attempts=20)
        assert out.annotation_gt.type == "keyed_point_map"
        assert out.trace_payload["projected_annotation"]["type"] == "keyed_point_map"
        assert set(out.annotation_gt.value) == set(out.trace_payload["execution_trace"]["annotation_roles"])
        roles = out.trace_payload["execution_trace"]["annotation_roles"]
        assert all("label" not in str(role) for role in roles)
        assert all(str(role).isupper() and len(str(role)) == 3 for role in roles)
        assert "angle_label_bboxes" in out.trace_payload["render_map"]
        width, height = out.image.size
        scene_points = _scene_point_lookup(out.trace_payload)
        for point in out.annotation_gt.value.values():
            assert len(point) == 2
            assert 0.0 <= float(point[0]) <= float(width)
            assert 0.0 <= float(point[1]) <= float(height)
        for key, point in out.annotation_gt.value.items():
            if str(key).isupper() and len(str(key)) == 3:
                expected_vertex = scene_points[str(key)[1]]
                assert [float(point[0]), float(point[1])] == pytest.approx(expected_vertex, abs=1e-3)


def test_algebraic_angle_uses_varied_expression_forms() -> None:
    task = GeometryAngleRelationsAlgebraicAngleValueTask()
    expressions: set[str] = set()
    for query_id in task.supported_query_ids:
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
    task = GeometryAngleRelationsParallelSupplementAngleTask()
    with pytest.raises(ValueError):
        task.generate(44031, params={"query_id": "not_a_query"}, max_attempts=20)


@pytest.mark.parametrize(
    "task_cls, expected_keys",
    (
        (GeometryMeasurementCompositeAreaValueTask, {"outer_region"}),
        (GeometryMeasurementCompositePerimeterValueTask, {"target_boundary"}),
        (GeometryCompositeShapeTabbedRectilinearPerimeterTask, {"target_boundary"}),
    ),
)
def test_rectilinear_composite_public_annotation_uses_shape_primitives(task_cls, expected_keys) -> None:
    task = task_cls()
    for query_id in sorted({case.query_id for case in task.cases}):
        out = task.generate(44121, params={"query_id": query_id, "case_index": 0}, max_attempts=20)
        assert out.annotation_gt.type == "keyed_bbox_map"
        assert expected_keys.issubset(set(out.annotation_gt.value))
        assert out.trace_payload["projected_annotation"]["type"] == "keyed_bbox_map"
        assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
        assert set(out.annotation_gt.value) == set(out.trace_payload["execution_trace"]["annotation_roles"])
        assert all("label" not in str(role) for role in out.trace_payload["execution_trace"]["annotation_roles"])
        assert "measurement_label_bboxes" in out.trace_payload["render_map"]
