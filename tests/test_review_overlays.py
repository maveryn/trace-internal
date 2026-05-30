"""Unit tests for shared review/sample evidence overlay helpers."""

from __future__ import annotations

from PIL import Image as PILImage

from trace.core.review_overlays import render_evidence_overlay, resolve_overlay_evidence


def test_resolve_overlay_evidence_uses_canonical_point_projection() -> None:
    evidence_type, evidence_value = resolve_overlay_evidence(
        evidence_type="point_set",
        evidence_value=[[0, 0], [1, 1], [2, 2]],
        trace_payload={"projected_evidence": {"pixel_point_set": [[40.0, 50.0], [60.0, 70.0], [80.0, 90.0]]}},
    )
    assert evidence_type == "point_set"
    assert evidence_value == [[40.0, 50.0], [60.0, 70.0], [80.0, 90.0]]


def test_resolve_overlay_evidence_uses_canonical_point_sequence_projection() -> None:
    evidence_type, evidence_value = resolve_overlay_evidence(
        evidence_type="point_sequence",
        evidence_value=[[0, 0], [1, 1], [2, 2]],
        trace_payload={"projected_evidence": {"pixel_point_sequence": [[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]]}},
    )
    assert evidence_type == "point_sequence"
    assert evidence_value == [[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]]


def test_resolve_overlay_evidence_uses_canonical_bbox_projection() -> None:
    evidence_type, evidence_value = resolve_overlay_evidence(
        evidence_type="bbox_set",
        evidence_value=[],
        trace_payload={
            "projected_evidence": {
                "bbox_set": [[10.0, 20.0, 30.0, 40.0], [50.0, 60.0, 70.0, 80.0]],
            }
        },
    )
    assert evidence_type == "bbox_set"
    assert evidence_value == [[10.0, 20.0, 30.0, 40.0], [50.0, 60.0, 70.0, 80.0]]


def test_resolve_overlay_evidence_uses_canonical_point_pair_projection() -> None:
    evidence_type, evidence_value = resolve_overlay_evidence(
        evidence_type="point_pair_set",
        evidence_value=[],
        trace_payload={
            "projected_evidence": {
                "point_pair_set": [
                    [[10.0, 20.0], [30.0, 40.0]],
                    [[50.0, 60.0], [70.0, 80.0]],
                ],
            }
        },
    )
    assert evidence_type == "point_pair_set"
    assert evidence_value == [
        [[10.0, 20.0], [30.0, 40.0]],
        [[50.0, 60.0], [70.0, 80.0]],
    ]


def test_resolve_overlay_evidence_uses_canonical_keyed_point_projection() -> None:
    evidence_type, evidence_value = resolve_overlay_evidence(
        evidence_type="keyed_point_map",
        evidence_value={"A": [0, 0]},
        trace_payload={"projected_evidence": {"pixel_keyed_point_map": {"A": [40.0, 50.0]}}},
    )
    assert evidence_type == "keyed_point_map"
    assert evidence_value == {"A": [40.0, 50.0]}


def test_resolve_overlay_evidence_uses_canonical_keyed_bbox_projection() -> None:
    evidence_type, evidence_value = resolve_overlay_evidence(
        evidence_type="keyed_bbox_map",
        evidence_value={},
        trace_payload={"projected_evidence": {"keyed_bbox_map": {"A": [10.0, 20.0, 30.0, 40.0]}}},
    )
    assert evidence_type == "keyed_bbox_map"
    assert evidence_value == {"A": [10.0, 20.0, 30.0, 40.0]}


def test_render_evidence_overlay_draws_visible_x_marker_for_points() -> None:
    source = PILImage.new("RGB", (100, 100), color=(255, 255, 255))
    overlay = render_evidence_overlay(source, evidence_type="point_set", evidence_value=[[50, 50]])
    assert overlay.getpixel((50, 50)) != (255, 255, 255)
    assert overlay.getpixel((56, 56)) != (255, 255, 255)
    assert overlay.getpixel((44, 56)) != (255, 255, 255)


def test_render_evidence_overlay_draws_visible_point_pair_segments() -> None:
    source = PILImage.new("RGB", (100, 100), color=(255, 255, 255))
    overlay = render_evidence_overlay(
        source,
        evidence_type="point_pair_set",
        evidence_value=[
            [[10, 10], [90, 10]],
            [[10, 30], [90, 70]],
        ],
    )
    assert overlay.getpixel((50, 10)) != (255, 255, 255)
    assert overlay.getpixel((50, 50)) != (255, 255, 255)


def test_render_evidence_overlay_draws_all_bbox_set_members_with_shadow() -> None:
    source = PILImage.new("RGB", (120, 80), color=(66, 133, 244))
    overlay = render_evidence_overlay(
        source,
        evidence_type="bbox_set",
        evidence_value=[
            [10, 10, 40, 40],
            [70, 10, 100, 40],
        ],
    )

    assert overlay.getpixel((10, 10)) != (66, 133, 244)
    assert overlay.getpixel((70, 10)) != (66, 133, 244)
    assert overlay.getpixel((14, 14)) != (66, 133, 244)
    assert overlay.getpixel((74, 14)) != (66, 133, 244)


def test_render_evidence_overlay_draws_keyed_maps() -> None:
    source = PILImage.new("RGB", (120, 100), color=(255, 255, 255))
    point_overlay = render_evidence_overlay(
        source,
        evidence_type="keyed_point_map",
        evidence_value={"A": [50, 50]},
    )
    bbox_overlay = render_evidence_overlay(
        source,
        evidence_type="keyed_bbox_map",
        evidence_value={"B": [10, 10, 40, 40]},
    )

    assert point_overlay.getpixel((50, 50)) != (255, 255, 255)
    assert bbox_overlay.getpixel((10, 10)) != (255, 255, 255)
