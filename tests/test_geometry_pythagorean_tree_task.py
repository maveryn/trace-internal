"""Regression tests for the Pythagorean tree geometry task."""

from __future__ import annotations

import json

import pytest

from trace.tasks import TASK_REGISTRY
from trace.tasks.geometry.measurement.pythagorean_tree import (
    TASK_ID,
    GeometryPythagoreanTreeMissingSquareAreaValueTask,
)


def _generate(seed: int, **params):
    task = GeometryPythagoreanTreeMissingSquareAreaValueTask()
    return task.generate(seed, params=dict(params), max_attempts=80)


def test_pythagorean_tree_registered_public_task() -> None:
    assert TASK_ID in TASK_REGISTRY
    assert TASK_REGISTRY[TASK_ID] is GeometryPythagoreanTreeMissingSquareAreaValueTask


def test_pythagorean_tree_hypotenuse_square_area_formula() -> None:
    out = _generate(20260604, query_id="hypotenuse_square_area", triple=(3, 4, 5))
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == "pythagorean_tree"
    assert out.query_id == "hypotenuse_square_area"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 25 == execution["answer"]
    assert execution["leg_square_1_area"] + execution["leg_square_2_area"] == execution["hypotenuse_square_area"]
    assert execution["target_role"] == "hypotenuse_square"

    assert out.annotation_gt.type == "keyed_bbox_map"
    annotation = out.annotation_gt.value
    assert set(annotation) == {"target_square", "leg_square_1", "leg_square_2", "hypotenuse_square"}
    assert annotation["target_square"] == annotation["hypotenuse_square"]
    _assert_bbox_map_inside_image(annotation, out.image.size)
    assert "task_variant" not in json.dumps(trace)


@pytest.mark.parametrize(
    ("target_role", "expected"),
    [
        ("leg_square_1", 9),
        ("leg_square_2", 16),
    ],
)
def test_pythagorean_tree_leg_square_area_formula(target_role: str, expected: int) -> None:
    out = _generate(20260605, query_id="leg_square_area", target_role=target_role, triple=(3, 4, 5))
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == "pythagorean_tree"
    assert out.query_id == "leg_square_area"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == expected == execution["answer"]
    assert execution["target_role"] == target_role
    assert execution["hypotenuse_square_area"] - expected in {
        execution["leg_square_1_area"],
        execution["leg_square_2_area"],
    }

    annotation = out.annotation_gt.value
    assert annotation["target_square"] == annotation[target_role]
    _assert_bbox_map_inside_image(annotation, out.image.size)
    assert "task_variant" not in json.dumps(trace)


def test_pythagorean_tree_generation_is_deterministic() -> None:
    params = {"query_id": "leg_square_area", "target_role": "leg_square_2", "triple": (5, 12, 13)}
    first = _generate(314159, **params)
    second = _generate(314159, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]


def _assert_bbox_map_inside_image(annotation: dict[str, list[float]], image_size: tuple[int, int]) -> None:
    width, height = image_size
    for bbox in annotation.values():
        assert isinstance(bbox, list)
        assert len(bbox) == 4
        x0, y0, x1, y1 = [float(value) for value in bbox]
        assert 0.0 <= x0 < x1 <= float(width)
        assert 0.0 <= y0 < y1 <= float(height)
