"""Contracts for cone sector-net geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.measurement.cone_sector_net import (
    SCENE_ID,
    GeometryConeSectorNetValueTask,
)

QUERY_IDS = ("base_radius_from_sector_angle", "height_from_sector_angle")


def test_cone_sector_net_task_emits_public_contract() -> None:
    task = GeometryConeSectorNetValueTask()
    out = task.generate(59001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_id
    assert out.answer_gt.type == "number"
    assert out.evidence_gt.type == "keyed_point_map"
    assert set(out.evidence_gt.value) in (
        {"S", "P", "Q", "C", "R"},
        {"S", "P", "Q", "C", "A"},
    )
    assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_evidence"]["type"] == "keyed_point_map"
    assert trace["projected_evidence"]["keyed_point_map"] == out.evidence_gt.value
    assert trace["execution_trace"]["slant_height"] > 0
    assert 0 < trace["execution_trace"]["theta_degrees"] < 360

    slant_height = float(trace["execution_trace"]["slant_height"])
    theta_degrees = float(trace["execution_trace"]["theta_degrees"])
    base_radius = theta_degrees * slant_height / 360.0
    cone_height = (slant_height**2 - base_radius**2) ** 0.5
    assert trace["execution_trace"]["base_radius"] == pytest.approx(
        round(base_radius, 1)
    )
    assert trace["execution_trace"]["cone_height"] == pytest.approx(
        round(cone_height, 1)
    )
    if out.query_id == "base_radius_from_sector_angle":
        assert out.answer_gt.value == pytest.approx(round(base_radius, 1))
    else:
        assert out.answer_gt.value == pytest.approx(round(cone_height, 1))


def test_cone_sector_net_task_is_deterministic() -> None:
    task = GeometryConeSectorNetValueTask()
    params = {}
    out_a = task.generate(59011, params=params, max_attempts=20)
    out_b = task.generate(59011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert (
        out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    )
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_cone_sector_net_task_supports_every_explicit_query() -> None:
    task = GeometryConeSectorNetValueTask()
    for index, query_id in enumerate(QUERY_IDS):
        out = task.generate(
            59021 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        assert out.query_id == query_id
        assert out.answer_gt.type == "number"
        assert out.trace_payload["query_spec"]["params"][
            "query_id_probabilities"
        ] == {query_id: 1.0}


def test_cone_sector_net_evidence_stays_inside_canvas() -> None:
    task = GeometryConeSectorNetValueTask()
    for index, query_id in enumerate(QUERY_IDS):
        out = task.generate(
            59041 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        width, height = out.image.size
        for x, y in out.evidence_gt.value.values():
            assert 0.0 <= x <= float(width)
            assert 0.0 <= y <= float(height)


def test_cone_sector_net_evidence_uses_labeled_construction_points_not_labels() -> None:
    task = GeometryConeSectorNetValueTask()
    expected_keys_by_query = {
        "base_radius_from_sector_angle": {"S", "P", "Q", "C", "R"},
        "height_from_sector_angle": {"S", "P", "Q", "C", "A"},
    }
    for index, query_id in enumerate(QUERY_IDS):
        out = task.generate(
            59061 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        expected_keys = expected_keys_by_query[str(query_id)]
        assert out.evidence_gt.type == "keyed_point_map"
        assert set(out.evidence_gt.value) == expected_keys
        assert set(out.trace_payload["execution_trace"]["evidence_roles"]) == expected_keys
        assert all(
            "label" not in str(role)
            for role in out.trace_payload["execution_trace"]["evidence_roles"]
        )
        assert "label_bboxes" in out.trace_payload["render_map"]
        assert "point_label_bboxes" in out.trace_payload["render_map"]


def test_cone_sector_net_tasks_reject_unknown_query_id() -> None:
    task = GeometryConeSectorNetValueTask()
    with pytest.raises(ValueError):
        task.generate(59031, params={"query_id": "not_a_query"}, max_attempts=20)
