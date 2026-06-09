"""Regression tests for circle centerline overlap geometry tasks."""

from __future__ import annotations

import json

import pytest

from trace.tasks import TASK_REGISTRY, create_task
from trace.tasks.geometry.measurement.circle_centerline_overlap import (
    BOUNDARY_PAIRS,
    BOUNDARY_TARGET_ROLES,
    QUERY_ID_BOUNDARY_SEGMENT,
    QUERY_ID_CENTER_DISTANCE,
    SCENE_ID,
    TASK_ID,
    GeometryCircleCenterlineOverlapSegmentLengthValueTask,
    _CASES,
    _segment_length,
)


def _generate(seed: int, **params):
    task = create_task(TASK_ID)
    return task.generate(seed, params=dict(params), max_attempts=80)


def test_circle_centerline_overlap_task_registered() -> None:
    assert TASK_ID in TASK_REGISTRY
    assert TASK_REGISTRY[TASK_ID] is GeometryCircleCenterlineOverlapSegmentLengthValueTask


@pytest.mark.parametrize("query_id", [QUERY_ID_CENTER_DISTANCE, QUERY_ID_BOUNDARY_SEGMENT])
def test_circle_centerline_overlap_queries_emit_keyed_point_annotation(query_id: str) -> None:
    out = _generate(20260701, query_id=query_id)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == query_id
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == execution["answer"]
    assert out.annotation_gt.type == "keyed_point_map"
    assert trace["projected_annotation"]["keyed_point_map"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_keyed_point_map"] == out.annotation_gt.value
    assert trace["render_spec"]["prompt"]["prompt_variant"]["prompt_bundle_id"] == "geometry_circle_centerline_overlap_v0"
    assert "task_variant" not in json.dumps(trace)
    _assert_point_map_inside_image(out.annotation_gt.value, out.image.size)


def test_circle_centerline_overlap_center_distance_formula() -> None:
    out = _generate(
        20260702,
        query_id=QUERY_ID_CENTER_DISTANCE,
        overlap_case=(5, 15, 5, 2, 2),
        label_mode="diameter",
    )
    execution = out.trace_payload["execution_trace"]

    assert out.answer_gt.value == 36
    assert execution["distance_ab"] == execution["radius_a"] + execution["radius_b"] - execution["overlap_ab"]
    assert execution["distance_bc"] == execution["radius_b"] + execution["radius_c"] - execution["overlap_bc"]
    assert execution["answer"] == execution["distance_ac"] == execution["distance_ab"] + execution["distance_bc"]
    assert tuple(out.annotation_gt.value.keys()) == (
        "center_a",
        "center_b",
        "center_c",
        "overlap_ab_left",
        "overlap_ab_right",
        "overlap_bc_left",
        "overlap_bc_right",
    )


@pytest.mark.parametrize("boundary_pair", BOUNDARY_PAIRS)
@pytest.mark.parametrize("boundary_target_role", BOUNDARY_TARGET_ROLES)
def test_circle_centerline_overlap_boundary_segment_formula(boundary_pair: str, boundary_target_role: str) -> None:
    out = _generate(
        20260703,
        query_id=QUERY_ID_BOUNDARY_SEGMENT,
        overlap_case=(6, 14, 8, 3, 4),
        boundary_pair=boundary_pair,
        boundary_target_role=boundary_target_role,
    )
    execution = out.trace_payload["execution_trace"]
    expected = _segment_length(_CASES[1], boundary_pair, boundary_target_role)

    assert out.answer_gt.value == expected
    assert execution["answer"] == expected
    assert execution["boundary_pair"] == boundary_pair
    assert execution["boundary_target_role"] == boundary_target_role
    assert tuple(out.annotation_gt.value.keys()) == (
        "target_start",
        "target_end",
        "known_segment_start",
        "known_segment_end",
        "center_a",
        "center_b",
        "center_c",
    )


def test_circle_centerline_overlap_case_bank_constraints_and_support() -> None:
    center_answers = {case.distance_ac for case in _CASES}
    boundary_answers = {
        _segment_length(case, pair, role)
        for case in _CASES
        for pair in BOUNDARY_PAIRS
        for role in BOUNDARY_TARGET_ROLES
    }
    assert len(center_answers) >= 7
    assert len(boundary_answers) >= 7
    assert min(center_answers) > 0
    assert min(boundary_answers) >= 3
    for case in _CASES:
        assert abs(case.radius_a - case.radius_b) + 1 < case.distance_ab < case.radius_a + case.radius_b
        assert abs(case.radius_b - case.radius_c) + 1 < case.distance_bc < case.radius_b + case.radius_c
        assert case.distance_ac > case.radius_a + case.radius_c + 1


def test_circle_centerline_overlap_generation_is_deterministic() -> None:
    params = {
        "query_id": QUERY_ID_BOUNDARY_SEGMENT,
        "overlap_case": (8, 16, 7, 4, 3),
        "label_mode": "radius",
        "boundary_pair": "BC",
        "boundary_target_role": "left_boundary_to_right_center",
    }
    first = _generate(314159, **params)
    second = _generate(314159, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
    assert first.image.tobytes() == second.image.tobytes()


def test_circle_centerline_overlap_rejects_invalid_params() -> None:
    task = create_task(TASK_ID)
    with pytest.raises(ValueError):
        task.generate(1, params={"query_id": "bad_query"}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(1, params={"label_mode": "circumference"}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(1, params={"boundary_pair": "AC"}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(1, params={"boundary_target_role": "whole_diameter"}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(1, params={"overlap_case": (4, 13, 9, 3, 2)}, max_attempts=1)


def _assert_point_map_inside_image(annotation: dict[str, list[float]], image_size: tuple[int, int]) -> None:
    width, height = image_size
    for point in annotation.values():
        assert isinstance(point, list)
        assert len(point) == 2
        x, y = [float(value) for value in point]
        assert 0.0 <= x <= float(width)
        assert 0.0 <= y <= float(height)
