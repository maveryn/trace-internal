"""Contract tests for the geometry graphing count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.tasks.geometry.graphing.count import GeometryGraphingCountTask


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        ({"scene_variant": "quadratic", "query_variant": "reference_line_crossing_count", "reference_line_kind": "x_axis", "target_count": 2}, 2),
        (
            {
                "scene_variant": "absolute_value",
                "query_variant": "reference_line_crossing_count",
                "reference_line_kind": "horizontal_line",
                "target_count": 2,
            },
            2,
        ),
        (
            {
                "scene_variant": "cubic",
                "query_variant": "reference_line_crossing_count",
                "reference_line_kind": "horizontal_line",
                "target_count": 2,
            },
            2,
        ),
        ({"scene_variant": "cubic", "query_variant": "reference_line_crossing_count", "reference_line_kind": "x_axis", "target_count": 3}, 3),
        (
            {
                "scene_variant": "sinusoid",
                "query_variant": "reference_line_crossing_count",
                "reference_line_kind": "horizontal_line",
                "target_count": 4,
            },
            4,
        ),
        ({"scene_variant": "piecewise_linear", "query_variant": "turning_point_count", "target_count": 6}, 6),
        ({"scene_variant": "sinusoid", "query_variant": "turning_point_count", "target_count": 4}, 4),
        ({"scene_variant": "sinusoid", "query_variant": "local_extremum_count", "extremum_kind": "minimum", "target_count": 2}, 2),
        ({"scene_variant": "sinusoid", "query_variant": "local_extremum_count", "extremum_kind": "maximum", "target_count": 2}, 2),
        ({"scene_variant": "piecewise_linear", "query_variant": "local_extremum_count", "extremum_kind": "minimum", "target_count": 6}, 6),
        ({"scene_variant": "piecewise_linear", "query_variant": "local_extremum_count", "extremum_kind": "maximum", "target_count": 6}, 6),
        (
            {
                "scene_variant": "piecewise_linear",
                "query_variant": "reference_line_crossing_count",
                "reference_line_kind": "x_axis",
                "target_count": 6,
            },
            6,
        ),
        (
            {
                "scene_variant": "piecewise_linear",
                "query_variant": "reference_line_crossing_count",
                "reference_line_kind": "horizontal_line",
                "target_count": 6,
            },
            6,
        ),
    ),
)
def test_geometry_graphing_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
) -> None:
    out = GeometryGraphingCountTask().generate(23401, params=params, max_attempts=40)
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "point_set"
    assert len(out.evidence_gt.value) == int(expected_answer)
    assert out.trace_payload["projected_evidence"]["point_set"] == out.evidence_gt.value
    assert out.trace_payload["query_spec"]["params"]["query_variant"] == out.query_variant
    assert out.trace_payload["execution_trace"]["target_count"] == int(expected_answer)
    for key in ("reference_line_kind", "extremum_kind"):
        if key in params:
            assert out.trace_payload["execution_trace"][key] == params[key]
            assert out.trace_payload["query_spec"]["params"][key] == params[key]


@pytest.mark.parametrize(
    ("scene_variant", "query_variant"),
    (
        ("quadratic", "turning_point_count"),
        ("quadratic", "local_extremum_count"),
        ("absolute_value", "turning_point_count"),
        ("absolute_value", "local_extremum_count"),
        ("cubic", "turning_point_count"),
        ("cubic", "local_extremum_count"),
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
            params={"scene_variant": "quartic", "query_variant": "reference_line_crossing_count"},
            max_attempts=20,
        )


def test_geometry_graphing_count_rejects_target_below_active_answer_range() -> None:
    with pytest.raises(ValueError):
        GeometryGraphingCountTask().generate(
            23413,
            params={
                "scene_variant": "piecewise_linear",
                "query_variant": "reference_line_crossing_count",
                "reference_line_kind": "x_axis",
                "target_count": 1,
            },
            max_attempts=40,
        )


@pytest.mark.parametrize(
    "source_query_variant",
    (
        "x_intercept_count",
        "horizontal_line_intersection_count",
        "local_minima_count",
        "local_maxima_count",
    ),
)
def test_geometry_graphing_count_rejects_source_query_variants(source_query_variant: str) -> None:
    with pytest.raises(ValueError):
        GeometryGraphingCountTask().generate(
            23414,
            params={"query_variant": source_query_variant},
            max_attempts=20,
        )


def test_geometry_graphing_count_crossing_prompts_exclude_tangencies() -> None:
    prompt_bundle = json.loads(Path("prompts/geometry/graphing/geometry_graphing_v0.json").read_text())
    prompts = prompt_bundle["query_templates"]["reference_line_crossing_count"]
    assert prompts
    assert all("cross" in str(prompt).lower() or "passing through" in str(prompt).lower() for prompt in prompts)
    assert all("tangenc" not in str(prompt).lower() for prompt in prompts)
