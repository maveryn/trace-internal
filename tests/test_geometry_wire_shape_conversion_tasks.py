"""Regression tests for wire-shape-conversion geometry tasks."""

from __future__ import annotations

import json

import pytest

from trace.core.taxonomy import lookup_task_taxonomy
from trace.tasks import TASK_REGISTRY, create_task
from trace.tasks.geometry.measurement.wire_shape_conversion import (
    FRAME_EDGE_ANNOTATION_KEYS,
    MISSING_DIMENSION_ANNOTATION_KEYS,
    QUERY_ID_SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE,
    QUERY_ID_TRAPEZOID_WIRE_LENGTH,
    QUERY_ID_TRAPEZOID_WIRE_TO_CUBE_FRAME,
    SCENE_ID,
    TASK_ID_FRAME_EDGE_LENGTH,
    TASK_ID_MISSING_DIMENSION,
    TASK_ID_WIRE_LENGTH,
    WIRE_LENGTH_ANNOTATION_KEYS,
    GeometryWireShapeConversionFrameEdgeLengthValueTask,
    GeometryWireShapeConversionMissingDimensionValueTask,
    GeometryWireShapeConversionWireLengthValueTask,
)


def _generate(seed: int, *, task_id: str = TASK_ID_WIRE_LENGTH, **params):
    task = create_task(task_id)
    return task.generate(seed, params=dict(params), max_attempts=80)


def test_wire_shape_conversion_tasks_registered() -> None:
    assert TASK_ID_WIRE_LENGTH in TASK_REGISTRY
    assert TASK_ID_FRAME_EDGE_LENGTH in TASK_REGISTRY
    assert TASK_ID_MISSING_DIMENSION in TASK_REGISTRY
    assert TASK_REGISTRY[TASK_ID_WIRE_LENGTH] is GeometryWireShapeConversionWireLengthValueTask
    assert TASK_REGISTRY[TASK_ID_FRAME_EDGE_LENGTH] is GeometryWireShapeConversionFrameEdgeLengthValueTask
    assert TASK_REGISTRY[TASK_ID_MISSING_DIMENSION] is GeometryWireShapeConversionMissingDimensionValueTask
    for task_id in (TASK_ID_WIRE_LENGTH, TASK_ID_FRAME_EDGE_LENGTH, TASK_ID_MISSING_DIMENSION):
        taxonomy = lookup_task_taxonomy(task_id)
        assert taxonomy is not None
        assert taxonomy.domain == "geometry"
        assert taxonomy.scene_id == SCENE_ID
        assert taxonomy.source_task_group == "measurement"


def test_trapezoid_wire_length_formula_and_annotation() -> None:
    out = _generate(
        20260720,
        query_id=QUERY_ID_TRAPEZOID_WIRE_LENGTH,
        wire_case=(4, 8, 5),
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == QUERY_ID_TRAPEZOID_WIRE_LENGTH
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 22 == execution["answer"]
    assert execution["source_shape"] == "isosceles_trapezoid_wire"
    assert execution["target_shape"] == ""
    assert execution["source_values"]["wire_length"] == 4 + 8 + 2 * 5
    assert execution["formula_family"] == "wire_shape_conversion"

    annotation = out.annotation_gt.value
    assert tuple(annotation.keys()) == WIRE_LENGTH_ANNOTATION_KEYS
    assert trace["projected_annotation"]["keyed_bbox_map"] == annotation
    assert trace["render_spec"]["prompt"]["prompt_variant"]["prompt_bundle_id"] == "geometry_wire_shape_conversion_v0"
    assert "task_variant" not in json.dumps(trace)
    _assert_bbox_map_inside_image(annotation, out.image.size, keys=WIRE_LENGTH_ANNOTATION_KEYS)


def test_trapezoid_to_cube_frame_formula_and_annotation() -> None:
    out = _generate(
        20260721,
        task_id=TASK_ID_FRAME_EDGE_LENGTH,
        query_id=QUERY_ID_TRAPEZOID_WIRE_TO_CUBE_FRAME,
        wire_case=(4, 8, 6),
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == QUERY_ID_TRAPEZOID_WIRE_TO_CUBE_FRAME
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 2 == execution["answer"]
    assert execution["source_shape"] == "isosceles_trapezoid_wire"
    assert execution["target_shape"] == "cube_frame"
    assert execution["source_values"]["wire_length"] == 24
    assert execution["target_values"]["edge"] == 2

    annotation = out.annotation_gt.value
    assert tuple(annotation.keys()) == FRAME_EDGE_ANNOTATION_KEYS
    assert trace["projected_annotation"]["keyed_bbox_map"] == annotation
    assert "task_variant" not in json.dumps(trace)
    _assert_bbox_map_inside_image(annotation, out.image.size, keys=FRAME_EDGE_ANNOTATION_KEYS)


def test_same_wire_circle_to_trapezoid_side_formula_and_annotation() -> None:
    out = _generate(
        20260722,
        task_id=TASK_ID_MISSING_DIMENSION,
        query_id=QUERY_ID_SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE,
        wire_case=(5, 8, 10),
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == QUERY_ID_SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 6 == execution["answer"]
    assert execution["source_shape"] == "circle_wire"
    assert execution["target_shape"] == "isosceles_trapezoid_wire"
    assert execution["source_values"]["wire_length"] == 30
    assert execution["target_values"]["side"] == 6

    annotation = out.annotation_gt.value
    assert tuple(annotation.keys()) == MISSING_DIMENSION_ANNOTATION_KEYS
    assert trace["projected_annotation"]["keyed_bbox_map"] == annotation
    assert "task_variant" not in json.dumps(trace)
    _assert_bbox_map_inside_image(annotation, out.image.size, keys=MISSING_DIMENSION_ANNOTATION_KEYS)


def test_wire_shape_conversion_generation_is_deterministic() -> None:
    params = {
        "query_id": QUERY_ID_TRAPEZOID_WIRE_LENGTH,
        "wire_case": (6, 10, 7),
    }
    first = _generate(314200, **params)
    second = _generate(314200, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt.value == 30
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
    assert first.image.tobytes() == second.image.tobytes()


def test_wire_shape_conversion_rejects_invalid_params() -> None:
    task = create_task(TASK_ID_WIRE_LENGTH)
    with pytest.raises(ValueError):
        task.generate(1, params={"query_id": "bad_query"}, max_attempts=1)
    frame_task = create_task(TASK_ID_FRAME_EDGE_LENGTH)
    with pytest.raises(ValueError):
        frame_task.generate(
            1,
            params={"query_id": QUERY_ID_TRAPEZOID_WIRE_TO_CUBE_FRAME, "wire_case": (4, 8, 5)},
            max_attempts=1,
        )
    missing_task = create_task(TASK_ID_MISSING_DIMENSION)
    with pytest.raises(ValueError):
        missing_task.generate(
            1,
            params={"query_id": QUERY_ID_SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE, "wire_case": (5, 8, 9)},
            max_attempts=1,
        )


def _assert_bbox_map_inside_image(
    annotation: dict[str, list[float]],
    image_size: tuple[int, int],
    *,
    keys: tuple[str, ...],
) -> None:
    width, height = image_size
    for key in keys:
        bbox = annotation[key]
        assert isinstance(bbox, list)
        assert len(bbox) == 4
        x0, y0, x1, y1 = [float(value) for value in bbox]
        assert 0.0 <= x0 < x1 <= float(width)
        assert 0.0 <= y0 < y1 <= float(height)
