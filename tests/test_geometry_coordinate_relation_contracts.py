"""Contract tests for the geometry coordinate-relation task."""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from trace.tasks.geometry.coordinate_plane.segment_relation_count import (
    GeometryCoordinateRelationTask,
    _segments_intersect,
)
from trace.tasks.shared.text_rendering import load_font, resolve_text_label_center


@pytest.mark.parametrize(
    ("params", "expected_answer_type", "expected_annotation_type", "expected_annotation_count"),
    (
        ({"scene_variant": "segment_set", "query_id": "parallel_count", "target_count": 2}, "integer", "point_set", 4),
        ({"scene_variant": "segment_set", "query_id": "perpendicular_count", "target_count": 1}, "integer", "point_set", 2),
        ({"scene_variant": "line_points", "query_id": "collinear_count", "target_count": 3}, "integer", "point_set", 3),
        ({"scene_variant": "quadrant_points", "query_id": "same_quadrant_count", "target_count": 3}, "integer", "point_set", 3),
        ({"scene_variant": "polygon_lattice", "query_id": "point_in_shape_count", "target_count": 2}, "integer", "point_set", 2),
        ({"scene_variant": "polygon_lattice", "query_id": "point_in_shape_count", "target_count": 8}, "integer", "point_set", 8),
    ),
)
def test_geometry_coordinate_relation_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer_type: str,
    expected_annotation_type: str,
    expected_annotation_count: int,
) -> None:
    out = GeometryCoordinateRelationTask().generate(23301, params=params, max_attempts=25)
    assert out.answer_gt.type == expected_answer_type
    assert out.annotation_gt.type == expected_annotation_type
    assert len(out.annotation_gt.value) == int(expected_annotation_count)
    assert out.trace_payload["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert out.trace_payload["query_spec"]["params"]["query_id"] == out.query_id


def test_geometry_coordinate_relation_rejects_unsupported_scene_variant() -> None:
    with pytest.raises(ValueError):
        GeometryCoordinateRelationTask().generate(
            23311,
            params={"scene_variant": "triangle", "query_id": "parallel_count"},
            max_attempts=20,
        )


def test_geometry_coordinate_relation_rejects_incompatible_scene_query_pair() -> None:
    with pytest.raises(ValueError):
        GeometryCoordinateRelationTask().generate(
            23312,
            params={"scene_variant": "segment_set", "query_id": "same_quadrant_count"},
            max_attempts=20,
        )


def test_geometry_coordinate_relation_uses_centered_segment_window_and_quadrant_point_annotation() -> None:
    segment_out = GeometryCoordinateRelationTask().generate(
        23313,
        params={"scene_variant": "segment_set", "query_id": "parallel_count", "target_count": 2},
        max_attempts=20,
    )
    segment_frame = segment_out.trace_payload["render_spec"]["graph_coordinate_frame"]
    assert float(segment_frame["origin_fraction_x"]) == pytest.approx(0.5)
    assert float(segment_frame["origin_fraction_y"]) == pytest.approx(0.5)
    assert segment_out.trace_payload["execution_trace"]["matching_segment_ids"]
    segment_render_map = segment_out.trace_payload["render_map"]
    reference_segment = tuple(tuple(int(coord) for coord in point) for point in segment_render_map["reference_segment_graph"])
    candidate_segments = [
        tuple(tuple(int(coord) for coord in point) for point in segment)
        for segment in segment_render_map["candidate_segments_graph"].values()
    ]
    assert max(abs(int(coord)) for point in reference_segment for coord in point) <= 8
    assert all(max(abs(int(coord)) for point in segment for coord in point) <= 8 for segment in candidate_segments)
    all_segments = [reference_segment, *candidate_segments]
    for index, segment in enumerate(all_segments):
        for other in all_segments[index + 1 :]:
            assert not _segments_intersect(segment, other)

    quadrant_out = GeometryCoordinateRelationTask().generate(
        23314,
        params={"scene_variant": "quadrant_points", "query_id": "same_quadrant_count", "target_count": 2},
        max_attempts=20,
    )
    quadrant_frame = quadrant_out.trace_payload["render_spec"]["graph_coordinate_frame"]
    assert float(quadrant_frame["origin_fraction_x"]) == pytest.approx(0.5)
    assert float(quadrant_frame["origin_fraction_y"]) == pytest.approx(0.5)
    assert quadrant_out.annotation_gt.type == "point_set"
    assert all(isinstance(point, list) and len(point) == 2 for point in quadrant_out.annotation_gt.value)


def test_geometry_coordinate_relation_collinear_scene_keeps_reference_and_candidates_inside_centered_board() -> None:
    out = GeometryCoordinateRelationTask().generate(
        23315,
        params={"scene_variant": "line_points", "query_id": "collinear_count", "target_count": 4},
        max_attempts=20,
    )
    frame = out.trace_payload["render_spec"]["graph_coordinate_frame"]
    assert float(frame["origin_fraction_x"]) == pytest.approx(0.5)
    assert float(frame["origin_fraction_y"]) == pytest.approx(0.5)
    render_map = out.trace_payload["render_map"]
    all_points = [
        *render_map["reference_points_graph"],
        *render_map["candidate_points_graph"],
    ]
    assert all(max(abs(int(coord)) for coord in point) <= 8 for point in all_points)
    assert len(render_map["matching_points_graph"]) == 4
    point_a, point_b = render_map["reference_points_graph"]
    dx = int(point_b[0]) - int(point_a[0])
    dy = int(point_b[1]) - int(point_a[1])
    for point in render_map["matching_points_graph"]:
        cross = ((int(point[0]) - int(point_a[0])) * dy) - ((int(point[1]) - int(point_a[1])) * dx)
        assert cross == 0


def test_resolve_text_label_center_avoids_blocked_points_when_placing_labels() -> None:
    image = Image.new("RGB", (240, 240), "white")
    draw = ImageDraw.Draw(image)
    font = load_font(22, bold=True)
    center, bbox = resolve_text_label_center(
        draw,
        text="A",
        anchor=(120.0, 120.0),
        base_direction=(1.0, -1.0),
        offset_px=14.0,
        font=font,
        blocked_points=[(120.0, 120.0), (138.0, 104.0)],
        point_clearance_px=10.0,
        canvas_size=240,
    )
    point_boxes = [
        (110.0, 110.0, 130.0, 130.0),
        (128.0, 94.0, 148.0, 114.0),
    ]
    assert all(
        bbox[2] <= blocked[0] or bbox[0] >= blocked[2] or bbox[3] <= blocked[1] or bbox[1] >= blocked[3]
        for blocked in point_boxes
    )
    assert center != (120.0, 120.0)
