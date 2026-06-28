"""Regression tests for the Pythagorean tree geometry task."""

from __future__ import annotations

import json

import pytest

from trace.tasks import TASK_REGISTRY
from trace.tasks.geometry.pythagorean_tree.missing_square_area_value import (
    SUPPORTED_QUERY_IDS,
    TASK_ID,
    GeometryPythagoreanTreeMissingSquareAreaValueTask,
    _TRIPLES,
)


def _generate(seed: int, **params):
    task = GeometryPythagoreanTreeMissingSquareAreaValueTask()
    return task.generate(seed, params=dict(params), max_attempts=80)


def test_pythagorean_tree_registered_public_task() -> None:
    assert TASK_ID in TASK_REGISTRY
    assert TASK_REGISTRY[TASK_ID] is GeometryPythagoreanTreeMissingSquareAreaValueTask


def test_pythagorean_tree_supports_expected_public_queries() -> None:
    task = GeometryPythagoreanTreeMissingSquareAreaValueTask()

    assert tuple(task.supported_query_ids) == SUPPORTED_QUERY_IDS
    assert SUPPORTED_QUERY_IDS == ("single",)


def test_pythagorean_tree_default_pool_has_distinct_square_area_support() -> None:
    assert len(_TRIPLES) >= 10

    legs = [value for leg_a, leg_b, _hypotenuse in _TRIPLES for value in (leg_a, leg_b)]
    hypotenuses = [hypotenuse for _leg_a, _leg_b, hypotenuse in _TRIPLES]

    assert len(set(legs)) == len(legs)
    assert len(set(hypotenuses)) == len(hypotenuses)
    for leg_a, leg_b, hypotenuse in _TRIPLES:
        assert int(leg_a) ** 2 + int(leg_b) ** 2 == int(hypotenuse) ** 2


@pytest.mark.parametrize(
    ("target_role", "expected", "visible_sides"),
    [
        ("leg_square_1", 9, {"AB": "AB=4", "BC": "BC=5"}),
        ("leg_square_2", 16, {"AC": "AC=3", "BC": "BC=5"}),
        ("hypotenuse_square", 25, {"AB": "AB=4", "AC": "AC=3"}),
    ],
)
def test_pythagorean_tree_marked_square_area_formula(
    target_role: str,
    expected: int,
    visible_sides: dict[str, str],
) -> None:
    out = _generate(20260604, query_id="single", target_role=target_role, triple=(3, 4, 5))
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == "pythagorean_tree"
    assert out.query_id == "single"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == expected == execution["answer"]
    assert execution["leg_square_1_area"] + execution["leg_square_2_area"] == execution["hypotenuse_square_area"]
    assert execution["target_role"] == target_role
    assert execution["visible_side_labels"] == visible_sides
    assert out.trace_payload["render_spec"]["prompt"]["prompt_bundle_id"] == "geometry_pythagorean_tree_v1"
    assert "Area=?" in out.prompt

    assert out.annotation_gt.type == "bbox_map"
    annotation = out.annotation_gt.value
    assert set(annotation) == {"target_square", "known_side_1_label", "known_side_2_label"}
    _assert_no_duplicate_public_bboxes(annotation)
    _assert_bbox_map_inside_image(annotation, out.image.size)
    assert trace["render_map"]["side_labels"] == visible_sides
    assert trace["render_map"]["square_labels"] == {target_role: "Area=?"}
    assert "task_variant" not in json.dumps(trace)


def test_pythagorean_tree_generation_is_deterministic() -> None:
    params = {"query_id": "single", "target_role": "leg_square_2", "triple": (5, 12, 13)}
    first = _generate(314159, **params)
    second = _generate(314159, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_pythagorean_tree_explicit_queries_generate(query_id: str) -> None:
    out = _generate(20260606, query_id=query_id, triple=(5, 12, 13))

    assert out.query_id == query_id
    assert out.scene_id == "pythagorean_tree"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_map"
    _assert_bbox_map_inside_image(out.annotation_gt.value, out.image.size)


def _assert_bbox_map_inside_image(annotation: dict[str, list[float]], image_size: tuple[int, int]) -> None:
    width, height = image_size
    for bbox in annotation.values():
        assert isinstance(bbox, list)
        assert len(bbox) == 4
        x0, y0, x1, y1 = [float(value) for value in bbox]
        assert 0.0 <= x0 < x1 <= float(width)
        assert 0.0 <= y0 < y1 <= float(height)


def _assert_no_duplicate_public_bboxes(annotation: dict[str, list[float]]) -> None:
    boxed = [tuple(round(float(value), 3) for value in bbox) for bbox in annotation.values()]
    assert len(boxed) == len(set(boxed))
