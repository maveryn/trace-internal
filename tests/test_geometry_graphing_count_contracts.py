"""Contract tests for the geometry graphing count task."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.graphing.count import GeometryGraphingCountTask


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        ({"scene_variant": "quadratic", "query_variant": "x_intercept_count", "target_count": 2}, 2),
        ({"scene_variant": "absolute_value", "query_variant": "horizontal_line_intersection_count", "target_count": 1}, 1),
        ({"scene_variant": "piecewise_linear", "task_variant": "turning_point_count", "target_count": 3}, 3),
        ({"scene_variant": "piecewise_linear", "query_variant": "local_minima_count", "target_count": 2}, 2),
        ({"scene_variant": "piecewise_linear", "query_variant": "local_maxima_count", "target_count": 2}, 2),
        ({"scene_variant": "piecewise_linear", "query_variant": "turning_point_count", "target_count": 0}, 0),
        ({"scene_variant": "quadratic", "query_variant": "x_intercept_count", "target_count": 0}, 0),
    ),
)
def test_geometry_graphing_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
) -> None:
    out = GeometryGraphingCountTask().generate(23401, params=params, max_attempts=40)
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "graph_point_set"
    assert len(out.evidence_gt.value) == int(expected_answer)
    assert out.trace_payload["query_spec"]["params"]["task_variant"] == out.task_variant
    assert out.trace_payload["execution_trace"]["target_count"] == int(expected_answer)


@pytest.mark.parametrize(
    ("scene_variant", "query_variant"),
    (
        ("quadratic", "turning_point_count"),
        ("quadratic", "local_minima_count"),
        ("quadratic", "local_maxima_count"),
        ("absolute_value", "turning_point_count"),
        ("absolute_value", "local_minima_count"),
        ("absolute_value", "local_maxima_count"),
    ),
)
def test_geometry_graphing_count_rejects_incompatible_scene_query_pairs(
    scene_variant: str,
    query_variant: str,
) -> None:
    with pytest.raises(ValueError):
        GeometryGraphingCountTask().generate(
            23411,
            params={"scene_variant": scene_variant, "query_variant": query_variant},
            max_attempts=20,
        )


def test_geometry_graphing_count_rejects_unsupported_scene_variant() -> None:
    with pytest.raises(ValueError):
        GeometryGraphingCountTask().generate(
            23412,
            params={"scene_variant": "cubic", "query_variant": "x_intercept_count"},
            max_attempts=20,
        )


def test_geometry_graphing_count_zero_case_keeps_empty_graph_point_evidence() -> None:
    out = GeometryGraphingCountTask().generate(
        23413,
        params={"scene_variant": "quadratic", "query_variant": "x_intercept_count", "target_count": 0},
        max_attempts=40,
    )
    assert int(out.answer_gt.value) == 0
    assert out.evidence_gt.value == []
    assert out.trace_payload["projected_evidence"]["grid_point_set"] == []
