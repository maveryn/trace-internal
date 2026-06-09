"""Contract tests for geometry graphing average-rate task."""

from __future__ import annotations

from trace.tasks.geometry.graphing.rate import (
    GeometryGraphingAverageRateValueBaseTask,
    GeometryGraphingAverageRateValueTask,
)


def test_geometry_graphing_average_rate_emits_expected_contract() -> None:
    out = GeometryGraphingAverageRateValueTask().generate(
        24001,
        params={"target_rate": 1.5},
        max_attempts=20,
    )

    assert out.answer_gt.type == "number"
    assert float(out.answer_gt.value) == 1.5
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == 2
    assert out.trace_payload["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert out.query_id == "average_rate_between_marked_points"
    assert out.trace_payload["query_spec"]["params"]["query_id"] == "average_rate_between_marked_points"
    assert out.trace_payload["query_spec"]["params"]["target_rate"] == 1.5
    assert out.trace_payload["execution_trace"]["average_rate"] == 1.5
    assert out.trace_payload["execution_trace"]["delta_y"] / out.trace_payload["execution_trace"]["delta_x"] == 1.5


def test_geometry_graphing_average_rate_rejects_unknown_query_id() -> None:
    task = GeometryGraphingAverageRateValueBaseTask()
    try:
        task.generate(
            24002,
            params={"query_id": "instantaneous_slope_value"},
            max_attempts=20,
        )
    except ValueError as exc:
        assert "unsupported query_id" in str(exc)
    else:
        raise AssertionError("unsupported query_id should raise ValueError")
