"""Contract tests for the geometry similarity counting task."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.similarity.count import GeometrySimilarityCountTask


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        ({"scene_variant": "triangle", "query_id": "congruent_count", "target_count": 2}, 2),
        ({"scene_variant": "quadrilateral", "query_id": "similar_count", "target_count": 3}, 3),
        ({"scene_variant": "triangle", "query_id": "similar_count", "target_count": 0}, 0),
        ({"scene_variant": "quadrilateral", "query_id": "congruent_count", "target_count": 5}, 5),
    ),
)
def test_geometry_similarity_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
) -> None:
    out = GeometrySimilarityCountTask().generate(23201, params=params, max_attempts=30)
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == int(expected_answer)
    assert out.trace_payload["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert out.trace_payload["query_spec"]["params"]["query_id"] == out.query_id
    assert out.trace_payload["execution_trace"]["target_count"] == int(expected_answer)


def test_geometry_similarity_count_rejects_unsupported_scene_variant() -> None:
    with pytest.raises(ValueError):
        GeometrySimilarityCountTask().generate(
            23211,
            params={"scene_variant": "circle", "query_id": "similar_count"},
            max_attempts=20,
        )


def test_geometry_similarity_count_rejects_unsupported_query_id() -> None:
    with pytest.raises(ValueError):
        GeometrySimilarityCountTask().generate(
            23212,
            params={"scene_variant": "triangle", "query_id": "largest_area"},
            max_attempts=20,
        )
