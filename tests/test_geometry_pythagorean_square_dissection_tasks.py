"""Contracts for Pythagorean square-dissection geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.measurement.pythagorean_square_dissection import (
    SCENE_ID,
    GeometryPythagoreanSquareAreaValueTask,
)

TASK_CLASSES = (GeometryPythagoreanSquareAreaValueTask,)

QUERY_IDS_BY_TASK = {
    GeometryPythagoreanSquareAreaValueTask: (
        "central_square_area_from_triangle_legs",
    ),
}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_pythagorean_square_dissection_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(58001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_id == "default"
    assert out.query_id
    assert out.answer_gt.type == "number"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 3
    assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_id"] == "default"
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_evidence"]["type"] == "bbox_set"

    vertical_leg = trace["execution_trace"]["leg_vertical"]
    horizontal_leg = trace["execution_trace"]["leg_horizontal"]
    outer_side = trace["execution_trace"]["outer_square_side"]
    corner_area = trace["execution_trace"]["corner_triangle_area_each"]
    central_area = outer_side**2 - (4.0 * corner_area)
    assert out.query_id == "central_square_area_from_triangle_legs"
    assert outer_side == vertical_leg + horizontal_leg
    assert trace["execution_trace"]["given_leg"] == vertical_leg
    assert trace["execution_trace"]["visible_other_leg"] == horizontal_leg
    assert out.answer_gt.value == pytest.approx(float(central_area))
    assert trace["execution_trace"]["vertical_square_area"] == vertical_leg**2
    assert trace["execution_trace"]["horizontal_square_area"] == horizontal_leg**2
    assert trace["execution_trace"]["central_square_area"] == pytest.approx(
        central_area
    )


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_pythagorean_square_dissection_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(58011, params=params, max_attempts=20)
    out_b = task.generate(58011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert (
        out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    )
    assert out_a.image.tobytes() == out_b.image.tobytes()


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_pythagorean_square_dissection_tasks_support_every_explicit_query(
    task_cls,
) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            58021 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        assert out.query_id == query_id
        assert out.answer_gt.type == "number"
        assert out.trace_payload["query_spec"]["params"][
            "query_id_probabilities"
        ] == {query_id: 1.0}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_pythagorean_square_dissection_evidence_stays_inside_canvas(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            58041 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        width, height = out.image.size
        for x0, y0, x1, y1 in out.evidence_gt.value:
            assert 0.0 <= x0 < x1 <= float(width)
            assert 0.0 <= y0 < y1 <= float(height)
            assert (x1 - x0) > 8.0
            assert (y1 - y0) > 8.0


def test_pythagorean_square_dissection_tasks_reject_unknown_query_id() -> None:
    task = GeometryPythagoreanSquareAreaValueTask()
    with pytest.raises(ValueError):
        task.generate(58031, params={"query_id": "not_a_query"}, max_attempts=20)


def test_pythagorean_square_dissection_target_orientation_varies() -> None:
    task = GeometryPythagoreanSquareAreaValueTask()
    orientations = set()
    evidence_centers = set()
    for index in range(8):
        out = task.generate(
            58101 + index,
            params={},
            max_attempts=20,
        )
        trace = out.trace_payload
        orientations.add(trace["render_spec"]["orientation"])
        x0, y0, x1, y1 = trace["render_map"]["label_bboxes"]["given_triangle_leg"]
        evidence_centers.add((round((x0 + x1) / 20.0), round((y0 + y1) / 20.0)))

    assert len(orientations) == 4
    assert len(evidence_centers) >= 3
