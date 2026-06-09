"""Regression tests for circle-pair tangent geometry tasks."""

from __future__ import annotations

import json

import pytest

from trace.tasks import TASK_REGISTRY, create_task
from trace.tasks.geometry.measurement.circle_pair_tangents import (
    ANNOTATION_KEYS,
    QUERY_ID,
    QUERY_ID_CENTER_DISTANCE,
    QUERY_ID_COMMON_TANGENT_LENGTH,
    SCENE_ID,
    TASK_ID,
    TASK_ID_CENTER_DISTANCE,
    TASK_ID_COMMON_TANGENT_LENGTH,
    GeometryCirclePairTangentsCenterDistanceValueTask,
    GeometryCirclePairTangentsCommonTangentLengthValueTask,
)


def _generate(seed: int, *, task_id: str = TASK_ID, **params):
    task = create_task(task_id)
    return task.generate(seed, params=dict(params), max_attempts=80)


def test_circle_pair_tangent_length_registered() -> None:
    assert TASK_ID_COMMON_TANGENT_LENGTH in TASK_REGISTRY
    assert TASK_REGISTRY[TASK_ID_COMMON_TANGENT_LENGTH] is GeometryCirclePairTangentsCommonTangentLengthValueTask
    assert TASK_ID_CENTER_DISTANCE in TASK_REGISTRY
    assert TASK_REGISTRY[TASK_ID_CENTER_DISTANCE] is GeometryCirclePairTangentsCenterDistanceValueTask


@pytest.mark.parametrize(
    ("task_id", "query_id", "expected_answer", "formula_family", "unknown_role"),
    [
        (
            TASK_ID_COMMON_TANGENT_LENGTH,
            QUERY_ID_COMMON_TANGENT_LENGTH,
            12,
            "external_common_tangent_length",
            "tangent_length",
        ),
        (
            TASK_ID_CENTER_DISTANCE,
            QUERY_ID_CENTER_DISTANCE,
            13,
            "external_common_tangent_center_distance",
            "center_distance",
        ),
    ],
)
@pytest.mark.parametrize("larger_side", ["left", "right"])
@pytest.mark.parametrize("tangent_side", ["above", "below"])
def test_circle_pair_tangent_formula_and_annotation(
    task_id: str,
    query_id: str,
    expected_answer: int,
    formula_family: str,
    unknown_role: str,
    larger_side: str,
    tangent_side: str,
) -> None:
    out = _generate(
        20260623,
        task_id=task_id,
        query_id=query_id,
        tangent_case=(3, 8, 13, 12),
        larger_circle_side=larger_side,
        tangent_side=tangent_side,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == query_id
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == expected_answer == execution["answer"]
    assert execution["center_distance"] == 13
    assert execution["radius_difference"] == 5
    assert execution["tangent_length"] ** 2 == execution["center_distance"] ** 2 - execution["radius_difference"] ** 2
    assert execution["formula_family"] == formula_family
    assert execution["larger_circle_side"] == larger_side
    assert execution["tangent_side"] == tangent_side
    assert execution["unknown_role"] == unknown_role
    assert trace["witness_symbolic"]["formula_family"] == formula_family
    assert trace["witness_symbolic"]["unknown_role"] == unknown_role

    assert out.annotation_gt.type == "keyed_point_map"
    annotation = out.annotation_gt.value
    assert tuple(annotation.keys()) == ANNOTATION_KEYS
    assert trace["projected_annotation"]["keyed_point_map"] == annotation
    assert trace["projected_annotation"]["pixel_keyed_point_map"] == annotation
    assert trace["render_spec"]["prompt"]["prompt_variant"]["prompt_bundle_id"] == "geometry_circle_pair_tangents_v0"
    assert "task_variant" not in json.dumps(trace)
    _assert_point_map_inside_image(annotation, out.image.size)


def test_circle_pair_tangent_length_generation_is_deterministic() -> None:
    params = {
        "query_id": QUERY_ID,
        "tangent_case": (4, 12, 17, 15),
        "larger_circle_side": "right",
        "tangent_side": "above",
    }
    first = _generate(314159, **params)
    second = _generate(314159, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
    assert first.image.tobytes() == second.image.tobytes()


def test_circle_pair_center_distance_generation_is_deterministic() -> None:
    params = {
        "query_id": QUERY_ID_CENTER_DISTANCE,
        "tangent_case": (4, 12, 17, 15),
        "larger_circle_side": "right",
        "tangent_side": "above",
    }
    first = _generate(314160, task_id=TASK_ID_CENTER_DISTANCE, **params)
    second = _generate(314160, task_id=TASK_ID_CENTER_DISTANCE, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt.value == 17
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
    assert first.image.tobytes() == second.image.tobytes()


def test_circle_pair_tangent_length_rejects_invalid_params() -> None:
    for task_id in (TASK_ID_COMMON_TANGENT_LENGTH, TASK_ID_CENTER_DISTANCE):
        task = create_task(task_id)
        with pytest.raises(ValueError):
            task.generate(1, params={"query_id": "bad_query"}, max_attempts=1)
        with pytest.raises(ValueError):
            task.generate(1, params={"larger_circle_side": "middle"}, max_attempts=1)
        with pytest.raises(ValueError):
            task.generate(1, params={"tangent_side": "inside"}, max_attempts=1)
        with pytest.raises(ValueError):
            task.generate(1, params={"tangent_case": (3, 8, 12, 12)}, max_attempts=1)


def _assert_point_map_inside_image(annotation: dict[str, list[float]], image_size: tuple[int, int]) -> None:
    width, height = image_size
    for key in ANNOTATION_KEYS:
        point = annotation[key]
        assert isinstance(point, list)
        assert len(point) == 2
        x, y = [float(value) for value in point]
        assert 0.0 <= x <= float(width)
        assert 0.0 <= y <= float(height)
