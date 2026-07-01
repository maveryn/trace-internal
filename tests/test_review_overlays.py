"""Unit tests for shared review/sample annotation overlay helpers."""

from __future__ import annotations

from PIL import Image as PILImage

from trace.core.review_overlays import render_annotation_overlay, resolve_overlay_annotation


def test_resolve_overlay_annotation_uses_canonical_point_projection() -> None:
    annotation_type, annotation_value = resolve_overlay_annotation(
        annotation_type="point_set",
        annotation_value=[[0, 0], [1, 1], [2, 2]],
        trace_payload={"projected_annotation": {"pixel_point_set": [[40.0, 50.0], [60.0, 70.0], [80.0, 90.0]]}},
    )
    assert annotation_type == "point_set"
    assert annotation_value == [[40.0, 50.0], [60.0, 70.0], [80.0, 90.0]]


def test_resolve_overlay_annotation_uses_canonical_point_sequence_projection() -> None:
    annotation_type, annotation_value = resolve_overlay_annotation(
        annotation_type="point_sequence",
        annotation_value=[[0, 0], [1, 1], [2, 2]],
        trace_payload={"projected_annotation": {"pixel_point_sequence": [[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]]}},
    )
    assert annotation_type == "point_sequence"
    assert annotation_value == [[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]]


def test_resolve_overlay_annotation_uses_canonical_bbox_projection() -> None:
    annotation_type, annotation_value = resolve_overlay_annotation(
        annotation_type="bbox_set",
        annotation_value=[],
        trace_payload={
            "projected_annotation": {
                "bbox_set": [[10.0, 20.0, 30.0, 40.0], [50.0, 60.0, 70.0, 80.0]],
            }
        },
    )
    assert annotation_type == "bbox_set"
    assert annotation_value == [[10.0, 20.0, 30.0, 40.0], [50.0, 60.0, 70.0, 80.0]]


def test_resolve_overlay_annotation_uses_canonical_segment_set_projection() -> None:
    annotation_type, annotation_value = resolve_overlay_annotation(
        annotation_type="segment_set",
        annotation_value=[],
        trace_payload={
            "projected_annotation": {
                "segment_set": [
                    [[10.0, 20.0], [30.0, 40.0]],
                    [[50.0, 60.0], [70.0, 80.0]],
                ],
            }
        },
    )
    assert annotation_type == "segment_set"
    assert annotation_value == [
        [[10.0, 20.0], [30.0, 40.0]],
        [[50.0, 60.0], [70.0, 80.0]],
    ]


def test_resolve_overlay_annotation_prefers_scalar_pixel_segment() -> None:
    annotation_type, annotation_value = resolve_overlay_annotation(
        annotation_type="segment",
        annotation_value=[[1, 2], [3, 4]],
        trace_payload={
            "projected_annotation": {
                "type": "segment",
                "segment": [[10, 20], [30, 40]],
                "pixel_segment": [[50, 60], [70, 80]],
            }
        },
    )

    assert annotation_type == "segment"
    assert annotation_value == [[50, 60], [70, 80]]


def test_resolve_overlay_annotation_uses_canonical_keyed_point_projection() -> None:
    annotation_type, annotation_value = resolve_overlay_annotation(
        annotation_type="point_map",
        annotation_value={"A": [0, 0]},
        trace_payload={"projected_annotation": {"pixel_point_map": {"A": [40.0, 50.0]}}},
    )
    assert annotation_type == "point_map"
    assert annotation_value == {"A": [40.0, 50.0]}


def test_resolve_overlay_annotation_uses_canonical_keyed_point_set_projection() -> None:
    annotation_type, annotation_value = resolve_overlay_annotation(
        annotation_type="point_set_map",
        annotation_value={"A": [[0, 0]]},
        trace_payload={"projected_annotation": {"pixel_point_set_map": {"A": [[40.0, 50.0], [60.0, 70.0]]}}},
    )
    assert annotation_type == "point_set_map"
    assert annotation_value == {"A": [[40.0, 50.0], [60.0, 70.0]]}


def test_resolve_overlay_annotation_uses_canonical_keyed_bbox_projection() -> None:
    annotation_type, annotation_value = resolve_overlay_annotation(
        annotation_type="bbox_map",
        annotation_value={},
        trace_payload={"projected_annotation": {"bbox_map": {"A": [10.0, 20.0, 30.0, 40.0]}}},
    )
    assert annotation_type == "bbox_map"
    assert annotation_value == {"A": [10.0, 20.0, 30.0, 40.0]}


