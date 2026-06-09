"""Contract tests for coordinate-composite geometry tasks."""

from __future__ import annotations

import json

import pytest

from trace.tasks import TASK_REGISTRY, create_task
from trace.tasks.geometry.coordinate.composite_intersections import (
    QUERY_IDS,
    SCENE_ID,
    TASK_ID,
    GeometryCoordinateCompositeIntersectionPointCountTask,
)


def _generate(seed: int, **params):
    task = create_task(TASK_ID)
    return task.generate(seed, params=dict(params), max_attempts=20)


def test_coordinate_composite_intersection_count_registered() -> None:
    assert TASK_ID in TASK_REGISTRY
    assert TASK_REGISTRY[TASK_ID] is GeometryCoordinateCompositeIntersectionPointCountTask


@pytest.mark.parametrize("query_id", QUERY_IDS)
def test_coordinate_composite_intersection_count_contract(query_id: str) -> None:
    out = _generate(20260620, query_id=query_id)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == query_id
    assert trace["scene_id"] == SCENE_ID
    assert trace["query_id"] == query_id
    assert trace["query_spec"]["query_id"] == query_id
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == len(execution["intersection_points_graph"])
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == out.answer_gt.value
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_point_set"] == out.annotation_gt.value
    assert trace["scene_ir"]["scene_id"] == SCENE_ID
    assert trace["render_spec"]["graph_paper_grid"]["spacing_px"] > 0
    assert trace["prompt"]["prompt_variant"]["prompt_bundle_id"] == "geometry_coordinate_composite_v0"
    assert "task_variant" not in json.dumps(trace)

    width, height = out.image.size
    for point in out.annotation_gt.value:
        assert len(point) == 2
        x_value, y_value = [float(value) for value in point]
        assert 0.0 <= x_value <= float(width)
        assert 0.0 <= y_value <= float(height)


def test_coordinate_composite_zero_intersection_uses_empty_annotation() -> None:
    out = _generate(
        20260621,
        query_id="line_circle_intersection_count",
        target_count=0,
    )
    assert out.answer_gt.value == 0
    assert out.annotation_gt.value == []
    assert out.trace_payload["projected_annotation"]["point_set"] == []


def test_coordinate_composite_is_deterministic() -> None:
    params = {"query_id": "circle_polygon_intersection_count", "target_count": 2, "transform": "rotate90"}
    first = _generate(20260622, **params)
    second = _generate(20260622, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
    assert first.image.tobytes() == second.image.tobytes()


def test_coordinate_composite_rejects_invalid_params() -> None:
    task = create_task(TASK_ID)
    with pytest.raises(ValueError):
        task.generate(1, params={"query_id": "bad_query"}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(1, params={"query_id": "circle_circle_intersection_count", "target_count": 5}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(1, params={"query_id": "line_circle_intersection_count", "transform": "skew"}, max_attempts=1)
