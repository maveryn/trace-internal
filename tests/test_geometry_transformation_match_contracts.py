"""Contract tests for the geometry transformation matching task."""

from __future__ import annotations

from itertools import combinations

import pytest

from trace.core.seed import hash64
from trace.tasks.geometry.transformation.match import GeometryTransformationMatchTask


@pytest.mark.parametrize(
    ("params", "expected_point_count"),
    (
        ({"scene_variant": "triangle", "query_variant": "translation_match"}, 3),
        ({"scene_variant": "quadrilateral", "query_variant": "reflection_match"}, 4),
        ({"scene_variant": "triangle", "query_variant": "rotation_match"}, 3),
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
    assert out.evidence_gt.type == "point_set"
    assert len(out.evidence_gt.value) == expected_point_count
    assert out.trace_payload["projected_evidence"]["point_set"] == out.evidence_gt.value
    assert out.trace_payload["query_spec"]["params"]["query_variant"] == out.query_variant
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


def test_geometry_transformation_match_keeps_candidate_polygons_separated() -> None:
    task = GeometryTransformationMatchTask()

    for index in range(30):
        out = task.generate(
            int(hash64(0, "geometry_transformation_match_base", index)),
            params={},
            max_attempts=100,
        )
        candidates = out.trace_payload["render_map"]["candidate_vertices_graph_by_label"]
        boxes = {
            label: (
                min(float(point[0]) for point in vertices),
                min(float(point[1]) for point in vertices),
                max(float(point[0]) for point in vertices),
                max(float(point[1]) for point in vertices),
            )
            for label, vertices in candidates.items()
        }
        for left_label, right_label in combinations(sorted(boxes), 2):
            left = boxes[left_label]
            right = boxes[right_label]
            assert (
                float(left[2]) + 0.75 <= float(right[0])
                or float(right[2]) + 0.75 <= float(left[0])
                or float(left[3]) + 0.75 <= float(right[1])
                or float(right[3]) + 0.75 <= float(left[1])
            ), (index, left_label, right_label, left, right)


def test_geometry_transformation_match_translation_cue_is_above_reference_and_left_of_y_axis() -> None:
    task = GeometryTransformationMatchTask()

    for index in range(30):
        out = task.generate(
            int(hash64(0, "geometry_transformation_match_base.translation", index)),
            params={"query_variant": "translation_match"},
            max_attempts=100,
        )
        cue = out.trace_payload["render_map"]["cue"]
        reference_vertices = out.trace_payload["render_map"]["reference_vertices_graph"]
        reference_top_y = max(int(point[1]) for point in reference_vertices)
        cue_bottom_y = min(int(cue["start_graph"][1]), int(cue["end_graph"][1]))
        assert cue["type"] == "translation_vector"
        assert max(int(cue["start_graph"][0]), int(cue["end_graph"][0])) < 0, (index, cue)
        assert cue_bottom_y - reference_top_y == 4, (index, cue, reference_vertices)