def test_resolve_overlay_annotation_uses_canonical_keyed_bbox_set_projection() -> None:
    annotation_type, annotation_value = resolve_overlay_annotation(
        annotation_type="bbox_set_map",
        annotation_value={},
        trace_payload={"projected_annotation": {"pixel_bbox_set_map": {"A": [[10.0, 20.0, 30.0, 40.0]]}}},
    )
    assert annotation_type == "bbox_set_map"
    assert annotation_value == {"A": [[10.0, 20.0, 30.0, 40.0]]}


def test_resolve_overlay_annotation_prefers_scalar_pixel_point() -> None:
    annotation_type, annotation_value = resolve_overlay_annotation(
        annotation_type="point",
        annotation_value=[1, 2],
        trace_payload={
            "projected_annotation": {
                "type": "point",
                "point": [3, 4],
                "pixel_point": [5, 6],
            }
        },
    )

    assert annotation_type == "point"
    assert annotation_value == [5, 6]


def test_resolve_overlay_annotation_prefers_scalar_pixel_bbox() -> None:
    annotation_type, annotation_value = resolve_overlay_annotation(
        annotation_type="bbox",
        annotation_value=[1, 2, 3, 4],
        trace_payload={
            "projected_annotation": {
                "type": "bbox",
                "bbox": [3, 4, 5, 6],
                "pixel_bbox": [7, 8, 9, 10],
            }
        },
    )

    assert annotation_type == "bbox"
    assert annotation_value == [7, 8, 9, 10]


def test_render_annotation_overlay_draws_visible_x_marker_for_points() -> None:
    source = PILImage.new("RGB", (100, 100), color=(255, 255, 255))
    overlay = render_annotation_overlay(source, annotation_type="point_set", annotation_value=[[50, 50]])
    assert overlay.getpixel((50, 50)) != (255, 255, 255)
    assert overlay.getpixel((56, 56)) != (255, 255, 255)
    assert overlay.getpixel((44, 56)) != (255, 255, 255)


def test_render_annotation_overlay_draws_visible_segments() -> None:
    source = PILImage.new("RGB", (100, 100), color=(255, 255, 255))
    overlay = render_annotation_overlay(
        source,
        annotation_type="segment_set",
        annotation_value=[
            [[10, 10], [90, 10]],
            [[10, 30], [90, 70]],
        ],
    )
    assert overlay.getpixel((50, 10)) != (255, 255, 255)
    assert overlay.getpixel((50, 50)) != (255, 255, 255)


def test_render_annotation_overlay_draws_visible_scalar_segment() -> None:
    source = PILImage.new("RGB", (100, 100), color=(255, 255, 255))
    overlay = render_annotation_overlay(
        source,
        annotation_type="segment",
        annotation_value=[[10, 10], [90, 10]],
    )
    assert overlay.getpixel((50, 10)) != (255, 255, 255)


def test_render_annotation_overlay_draws_all_bbox_set_members_with_shadow() -> None:
    source = PILImage.new("RGB", (120, 80), color=(66, 133, 244))
    overlay = render_annotation_overlay(
        source,
        annotation_type="bbox_set",
        annotation_value=[
            [10, 10, 40, 40],
            [70, 10, 100, 40],
        ],
    )

    assert overlay.getpixel((10, 10)) != (66, 133, 244)
    assert overlay.getpixel((70, 10)) != (66, 133, 244)
    assert overlay.getpixel((14, 14)) != (66, 133, 244)
    assert overlay.getpixel((74, 14)) != (66, 133, 244)


def test_render_annotation_overlay_draws_keyed_maps() -> None:
    source = PILImage.new("RGB", (120, 100), color=(255, 255, 255))
    point_overlay = render_annotation_overlay(
        source,
        annotation_type="point_map",
        annotation_value={"A": [50, 50]},
    )
    bbox_overlay = render_annotation_overlay(
        source,
        annotation_type="bbox_map",
        annotation_value={"B": [10, 10, 40, 40]},
    )

    assert point_overlay.getpixel((50, 50)) != (255, 255, 255)
    assert bbox_overlay.getpixel((10, 10)) != (255, 255, 255)


def test_render_annotation_overlay_draws_keyed_set_maps() -> None:
    source = PILImage.new("RGB", (140, 120), color=(255, 255, 255))
    point_overlay = render_annotation_overlay(
        source,
        annotation_type="point_set_map",
        annotation_value={"A": [[50, 50], [70, 50]]},
    )
    bbox_overlay = render_annotation_overlay(
        source,
        annotation_type="bbox_set_map",
        annotation_value={"B": [[10, 10, 40, 40], [70, 10, 100, 40]]},
    )

    assert point_overlay.getpixel((50, 50)) != (255, 255, 255)
    assert point_overlay.getpixel((70, 50)) != (255, 255, 255)
    assert bbox_overlay.getpixel((10, 10)) != (255, 255, 255)
    assert bbox_overlay.getpixel((70, 10)) != (255, 255, 255)
