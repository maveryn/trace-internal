"""Contracts for concentric-circle tangent-chord geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.measurement.concentric_circle_chord import (
    SCENE_ID,
    GeometryConcentricCircleChordValueTask,
)

QUERY_IDS = ("chord_length_from_radii", "inner_radius_from_chord")


def test_concentric_circle_chord_task_emits_public_contract() -> None:
    task = GeometryConcentricCircleChordValueTask()
    out = task.generate(56001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_id == "default"
    assert out.query_id
    assert out.answer_gt.type == "number"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 2
    assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_id"] == "default"
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_evidence"]["type"] == "bbox_set"
    assert trace["execution_trace"]["outer_radius"] ** 2 == (
        trace["execution_trace"]["inner_radius"] ** 2
        + trace["execution_trace"]["half_chord"] ** 2
    )


def test_concentric_circle_chord_task_is_deterministic() -> None:
    task = GeometryConcentricCircleChordValueTask()
    params = {}
    out_a = task.generate(56011, params=params, max_attempts=20)
    out_b = task.generate(56011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert (
        out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    )
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_concentric_circle_chord_task_supports_every_explicit_query() -> None:
    task = GeometryConcentricCircleChordValueTask()
    for index, query_id in enumerate(QUERY_IDS):
        out = task.generate(
            56021 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        assert out.query_id == query_id
        assert out.answer_gt.type == "number"
        assert out.trace_payload["query_spec"]["params"][
            "query_id_probabilities"
        ] == {query_id: 1.0}


def test_concentric_circle_chord_evidence_stays_inside_canvas() -> None:
    task = GeometryConcentricCircleChordValueTask()
    for index, query_id in enumerate(QUERY_IDS):
        out = task.generate(
            56041 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        width, height = out.image.size
        for x0, y0, x1, y1 in out.evidence_gt.value:
            assert 0.0 <= x0 < x1 <= float(width)
            assert 0.0 <= y0 < y1 <= float(height)
            assert (x1 - x0) > 8.0
            assert (y1 - y0) > 8.0


def test_concentric_circle_chord_tasks_reject_unknown_query_id() -> None:
    task = GeometryConcentricCircleChordValueTask()
    with pytest.raises(ValueError):
        task.generate(56031, params={"query_id": "not_a_query"}, max_attempts=20)
