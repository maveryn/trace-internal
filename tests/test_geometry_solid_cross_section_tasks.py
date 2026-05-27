"""Contracts for solid cross-section geometry tasks."""

from __future__ import annotations

import math

import pytest

from trace.tasks.geometry.measurement.solid_cross_section import (
    SCENE_ID,
    GeometrySolidCrossSectionAreaValueTask,
)

TASK_CLASSES = (GeometrySolidCrossSectionAreaValueTask,)

QUERY_IDS_BY_TASK = {
    GeometrySolidCrossSectionAreaValueTask: (
        "cone_parallel_slice_area",
        "square_pyramid_parallel_slice_area",
    ),
}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_solid_cross_section_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(65001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_id == "default"
    assert out.query_id
    assert out.answer_gt.type == "number"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 5
    assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_id"] == "default"
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_evidence"]["type"] == "bbox_set"
    assert trace["execution_trace"]["answer_rounding"] == "one_decimal"


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_solid_cross_section_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(65011, params=params, max_attempts=20)
    out_b = task.generate(65011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert (
        out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    )
    assert out_a.image.tobytes() == out_b.image.tobytes()


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_solid_cross_section_tasks_support_every_explicit_query(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            65021 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        trace = out.trace_payload["execution_trace"]
        assert out.query_id == query_id
        assert out.answer_gt.type == "number"
        assert out.trace_payload["query_spec"]["params"][
            "query_id_probabilities"
        ] == {query_id: 1.0}

        scale = float(trace["slice_distance_from_apex"]) / float(trace["solid_height"])
        assert trace["similarity_scale"] == pytest.approx(scale)
        if query_id == "cone_parallel_slice_area":
            base_radius = float(trace["base_radius"])
            slice_radius = base_radius * scale
            assert trace["slice_radius"] == pytest.approx(round(slice_radius, 1))
            assert out.answer_gt.value == pytest.approx(round(math.pi * slice_radius**2, 1))
        elif query_id == "square_pyramid_parallel_slice_area":
            base_side = float(trace["base_side"])
            slice_side = base_side * scale
            assert trace["slice_side"] == pytest.approx(round(slice_side, 1))
            assert out.answer_gt.value == pytest.approx(round(slice_side**2, 1))


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_solid_cross_section_evidence_stays_inside_canvas(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            65041 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        width, height = out.image.size
        for x0, y0, x1, y1 in out.evidence_gt.value:
            assert 0.0 <= x0 < x1 <= float(width)
            assert 0.0 <= y0 < y1 <= float(height)
            assert (x1 - x0) > 8.0
            assert (y1 - y0) > 8.0


def test_solid_cross_section_tasks_reject_unknown_query_id() -> None:
    task = GeometrySolidCrossSectionAreaValueTask()
    with pytest.raises(ValueError):
        task.generate(65031, params={"query_id": "not_a_query"}, max_attempts=20)
