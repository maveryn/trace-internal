"""Contract tests for the geometry transformation matching task."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.transformation.match import GeometryTransformationMatchTask


@pytest.mark.parametrize(
    ("params", "expected_point_count"),
    (
        ({"scene_variant": "triangle", "query_variant": "translation_match"}, 3),
        ({"scene_variant": "quadrilateral", "query_variant": "reflection_match"}, 4),
        ({"scene_variant": "triangle", "task_variant": "rotation_match"}, 3),
    ),
)
def test_geometry_transformation_match_emits_expected_contract(
    params: dict[str, str],
    expected_point_count: int,
) -> None:
    out = GeometryTransformationMatchTask().generate(23101, params=params, max_attempts=20)
    assert out.answer_gt.type == "option_letter"
    assert isinstance(out.answer_gt.value, str)
    assert len(str(out.answer_gt.value)) == 1
    assert out.evidence_gt.type == "graph_point_set"
    assert len(out.evidence_gt.value) == expected_point_count
    assert out.trace_payload["query_spec"]["params"]["task_variant"] == out.task_variant
    assert out.trace_payload["execution_trace"]["required_evidence_labels"] == [
        f"vertex_{index}" for index in range(1, expected_point_count + 1)
    ]


def test_geometry_transformation_match_rejects_unsupported_scene_variant() -> None:
    with pytest.raises(ValueError):
        GeometryTransformationMatchTask().generate(
            23111,
            params={"scene_variant": "circle", "query_variant": "translation_match"},
            max_attempts=20,
        )


def test_geometry_transformation_match_rejects_unsupported_query_variant() -> None:
    with pytest.raises(ValueError):
        GeometryTransformationMatchTask().generate(
            23112,
            params={"scene_variant": "triangle", "query_variant": "largest_area"},
            max_attempts=20,
        )
