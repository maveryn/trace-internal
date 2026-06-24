"""Contract tests for the geometry similarity counting task."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.shape_gallery.congruent_count import GeometryShapeGalleryCongruentCountTask
from trace.tasks.geometry.shape_gallery.similar_count import GeometryShapeGallerySimilarCountTask


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_answer", "expected_relation"),
    (
        (GeometryShapeGalleryCongruentCountTask, {"scene_variant": "triangle", "target_count": 2}, 2, "congruent"),
        (GeometryShapeGallerySimilarCountTask, {"scene_variant": "quadrilateral", "target_count": 3}, 3, "similar"),
        (GeometryShapeGallerySimilarCountTask, {"scene_variant": "triangle", "target_count": 0}, 0, "similar"),
        (GeometryShapeGalleryCongruentCountTask, {"scene_variant": "quadrilateral", "target_count": 5}, 5, "congruent"),
    ),
)
def test_geometry_similarity_count_emits_expected_contract(
    task_cls,
    params: dict[str, int | str],
    expected_answer: int,
    expected_relation: str,
) -> None:
    out = task_cls().generate(23201, params=params, max_attempts=30)
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == int(expected_answer)
    assert out.trace_payload["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert out.trace_payload["query_spec"]["params"]["query_id"] == out.query_id
    assert out.query_id == "single"
    assert out.trace_payload["execution_trace"]["relation_rule"] == expected_relation
    assert out.trace_payload["execution_trace"]["target_count"] == int(expected_answer)


def test_geometry_similarity_count_rejects_unsupported_scene_variant() -> None:
    with pytest.raises(ValueError):
        GeometryShapeGallerySimilarCountTask().generate(
            23211,
            params={"scene_variant": "circle"},
            max_attempts=20,
        )


def test_geometry_similarity_count_rejects_unsupported_query_id() -> None:
    with pytest.raises(ValueError):
        GeometryShapeGalleryCongruentCountTask().generate(
            23212,
            params={"scene_variant": "triangle", "query_id": "largest_area"},
            max_attempts=20,
        )
