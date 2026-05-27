"""Contracts for sector formula geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.measurement.sector_formula import (
    SCENE_ID,
    GeometrySectorAngleRelationValueTask,
    GeometrySectorMeasureValueTask,
)


TASK_CLASSES = (
    GeometrySectorMeasureValueTask,
    GeometrySectorAngleRelationValueTask,
)

QUERY_IDS_BY_TASK = {
    GeometrySectorMeasureValueTask: (
        "area_from_radius_and_complement_angle",
        "arc_length_from_radius_and_supplement_angle",
        "area_from_arc_length_and_radius",
        "arc_length_from_area_and_radius",
    ),
    GeometrySectorAngleRelationValueTask: (
        "angle_from_arc_length_and_radius",
        "angle_from_area_and_radius",
        "complement_angle_from_arc_length",
        "supplement_angle_from_area",
        "remaining_angle_from_sector_measure",
    ),
}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_sector_formula_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(55001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_variant == "default"
    assert out.query_id
    assert out.answer_gt.type == "number"
    assert out.evidence_gt.type == "bbox_set"
    assert 2 <= len(out.evidence_gt.value) <= 4
    assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_variant"] == "default"
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_evidence"]["type"] == "bbox_set"


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_sector_formula_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(55011, params=params, max_attempts=20)
    out_b = task.generate(55011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_sector_formula_tasks_support_every_explicit_query(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            55021 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        assert out.query_id == query_id
        assert out.answer_gt.type == "number"
        assert out.trace_payload["query_spec"]["params"]["query_variant_probabilities"] == {
            query_id: 1.0
        }


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_sector_formula_evidence_stays_inside_canvas(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            55041 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        width, height = out.image.size
        for x0, y0, x1, y1 in out.evidence_gt.value:
            assert 0.0 <= x0 < x1 <= float(width)
            assert 0.0 <= y0 < y1 <= float(height)
            assert (x1 - x0) > 8.0
            assert (y1 - y0) > 8.0


def test_sector_formula_tasks_reject_unknown_query_id() -> None:
    task = GeometrySectorMeasureValueTask()
    with pytest.raises(ValueError):
        task.generate(55031, params={"query_id": "not_a_query"}, max_attempts=20)
